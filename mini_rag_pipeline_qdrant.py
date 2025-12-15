# Yksinkertainen RAG-putki: indeksoi -> hae (MMR + rerank + dedupe) -> rakenna vastausprompt
from typing import List, Dict, Tuple, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer, CrossEncoder
from utils.metrics_relevance import eval_query, recall_at_k, ndcg_at_k
from utils.latency_utils import measure_latency
from utils.groundedness_proxy import groundedness_proxy
import numpy as np
import uuid
import sys
from mistralai import Mistral
from dotenv import load_dotenv
import os

COLLECTION = "demo_docs"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# Kytkimet
RESET = False             # True -> nollaa kokoelman kerran ennen luontia
DEDUPE_BY_SOURCE = False  # True -> max 1 katkelma per lähde (polku/x)

# 1) Demodokumentit
DOCS = [
    {"id": "polku/1", "title": "Qdrant pähkinänkuoressa",
     "text": "Qdrant on vektoritietokanta, joka tukee HNSW-indeksointia, metadatafilttereitä ja reaaliaikaisia päivityksiä."},
    {"id": "polku/2", "title": "RAG-perusteet",
     "text": "RAG yhdistää haun ja generoinnin: dokumentit pilkotaan, indeksoidaan vektorimuotoon ja haetaan semanttisesti."},
    {"id": "polku/3", "title": "Embeddings lyhyesti",
     "text": "Upotteet (embeddings) kuvaavat tekstin merkityssisältöä, mahdollistaen samankaltaisuushakuja kosinietäisyydellä."},
]

# ---------- Apurit ----------

def chunk(text: str, max_len: int = 256) -> List[str]:
    s = [p.strip() for p in text.replace("\n", " ").split(".") if p.strip()]
    chunks, buf = [], ""
    for sent in s:
        if len(buf) + len(sent) + 1 <= max_len:
            buf = f"{buf} {sent}".strip()
        else:
            if buf:
                chunks.append(buf)
            buf = sent
    if buf:
        chunks.append(buf)
    return chunks

def build_corpus(docs: List[Dict]) -> List[Dict]:
    corpus = []
    for d in docs:
        for i, ch in enumerate(chunk(d["text"])):
            corpus.append({
                "uid": f"{d['id']}#{i}",   # deterministinen inhimillinen tunniste
                "title": d["title"],
                "text": ch,
                "source": d["id"]
            })
    return corpus

def ensure_collection(client: QdrantClient, dim: int):
    # Kerran nollaus: aseta RESET=True ja aja; palaa False:ksi seuraavilla ajoilla
    if RESET and client.collection_exists(COLLECTION):
        client.delete_collection(COLLECTION)
    if not client.collection_exists(COLLECTION):
        client.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )

def index(client: QdrantClient, model: SentenceTransformer, corpus: List[Dict]):
    vectors = model.encode([c["text"] for c in corpus], normalize_embeddings=True).tolist()
    points = []
    for v, c in zip(vectors, corpus):
        pid = uuid.uuid5(uuid.NAMESPACE_URL, c["uid"])  # sama uid -> sama UUID
        points.append(
            PointStruct(
                id=str(pid),
                vector=v,
                payload={"uid": c["uid"], "title": c["title"], "text": c["text"], "source": c["source"]},
            )
        )
    client.upsert(collection_name=COLLECTION, points=points)

def _nz_norm(x: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(x)
    return x / (n + 1e-12)

def _dedupe_by_uid(items: List[Dict]) -> List[Dict]:
    """Poista duplikaatit uidin perusteella; fallbackina (source, text)."""
    unique, seen = [], set()
    for it in items:
        key = it.get("uid") or (it.get("source", ""), it.get("text", ""))
        if key in seen:
            continue
        seen.add(key)
        unique.append(it)
    return unique

def _dedupe_by_source(items: List[Dict]) -> List[Dict]:
    """Pidä korkeintaan 1 katkelma per lähde (polku/x)."""
    unique, seen = [], set()
    for it in items:
        src = it.get("source")
        if src in seen:
            continue
        seen.add(src)
        unique.append(it)
    return unique

# ---------- MMR + RERANK ----------

def mmr_select(query_vec: np.ndarray, doc_vecs: List[np.ndarray], top_n: int, diversity: float = 0.35) -> List[int]:
    """
    Maximal Marginal Relevance.
    Palauttaa indeksit valituista dokumenteista listasta doc_vecs.
    diversity \in [0,1]: 0 = vain relevanssi, 1 = maksimaalinen erilaisuus.
    """
    if not doc_vecs:
        return []
    q = _nz_norm(query_vec.astype(np.float32))
    dv = [_nz_norm(v.astype(np.float32)) for v in doc_vecs]

    sims_to_q = [float(np.dot(q, v)) for v in dv]
    selected = [int(np.argmax(sims_to_q))]
    candidates = [i for i in range(len(dv)) if i != selected[0]]

    while len(selected) < min(top_n, len(dv)) and candidates:
        best, best_val = None, -1e-9
        for c in candidates:
            relevance = sims_to_q[c]
            diversity_penalty = max(float(np.dot(dv[c], dv[s])) for s in selected)
            score = (1 - diversity) * relevance - diversity * diversity_penalty
            if score > best_val:
                best, best_val = c, score
        selected.append(best)
        candidates.remove(best)
    return selected

def crossencode_rerank(cross_encoder: CrossEncoder, query: str, items: List[Dict], top_k: int) -> List[Dict]:
    pairs = [(query, it["text"]) for it in items]
    scores = cross_encoder.predict(pairs).tolist()
    for it, sc in zip(items, scores):
        it["rerank_score"] = float(sc)
    items.sort(key=lambda x: x["rerank_score"], reverse=True)
    return items[:top_k]

def search(
    client: QdrantClient,
    model: SentenceTransformer,
    query: str,
    top_k: int = 4,
    initial_limit: int = 30,   # enemmän kandidaatteja MMR:lle
    diversity: float = 0.35,   # maltillinen
    score_threshold: float = 0.25,
    cross_encoder: Optional[CrossEncoder] = None,
) -> List[Dict]:
    # 1) Ensihaku Qdrantista (pyydä vektorit & payloadit takaisin)
    q_vec = model.encode([query], normalize_embeddings=True)[0]
    hits = client.search(
        collection_name=COLLECTION,
        query_vector=q_vec.tolist(),
        limit=initial_limit,
        with_vectors=True,
        with_payload=True,
    )

    # Suodata heikot osumat (vector-score)
    prelim = [h for h in hits if (h.score is None or h.score >= score_threshold)]
    if not prelim:
        return []  # -> ei kontekstia; main() ei kutsu LLM:ää

    # 2) Kerää vektorit ja aja MMR
    prelim_with_vecs: List[Tuple[np.ndarray, object]] = []
    for h in prelim:
        if getattr(h, "vector", None) is not None:
            prelim_with_vecs.append((np.array(h.vector, dtype=np.float32), h))
    if not prelim_with_vecs:
        return []

    idxs = mmr_select(np.array(q_vec), [v for v, _ in prelim_with_vecs],
                      top_n=min(top_k * 2, len(prelim_with_vecs)), diversity=diversity)
    mmr_hits = [prelim_with_vecs[i][1] for i in idxs]

    # 3) Muodosta dictit (sis. uid)
    mmr_items = [{
        "uid": h.payload.get("uid"),
        "score": round(h.score, 3) if h.score is not None else None,
        "title": h.payload.get("title"),
        "text": h.payload.get("text"),
        "source": h.payload.get("source"),
    } for h in mmr_hits]

    # 4) Rerank (valinnainen)
    if cross_encoder is not None and len(mmr_items) > 1:
        mmr_items = crossencode_rerank(cross_encoder, query, mmr_items, top_k=max(top_k, 2))

    # 5) Deduplikointi
    if DEDUPE_BY_SOURCE:
        unique = _dedupe_by_source(mmr_items)
    else:
        unique = _dedupe_by_uid(mmr_items)

    return unique[:top_k]

# ---------- Prompt ----------

def format_contexts(contexts: List[Dict]) -> str:
    if not contexts:
        return ""
    lines = []
    for c in contexts:
        src = c.get("source", "tuntematon")
        title = c.get("title", "—")
        score = c.get("score")
        score_s = f"{score:.3f}" if isinstance(score, (int, float)) else "—"
        text = c.get("text", "")
        lines.append(f"[lähde: {src}] {title} (osuma: {score_s})\n{text}")
    return "\n\n---\n\n".join(lines)

def build_prompt(question: str, contexts: List[Dict]) -> str:
    ctx = format_contexts(contexts)
    return f"""Vastaa suomeksi käyttäen termiä "vektoritietokanta".
Hyödynnä VAIN alla olevaa kontekstia. Jos konteksti puuttuu, vastaa täsmälleen: "en tiedä" ja pyydä lisää lähteitä.
Älä lisää ulkopuolisia linkkejä. Vältä toistoa ja tautologioita (esim. "hakuun perustuva haku"); vältä anglismeja ("embed") ja käytä "upote"/"upottaa".

KYSYMYS:
{question}

KONTEKSTI:
{ctx}

OHJEET VASTAUKSEEN:
- Anna 3–4 napakkaa bullet-kohtaa (ei pitkiä kappaleita) vain jos kontekstia on.
- Käsittele mieluiten: semanttinen haku, HNSW/nopeus, metadatafiltterit, reaaliaikaiset päivitykset.
- Pysy kontekstissa; älä keksi uutta.
- **Lopeta aina otsikolla 'Lähteet:' ja listaa käytetyt polut muodossa [lähde: POLKU].**
"""

# ---------- Main ----------

def main():
    # Mallit
    model = SentenceTransformer(EMBED_MODEL)
    cross_encoder = CrossEncoder(RERANK_MODEL)  # kevyt rerankkeri
    client = QdrantClient(url="http://localhost:6333")

    # Rakennus & indeksointi
    corpus = build_corpus(DOCS)
    ensure_collection(client, dim=model.get_sentence_embedding_dimension())
    index(client, model, corpus)

    # Haku (MMR + rerank + dedupe)
    question = "Miksi vektoritietokanta on hyödyllinen RAG-järjestelmässä?"
    results = search(
        client, model, question,
        top_k=4, initial_limit=30, diversity=0.35,
        score_threshold=0.25, cross_encoder=cross_encoder
    )

    print("== Haun osumat (MMR + rerank + dedupe) ==")
    if not results:
        print("Ei riittäviä osumia (score < threshold). LLM:ää ei kutsuta.")
        print("\n== LLM-vastaus ==\n")
        print("en tiedä. Tarvitsen lisää lähteitä.")
        return
    else:
        for r in results:
            rr = r.get("rerank_score")
            rr_s = f", rerank={rr:.3f}" if rr is not None else ""
            uid_s = f", uid={r.get('uid')}" if r.get("uid") else ""
            print(f"{r['score']}{rr_s}: {r['title']} [{r['source']}] -> {r['text'][:120]}...{uid_s}")

    # == (A) Relevanssi: recall@k ja nDCG@k tälle kysymykselle ==
    gold = {d["id"] for d in DOCS}  # demossa kaikki polku/1..3 ovat “gold”
    k = len(results)

    # eval_query tarvitsee hakufunktion signatuurilla (query, top_k) -> list[dict]
    def search_fn(q, top_k):
        return search(client, model, q,
                      top_k=top_k, initial_limit=50, diversity=0.35,
                      score_threshold=0.0, cross_encoder=None)

    rel_metrics = eval_query(search_fn, question, gold, k=k)
    print("\n== Mittarit (relevanssi) ==")
    print(rel_metrics)  # sisältää preds, recall@k, ndcg@k

    # == (B) Latenssi: p50/p95/p99 pelkälle haulle (raaka nopeus, ilman rerankkausta) ==
    def run_once():
        _ = search_fn(question, top_k=4)

    lat = measure_latency(run_once, runs=20, warmup=3)
    print("\n== Latenssi (haku) ==")
    print(f"p50: {lat['p50_ms']:.1f} ms | p95: {lat['p95_ms']:.1f} ms | p99: {lat['p99_ms']:.1f} ms")

    # Prompt + LLM
    prompt = build_prompt(question, results)
    print("\n== Generointiprompt (syötä LLM:lle) ==\n")
    print(prompt)

    load_dotenv()
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        sys.exit("Missing MISTRAL_API_KEY environment variable. Please set it first.")

    with Mistral(api_key=api_key) as client_llm:
        resp = client_llm.chat.complete(
            model="open-mistral-nemo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,   # tiukempi kieli, vähemmän jaarittelua
            max_tokens=500,    # ↑ vähentää kesken katkeamista
        )

    print("\n== LLM-vastaus ==\n")
    out = resp.choices[0].message.content

    # Varmuuskatkaisin: lisää Lähteet:, jos malli unohti
    if "Lähteet:" not in out:
        used_sources = [r["source"] for r in results if r.get("source")]
        # säilytä alkuperäinen järjestys ilman duplikaatteja
        seen, ordered = set(), []
        for s in used_sources:
            if s not in seen:
                seen.add(s)
                ordered.append(s)
        src_block = "\n".join(f"- [lähde: {s}]" for s in ordered)
        out = out.rstrip() + "\n\nLähteet:\n" + src_block

    # (valinnainen pikasiivous yleisimmille sanamuodoille)
    out = out.replace("hakuun perustuva haku", "semanttinen haku")

    print(out)

    # == (C) Groundedness-proxy: löytyykö "Lähteet"-osio ja mainitaanko käytetyt lähteet ==
    used_sources = [r["source"] for r in results if r.get("source")]
    g = groundedness_proxy(out, used_sources)
    print("\n== Groundedness (proxy) ==")
    print(g)


if __name__ == "__main__":
    main()

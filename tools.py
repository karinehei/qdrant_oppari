#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mini_rag_qdrant.py
------------------
Pieni, käytännöllinen RAG-putki Qdrantilla. Sisältää:
- Kokoelman luonti ja HNSW-viritys (m, ef_construct, efSearch)
- Chunkkaus ja upotteiden laskenta (SentenceTransformers)
- Indeksointi Qdrantiin payload/metadata-kentillä (tenant_id, doc_type, domain)
- Semanttinen haku + ACL-filtterit
- (Valinnainen) CrossEncoder-rerankkaus
- (Valinnainen) Kevyt hybridi (vektori + BM25)
- Snapshot-esimerkki (backup)
- Promptin rakentaja lähdeviitteillä

Käyttöesimerkkejä:
    # 1) Käynnistä Qdrant (Docker)
    # docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant:latest

    # 2) Asenna riippuvuudet
    # pip install qdrant-client sentence-transformers rank_bm25

    # 3) Aja indeksointi ja tee haku
    # python mini_rag_qdrant.py --index --search "Miksi vektoridatabase on hyödyllinen RAG:ssa?" --print-prompt

    # 4) Hybridi ja rerankkaus
    # pip install sentence-transformers  # (jo asennettu) + CrossEncoder käyttää samaa pakettia
    # python mini_rag_qdrant.py --index --search "..." --topk 8 --rerank --hybrid --print-prompt

    # 5) Snapshot
    # python mini_rag_qdrant.py --snapshot

Huom: Tämä on demo. Tuotannossa lisää virheenkäsittelyä, lokitusta ja tehokkaampaa korpuksen hallintaa.
"""
from __future__ import annotations

from typing import List, Dict, Optional, Any
from dataclasses import dataclass
import argparse
import uuid
import sys

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, SearchParams,
    Filter, FieldCondition, MatchValue, HnswConfigDiff
)

try:
    from sentence_transformers import SentenceTransformer
    HAS_ST = True
except Exception as e:
    HAS_ST = False
    SentenceTransformer = None  # type: ignore

# Reranker (valinnainen)
try:
    from sentence_transformers import CrossEncoder
    HAS_CE = True
except Exception:
    HAS_CE = False
    CrossEncoder = None  # type: ignore

# BM25 (valinnainen)
try:
    from rank_bm25 import BM25Okapi
    HAS_BM25 = True
except Exception:
    HAS_BM25 = False
    BM25Okapi = None  # type: ignore


# ------------------------
# Konfiguraatio
# ------------------------
COLLECTION = "demo_docs"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


# ------------------------
# Esimerkkidokumentit
# ------------------------
DOCS: List[Dict[str, str]] = [
    {"id": "polku/1", "title": "Qdrant pähkinänkuoressa",
     "text": "Qdrant on vektoridatabäsi, joka tukee HNSW-indeksointia, metadatafilttereitä ja reaaliaikaisia päivityksiä."},
    {"id": "polku/2", "title": "RAG-perusteet",
     "text": "RAG yhdistää haun ja generoinnin: dokumentit pilkotaan, indeksoidaan vektorimuotoon ja haetaan semanttisesti."},
    {"id": "polku/3", "title": "Embeddings lyhyesti",
     "text": "Upotteet (embeddings) kuvaavat tekstin merkityssisältöä, mahdollistaen samankaltaisuushakuja kosinietäisyydellä."},
]


# ------------------------
# Aputoiminnot
# ------------------------
def chunk(text: str, max_len: int = 256) -> List[str]:
    """Hyvin yksinkertainen chunkkaus lausejakajalla."""
    s = [p.strip() for p in text.replace("\n", " ").split(".") if p.strip()]
    chunks, buf = [], ""
    for sent in s:
        if len(buf) + len(sent) + 1 <= max_len:
            buf = f"{buf} {sent}".strip()
        else:
            if buf: chunks.append(buf)
            buf = sent
    if buf: chunks.append(buf)
    return chunks


def build_corpus(docs: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Luo korpus ja lisää metadataa (tenant_id, doc_type, domain)."""
    corpus: List[Dict[str, str]] = []
    for d in docs:
        for i, ch in enumerate(chunk(d["text"])):
            corpus.append({
                "uid": f"{d['id']}#{i}",
                "title": d["title"],
                "text": ch,
                "source": d["id"],
                "domain": "demo",
                "tenant_id": "acme",        # ACL-esimerkki
                "doc_type": "knowledge"     # tyypittely
            })
    return corpus


def ensure_collection(client: QdrantClient, dim: int) -> None:
    """Luo kokoelma HNSW:llä jos puuttuu (COSINE-etäisyys)."""
    exists = client.collection_exists(COLLECTION)
    if not exists:
        client.recreate_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def tune_hnsw(client: QdrantClient, m: int = 16, ef_construct: int = 256, full_scan_threshold: int = 10_000) -> None:
    """HNSW-viritys paremman recallin saavuttamiseksi."""
    client.update_collection(
        collection_name=COLLECTION,
        hnsw_config=HnswConfigDiff(
            m=m,
            ef_construct=ef_construct,
            full_scan_threshold=full_scan_threshold
        )
    )


def index_points(client: QdrantClient, model: SentenceTransformer, corpus: List[Dict[str, str]]) -> None:
    vectors = model.encode([c["text"] for c in corpus], normalize_embeddings=True).tolist()
    points = []
    for v, c in zip(vectors, corpus):
        points.append(
            PointStruct(
                id=str(uuid.uuid4()),
                vector=v,
                payload={
                    "title": c["title"],
                    "text": c["text"],
                    "source": c["source"],
                    "domain": c["domain"],
                    "tenant_id": c["tenant_id"],
                    "doc_type": c["doc_type"],
                }
            )
        )
    client.upsert(collection_name=COLLECTION, points=points)


def semantic_search(
        client: QdrantClient,
        model: SentenceTransformer,
        query: str,
        top_k: int = 4,
        hnsw_ef: int = 256,
        tenant: Optional[str] = None,
        doc_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Semanttinen haku, jossa voi käyttää ACL-tyyppisiä filttereitä."""
    q_vec = model.encode([query], normalize_embeddings=True).tolist()[0]
    q_filter: Optional[Filter] = None
    must = []
    if tenant:
        must.append(FieldCondition(key="tenant_id", match=MatchValue(value=tenant)))
    if doc_type:
        must.append(FieldCondition(key="doc_type", match=MatchValue(value=doc_type)))
    if must:
        q_filter = Filter(must=must)

    hits = client.search(
        collection_name=COLLECTION,
        query_vector=q_vec,
        limit=top_k,
        search_params=SearchParams(hnsw_ef=hnsw_ef),
        query_filter=q_filter
    )
    return [{
        "score": float(h.score),
        "title": h.payload.get("title"),
        "text": h.payload.get("text"),
        "source": h.payload.get("source"),
    } for h in hits]


def ensure_bm25(corpus: List[Dict[str, str]]):
    """Valmistele BM25 pienelle demokorpukselle."""
    if not HAS_BM25:
        raise RuntimeError("rank_bm25 ei ole asennettu. Asenna: pip install rank_bm25")
    return BM25Okapi([c["text"].split() for c in corpus]), [c["text"] for c in corpus]


def hybrid_search(
        client: QdrantClient,
        model: SentenceTransformer,
        bm25: BM25Okapi,
        bm25_texts: List[str],
        question: str,
        vec_top_k: int = 20,
        final_k: int = 5,
        alpha: float = 0.6,
) -> List[Dict[str, Any]]:
    """Kevyt hybridi: yhdistää vektori- ja BM25-pisteet (painotettu summa)."""
    q_vec = model.encode([question], normalize_embeddings=True).tolist()[0]
    vec_hits = client.search(
        collection_name=COLLECTION,
        query_vector=q_vec,
        limit=vec_top_k,
        search_params=SearchParams(hnsw_ef=256),
    )
    if not vec_hits:
        return []

    bm25_scores = bm25.get_scores(question.split())

    # Yhdistä pisteet (min-max-normalisointi + painotettu summa)
    results = []
    for h in vec_hits:
        text = h.payload["text"]
        try:
            idx = bm25_texts.index(text)  # demo: O(n), ok pienelle datalle
        except ValueError:
            idx = -1
        v = float(h.score)
        b = float(bm25_scores[idx]) if idx >= 0 else 0.0
        results.append({"text": text, "title": h.payload["title"], "source": h.payload["source"],
                        "vec": v, "bm25": b})

    vmin, vmax = min(r["vec"] for r in results), max(r["vec"] for r in results)
    bmin, bmax = min(r["bm25"] for r in results), max(r["bm25"] for r in results)
    for r in results:
        r["vec_n"]  = 0 if vmax == vmin else (r["vec"]  - vmin)/(vmax - vmin)
        r["bm25_n"] = 0 if bmax == bmin else (r["bm25"] - bmin)/(bmax - bmin)
        r["hybrid"] = alpha*r["vec_n"] + (1 - alpha)*r["bm25_n"]

    results.sort(key=lambda x: x["hybrid"], reverse=True)
    return results[:final_k]


def ensure_reranker():
    """Luo CrossEncoder-rerankkerin (valinnainen)."""
    if not HAS_CE:
        raise RuntimeError("CrossEncoder ei ole käytettävissä. Asenna: pip install sentence-transformers")
    return CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank(question: str, results: List[Dict[str, Any]], reranker) -> List[Dict[str, Any]]:
    pairs = [(question, r["text"]) for r in results]
    scores = reranker.predict(pairs)
    for s, r in zip(scores, results):
        r["rerank"] = float(s)
    return sorted(results, key=lambda x: x["rerank"], reverse=True)


def build_prompt_with_refs(question: str, contexts: List[Dict[str, Any]]) -> str:
    lines = []
    for i, c in enumerate(contexts, 1):
        lines.append(f"[{i}] {c.get('title')} — {c.get('text')}")
    ctx = "\n\n---\n\n".join(lines)
    return f"""Vastaa kysymykseen käyttäen VAIN alla olevaa kontekstia. 
Jos vastaus ei löydy, sano 'en tiedä' ja pyydä lisää lähteitä. 
Viittaa lähteisiin [1], [2], ... vastausta kirjoittaessasi.

KYSYMYS:
{question}

KONTEKSTI:
{ctx}
"""


def create_snapshot(client: QdrantClient) -> Any:
    """Luo kokoelman snapshotin (tiedosto Qdrantin storageen)."""
    return client.create_snapshot(collection_name=COLLECTION)


# ------------------------
# CLI
# ------------------------
def parse_args():
    ap = argparse.ArgumentParser(description="Mini RAG Qdrant — end-to-end demo")
    ap.add_argument("--host", default="http://localhost", help="Qdrant host (oletus: http://localhost)")
    ap.add_argument("--port", type=int, default=6333, help="Qdrant port (oletus: 6333)")
    ap.add_argument("--index", action="store_true", help="Indeksoi demodokumentit kokoelmaan")
    ap.add_argument("--search", type=str, default=None, help="Suorita haku annetulla kysymyksellä")
    ap.add_argument("--topk", type=int, default=3, help="Top-K tulosten määrä (oletus: 3)")
    ap.add_argument("--hnsw_ef", type=int, default=256, help="Hakuvaiheen hnsw_ef (oletus: 256)")
    ap.add_argument("--tenant", type=str, default="acme", help="ACL: tenant_id suodatus (oletus: acme)")
    ap.add_argument("--doc_type", type=str, default="knowledge", help="ACL: doc_type suodatus (oletus: knowledge)")
    ap.add_argument("--rerank", action="store_true", help="Käytä CrossEncoder-rerankkausta")
    ap.add_argument("--hybrid", action="store_true", help="Käytä kevyttä hybridiä (vektori + BM25)")
    ap.add_argument("--snapshot", action="store_true", help="Luo kokoelman snapshot")
    ap.add_argument("--print-prompt", action="store_true", help="Tulosta rakennettu promptti")
    return ap.parse_args()


def main():
    args = parse_args()

    if not HAS_ST:
        print("sentence-transformers puuttuu. Asenna: pip install sentence-transformers", file=sys.stderr)
        sys.exit(1)

    # Malli ja Qdrant
    model = SentenceTransformer(EMBED_MODEL)
    client = QdrantClient(url=f"{args.host}:{args.port}")

    # Kokoelma + HNSW
    ensure_collection(client, dim=model.get_sentence_embedding_dimension())
    tune_hnsw(client)  # perusviritys

    # Rakenna korpus
    corpus = build_corpus(DOCS)

    # Indeksoi
    if args.index:
        index_points(client, model, corpus)
        print(f"Indeksoitu pisteitä: {len(corpus)}")

    # Snapshot
    if args.snapshot:
        snap = create_snapshot(client)
        print("Snapshot luotu:", snap)

    # Haku
    if args.search:
        question = args.search
        results: List[Dict[str, Any]]

        if args.hybrid:
            if not HAS_BM25:
                print("Hybridi vaatii rank_bm25-kirjaston. Asenna: pip install rank_bm25", file=sys.stderr)
                sys.exit(2)
            bm25, bm25_texts = ensure_bm25(corpus)
            results = hybrid_search(client, model, bm25, bm25_texts, question, vec_top_k=max(10, args.topk*3), final_k=args.topk)
        else:
            results = semantic_search(
                client, model, question, top_k=args.topk,
                hnsw_ef=args.hnsw_ef, tenant=args.tenant, doc_type=args.doc_type
            )

        # Rerankkaus
        if args.rerank:
            try:
                rr = ensure_reranker()
                results = rerank(question, results, rr)
                results = results[:args.topk]
            except Exception as e:
                print(f"Rerankkeria ei voitu käyttää: {e}", file=sys.stderr)

        print("== Haun osumat ==")
        for r in results:
            # tulosta pisteet ensisijaisessa järjestyskentässä
            score_key = "hybrid" if "hybrid" in r else ("rerank" if "rerank" in r else "score")
            score_val = r.get(score_key, r.get("score", 0.0))
            print(f"{score_val:.3f}: {r['title']} [{r['source']}] -> {r['text'][:120]}...")

        if args.print_prompt:
            prompt = build_prompt_with_refs(question, results)
            print("\n== Generointiprompt (syötä LLM:lle) ==\n")
            print(prompt)


if __name__ == "__main__":
    main()

# Qdrant RAG – Opinnäytetyön tutkimusprototyyppi

Qdrant-pohjainen RAG-tutkimusprototyyppi retrieval-ablaatioiden arviointiin suomenkielisellä aineistolla (Theseus-opinnäytteet).

## 📋 Sisällysluettelo

- [Projektikuvaus](#projektikuvaus)
- [Tutkimusputki](#tutkimusputki)
- [Projektirakenne](#projektirakenne)
- [Data Preparation](#data-preparation)
- [Annotations and Evaluation Setup](#annotations-and-evaluation-setup)
- [Running Retrieval Experiments](#running-retrieval-experiments)
- [Case Studies and Appendix](#case-studies-and-appendix)
- [Build Report Tables](#build-report-tables)
- [Reproducibility](#reproducibility)
- [Limitations](#limitations)
- [Julkaisun huomautus (q5)](#julkaisun-huomautus-q5)
- [Interaktiivinen tulosesittely](#interaktiivinen-tulosesittely)
- [Demo and CLI Usage (legacy / development)](#demo-and-cli-usage-legacy--development)
- [Installation](#installation)
- [License](#license)

---

## Projektikuvaus

Tämä projekti on **opinnäytetyön tutkimusprototyyppi**, ei tuotantokäyttöinen palvelu. Se toteuttaa:

- **Qdrant-pohjaisen RAG-vetoritietokannan** semanttiseen hakuun
- **Retrieval-ablaatiot**: baseline, MMR, reranking, deduplication
- **Arviointimittarit**: recall@k, nDCG@k, latenssi (p50/p95/p99)
- **Suomenkielinen aineisto**: Theseus-opinnäytteet

### Ei pääfokus

- Tuotantokäyttöinen palvelu (production-ready)
- LLM-generointi tai groundedness-arviointi (retrieval-fokus)
- Monikielinen tai laajasti skaalautuva järjestelmä

---

## Tutkimusputki

Tutkimusputki etenee seuraavasti:

| Vaihe | Skripti / moduuli | Tuotokset |
|-------|-------------------|-----------|
| 1. Raakadatan keruu | `data/raw` | PDF-tiedostot (Theseus-opinnäytteet) |
| 2. Preprocessointi | `scripts/preprocess_corpus.py` | `documents.jsonl`, `chunks.jsonl` |
| 3. Datan laadun tarkistus | `scripts/check_data_quality.py` | `data_quality_report.json` |
| 4. Indeksointi Qdrantiin | `scripts/index_corpus.py` | Qdrant-kokoelma (esim. `rag_thesis_fi`) |
| 5. Queryt + gold-annotaatiot | `data/annotations/`, `annotations.py`, `scripts/validate_annotations.py` | `queries.jsonl`, `gold_annotations.jsonl` |
| 6. Retrieval-ablaatiot | `scripts/run_experiments.py` | `retrieval_hits.csv`, `per_query_metrics.csv`, `metrics_summary.csv`, `run_metadata.json` |
| 7. Raportointitaulukot | `scripts/build_report_tables.py` | `report_table_ablation.csv`, `report_table_latency.csv`, `report_tables.md` |
| 8. Case studies → liite | `scripts/generate_case_studies.py` → `scripts/format_case_studies_for_appendix.py` | `case_studies.md`, `LIITE_X_Case_esimerkit.md` |
| 9. Putken sanity check | `scripts/sanity_check_pipeline.py` | Konsoliyhteenveto putken valmiudesta |

---

## Projektirakenne

```
qdrant_oppari/
├── README.md
├── requirements.txt
├── config.py                          # Konfiguraatio (mallit, kokoelma)
├── reproducibility.py                 # Toteutettavuus (seed, ympäristö, git)
├── data_loading.py                    # Raakadatan lataus
├── document_processing.py             # PDF-siivous + chunkkaus
├── indexing.py                        # Qdrant-indeksointi
├── retrieval.py                       # Haku, MMR, reranking, dedupe
├── prompting.py                       # LLM-promptit
├── annotations.py                     # Queryt + gold-annotaatiot
├── data/
│   ├── raw/                           # Raaka-PDF:t
│   ├── processed/                     # documents.jsonl, chunks.jsonl
│   ├── metadata/                      # metadata.csv (valinnainen)
│   └── annotations/                   # queries.jsonl, gold_annotations.jsonl
├── outputs/
│   ├── logs/                          # preprocess_summary.json, data_quality_report.json
│   ├── experiments/                   # Pääkokeet: retrieval_hits.csv, metrics_summary.csv, run_metadata.json
│   └── experiments_rerank/            # Rerank-vertailu (--output-dir outputs/experiments_rerank)
├── scripts/
│   ├── preprocess_corpus.py
│   ├── check_data_quality.py
│   ├── index_corpus.py
│   ├── validate_annotations.py
│   ├── run_experiments.py             # Pääskripti retrieval-ablaatioille
│   ├── build_report_tables.py
│   ├── generate_case_studies.py       # Case studies (1. aja ensin)
│   ├── format_case_studies_for_appendix.py  # Liite (2. aja tämän jälkeen)
│   └── sanity_check_pipeline.py
├── utils/
│   ├── metrics_relevance.py           # recall@k, nDCG@k
│   └── ...
├── mini_rag_pipeline_qdrant.py        # Demo/CLI (legacy)
└── tools.py                           # CLI-työkalut (legacy)
```

---

## Data Preparation

### 1. Raakadatan sijoittaminen

Sijoita Theseus-opinnäytetyöt PDF-muodossa kansioon `data/raw/`.

### 2. Preprocessointi

```bash
python scripts/preprocess_corpus.py
python scripts/preprocess_corpus.py --raw-dir data/raw --limit-docs 5 --verbose
```

**Tuotokset:**
- `data/processed/documents.jsonl` – dokumentit
- `data/processed/chunks.jsonl` – chunkkatut katkelmat
- `outputs/logs/preprocess_summary.json` – yhteenveto

### 3. Datan laadun tarkistus

```bash
python scripts/check_data_quality.py
python scripts/check_data_quality.py --verbose --min-doc-chars 300
```

**Tuotokset:**
- `outputs/logs/data_quality_report.json`

### 4. Indeksointi Qdrantiin

Varmista Qdrant käynnissä (`docker run -p 6333:6333 ...`):

```bash
python scripts/index_corpus.py
python scripts/index_corpus.py --collection-name rag_thesis_fi --recreate-collection --batch-size 128
```

---

## Annotations and Evaluation Setup

### Queryt ja gold-annotaatiot

- **`queries.jsonl`**: `query_id`, `query_text`, `category`, `language`
- **`gold_annotations.jsonl`**: `query_id`, `relevant_doc_ids`, `relevant_chunk_ids`, `notes`

### Doc-level vs chunk-level

- **Doc-level** (`--eval-level doc`): relevanssi dokumenttitasolla (`relevant_doc_ids`)
- **Chunk-level** (`--eval-level chunk`): relevanssi chunk-tasolla (`relevant_chunk_ids`)

Gold-annotaatiot tarvitaan recall@k:n ja nDCG@k:n laskemiseen.

### Validointi

```bash
python scripts/validate_annotations.py
python scripts/validate_annotations.py --queries-path data/annotations/queries.jsonl --verbose
```

---

## Running Retrieval Experiments

### Esimerkkikomennot

```bash
# Dry-run (ei Qdrant-hakuja)
python scripts/run_experiments.py --dry-run --verbose

# Debug: rajoita kyselyjä
python scripts/run_experiments.py --collection-name rag_thesis_fi --eval-level doc --limit-queries 5 --verbose

# Normaali ajo
python scripts/run_experiments.py --collection-name rag_thesis_fi --eval-level doc --verbose

# Toteutettavuus: seed + parametrit
python scripts/run_experiments.py --collection-name rag_thesis_fi --eval-level doc --seed 42 --limit-queries 5 --verbose

# Rerank-mallien vertailu (tulokset erilliseen kansioon)
python scripts/run_experiments.py --output-dir outputs/experiments_rerank --rerank-models cross-encoder/ms-marco-MiniLM-L-6-v2 BAAI/bge-reranker-v2-m3 --verbose
```

### Parametrit

| Parametri | Kuvaus | Oletus |
|-----------|--------|--------|
| `--collection-name` | Qdrant-kokoelma | `rag_thesis_fi` |
| `--eval-level` | `doc` tai `chunk` | `doc` |
| `--output-dir` | Tulostiedostojen kansio | `outputs/experiments` |
| `--rerank-models` | Vertailtavat rerank-mallit (C2/C3) | oletusmalli |
| `--seed` | Satunnaissiemen | `42` |
| `--qdrant-url` | Qdrant-osoite | `http://localhost:6333` |
| `--limit-queries` | Kyselyt (debug) | ei rajaa |
| `--dry-run` | Vain validointi | - |

### Tuotokset (`outputs/experiments/`)

| Tiedosto | Sisältö |
|----------|---------|
| `retrieval_hits.csv` | Hakutulokset (query_id, config, rank, doc_id, chunk_id, score) |
| `per_query_metrics.csv` | Per-query recall@k, nDCG@k, latenssi |
| `metrics_summary.csv` | Keskiarvot per config (mean recall@k, nDCG@k, p50/p95/p99) |
| `run_metadata.json` | Toteutettavuusmetadata (seed, ympäristö, git) |

---

## Case Studies and Appendix

Liitteen esimerkkitapaukset tuotetaan **aina tässä järjestyksessä**:

```bash
python scripts/generate_case_studies.py
python scripts/format_case_studies_for_appendix.py
```

- **`generate_case_studies.py`** luo `case_studies.md` retrieval-tuloksista
- **`format_case_studies_for_appendix.py`** muuntaa sen thesis-liitteeksi `LIITE_X_Case_esimerkit.md`

Rerank-kokeista (erillinen `outputs/experiments_rerank`):

```bash
python scripts/generate_case_studies.py --experiments-dir outputs/experiments_rerank --output-path outputs/experiments_rerank/case_studies.md
python scripts/format_case_studies_for_appendix.py --input outputs/experiments_rerank/case_studies.md --output outputs/experiments_rerank/LIITE_X_Case_esimerkit.md
```

---

## Build Report Tables

Luo opinnäytetyön raportointia varten taulukot:

```bash
python scripts/build_report_tables.py
python scripts/build_report_tables.py --input-dir outputs/experiments --output-dir outputs/experiments
```

Rerank-vertailun tuloksille (erillinen kansio):

```bash
python scripts/build_report_tables.py --input-dir outputs/experiments_rerank --output-dir outputs/experiments_rerank
```

### Tuotokset

| Tiedosto | Sisältö |
|----------|---------|
| `report_table_ablation.csv` | Ablaatiovertailu (recall@k, nDCG@k, std) |
| `report_table_latency.csv` | Latenssi (p50, p95, p99) |
| `report_table_best_config.csv` | Paras config per mittari |
| `report_tables.md` | Markdown-yhteenveto |

---

## Pipeline Sanity Check

Nopea tarkistus, että tutkimusputken keskeiset tiedostot löytyvät:

```bash
python scripts/sanity_check_pipeline.py
```

Tämä on hyödyllinen ennen varsinaista `run_experiments.py`-ajoa.

---

## Reproducibility

Projekti tukee toistettavuutta:

- **`--seed`**: `run_experiments.py` asettaa `random`, `numpy`, `torch` -seedit
- **`run_metadata.json`**: sisältää `seed`, `environment_info`, `git_commit_hash`, `git_branch`, `timestamp_utc`
- **`reproducibility.py`**: `set_global_seed()`, `collect_environment_info()`, `build_reproducibility_metadata()`

Ympäristötiedot dokumentoivat Python-version, pakettiversiot (qdrant-client, sentence-transformers, torch, numpy) ja GPU-tiedot.

---

## Limitations

- **PDF-ekstraktio**: Tavutus, header/footer ja OCR-rajoitus voivat vaikuttaa laatuun
- **Gold-annotaatio**: Subjektiivinen; annotaattorien välinen yhteensopivuus voi vaihdella
- **Aineisto**: Suomenkielinen, domain-spesifinen (Theseus-opinnäytteet)
- **Retrieval vs generointi**: recall@k ja nDCG@k mittavat relevanssia; groundedness tai vastaavuus totuuteen ei ole sama asia
- **Julkaistu PDF**: luvun 6.4 q5-esimerkissä on kirjoitusvirhe (ks. [Julkaisun huomautus](#julkaisun-huomautus-q5)); päätulostaulukot eivät muutu

---

## Julkaisun huomautus (q5)

Luvun 6.4 tapausesimerkissä kyselyn **q5** recall@k-luvut on kirjoitettu väärin:

| Lähde | C0 | C1 | C2 | C3 |
|-------|----|----|----|----|
| Julkaistu PDF (6.4, q5) | 0 | 0 | 0,5 | 0,5 |
| Repositorio / liite 3 (`per_query_metrics.csv`) | **1,00** | **0,00** | **1,00** | **1,00** |

PDF:n luvut kuuluvat kyselylle **q2**, eivät q5:lle. Oikea q5-tarina: baseline löytää goldin (C0 = 1), MMR pudottaa sen (C1 = 0), rerank palauttaa sen (C2 = C3 = 1).

**Tämän repositorion ja tulosesittelyn lähde on CSV / liite 3.** Ablaatioiden keskiarvot (taulukot 3–6) sekä pohdinnan ja yhteenvedon pääjohtopäätökset perustuvat niihin; yksi väärä tapausvirke ei muuta niitä.

Lisätietoja: `docs/publication_traceability.md`.

---

## Interaktiivinen tulosesittely

Tämä repositorio sisältää julkaistun opinnäytetyön tutkimuskoodin ja tallennetut tulokset:

Heinonen, Karine (2026). *Hakustrategioiden vaikutus suomenkielisen RAG-järjestelmän tiedonhaun laatuun ja suorituskykyyn.* LAB-ammattikorkeakoulu.  
https://www.theseus.fi/items/4c5b8d64-c921-47f4-9c9a-52866778055a

Hakemiston `web/` sivusto on julkaisun interaktiivinen tulosesittely. Se näyttää vain tallennettuja tuloksia. Se ei ole chatbot, ei käynnistä Qdrantia eikä laske uusia hakuja. Näkyvä raja on: “Opinnäytetyön tallennetut tutkimustulokset · Ei reaaliaikaista hakua”. q5:n luvut näytetään liitteen 3 mukaisesti (ks. [Julkaisun huomautus](#julkaisun-huomautus-q5)).

Sivusto ei ole vielä julkaistu. Odotettu osoite Pages-käyttöönoton jälkeen on https://karinehei.github.io/qdrant_oppari/

### Paikallinen vienti, build ja esikatselu

Komennot ajetaan repositorion juuresta. Ne toimivat Windowsissa ja Unix-kuoressa saman npm-skriptin kautta.

```bash
python scripts/website_export.py
cd web
npm ci
npm test
npm run build:demo
npm run preview:demo
```

Esikatselu käyttää samaa polkua kuin GitHub Pages: http://127.0.0.1:4173/qdrant_oppari/

`python scripts/website_export.py --strict-publication` palauttaa virhekoodin, jos aineellinen julkaisuristiriita on auki. Tavallinen vienti kirjoittaa silti paikallisen aineiston. Vienti ei muuta `outputs/`- tai `data/annotations/`-tiedostoja.

### Jäljitettävyys ja validointi

- `docs/publication_traceability.md` yhdistää julkaisun taulun tai kuvion, repositorion tiedoston ja sivuston näkymän.
- Tarkistus vertaa kyselykohtaisia mittareita, koosteita ja raporttitauluja sekä laskee diagnostisesti recall@5- ja nDCG@5-arvot tallennetuista osumista ja nykyisistä annotaatioista. Lukuja ei kirjoiteta takaisin.
- Pääablaatio (`outputs/experiments`) ja uudelleenjärjestäjävertailu (`outputs/experiments_rerank`) pidetään erillisinä etenkin latenssissa.
- Lähdedokumenttien tekstiä ja PDF-tiedostoja ei julkaista. Näyttönimet on johdettu tiedostonimistä, eikä niille keksitä Theseus-osoitteita.

### Tulevat kokeet

Uudet ajot kirjoitetaan omaan tuloshakemistoonsa. Niitä ei lisätä tämän julkaistun aineiston `outputs/experiments`- tai `outputs/experiments_rerank`-tiedostoihin eikä sivuston datasettiin ilman erillistä julkaisupäätöstä.

### GitHub Pages

Workflow `.github/workflows/pages.yml` käynnistyy vain käsin (`workflow_dispatch`). Se validoi aineiston, ajaa kevyen viennin, testit ja `web/`-buildin. Se ei asenna mallipinoa, käynnistä Qdrantia eikä aja hakukokeita. Artefaktina julkaistaan vain `web/dist`.

Pages otetaan käyttöön repositorion asetuksista lähteellä GitHub Actions. Tätä workflowta ei ole käynnistetty, eikä sivustoa ole julkaistu. Niin kauan kuin `website_export.py --strict-publication` epäonnistuu, julkaisutyö pysähtyy ennen lähetystä.

## Demo and CLI Usage (legacy / development)

Opinnäytetyön mittaustulokset tuotetaan **`scripts/run_experiments.py`** -skriptillä. Demo- ja CLI-komponentit ovat kehitys- ja demo-käyttöön; **kokeet eivät vaadi LLM-integraatiota**.

### `mini_rag_pipeline_qdrant.py`

- Täysi RAG-pipeline MMR:llä, rerankingilla ja arvioinnilla
- Valinnainen LLM-integraatio (Mistral AI) – vaatii `MISTRAL_API_KEY`

```python
from mini_rag_pipeline_qdrant import main
main()
```

### `tools.py`

- CLI-työkalu hybridihakuun ja HNSW-viritykseen

```bash
python tools.py --index --search "Mitä on RAG?" --rerank --topk 5
python tools.py --search "..." --hybrid --topk 8
```

---

## Installation

### Prerequisites

- Python 3.8+
- Qdrant (Docker suositeltu)

### Asennus

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
# .venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### Qdrant

```bash
docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant:latest
```

### Mallit ja LLM-integraatio

**Generatiivinen LLM (suora API-kutsu koodissa):**
- `open-mistral-nemo` (`mini_rag_pipeline_qdrant.py`, Mistral API; vaatii `MISTRAL_API_KEY`)

**Retrieval-putken tekstimallit (ei generatiivinen LLM-vastaus):**
- Embedding-malli: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (`config.py`)
- Rerank-malli (oletus): `BAAI/bge-reranker-v2-m3` (`config.py`)
- Rerank-vertailussa käytetty myös: `cross-encoder/ms-marco-MiniLM-L-6-v2` (`scripts/run_experiments.py` esimerkkiajo)

**Huomio mittausputkesta:**
- `scripts/run_experiments.py` arvioi retrievalin (recall@k, nDCG@k, latenssi), ei tee LLM-generointia.
- `outputs/experiments/groundedness_summary.csv` viittaa LLM-pohjaisiin groundedness-tuloksiin, mutta tässä repossa ei ole erillistä skriptiä, joka suorittaisi usean LLM-providerin generointiajot alusta asti.

---

## License

This project is licensed under the MIT License.

---

## Keskeiset työkalut ja lähteet

- [Qdrant](https://qdrant.tech/) – vektoritietokanta
- [SentenceTransformers](https://www.sbert.net/) – embedding- ja rerank-kirjasto
- [Hugging Face](https://huggingface.co/) – mallien jakelu ja model hub
- [BAAI](https://www.baai.ac.cn/) – `bge-reranker-v2-m3`-malli
- [MS MARCO Cross-Encoders](https://www.sbert.net/docs/pretrained-models/ce-msmarco.html) – `cross-encoder/ms-marco-MiniLM-L-6-v2` rerank-vertailuihin
- [Mistral AI](https://mistral.ai/) – LLM-palveluntarjoaja (valinnainen demo)
- [pypdf](https://pypdf.readthedocs.io/) – PDF-tekstin purku preprocess-vaiheessa
- [Theseus](https://www.theseus.fi/) – opinnäytetyöaineiston lähde

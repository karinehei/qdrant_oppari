# Qdrant RAG – Opinnäytetyön tutkimusprototyyppi

Qdrant-pohjainen RAG-tutkimusprototyyppi retrieval-ablaatioiden arviointiin suomenkielisellä aineistolla (Theseus-opinnäytteet + viralliset suomidokumentit).

## 📋 Sisällysluettelo

- [Projektikuvaus](#projektikuvaus)
- [Tutkimusputki](#tutkimusputki)
- [Projektirakenne](#projektirakenne)
- [Data Preparation](#data-preparation)
- [Annotations and Evaluation Setup](#annotations-and-evaluation-setup)
- [Running Retrieval Experiments](#running-retrieval-experiments)
- [Build Report Tables](#build-report-tables)
- [Reproducibility](#reproducibility)
- [Limitations](#limitations)
- [Demo and CLI Usage (legacy / development)](#demo-and-cli-usage-legacy--development)
- [Installation](#installation)
- [License](#license)

---

## Projektikuvaus

Tämä projekti on **opinnäytetyön tutkimusprototyyppi**, ei tuotantokäyttöinen palvelu. Se toteuttaa:

- **Qdrant-pohjaisen RAG-vetoritietokannan** semanttiseen hakuun
- **Retrieval-ablaatiot**: baseline, MMR, reranking, deduplication
- **Arviointimittarit**: recall@k, nDCG@k, latenssi (p50/p95/p99)
- **Suomenkielinen aineisto**: Theseus-opinnäytteet ja viralliset suomidokumentit

### Ei pääfokus

- Tuotantokäyttöinen palvelu (production-ready)
- LLM-generointi tai groundedness-arviointi (retrieval-fokus)
- Monikielinen tai laajasti skaalautuva järjestelmä

---

## Tutkimusputki

Tutkimusputki etenee seuraavasti:

| Vaihe | Skripti / moduuli | Tuotokset |
|-------|-------------------|-----------|
| 1. Raakadatan keruu | `data/raw` | PDF-tiedostot (Theseus, viralliset) |
| 2. Preprocessointi | `scripts/preprocess_corpus.py` | `documents.jsonl`, `chunks.jsonl` |
| 3. Datan laadun tarkistus | `scripts/check_data_quality.py` | `data_quality_report.json` |
| 4. Indeksointi Qdrantiin | `scripts/index_corpus.py` | Qdrant-kokoelma (esim. `rag_thesis_fi`) |
| 5. Queryt + gold-annotaatiot | `data/annotations/`, `annotations.py`, `scripts/validate_annotations.py` | `queries.jsonl`, `gold_annotations.jsonl` |
| 6. Retrieval-ablaatiot | `scripts/run_experiments.py` | `retrieval_hits.csv`, `per_query_metrics.csv`, `metrics_summary.csv`, `run_metadata.json` |
| 7. Raportointitaulukot | `scripts/build_report_tables.py` | `report_table_ablation.csv`, `report_table_latency.csv`, `report_tables.md` |

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
│   └── experiments/                   # retrieval_hits.csv, metrics_summary.csv, run_metadata.json
├── scripts/
│   ├── preprocess_corpus.py
│   ├── check_data_quality.py
│   ├── index_corpus.py
│   ├── validate_annotations.py
│   ├── run_experiments.py             # Pääskripti retrieval-ablaatioille
│   ├── build_report_tables.py
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

Sijoita Theseus-PDF:t ja viralliset suomidokumentit kansioon `data/raw/`.

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
```

### Parametrit

| Parametri | Kuvaus | Oletus |
|-----------|--------|--------|
| `--collection-name` | Qdrant-kokoelma | `rag_thesis_fi` |
| `--eval-level` | `doc` tai `chunk` | `doc` |
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

## Build Report Tables

Luo opinnäytetyön raportointia varten taulukot:

```bash
python scripts/build_report_tables.py
python scripts/build_report_tables.py --input-dir outputs/experiments --output-dir outputs/experiments
```

### Tuotokset

| Tiedosto | Sisältö |
|----------|---------|
| `report_table_ablation.csv` | Ablaatiovertailu (recall@k, nDCG@k, std) |
| `report_table_latency.csv` | Latenssi (p50, p95, p99) |
| `report_table_best_config.csv` | Paras config per mittari |
| `report_tables.md` | Markdown-yhteenveto |

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
- **Aineisto**: Suomenkielinen, domain-spesifinen (opinnäytteet + viralliset dokumentit)
- **Retrieval vs generointi**: recall@k ja nDCG@k mittavat relevanssia; groundedness tai vastaavuus totuuteen ei ole sama asia

---

## Demo and CLI Usage (legacy / development)

Opinnäytetyön mittaustulokset tuotetaan **`scripts/run_experiments.py`** -skriptillä. Demo- ja CLI-komponentit ovat kehitys- ja demo-käyttöön:

### `mini_rag_pipeline_qdrant.py`

- Täysi RAG-pipeline MMR:llä, rerankingilla ja arvioinnilla
- LLM-integraatio (Mistral AI)

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

### LLM-integraatio (valinnainen)

Luodaan `.env` ja lisätään `MISTRAL_API_KEY` käyttäen `mini_rag_pipeline_qdrant.py` tai `tools.py` LLM-kutsuja.

---

## License

This project is licensed under the MIT License.

---

## Acknowledgments

- [Qdrant](https://qdrant.tech/) – Vector database
- [SentenceTransformers](https://www.sbert.net/) – Embedding models
- [Mistral AI](https://mistral.ai/) – LLM provider (demo)

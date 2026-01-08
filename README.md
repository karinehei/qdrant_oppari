# Qdrant RAG Pipeline

A production-ready Retrieval-Augmented Generation (RAG) pipeline built with Qdrant vector database, featuring advanced retrieval techniques, evaluation metrics, and LLM integration.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Usage](#usage)
- [Components](#components)
- [Configuration](#configuration)
- [Evaluation Metrics](#evaluation-metrics)
- [API Reference](#api-reference)
- [Examples](#examples)
- [License](#license)

## 🎯 Overview

This project implements a complete RAG (Retrieval-Augmented Generation) system that combines semantic search with large language models. It uses Qdrant as the vector database and includes advanced retrieval techniques like MMR (Maximal Marginal Relevance), reranking, and hybrid search.

### Key Capabilities

- **Semantic Search**: Vector-based similarity search using sentence transformers
- **MMR (Maximal Marginal Relevance)**: Balances relevance and diversity in search results
- **Reranking**: Cross-encoder based reranking for improved precision
- **Hybrid Search**: Combines vector search with BM25 for better recall
- **Evaluation Metrics**: Built-in metrics for relevance (recall@k, nDCG@k) and latency
- **Groundedness Checking**: Validates that LLM responses cite sources correctly
- **LLM Integration**: Ready-to-use integration with Mistral AI

## ✨ Features

### Core Features

- ✅ **Vector Indexing**: Efficient document chunking and embedding generation
- ✅ **Advanced Retrieval**: MMR, reranking, and deduplication
- ✅ **Metadata Filtering**: Support for ACL-style filters (tenant_id, doc_type, domain)
- ✅ **HNSW Optimization**: Configurable HNSW parameters for performance tuning
- ✅ **Hybrid Search**: Vector + BM25 combination for improved results
- ✅ **Evaluation Framework**: Comprehensive metrics for system evaluation
- ✅ **Latency Monitoring**: Performance measurement with percentile metrics
- ✅ **Source Attribution**: Automatic source citation in LLM responses

### Two Implementation Approaches

1. **`mini_rag_pipeline_qdrant.py`**: Full-featured pipeline with MMR, reranking, and evaluation
2. **`tools.py`**: CLI-based tool with hybrid search and HNSW tuning options

## 🏗️ Architecture

```
┌─────────────────┐
│   Documents     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Chunking      │  (Sentence-based chunking)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Embedding     │  (SentenceTransformers)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Qdrant Index  │  (HNSW, COSINE distance)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Query         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Vector Search │  (Initial retrieval)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   MMR Selection │  (Diversity optimization)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Reranking     │  (CrossEncoder)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Deduplication │  (Source/UID based)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   LLM Prompt    │  (Context + Question)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   LLM Response  │  (Mistral AI)
└─────────────────┘
```

## 📦 Installation

### Prerequisites

- Python 3.8+
- Qdrant server (Docker recommended)
- Mistral AI API key (for LLM integration)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Start Qdrant Server

Using Docker:

```bash
docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant:latest
```

Or use Qdrant Cloud for a managed solution.

### Step 3: Configure Environment Variables

Create a `.env` file:

```bash
MISTRAL_API_KEY=your_mistral_api_key_here
```

## 🚀 Quick Start

### Basic Usage

```python
from mini_rag_pipeline_qdrant import main
main()
```

This will:
1. Index demo documents into Qdrant
2. Perform a semantic search with MMR and reranking
3. Generate an LLM response using Mistral AI
4. Display evaluation metrics

### CLI Usage (tools.py)

```bash
# Index documents
python tools.py --index

# Search with basic semantic search
python tools.py --search "Why is vector database useful in RAG?"

# Search with reranking
python tools.py --search "..." --rerank --topk 5

# Hybrid search (vector + BM25)
python tools.py --search "..." --hybrid --topk 8

# Create snapshot
python tools.py --snapshot
```

## 📖 Usage

### Main Pipeline (`mini_rag_pipeline_qdrant.py`)

The main pipeline provides a complete RAG workflow:

```python
from mini_rag_pipeline_qdrant import search, build_prompt, index
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer, CrossEncoder

# Initialize
client = QdrantClient(url="http://localhost:6333")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# Index documents
corpus = build_corpus(DOCS)
index(client, model, corpus)

# Search
results = search(
    client=client,
    model=model,
    query="Your question here",
    top_k=4,
    initial_limit=30,
    diversity=0.35,
    cross_encoder=reranker
)

# Build prompt for LLM
prompt = build_prompt(question="Your question", contexts=results)
```

### CLI Tool (`tools.py`)

The CLI tool provides flexible command-line access:

```bash
# Basic search
python tools.py --index --search "Your question" --topk 5

# With reranking
python tools.py --index --search "Your question" --rerank --topk 5

# Hybrid search
python tools.py --index --search "Your question" --hybrid --topk 8

# With ACL filters
python tools.py --search "Your question" --tenant acme --doc_type knowledge

# Print generated prompt
python tools.py --search "Your question" --print-prompt
```

## 🔧 Components

### 1. Document Processing

- **Chunking**: Sentence-based chunking with configurable max length
- **Embedding**: Uses SentenceTransformers for generating embeddings
- **Metadata**: Supports tenant_id, doc_type, domain for filtering

### 2. Retrieval Pipeline

#### Vector Search
- Initial retrieval using cosine similarity
- Configurable HNSW parameters (ef_construct, ef_search)
- Score threshold filtering

#### MMR (Maximal Marginal Relevance)
- Balances relevance and diversity
- Configurable diversity parameter (0-1)
- Reduces redundancy in results

#### Reranking
- Cross-encoder based reranking
- Improves precision of top results
- Optional component

#### Deduplication
- Removes duplicate chunks by UID or source
- Configurable deduplication strategy

### 3. Evaluation Metrics

- **Recall@k**: Fraction of relevant documents retrieved
- **nDCG@k**: Normalized Discounted Cumulative Gain
- **Latency**: p50, p95, p99 percentile measurements
- **Groundedness**: Checks for source citations in responses

### 4. LLM Integration

- Mistral AI integration
- Automatic source citation
- Configurable temperature and max tokens

## ⚙️ Configuration

### Main Pipeline Configuration

```python
COLLECTION = "demo_docs"  # Qdrant collection name
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # Embedding model
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"  # Reranking model

# Flags
RESET = False  # Reset collection on startup
DEDUPE_BY_SOURCE = False  # Deduplicate by source instead of UID
```

### Search Parameters

```python
top_k = 4              # Final number of results
initial_limit = 30     # Initial retrieval size (before MMR)
diversity = 0.35       # MMR diversity parameter (0-1)
score_threshold = 0.25 # Minimum similarity score
```

### HNSW Parameters (tools.py)

```python
m = 16                 # Number of bi-directional links
ef_construct = 256     # Size of candidate list during construction
hnsw_ef = 256          # Size of candidate list during search
```

## 📊 Evaluation Metrics

### Relevance Metrics

```python
from utils.metrics_relevance import eval_query, recall_at_k, ndcg_at_k

# Evaluate a query
metrics = eval_query(
    search_fn=lambda q, k: search(client, model, q, top_k=k),
    query="Your question",
    expected_sources={"polku/1", "polku/2"},
    k=5
)

print(f"Recall@5: {metrics['recall@5']}")
print(f"nDCG@5: {metrics['ndcg@5']}")
```

### Latency Metrics

```python
from utils.latency_utils import measure_latency

latency = measure_latency(
    fn=lambda: search(client, model, "query", top_k=5),
    runs=20,
    warmup=3
)

print(f"p50: {latency['p50_ms']:.1f} ms")
print(f"p95: {latency['p95_ms']:.1f} ms")
print(f"p99: {latency['p99_ms']:.1f} ms")
```

### Groundedness Check

```python
from utils.groundedness_proxy import groundedness_proxy

result = groundedness_proxy(
    answer_text=llm_response,
    allowed_sources=["polku/1", "polku/2"]
)

print(f"Has sources section: {result['has_sources_section']}")
print(f"Mentions allowed source: {result['mentions_allowed_source']}")
```

## 📚 API Reference

### Main Functions

#### `chunk(text: str, max_len: int = 256) -> List[str]`
Splits text into chunks based on sentences.

**Parameters:**
- `text`: Input text to chunk
- `max_len`: Maximum chunk length in characters

**Returns:** List of text chunks

#### `build_corpus(docs: List[Dict]) -> List[Dict]`
Builds a corpus from documents with chunking and metadata.

**Parameters:**
- `docs`: List of documents with `id`, `title`, `text` fields

**Returns:** List of corpus entries with `uid`, `title`, `text`, `source`

#### `index(client: QdrantClient, model: SentenceTransformer, corpus: List[Dict])`
Indexes corpus into Qdrant collection.

**Parameters:**
- `client`: Qdrant client instance
- `model`: SentenceTransformer model for embeddings
- `corpus`: Corpus to index

#### `search(client, model, query: str, top_k: int = 4, ...) -> List[Dict]`
Performs semantic search with MMR, reranking, and deduplication.

**Parameters:**
- `client`: Qdrant client
- `model`: Embedding model
- `query`: Search query
- `top_k`: Number of results to return
- `initial_limit`: Initial retrieval size
- `diversity`: MMR diversity parameter (0-1)
- `score_threshold`: Minimum similarity score
- `cross_encoder`: Optional reranker

**Returns:** List of search results with scores and metadata

#### `build_prompt(question: str, contexts: List[Dict]) -> str`
Builds a prompt for LLM with question and retrieved contexts.

**Parameters:**
- `question`: User question
- `contexts`: Retrieved document chunks

**Returns:** Formatted prompt string

### Utility Functions

See individual module documentation:
- `utils/metrics_relevance.py`: Relevance evaluation metrics
- `utils/latency_utils.py`: Latency measurement
- `utils/groundedness_proxy.py`: Source citation validation

## 💡 Examples

### Example 1: Basic RAG Pipeline

```python
from mini_rag_pipeline_qdrant import main
main()
```

### Example 2: Custom Search

```python
from mini_rag_pipeline_qdrant import search, build_corpus, index, ensure_collection
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer, CrossEncoder

# Setup
client = QdrantClient(url="http://localhost:6333")
model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

# Index
corpus = build_corpus(DOCS)
ensure_collection(client, dim=model.get_sentence_embedding_dimension())
index(client, model, corpus)

# Search
results = search(
    client, model, "Why use vector databases?",
    top_k=5, diversity=0.4, cross_encoder=reranker
)

for r in results:
    print(f"{r['score']:.3f}: {r['title']} - {r['text'][:100]}")
```

### Example 3: Evaluation

```python
from mini_rag_pipeline_qdrant import search
from utils.metrics_relevance import eval_query

def search_fn(query, top_k):
    return search(client, model, query, top_k=top_k)

metrics = eval_query(
    search_fn=search_fn,
    query="Vector database benefits",
    expected_sources={"polku/1", "polku/2"},
    k=5
)

print(metrics)
```

## 🔍 Project Structure

```
qdrant/
├── README.md                          # This file
├── API.md                             # API reference documentation
├── requirements.txt                   # Python dependencies
├── mini_rag_pipeline_qdrant.py       # Main RAG pipeline (orchestrator)
├── tools.py                           # CLI tool with hybrid search
├── config.py                          # Configuration constants
├── document_processing.py             # Document chunking and corpus building
├── indexing.py                        # Qdrant collection management and indexing
├── retrieval.py                       # Search, MMR, reranking, deduplication
├── prompting.py                       # LLM prompt construction
└── utils/
    ├── __init__.py
    ├── groundedness_proxy.py          # Source citation validation
    ├── latency_utils.py               # Performance measurement
    └── metrics_relevance.py           # Relevance evaluation metrics
```

### Module Organization

The project is organized into logical modules:

- **`config.py`**: Centralized configuration (models, collection names, flags, demo documents)
- **`document_processing.py`**: Text chunking and corpus construction
- **`indexing.py`**: Qdrant collection setup and document indexing
- **`retrieval.py`**: Semantic search, MMR selection, reranking, and deduplication
- **`prompting.py`**: LLM prompt formatting and construction
- **`mini_rag_pipeline_qdrant.py`**: Main orchestrator that ties everything together

## 🛠️ Development

### Adding Custom Documents

Modify the `DOCS` list in either file:

```python
DOCS = [
    {"id": "custom/1", "title": "Your Title", "text": "Your content..."},
    # ... more documents
]
```

### Customizing Embedding Model

Change the `EMBED_MODEL` constant:

```python
EMBED_MODEL = "sentence-transformers/all-mpnet-base-v2"  # Larger, more accurate
```

### Tuning HNSW Parameters

In `tools.py`, use the `tune_hnsw` function:

```python
tune_hnsw(client, m=32, ef_construct=512, full_scan_threshold=5000)
```

## 📝 Notes

- The code includes Finnish comments and variable names, but the API is language-agnostic
- Demo documents are in Finnish, but the system works with any language
- For production use, add error handling, logging, and more robust chunking strategies
- Consider using larger embedding models for better accuracy
- HNSW parameters should be tuned based on your dataset size and latency requirements

## 🤝 Contributing

This is a demonstration project. For production use, consider:
- Adding comprehensive error handling
- Implementing logging
- Adding unit tests
- Supporting more document formats
- Implementing batch processing for large datasets

## 📄 License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for the full license text.

## 🙏 Acknowledgments

- [Qdrant](https://qdrant.tech/) - Vector database
- [SentenceTransformers](https://www.sbert.net/) - Embedding models
- [Mistral AI](https://mistral.ai/) - LLM provider

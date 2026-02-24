#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sanity Check Pipeline Script

Tests the full RAG pipeline end-to-end with a small sample before production runs.
Indexes limited chunks to a test collection, runs sample queries, prints results.

Usage:
    python scripts/sanity_check_pipeline.py
    python scripts/sanity_check_pipeline.py --limit-chunks 100 --recreate-collection
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

# Placeholder test queries (Finnish RAG/thesis topics)
DEFAULT_QUERIES = [
    "Mitä on RAG-järjestelmä?",
    "Miten vektoritietokanta toimii semanttisessa haussa?",
    "Mitä hyötyä on hybridihakusta?",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sanity check: index sample chunks and run test queries"
    )
    parser.add_argument(
        "--chunks-path",
        default="data/processed/chunks.jsonl",
        help="Path to chunks.jsonl",
    )
    parser.add_argument(
        "--collection-name",
        default="sanity_test_collection",
        help="Qdrant collection name for test (default: sanity_test_collection)",
    )
    parser.add_argument(
        "--limit-chunks",
        type=int,
        default=50,
        help="Max chunks to index (default: 50)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-K results per query (default: 5)",
    )
    parser.add_argument(
        "--recreate-collection",
        action="store_true",
        help="Delete and recreate collection before indexing",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def resolve_path(p: str) -> Path:
    path = Path(p)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def load_chunks(path: Path, limit: int) -> list[dict]:
    """Load chunks from JSONL, convert to indexing format."""
    if not path.exists():
        raise FileNotFoundError(f"Chunks file not found: {path}")

    chunks: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            c = json.loads(line)
            chunks.append({
                "uid": c.get("uid", c.get("chunk_id", "")),
                "title": c.get("title", ""),
                "text": c.get("text", ""),
                "source": c.get("source", c.get("doc_id", "")),
            })
        except json.JSONDecodeError as e:
            logger.warning("Skipping invalid chunk: %s", e)
            continue
        if len(chunks) >= limit:
            break

    return chunks


def load_queries(path: Path) -> list[str]:
    """Load query texts from queries.jsonl if available."""
    if not path.exists():
        return []
    queries: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            text = row.get("text", row.get("query", ""))
            if text:
                queries.append(text)
        except json.JSONDecodeError:
            continue
    return queries[:5]  # Max 5 from file


def run_sanity_check(args: argparse.Namespace) -> bool:
    """Run sanity check. Returns True if successful."""
    chunks_path = resolve_path(args.chunks_path)
    queries_path = PROJECT_ROOT / "data" / "annotations" / "queries.jsonl"

    # Load chunks
    try:
        corpus = load_chunks(chunks_path, args.limit_chunks)
    except FileNotFoundError as e:
        logger.error("%s", e)
        return False

    if not corpus:
        logger.error("No chunks loaded. Check %s", chunks_path)
        return False

    logger.info("Loaded %d chunks", len(corpus))

    # Load queries
    queries = load_queries(queries_path)
    if not queries:
        queries = DEFAULT_QUERIES
        logger.info("Using default placeholder queries")
    else:
        logger.info("Loaded %d queries from %s", len(queries), queries_path)

    # Import heavy deps (fail early if missing)
    try:
        from qdrant_client import QdrantClient
        from sentence_transformers import SentenceTransformer, CrossEncoder
    except ImportError as e:
        logger.error("Missing dependency: %s", e)
        return False

    from config import EMBED_MODEL, RERANK_MODEL
    from indexing import ensure_collection, index
    from retrieval import search

    # Connect to Qdrant
    try:
        client = QdrantClient(url="http://localhost:6333")
        client.get_collections()  # Verify connection
    except Exception as e:
        logger.error("Cannot connect to Qdrant (http://localhost:6333): %s", e)
        logger.info("Start Qdrant with: docker run -p 6333:6333 qdrant/qdrant:latest")
        return False

    # Load models
    try:
        model = SentenceTransformer(EMBED_MODEL)
        cross_encoder = CrossEncoder(RERANK_MODEL)
    except Exception as e:
        logger.error("Failed to load models: %s", e)
        return False

    coll = args.collection_name
    dim = model.get_sentence_embedding_dimension()

    # Create/recreate collection
    if args.recreate_collection and client.collection_exists(coll):
        client.delete_collection(coll)
        logger.info("Deleted existing collection %s", coll)

    ensure_collection(client, dim, collection_name=coll)
    index(client, model, corpus, collection_name=coll)
    logger.info("Indexed %d chunks to %s", len(corpus), coll)

    # Run queries: baseline (no MMR, no rerank) and enhanced (MMR + rerank)
    configs = [
        ("baseline", {"diversity": 0.0, "cross_encoder": None}),
        ("enhanced (MMR+rerank)", {"diversity": 0.35, "cross_encoder": cross_encoder}),
    ]

    for config_name, kwargs in configs:
        print(f"\n{'='*60}")
        print(f"CONFIG: {config_name}")
        print("=" * 60)

        for i, q in enumerate(queries[:3], 1):
            print(f"\n--- Query {i}: {q[:60]}...")
            try:
                results = search(
                    client,
                    model,
                    q,
                    top_k=args.top_k,
                    initial_limit=min(30, len(corpus) * 2),
                    score_threshold=0.0,
                    collection_name=coll,
                    **kwargs,
                )
            except Exception as e:
                logger.warning("Search failed for query %d: %s", i, e)
                continue

            for rank, r in enumerate(results, 1):
                uid = r.get("uid", "?")
                score = r.get("score", r.get("rerank_score", 0))
                title = r.get("title", "—")
                source = r.get("source", "—")
                text = (r.get("text", "") or "")[:120]
                print(f"  {rank}. [{score:.3f}] {uid} | {title} [{source}]")
                print(f"      {text}...")

    return True


def main() -> None:
    args = parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    ok = run_sanity_check(args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Index Corpus Script

Indexes preprocessed chunks from chunks.jsonl into Qdrant for research use.
Supports batch encoding, rich payload metadata, and HNSW tuning.

Usage:
    python scripts/index_corpus.py
    python scripts/index_corpus.py --recreate-collection --batch-size 128
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Optional

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index preprocessed chunks into Qdrant"
    )
    parser.add_argument(
        "--chunks-path",
        default="data/processed/chunks.jsonl",
        help="Path to chunks.jsonl",
    )
    parser.add_argument(
        "--collection-name",
        default="rag_thesis_fi",
        help="Qdrant collection name (default: rag_thesis_fi)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=64,
        help="Batch size for encoding and upsert (default: 64)",
    )
    parser.add_argument(
        "--recreate-collection",
        action="store_true",
        help="Delete and recreate collection before indexing",
    )
    parser.add_argument(
        "--distance",
        choices=["cosine", "euclidean", "dot"],
        default="cosine",
        help="Vector distance metric (default: cosine)",
    )
    parser.add_argument(
        "--hnsw-m",
        type=int,
        default=None,
        help="HNSW m parameter (optional)",
    )
    parser.add_argument(
        "--hnsw-ef-construct",
        type=int,
        default=None,
        help="HNSW ef_construct parameter (optional)",
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


def load_chunks(path: Path) -> tuple[list[dict], int]:
    """
    Load chunks from JSONL. Returns (valid_chunks, skipped_count).
    """
    if not path.exists():
        raise FileNotFoundError(f"Chunks file not found: {path}")

    valid: list[dict] = []
    skipped = 0

    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            c = json.loads(line)
            chunk_id = c.get("chunk_id") or c.get("uid") or c.get("id")
            text = c.get("text", "")
            if not chunk_id or not isinstance(text, str):
                logger.warning("Line %d: missing chunk_id or text, skipping", i)
                skipped += 1
                continue
            if not text.strip():
                logger.warning("Line %d: empty text for %s, skipping", i, chunk_id)
                skipped += 1
                continue
            valid.append(c)
        except json.JSONDecodeError as e:
            logger.warning("Line %d: invalid JSON: %s", i, e)
            skipped += 1
            continue

    return valid, skipped


def build_payload(c: dict) -> dict[str, Any]:
    """Build Qdrant payload from chunk dict with safe fallbacks.

    year and filepath may be None when metadata is missing (e.g. no metadata.csv,
    or documents loaded without filepath). This is expected and not an error.
    """
    return {
        "chunk_id": c.get("chunk_id") or c.get("uid", ""),
        "doc_id": c.get("doc_id") or c.get("source", ""),
        "title": c.get("title") or "",
        "source": c.get("source") or c.get("doc_id", ""),
        "source_type": c.get("source_type") or "raw",
        "language": c.get("language") or "fi",
        "year": c.get("year"),
        "chunk_index": c.get("chunk_index"),
        "text": c.get("text", ""),
        "char_start": c.get("char_start"),
        "char_end": c.get("char_end"),
        "filepath": c.get("filepath"),
        # uid for retrieval compatibility
        "uid": c.get("uid") or c.get("chunk_id", ""),
    }


def run_indexing(args: argparse.Namespace) -> dict:
    """Run indexing pipeline. Returns summary dict."""
    chunks_path = resolve_path(args.chunks_path)
    report_path = PROJECT_ROOT / "outputs" / "logs" / "index_summary.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    # Load chunks
    try:
        chunks, skipped = load_chunks(chunks_path)
    except FileNotFoundError as e:
        logger.error("%s", e)
        raise SystemExit(1) from e

    if not chunks:
        logger.error("No valid chunks to index")
        raise SystemExit(1)

    logger.info("Loaded %d chunks, skipped %d", len(chunks), skipped)

    # Import deps
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams, PointStruct
        from sentence_transformers import SentenceTransformer
    except ImportError as e:
        logger.error("Missing dependency: %s", e)
        raise SystemExit(1) from e

    try:
        from qdrant_client.models import HnswConfigDiff
        HAS_HNSW = True
    except ImportError:
        HAS_HNSW = False
        if args.hnsw_m is not None or args.hnsw_ef_construct is not None:
            logger.info("HNSW params requested but HnswConfigDiff not available in this qdrant-client version. Skipping HNSW tuning.")

    from config import EMBED_MODEL

    # Connect to Qdrant
    try:
        client = QdrantClient(url="http://localhost:6333")
        client.get_collections()
    except Exception as e:
        logger.error("Cannot connect to Qdrant: %s", e)
        raise SystemExit(1) from e

    # Load model
    try:
        model = SentenceTransformer(EMBED_MODEL)
    except Exception as e:
        logger.error("Failed to load embedding model: %s", e)
        raise SystemExit(1) from e

    dim = model.get_sentence_embedding_dimension()
    coll = args.collection_name

    # Distance mapping
    dist_map = {
        "cosine": Distance.COSINE,
        "euclidean": Distance.EUCLID,
        "dot": Distance.DOT,
    }
    distance = dist_map.get(args.distance, Distance.COSINE)

    # Recreate collection if requested
    if args.recreate_collection and client.collection_exists(coll):
        client.delete_collection(coll)
        logger.info("Deleted collection %s", coll)

    # Create collection if missing
    if not client.collection_exists(coll):
        client.create_collection(
            collection_name=coll,
            vectors_config=VectorParams(size=dim, distance=distance),
        )
        logger.info("Created collection %s", coll)

    # Apply HNSW if requested
    hnsw_applied = False
    if HAS_HNSW and (args.hnsw_m is not None or args.hnsw_ef_construct is not None):
        try:
            kwargs: dict[str, Any] = {}
            if args.hnsw_m is not None:
                kwargs["m"] = args.hnsw_m
            if args.hnsw_ef_construct is not None:
                kwargs["ef_construct"] = args.hnsw_ef_construct
            client.update_collection(
                collection_name=coll,
                hnsw_config=HnswConfigDiff(**kwargs),
            )
            hnsw_applied = True
            logger.info("Applied HNSW config: %s", kwargs)
        except Exception as e:
            logger.warning("Could not apply HNSW config: %s", e)

    # Batch encode and upsert
    t0 = time.perf_counter()
    batch_size = args.batch_size
    num_batches = (len(chunks) + batch_size - 1) // batch_size
    indexed = 0

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        texts = [c.get("text", "") or "" for c in batch]
        try:
            vectors = model.encode(texts, normalize_embeddings=True).tolist()
        except Exception as e:
            logger.warning("Batch %d: encode failed: %s", i // batch_size + 1, e)
            continue

        points = []
        for v, c in zip(vectors, batch):
            chunk_id = c.get("chunk_id") or c.get("uid", "")
            pid = uuid.uuid5(uuid.NAMESPACE_URL, chunk_id)
            payload = build_payload(c)
            points.append(
                PointStruct(id=str(pid), vector=v, payload=payload)
            )

        try:
            client.upsert(collection_name=coll, points=points)
            indexed += len(points)
        except Exception as e:
            logger.warning("Batch %d: upsert failed: %s", i // batch_size + 1, e)
            continue

    duration = time.perf_counter() - t0

    summary = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "chunks_path": str(chunks_path),
        "collection_name": coll,
        "indexed_count": indexed,
        "skipped_count": skipped,
        "total_loaded": len(chunks) + skipped,
        "batch_size": batch_size,
        "num_batches": num_batches,
        "embedding_model": EMBED_MODEL,
        "distance": args.distance,
        "hnsw_applied": hnsw_applied,
        "hnsw_m": args.hnsw_m,
        "hnsw_ef_construct": args.hnsw_ef_construct,
        "duration_seconds": round(duration, 2),
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary


def main() -> None:
    args = parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    summary = run_indexing(args)

    print("\n" + "=" * 60)
    print("INDEX SUMMARY")
    print("=" * 60)
    print(f"Chunks loaded:      {summary['total_loaded']}")
    print(f"Chunks skipped:     {summary['skipped_count']}")
    print(f"Chunks indexed:     {summary['indexed_count']}")
    print(f"Batches:            {summary['num_batches']} (size {summary['batch_size']})")
    print(f"Collection:         {summary['collection_name']}")
    print(f"Model:              {summary['embedding_model']}")
    print(f"Duration:           {summary['duration_seconds']} s")
    if summary.get("hnsw_applied"):
        print(f"HNSW:               m={summary.get('hnsw_m')}, ef_construct={summary.get('hnsw_ef_construct')}")
    print("=" * 60)
    print(f"Report: outputs/logs/index_summary.json")


if __name__ == "__main__":
    main()

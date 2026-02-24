#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Preprocess Corpus Script

Builds research corpus from raw data: loads documents from data/raw,
cleans and chunks them, writes documents.jsonl and chunks.jsonl.

Usage:
    python scripts/preprocess_corpus.py
    python scripts/preprocess_corpus.py --raw-dir data/raw --limit-docs 5 --verbose
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data_loading import load_documents_from_raw_dir
from document_processing import chunk_document, clean_pdf_text

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess raw documents into research corpus (documents.jsonl, chunks.jsonl)"
    )
    parser.add_argument(
        "--raw-dir",
        default="data/raw",
        help="Raw documents directory (default: data/raw)",
    )
    parser.add_argument(
        "--metadata-csv",
        default="data/metadata/metadata.csv",
        help="Optional metadata CSV (default: data/metadata/metadata.csv)",
    )
    parser.add_argument(
        "--documents-out",
        default="data/processed/documents.jsonl",
        help="Output path for documents (default: data/processed/documents.jsonl)",
    )
    parser.add_argument(
        "--chunks-out",
        default="data/processed/chunks.jsonl",
        help="Output path for chunks (default: data/processed/chunks.jsonl)",
    )
    parser.add_argument(
        "--summary-out",
        default="outputs/logs/preprocess_summary.json",
        help="Output path for summary (default: outputs/logs/preprocess_summary.json)",
    )
    parser.add_argument(
        "--max-len-chars",
        type=int,
        default=800,
        help="Max chunk length in characters (default: 800)",
    )
    parser.add_argument(
        "--overlap-chars",
        type=int,
        default=120,
        help="Overlap between chunks (default: 120)",
    )
    parser.add_argument(
        "--strategy",
        choices=["paragraph", "sentence"],
        default="paragraph",
        help="Chunking strategy (default: paragraph)",
    )
    parser.add_argument(
        "--min-chunk-chars",
        type=int,
        default=100,
        help="Minimum chunk length; shorter chunks are dropped (default: 100)",
    )
    parser.add_argument(
        "--limit-docs",
        type=int,
        default=None,
        help="Limit number of documents (for debugging)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def ensure_dirs(*paths: str) -> None:
    """Create parent directories for given paths."""
    for p in paths:
        Path(p).parent.mkdir(parents=True, exist_ok=True)


def run_preprocess(args: argparse.Namespace) -> dict:
    """
    Run full preprocessing pipeline. Returns summary dict.
    """
    def resolve_path(p: str) -> Path:
        path = Path(p)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    raw_dir = resolve_path(args.raw_dir)
    if not raw_dir.exists():
        logger.error("Raw directory does not exist: %s", raw_dir)
        raise SystemExit(1)

    metadata_csv = args.metadata_csv
    if metadata_csv:
        mc_path = resolve_path(metadata_csv)
        if mc_path.exists():
            metadata_csv = str(mc_path)
        else:
            logger.warning("Metadata CSV not found: %s. Continuing without metadata.", mc_path)
            metadata_csv = None

    documents_out = resolve_path(args.documents_out)
    chunks_out = resolve_path(args.chunks_out)
    summary_out = resolve_path(args.summary_out)

    ensure_dirs(str(documents_out), str(chunks_out), str(summary_out))

    # 1) Load documents
    docs = load_documents_from_raw_dir(str(raw_dir), metadata_csv)
    doc_count_loaded = len(docs)

    if args.limit_docs:
        docs = docs[: args.limit_docs]
        logger.info("Limited to %d documents (--limit-docs)", len(docs))

    logger.info("Loaded %d documents from %s", doc_count_loaded, raw_dir)

    # 2) Process each document
    doc_count_processed = 0
    doc_count_failed = 0
    doc_count_zero_chunks = 0
    all_chunks: list[dict] = []
    doc_records: list[dict] = []
    doc_lengths: list[tuple[str, int]] = []
    chunk_texts: list[str] = []

    for doc in docs:
        try:
            cleaned_text = clean_pdf_text(doc.get("text", ""))
            doc["text"] = cleaned_text
            cleaned_len = len(cleaned_text)

            chunks = chunk_document(
                doc,
                max_len_chars=args.max_len_chars,
                overlap_chars=args.overlap_chars,
                strategy=args.strategy,
            )

            # Filter by min_chunk_chars
            chunks = [c for c in chunks if len(c.get("text", "")) >= args.min_chunk_chars]

            if not chunks:
                logger.warning("Document %s produced zero chunks (after filtering)", doc.get("id", "?"))
                doc_count_zero_chunks += 1

            for c in chunks:
                all_chunks.append(c)
                chunk_texts.append(c.get("text", ""))

            doc_count_processed += 1
            doc_lengths.append((doc.get("id", "?"), cleaned_len))

            # Document record for JSONL (metadata + cleaned_text, avoid huge duplication)
            doc_record = {
                "id": doc.get("id"),
                "title": doc.get("title"),
                "source": doc.get("source"),
                "source_type": doc.get("source_type"),
                "language": doc.get("language"),
                "author": doc.get("author"),
                "year": doc.get("year"),
                "url": doc.get("url"),
                "filepath": doc.get("filepath"),
                "cleaned_text_length": cleaned_len,
                "chunk_count": len(chunks),
            }
            doc_record["cleaned_text"] = cleaned_text
            doc_records.append(doc_record)

        except Exception as e:
            doc_count_failed += 1
            logger.exception("Failed to process document %s: %s", doc.get("id", "?"), e)

    # 3) Write JSONL files
    with open(documents_out, "w", encoding="utf-8") as f:
        for rec in doc_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    with open(chunks_out, "w", encoding="utf-8") as f:
        for c in all_chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # 4) Build summary
    chunk_lengths = [len(c.get("text", "")) for c in all_chunks]
    source_type_counts = dict(Counter(c.get("source_type", "raw") for c in all_chunks))
    language_counts = dict(Counter(c.get("language", "fi") for c in all_chunks))

    # Duplicate chunk estimate (exact text match)
    text_to_count: Counter[str] = Counter(chunk_texts)
    duplicate_count = sum(1 for _, cnt in text_to_count.items() if cnt > 1)
    duplicate_chunk_estimate = sum(cnt - 1 for cnt in text_to_count.values() if cnt > 1)

    doc_lengths_sorted_desc = sorted(doc_lengths, key=lambda x: x[1], reverse=True)
    doc_lengths_sorted_asc = sorted(doc_lengths, key=lambda x: x[1])
    top10_longest = [{"id": d[0], "length": d[1]} for d in doc_lengths_sorted_desc[:10]]
    top10_shortest = [{"id": d[0], "length": d[1]} for d in doc_lengths_sorted_asc[:10]]

    summary = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "raw_dir": str(raw_dir),
        "document_count_loaded": doc_count_loaded,
        "document_count_processed": doc_count_processed,
        "document_count_failed": doc_count_failed,
        "document_count_zero_chunks": doc_count_zero_chunks,
        "chunk_count_total": len(all_chunks),
        "avg_chunk_length_chars": sum(chunk_lengths) / len(chunk_lengths) if chunk_lengths else 0,
        "min_chunk_length_chars": min(chunk_lengths) if chunk_lengths else 0,
        "max_chunk_length_chars": max(chunk_lengths) if chunk_lengths else 0,
        "source_type_counts": source_type_counts,
        "language_counts": language_counts,
        "parameters": {
            "max_len_chars": args.max_len_chars,
            "overlap_chars": args.overlap_chars,
            "strategy": args.strategy,
            "min_chunk_chars": args.min_chunk_chars,
            "limit_docs": args.limit_docs,
        },
        "output_paths": {
            "documents": str(documents_out),
            "chunks": str(chunks_out),
            "summary": str(summary_out),
        },
        "top_10_longest_documents": top10_longest,
        "top_10_shortest_documents": top10_shortest,
        "duplicate_chunk_estimate": {
            "unique_text_count": len(text_to_count),
            "duplicate_text_groups": duplicate_count,
            "redundant_chunks_estimate": duplicate_chunk_estimate,
        },
    }

    with open(summary_out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    return summary


def main() -> None:
    args = parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    summary = run_preprocess(args)

    # Console summary
    print("\n" + "=" * 60)
    print("PREPROCESS SUMMARY")
    print("=" * 60)
    print(f"Documents loaded:     {summary['document_count_loaded']}")
    print(f"Documents processed:  {summary['document_count_processed']}")
    print(f"Documents failed:     {summary['document_count_failed']}")
    print(f"Documents (0 chunks): {summary['document_count_zero_chunks']}")
    print(f"Chunks total:         {summary['chunk_count_total']}")
    if summary["chunk_count_total"] > 0:
        print(f"Avg chunk length:     {summary['avg_chunk_length_chars']:.1f} chars")
        print(f"Min / max chunk:     {summary['min_chunk_length_chars']} / {summary['max_chunk_length_chars']} chars")
    print("-" * 60)
    print("Output files:")
    for k, v in summary["output_paths"].items():
        print(f"  {k}: {v}")
    print("=" * 60)


if __name__ == "__main__":
    main()

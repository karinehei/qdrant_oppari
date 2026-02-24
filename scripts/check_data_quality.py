#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data Quality Check Script

Validates preprocessed corpus (documents.jsonl, chunks.jsonl) before indexing.
Reports document/chunk stats, anomalies, and potential issues.

Usage:
    python scripts/check_data_quality.py
    python scripts/check_data_quality.py --verbose --min-doc-chars 300
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from collections import Counter
from pathlib import Path
from statistics import median

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check quality of preprocessed documents and chunks"
    )
    parser.add_argument(
        "--documents-path",
        default="data/processed/documents.jsonl",
        help="Path to documents.jsonl",
    )
    parser.add_argument(
        "--chunks-path",
        default="data/processed/chunks.jsonl",
        help="Path to chunks.jsonl",
    )
    parser.add_argument(
        "--report-out",
        default="outputs/logs/data_quality_report.json",
        help="Output path for JSON report",
    )
    parser.add_argument(
        "--min-doc-chars",
        type=int,
        default=500,
        help="Threshold for short documents (default: 500)",
    )
    parser.add_argument(
        "--min-chunk-chars",
        type=int,
        default=100,
        help="Threshold for short chunks (default: 100)",
    )
    parser.add_argument(
        "--max-chunk-chars",
        type=int,
        default=960,
        help="Threshold for long chunks (max_len*1.2 for 800) (default: 960)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def run_quality_check(args: argparse.Namespace) -> dict:
    """Run quality checks and return report dict."""
    def resolve(p: str) -> Path:
        path = Path(p)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    docs_path = resolve(args.documents_path)
    chunks_path = resolve(args.chunks_path)
    report_path = resolve(args.report_out)

    if not docs_path.exists():
        raise FileNotFoundError(f"Documents file not found: {docs_path}")

    if not chunks_path.exists():
        raise FileNotFoundError(f"Chunks file not found: {chunks_path}")

    # Load documents
    documents: list[dict] = []
    for line in docs_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            documents.append(json.loads(line))
        except json.JSONDecodeError as e:
            logger.warning("Skipping invalid document line: %s", e)
            continue

    # Load chunks
    chunks: list[dict] = []
    for line in chunks_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            chunks.append(json.loads(line))
        except json.JSONDecodeError as e:
            logger.warning("Skipping invalid chunk line: %s", e)
            continue

    # Document stats
    doc_lengths = []
    empty_docs: list[str] = []
    short_docs: list[tuple[str, int]] = []
    docs_with_zero_chunks: list[str] = []
    doc_id_to_chunk_count: set[str] = set()

    for d in documents:
        doc_id = d.get("id", "?")
        length = d.get("cleaned_text_length", 0) or len(d.get("cleaned_text", ""))
        if not isinstance(length, int):
            length = 0
        doc_lengths.append(length)
        if length == 0:
            empty_docs.append(doc_id)
        elif length < args.min_doc_chars:
            short_docs.append((doc_id, length))
        chunk_count = d.get("chunk_count", 0)
        if chunk_count == 0:
            docs_with_zero_chunks.append(doc_id)
        doc_id_to_chunk_count.add(doc_id)

    # Chunk stats
    chunk_lengths = []
    short_chunks: list[tuple[str, int]] = []
    long_chunks: list[tuple[str, int]] = []
    chunk_texts: list[str] = []
    suspicious_chunks: list[dict] = []

    for c in chunks:
        text = c.get("text", "") or ""
        length = len(text)
        chunk_id = c.get("chunk_id", c.get("uid", "?"))
        chunk_lengths.append(length)
        if length < args.min_chunk_chars:
            short_chunks.append((chunk_id, length))
        if length > args.max_chunk_chars:
            long_chunks.append((chunk_id, length))
        chunk_texts.append(text)
        if length < args.min_chunk_chars or (text and not re.search(r"[a-zäöåA-ZÄÖÅ]", text)):
            suspicious_chunks.append({
                "chunk_id": chunk_id,
                "length": length,
                "preview": text[:80] + "..." if len(text) > 80 else text,
            })

    # Duplicate chunks (normalized: strip whitespace)
    text_to_count: Counter[str] = Counter(t.strip() for t in chunk_texts if t)
    duplicate_count = sum(1 for _, cnt in text_to_count.items() if cnt > 1)
    redundant_estimate = sum(cnt - 1 for cnt in text_to_count.values() if cnt > 1)

    # Source type and year
    source_type_counts = dict(Counter(c.get("source_type", "raw") for c in chunks))
    year_counts: dict[str, int] = {}
    for c in chunks:
        y = c.get("year")
        key = str(y) if y is not None else "null"
        year_counts[key] = year_counts.get(key, 0) + 1

    # Docs with chunks but not in documents.jsonl
    chunk_doc_ids = {c.get("doc_id", c.get("source", "")) for c in chunks}
    doc_ids = {d.get("id", "") for d in documents}
    orphan_doc_ids = chunk_doc_ids - doc_ids

    # Top suspicious lines (repeated header/footer patterns)
    line_to_count: Counter[str] = Counter()
    for text in chunk_texts:
        for line in text.split("\n"):
            line = line.strip()
            if len(line) > 5 and len(line) < 120:
                line_to_count[line] += 1
    top_suspicious_lines = [
        {"line": line, "count": cnt}
        for line, cnt in line_to_count.most_common(20)
        if cnt >= 2
    ][:20]

    # Build report
    report = {
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "empty_document_count": len(empty_docs),
        "empty_document_ids": empty_docs[:50],
        "short_document_count": len(short_docs),
        "short_documents": short_docs[:20],
        "document_count_zero_chunks": len(docs_with_zero_chunks),
        "documents_zero_chunks": docs_with_zero_chunks[:20],
        "short_chunk_count": len(short_chunks),
        "short_chunks_sample": short_chunks[:20],
        "long_chunk_count": len(long_chunks),
        "long_chunks_sample": long_chunks[:20],
        "chunk_length_stats": {
            "min": min(chunk_lengths) if chunk_lengths else 0,
            "max": max(chunk_lengths) if chunk_lengths else 0,
            "avg": sum(chunk_lengths) / len(chunk_lengths) if chunk_lengths else 0,
            "median": median(chunk_lengths) if chunk_lengths else 0,
        },
        "duplicate_chunk_count": duplicate_count,
        "redundant_chunks_estimate": redundant_estimate,
        "source_type_counts": source_type_counts,
        "year_counts": year_counts,
        "orphan_chunk_doc_ids": list(orphan_doc_ids)[:20],
        "top_suspicious_lines": top_suspicious_lines,
        "suspicious_chunks_sample": suspicious_chunks[:10],
        "parameters": {
            "min_doc_chars": args.min_doc_chars,
            "min_chunk_chars": args.min_chunk_chars,
            "max_chunk_chars": args.max_chunk_chars,
        },
    }

    ensure_parent(report_path)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    return report


def main() -> None:
    args = parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )

    try:
        report = run_quality_check(args)
    except FileNotFoundError as e:
        logger.error("%s", e)
        sys.exit(1)

    # Console summary
    print("\n" + "=" * 60)
    print("DATA QUALITY REPORT")
    print("=" * 60)
    print(f"Documents:          {report['document_count']}")
    print(f"Chunks:             {report['chunk_count']}")
    print(f"Empty docs:         {report['empty_document_count']}")
    print(f"Short docs (<{args.min_doc_chars}): {report['short_document_count']}")
    print(f"Docs with 0 chunks: {report['document_count_zero_chunks']}")
    print(f"Short chunks (<{args.min_chunk_chars}): {report['short_chunk_count']}")
    print(f"Long chunks (>{args.max_chunk_chars}): {report['long_chunk_count']}")
    print("-" * 60)
    stats = report["chunk_length_stats"]
    print(f"Chunk length: min={stats['min']}, max={stats['max']}, avg={stats['avg']:.1f}, median={stats['median']:.1f}")
    print(f"Duplicate chunks (exact): {report['duplicate_chunk_count']} groups, ~{report['redundant_chunks_estimate']} redundant")
    print(f"Source types: {report['source_type_counts']}")
    print("=" * 60)


if __name__ == "__main__":
    main()

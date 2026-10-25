# -*- coding: utf-8 -*-
"""
Annotations Module

Handles query and gold annotation JSONL formats for RAG evaluation.
Provides read/write, validation, and helper functions to combine queries with gold.

Formats:
- QueryRecord: query_id, query_text, category, language
- GoldAnnotation: query_id, relevant_doc_ids (list), relevant_chunk_ids (list, optional), notes (optional)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, TypedDict, cast

__all__ = [
    "QueryRecord",
    "GoldAnnotation",
    "load_queries",
    "load_gold_annotations",
    "save_queries",
    "save_gold_annotations",
    "validate_queries",
    "validate_gold_annotations",
    "load_queries_with_gold",
]

logger = logging.getLogger(__name__)


class QueryRecord(TypedDict, total=False):
    """Query record format. query_id and query_text are required."""
    query_id: str
    query_text: str
    category: str
    language: str


class GoldAnnotation(TypedDict, total=False):
    """Gold annotation format. query_id and relevant_doc_ids are required."""
    query_id: str
    relevant_doc_ids: list[str]
    relevant_chunk_ids: list[str]
    notes: str


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load JSONL file. Skips empty lines and invalid JSON."""
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            logger.warning("Line %d in %s: invalid JSON: %s", i, path, e)
    return records


def _save_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Save records as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_queries(path: str | Path) -> list[QueryRecord]:
    """Load queries from JSONL. Returns list of QueryRecord dicts."""
    path = Path(path)
    raw = _load_jsonl(path)
    return cast(list[QueryRecord], [r for r in raw if isinstance(r, dict)])


def load_gold_annotations(path: str | Path) -> list[GoldAnnotation]:
    """Load gold annotations from JSONL. Returns list of GoldAnnotation dicts."""
    path = Path(path)
    raw = _load_jsonl(path)
    return cast(list[GoldAnnotation], [r for r in raw if isinstance(r, dict)])


def save_queries(path: str | Path, queries: list[QueryRecord]) -> None:
    """Save queries to JSONL."""
    _save_jsonl(Path(path), cast(list[dict[str, Any]], queries))


def save_gold_annotations(path: str | Path, annotations: list[GoldAnnotation]) -> None:
    """Save gold annotations to JSONL."""
    _save_jsonl(Path(path), cast(list[dict[str, Any]], annotations))


def validate_queries(queries: list[QueryRecord]) -> tuple[list[QueryRecord], list[str]]:
    """
    Validate queries. Returns (valid_queries, error_messages).
    Checks: query_id present, query_text non-empty, no duplicate query_ids.
    """
    valid: list[QueryRecord] = []
    errors: list[str] = []
    seen_ids: set[str] = set()

    for i, q in enumerate(queries):
        qid = q.get("query_id")
        text = q.get("query_text", "")

        if not qid or not isinstance(qid, str):
            errors.append(f"Query row {i+1}: missing or invalid query_id")
            continue
        if qid in seen_ids:
            errors.append(f"Query {qid}: duplicate query_id")
            continue
        seen_ids.add(qid)

        if not text or not isinstance(text, str) or not text.strip():
            errors.append(f"Query {qid}: missing or empty query_text")
            continue

        valid.append(q)

    return valid, errors


def validate_gold_annotations(
    annotations: list[GoldAnnotation],
    known_query_ids: set[str] | None = None,
) -> tuple[list[GoldAnnotation], list[str]]:
    """
    Validate gold annotations. Returns (valid_annotations, error_messages).
    Checks: query_id present, relevant_doc_ids is list, no duplicate query_ids.
    If known_query_ids given, warns about annotations for unknown queries.
    """
    valid: list[GoldAnnotation] = []
    errors: list[str] = []
    seen_ids: set[str] = set()

    for i, g in enumerate(annotations):
        qid = g.get("query_id")

        if not qid or not isinstance(qid, str):
            errors.append(f"Gold row {i+1}: missing or invalid query_id")
            continue
        if qid in seen_ids:
            errors.append(f"Gold {qid}: duplicate query_id")
            continue
        seen_ids.add(qid)

        doc_ids = g.get("relevant_doc_ids")
        if doc_ids is not None and not isinstance(doc_ids, list):
            errors.append(f"Gold {qid}: relevant_doc_ids must be a list")
            continue
        if doc_ids is None:
            doc_ids = []
        if not all(isinstance(x, str) for x in doc_ids):
            errors.append(f"Gold {qid}: relevant_doc_ids must contain strings")
            continue

        chunk_ids = g.get("relevant_chunk_ids")
        if chunk_ids is not None and not isinstance(chunk_ids, list):
            errors.append(f"Gold {qid}: relevant_chunk_ids must be a list")
            continue
        if chunk_ids is None:
            chunk_ids = []

        if known_query_ids is not None and qid not in known_query_ids:
            errors.append(f"Gold {qid}: query_id not found in queries")
            continue

        valid.append(g)

    return valid, errors


def load_queries_with_gold(
    queries_path: str | Path,
    gold_path: str | Path,
) -> list[dict[str, Any]]:
    """
    Load and combine queries with their gold annotations.
    Returns list of dicts: {query_id, query_text, category, language, relevant_doc_ids, relevant_chunk_ids, notes}.
    Only includes queries that exist; gold without matching query is skipped.
    """
    queries = load_queries(queries_path)
    golds = load_gold_annotations(gold_path)

    valid_queries, _ = validate_queries(queries)
    query_by_id = {q["query_id"]: q for q in valid_queries}

    combined: list[dict[str, Any]] = []
    for g in golds:
        qid = g.get("query_id")
        if qid not in query_by_id:
            continue
        q = query_by_id[qid]
        combined.append({
            "query_id": qid,
            "query_text": q.get("query_text", ""),
            "category": q.get("category", ""),
            "language": q.get("language", "fi"),
            "relevant_doc_ids": g.get("relevant_doc_ids") or [],
            "relevant_chunk_ids": g.get("relevant_chunk_ids") or [],
            "notes": g.get("notes", ""),
        })

    return combined

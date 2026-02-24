#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Validate Annotations Script

Validates queries.jsonl and gold_annotations.jsonl format and consistency.
Reports errors and summary statistics.

Usage:
    python scripts/validate_annotations.py
    python scripts/validate_annotations.py --queries-path data/annotations/queries.jsonl
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from annotations import (
    load_queries,
    load_gold_annotations,
    validate_queries,
    validate_gold_annotations,
    load_queries_with_gold,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate query and gold annotation files"
    )
    parser.add_argument(
        "--queries-path",
        default="data/annotations/queries.jsonl",
        help="Path to queries.jsonl",
    )
    parser.add_argument(
        "--gold-path",
        default="data/annotations/gold_annotations.jsonl",
        help="Path to gold_annotations.jsonl",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show all validation details",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    def resolve(p: str) -> Path:
        path = Path(p)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path

    queries_path = resolve(args.queries_path)
    gold_path = resolve(args.gold_path)

    has_errors = False

    # Load and validate queries
    if not queries_path.exists():
        print(f"ERROR: Queries file not found: {queries_path}")
        sys.exit(1)

    queries_raw = load_queries(queries_path)
    valid_queries, query_errors = validate_queries(queries_raw)

    if query_errors:
        has_errors = True
        print("\n--- Query validation errors ---")
        for e in query_errors:
            print(f"  {e}")

    # Load and validate gold
    if not gold_path.exists():
        print(f"ERROR: Gold file not found: {gold_path}")
        sys.exit(1)

    gold_raw = load_gold_annotations(gold_path)
    known_ids = {q["query_id"] for q in valid_queries}
    valid_gold, gold_errors = validate_gold_annotations(gold_raw, known_query_ids=known_ids)

    if gold_errors:
        has_errors = True
        print("\n--- Gold validation errors ---")
        for e in gold_errors:
            print(f"  {e}")

    # Combined load (queries with gold)
    combined = load_queries_with_gold(queries_path, gold_path)

    # Summary
    print("\n" + "=" * 50)
    print("VALIDATION SUMMARY")
    print("=" * 50)
    print(f"Queries loaded:       {len(queries_raw)}")
    print(f"Queries valid:       {len(valid_queries)}")
    print(f"Queries with errors: {len(queries_raw) - len(valid_queries)}")
    print("-" * 50)
    print(f"Gold loaded:         {len(gold_raw)}")
    print(f"Gold valid:          {len(valid_gold)}")
    print(f"Gold with errors:    {len(gold_raw) - len(valid_gold)}")
    print("-" * 50)
    print(f"Queries with gold:   {len(combined)}")
    queries_without_gold = len(valid_queries) - len(combined)
    gold_without_query = len(gold_raw) - len(valid_gold)
    if queries_without_gold > 0:
        print(f"Queries missing gold: {queries_without_gold}")
    if gold_without_query > 0:
        print(f"Gold rows rejected:  {gold_without_query}")
    print("=" * 50)

    if has_errors:
        print("\nValidation FAILED (see errors above)")
        sys.exit(1)
    else:
        print("\nValidation OK")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Report Tables Script

Reads retrieval experiment output files and produces thesis-ready report tables
(CSV + Markdown) for ablation comparison, latency, and optional groundedness.

Usage:
    python scripts/build_report_tables.py
    python scripts/build_report_tables.py --input-dir outputs/experiments
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

# Logical config order for tables
CONFIG_ORDER = ["C0_baseline", "C1_mmr", "C2_mmr_rerank", "C3_mmr_rerank_dedupe"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build report tables from retrieval experiment outputs"
    )
    parser.add_argument(
        "--input-dir",
        default="outputs/experiments",
        help="Input directory (default: outputs/experiments)",
    )
    parser.add_argument(
        "--metrics-summary",
        default=None,
        help="Override path to metrics_summary.csv",
    )
    parser.add_argument(
        "--per-query-metrics",
        default=None,
        help="Override path to per_query_metrics.csv",
    )
    parser.add_argument(
        "--run-metadata",
        default=None,
        help="Override path to run_metadata.json",
    )
    parser.add_argument(
        "--groundedness-summary",
        default=None,
        help="Override path to groundedness summary (optional)",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Output directory (default: same as input-dir)",
    )
    parser.add_argument(
        "--round-digits",
        type=int,
        default=3,
        help="Decimal places for rounding (default: 3)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    return parser.parse_args()


def resolve_path(p: str, base: Path) -> Path:
    """Resolve path; if relative, treat as relative to project root."""
    path = Path(p)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def load_csv(path: Path) -> list[dict[str, Any]]:
    """Load CSV with header. Returns list of dicts."""
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def load_json(path: Path) -> dict[str, Any] | None:
    """Load JSON file. Returns None if missing or invalid."""
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load %s: %s", path, e)
        return None


def _round_val(val: Any, digits: int) -> str | None:
    """Round numeric value or return NA for missing."""
    if val is None or val == "":
        return "NA"
    try:
        f = float(val)
        return str(round(f, digits))
    except (TypeError, ValueError):
        return str(val)


def _sort_configs(configs: list[str]) -> list[str]:
    """Sort configs by logical order (C0, C1, C2, C3)."""
    seen = set(CONFIG_ORDER)
    ordered = [c for c in CONFIG_ORDER if c in configs]
    return ordered + [c for c in sorted(configs) if c not in seen]


def _std(values: list[float]) -> float:
    """Compute sample standard deviation."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    var = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(var)


def run_build(args: argparse.Namespace) -> bool:
    """Build report tables. Returns True if successful."""
    in_dir = resolve_path(args.input_dir, PROJECT_ROOT)
    out_dir = resolve_path(args.output_dir or args.input_dir, PROJECT_ROOT)
    out_dir.mkdir(parents=True, exist_ok=True)
    digits = args.round_digits

    # Resolve input paths
    metrics_path = resolve_path(args.metrics_summary or str(in_dir / "metrics_summary.csv"), PROJECT_ROOT)
    per_query_path = resolve_path(args.per_query_metrics or str(in_dir / "per_query_metrics.csv"), PROJECT_ROOT)
    metadata_path = resolve_path(args.run_metadata or str(in_dir / "run_metadata.json"), PROJECT_ROOT)
    groundedness_path: Path | None = None
    if args.groundedness_summary:
        groundedness_path = resolve_path(args.groundedness_summary, PROJECT_ROOT)
    elif (in_dir / "groundedness_summary.csv").exists():
        groundedness_path = in_dir / "groundedness_summary.csv"

    missing: list[str] = []
    if not metrics_path.exists():
        missing.append(str(metrics_path))
    if not per_query_path.exists():
        missing.append(str(per_query_path))
    if not metadata_path.exists():
        missing.append(str(metadata_path))
    for m in missing:
        logger.warning("Input file not found: %s", m)

    if missing and not per_query_path.exists() and not metrics_path.exists():
        logger.error("No metrics data available. Run scripts/run_experiments.py first.")
        return False

    # Load data
    summary_rows = load_csv(metrics_path)
    per_query_rows = load_csv(per_query_path)
    metadata = load_json(metadata_path)
    groundedness_rows: list[dict[str, Any]] = []
    if groundedness_path and groundedness_path.exists():
        groundedness_rows = load_csv(groundedness_path)
        if groundedness_rows:
            logger.info("Loaded groundedness data from %s", groundedness_path)

    configs = _sort_configs(list({r["config_name"] for r in summary_rows}) if summary_rows else [])

    # --- report_table_ablation.csv ---
    ablation_rows: list[dict[str, Any]] = []
    if summary_rows:
        # Compute std from per_query if available
        ok_rows = [r for r in per_query_rows if r.get("status") == "ok"]
        recalls_by_config: dict[str, list[float]] = {c: [] for c in configs}
        ndcgs_by_config: dict[str, list[float]] = {c: [] for c in configs}
        for r in ok_rows:
            if r.get("recall_at_k") not in (None, ""):
                try:
                    recalls_by_config.setdefault(r["config_name"], []).append(float(r["recall_at_k"]))
                except (ValueError, KeyError):
                    pass
            if r.get("ndcg_at_k") not in (None, ""):
                try:
                    ndcgs_by_config.setdefault(r["config_name"], []).append(float(r["ndcg_at_k"]))
                except (ValueError, KeyError):
                    pass

        for c in configs:
            row = next((s for s in summary_rows if s.get("config_name") == c), None)
            if not row:
                continue
            ablation = {
                "config_name": c,
                "query_count": row.get("query_count", "NA"),
                "mean_recall_at_k": _round_val(row.get("mean_recall_at_k"), digits),
                "mean_ndcg_at_k": _round_val(row.get("mean_ndcg_at_k"), digits),
            }
            recalls = recalls_by_config.get(c, [])
            ndcgs = ndcgs_by_config.get(c, [])
            if recalls:
                ablation["std_recall_at_k"] = _round_val(_std(recalls), digits)
            else:
                ablation["std_recall_at_k"] = "NA"
            if ndcgs:
                ablation["std_ndcg_at_k"] = _round_val(_std(ndcgs), digits)
            else:
                ablation["std_ndcg_at_k"] = "NA"
            ablation_rows.append(ablation)

        ablation_path = out_dir / "report_table_ablation.csv"
        with open(ablation_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["config_name", "query_count", "mean_recall_at_k", "mean_ndcg_at_k", "std_recall_at_k", "std_ndcg_at_k"])
            w.writeheader()
            w.writerows(ablation_rows)
        logger.info("Wrote %s", ablation_path)

    # --- report_table_latency.csv ---
    latency_rows: list[dict[str, Any]] = []
    if summary_rows:
        for c in configs:
            row = next((s for s in summary_rows if s.get("config_name") == c), None)
            if not row:
                continue
            latency_rows.append({
                "config_name": c,
                "p50_latency_ms": _round_val(row.get("p50_latency_ms"), digits),
                "p95_latency_ms": _round_val(row.get("p95_latency_ms"), digits),
                "p99_latency_ms": _round_val(row.get("p99_latency_ms"), digits),
                "query_count": row.get("query_count", "NA"),
            })

        latency_path = out_dir / "report_table_latency.csv"
        with open(latency_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["config_name", "p50_latency_ms", "p95_latency_ms", "p99_latency_ms", "query_count"])
            w.writeheader()
            w.writerows(latency_rows)
        logger.info("Wrote %s", latency_path)

    # --- report_table_groundedness.csv (optional) ---
    groundedness_out: list[dict[str, Any]] = []
    if groundedness_rows:
        # Infer columns from first row
        cols = list(groundedness_rows[0].keys()) if groundedness_rows else []
        preferred = ["config_name", "prompt_variant", "groundedness_score", "mean_groundedness", "answer_count"]
        fieldnames = [x for x in preferred if x in cols] + [x for x in cols if x not in preferred]
        groundedness_out_path = out_dir / "report_table_groundedness.csv"
        with open(groundedness_out_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(groundedness_rows)
        logger.info("Wrote %s", groundedness_out_path)

    # --- report_table_best_config.csv ---
    best_rows: list[dict[str, Any]] = []
    best_ndcg: dict[str, Any] | None = None
    best_recall: dict[str, Any] | None = None
    best_latency: dict[str, Any] | None = None
    if summary_rows:
        # Best nDCG
        ndcg_candidates = [s for s in summary_rows if s.get("mean_ndcg_at_k") not in (None, "")]
        best_ndcg = max(ndcg_candidates, key=lambda x: float(x.get("mean_ndcg_at_k", 0)), default=None) if ndcg_candidates else None
        # Best recall
        recall_candidates = [s for s in summary_rows if s.get("mean_recall_at_k") not in (None, "")]
        best_recall = max(recall_candidates, key=lambda x: float(x.get("mean_recall_at_k", 0)), default=None) if recall_candidates else None
        # Best latency (lowest p50)
        lat_candidates = [s for s in summary_rows if s.get("p50_latency_ms") not in (None, "")]
        best_latency = min(lat_candidates, key=lambda x: float(x.get("p50_latency_ms", float("inf"))), default=None) if lat_candidates else None

        if best_ndcg:
            best_rows.append({"criterion": "best_ndcg_at_k", "config_name": best_ndcg.get("config_name", "NA"), "value": _round_val(best_ndcg.get("mean_ndcg_at_k"), digits)})
        if best_recall:
            best_rows.append({"criterion": "best_recall_at_k", "config_name": best_recall.get("config_name", "NA"), "value": _round_val(best_recall.get("mean_recall_at_k"), digits)})
        if best_latency:
            best_rows.append({"criterion": "best_p50_latency_ms", "config_name": best_latency.get("config_name", "NA"), "value": _round_val(best_latency.get("p50_latency_ms"), digits)})

        if best_rows:
            best_path = out_dir / "report_table_best_config.csv"
            with open(best_path, "w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=["criterion", "config_name", "value"])
                w.writeheader()
                w.writerows(best_rows)
            logger.info("Wrote %s", best_path)

    # --- report_tables.md ---
    md_lines: list[str] = []
    md_lines.append("# Retrieval Experiment Report Tables")
    md_lines.append("")
    md_lines.append(f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC*")
    md_lines.append("")

    if metadata:
        md_lines.append("## Run Summary")
        md_lines.append("")
        md_lines.append("| Parameter | Value |")
        md_lines.append("|-----------|-------|")
        for key in ["collection_name", "top_k", "eval_level", "queries_path", "gold_path", "configs_run", "query_count"]:
            val = metadata.get(key)
            if val is None:
                val = "-"
            elif isinstance(val, list):
                val = ", ".join(str(v) for v in val)
            md_lines.append(f"| {key} | {val} |")
        md_lines.append("")
    elif missing:
        md_lines.append("## Run Summary")
        md_lines.append("")
        md_lines.append("*run_metadata.json not found. Run scripts/run_experiments.py first.*")
        md_lines.append("")

    if ablation_rows:
        md_lines.append("## Ablation Comparison (Recall & nDCG)")
        md_lines.append("")
        md_lines.append("| config_name | query_count | mean_recall_at_k | mean_ndcg_at_k | std_recall_at_k | std_ndcg_at_k |")
        md_lines.append("|-------------|-------------|------------------|----------------|-----------------|---------------|")
        for r in ablation_rows:
            md_lines.append(f"| {r['config_name']} | {r['query_count']} | {r['mean_recall_at_k']} | {r['mean_ndcg_at_k']} | {r['std_recall_at_k']} | {r['std_ndcg_at_k']} |")
        md_lines.append("")

    if latency_rows:
        md_lines.append("## Latency Comparison")
        md_lines.append("")
        md_lines.append("| config_name | p50_latency_ms | p95_latency_ms | p99_latency_ms | query_count |")
        md_lines.append("|-------------|---------------|---------------|---------------|-------------|")
        for r in latency_rows:
            md_lines.append(f"| {r['config_name']} | {r['p50_latency_ms']} | {r['p95_latency_ms']} | {r['p99_latency_ms']} | {r['query_count']} |")
        md_lines.append("")

    if groundedness_rows:
        md_lines.append("## Groundedness Summary")
        md_lines.append("")
        cols = list(groundedness_rows[0].keys()) if groundedness_rows else []
        header = " | ".join(cols)
        md_lines.append(f"| {header} |")
        md_lines.append("|" + "---|" * len(cols))
        for r in groundedness_rows:
            md_lines.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
        md_lines.append("")

    if best_rows:
        md_lines.append("## Best Configurations (Auto-generated)")
        md_lines.append("")
        md_lines.append("| Criterion | Best Config | Value |")
        md_lines.append("|-----------|-------------|-------|")
        for r in best_rows:
            md_lines.append(f"| {r['criterion']} | {r['config_name']} | {r['value']} |")
        md_lines.append("")

        # Text summary
        md_lines.append("## Text Summary")
        md_lines.append("")
        if best_ndcg:
            md_lines.append(f"- **Paras nDCG@k** saavutettiin konfiguraatiolla **{best_ndcg.get('config_name', 'NA')}** (mean nDCG@k = {_round_val(best_ndcg.get('mean_ndcg_at_k'), digits)}).")
        if best_recall:
            md_lines.append(f"- **Paras recall@k** saavutettiin konfiguraatiolla **{best_recall.get('config_name', 'NA')}** (mean recall@k = {_round_val(best_recall.get('mean_recall_at_k'), digits)}).")
        if best_latency:
            md_lines.append(f"- **Pienin p50-latenssi** havaittiin konfiguraatiolla **{best_latency.get('config_name', 'NA')}** (p50 = {_round_val(best_latency.get('p50_latency_ms'), digits)} ms).")
        md_lines.append("")

    if missing:
        md_lines.append("## Missing Input Files")
        md_lines.append("")
        for m in missing:
            md_lines.append(f"- `{m}`")
        md_lines.append("")

    md_path = out_dir / "report_tables.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")
    logger.info("Wrote %s", md_path)

    return True


def main() -> None:
    args = parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    ok = run_build(args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

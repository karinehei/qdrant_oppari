#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate Case Studies Script

Produces an opinnäytetyö-friendly appendix (case_studies.md) from retrieval experiment
outputs. Shows concrete examples: question → retrieved sources → metrics → interpretation.

Workflow order (always run in this sequence):
  1. python scripts/generate_case_studies.py
  2. python scripts/format_case_studies_for_appendix.py

Usage:
    python scripts/generate_case_studies.py
    python scripts/generate_case_studies.py --config-focus C2_mmr_rerank --num-cases 10
    python scripts/generate_case_studies.py --include-snippets false
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate case studies Markdown from retrieval experiment outputs"
    )
    parser.add_argument(
        "--experiments-dir",
        default="outputs/experiments",
        help="Directory with experiment outputs (default: outputs/experiments)",
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
        "--output-path",
        default="outputs/experiments/case_studies.md",
        help="Output Markdown path (default: outputs/experiments/case_studies.md)",
    )
    parser.add_argument(
        "--top-k-hits",
        type=int,
        default=5,
        help="Number of top hits to show per case (default: 5)",
    )
    parser.add_argument(
        "--num-cases",
        type=int,
        default=8,
        help="Target number of cases (default: 8)",
    )
    parser.add_argument(
        "--config-focus",
        default=None,
        metavar="CONFIG",
        help="Focus case selection on this config_name; else use best by mean_ndcg",
    )
    parser.add_argument(
        "--include-snippets",
        type=lambda x: str(x).lower() not in ("false", "0", "no", "off"),
        default=True,
        metavar="BOOL",
        help="Include short text snippets from chunks (default: true). Use false to disable.",
    )
    parser.add_argument(
        "--no-snippets",
        dest="include_snippets",
        action="store_false",
        help="Disable snippets (shorthand for --include-snippets false)",
    )
    parser.add_argument(
        "--snippet-max-chars",
        type=int,
        default=200,
        help="Max characters per snippet (default: 200)",
    )
    parser.add_argument(
        "--chunks-path",
        default="data/processed/chunks.jsonl",
        help="Path to chunks.jsonl for snippets (default: data/processed/chunks.jsonl)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    return parser.parse_args()


def resolve_path(p: str, base: Path) -> Path:
    path = Path(p)
    if not path.is_absolute():
        path = base / path
    return path


def load_csv(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(dict(row))
    return rows


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("Failed to load %s: %s", path, e)
        return None


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def _round_val(val: Any, decimals: int = 3) -> str:
    """Format numeric value for display; return empty string if not numeric."""
    if val is None or val == "":
        return ""
    try:
        return f"{float(val):.{decimals}f}"
    except (TypeError, ValueError):
        return str(val)


def _sanitize_snippet(text: str, max_chars: int) -> str:
    """Compress newlines, trim to max_chars, remove excessive whitespace."""
    if not text or not isinstance(text, str):
        return ""
    s = re.sub(r"\s+", " ", text).strip()
    return (s[:max_chars] + "…") if len(s) > max_chars else s


def _load_chunk_snippets(chunks_path: Path, max_chars: int) -> dict[str, str]:
    """Load chunk_id -> snippet mapping from chunks.jsonl."""
    out: dict[str, str] = {}
    if not chunks_path.exists():
        return out
    for line in chunks_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            cid = obj.get("chunk_id") or obj.get("uid")
            text = obj.get("text", "")
            if cid and text:
                out[cid] = _sanitize_snippet(text, max_chars)
        except json.JSONDecodeError:
            continue
    return out


def _determine_focus_config(
    metrics_summary: list[dict[str, Any]],
    config_focus: str | None,
    per_query: list[dict[str, Any]],
) -> str:
    """Select focus config: --config-focus, or best by mean_ndcg, or C1_mmr, or first."""
    if config_focus:
        configs = {r.get("config_name") for r in per_query if r.get("config_name")}
        if config_focus in configs:
            return config_focus
        # Try base_config match for expanded configs
        for c in configs:
            if c == config_focus or (c and c.startswith(config_focus + "__")):
                return c
        logger.warning("Config %s not found, falling back to best config", config_focus)

    if metrics_summary:
        best = max(
            metrics_summary,
            key=lambda r: float(r.get("mean_ndcg_at_k") or 0),
        )
        return str(best.get("config_name", ""))

    configs = list({r.get("config_name") for r in per_query if r.get("config_name")})
    if "C1_mmr" in configs:
        return "C1_mmr"
    return configs[0] if configs else ""


def _select_cases(
    per_query: list[dict[str, Any]],
    focus_config: str,
    num_cases: int,
) -> list[tuple[str, str]]:
    """
    Select case query_ids. Returns list of (query_id, reason).
    Reasons: best_ndcg, worst_ndcg, latency_outlier, disagreement, diverse.
    """
    focus_rows = [r for r in per_query if r.get("config_name") == focus_config and r.get("status") == "ok"]
    by_query: dict[str, list[dict]] = {}
    for r in focus_rows:
        qid = r.get("query_id", "")
        if qid:
            by_query.setdefault(qid, []).append(r)

    selected: dict[str, str] = {}
    qids = list(by_query.keys())
    if not qids:
        return []

    # a) Top 2 by ndcg_at_k
    sorted_ndcg = sorted(
        qids,
        key=lambda q: float(by_query[q][0].get("ndcg_at_k") or 0),
        reverse=True,
    )
    for q in sorted_ndcg[:2]:
        if q not in selected:
            selected[q] = "best_ndcg"

    # b) Bottom 2 by ndcg_at_k (or recall_at_k)
    for q in sorted_ndcg[-2:]:
        if q not in selected:
            selected[q] = "worst_ndcg"

    # c) Highest latency (ensure we have at least one; may combine with worst)
    sorted_lat = sorted(
        qids,
        key=lambda q: float(by_query[q][0].get("latency_ms") or 0),
        reverse=True,
    )
    if sorted_lat:
        q_lat = sorted_lat[0]
        prev = selected.get(q_lat, "")
        selected[q_lat] = f"{prev}; latency_outlier".strip("; ") if prev else "latency_outlier"

    # d) Fill with disagreement / diverse
    all_configs = list({r.get("config_name") for r in per_query if r.get("config_name")})
    by_qid_all: dict[str, dict[str, dict]] = {}
    for r in per_query:
        if r.get("status") != "ok":
            continue
        qid = r.get("query_id", "")
        cfg = r.get("config_name", "")
        if qid and cfg:
            by_qid_all.setdefault(qid, {})[cfg] = r

    def has_disagreement(qid: str) -> bool:
        rows = by_qid_all.get(qid, {})
        recalls = [float(r.get("recall_at_k") or 0) for r in rows.values()]
        return len(set(recalls)) > 1 if len(recalls) > 1 else False

    disagreement_qids = [q for q in qids if has_disagreement(q) and q not in selected]
    for q in disagreement_qids[:2]:
        selected[q] = "disagreement"

    # Fill remaining with diverse (round-robin from remaining)
    remaining = [q for q in qids if q not in selected]
    for i, q in enumerate(remaining):
        if len(selected) >= num_cases:
            break
        selected[q] = "diverse"

    # Trim to num_cases, preserve order: best, worst, outlier, disagreement, diverse
    order = ["best_ndcg", "worst_ndcg", "latency_outlier", "disagreement", "diverse"]
    sorted_selected = sorted(
        selected.items(),
        key=lambda x: (order.index(x[1]) if x[1] in order else 99, x[0]),
    )
    return sorted_selected[:num_cases]


def run_generate(args: argparse.Namespace) -> bool:
    """Generate case_studies.md. Returns True if successful."""
    base = PROJECT_ROOT
    exp_dir = resolve_path(args.experiments_dir, base)
    queries_path = resolve_path(args.queries_path, base)
    gold_path = resolve_path(args.gold_path, base)
    out_path = resolve_path(args.output_path, base)
    chunks_path = resolve_path(args.chunks_path, base)

    # Required files
    per_query_path = exp_dir / "per_query_metrics.csv"
    hits_path = exp_dir / "retrieval_hits.csv"
    metadata_path = exp_dir / "run_metadata.json"
    metrics_summary_path = exp_dir / "metrics_summary.csv"

    missing: list[str] = []
    if not per_query_path.exists():
        missing.append(str(per_query_path))
    if not hits_path.exists():
        missing.append(str(hits_path))
    if not metadata_path.exists():
        missing.append(str(metadata_path))
    if not queries_path.exists():
        missing.append(str(queries_path))
    if not gold_path.exists():
        missing.append(str(gold_path))

    if missing:
        logger.error("Missing required files:\n  %s", "\n  ".join(missing))
        return False

    per_query = load_csv(per_query_path)
    hits = load_csv(hits_path)
    metadata = load_json(metadata_path) or {}
    queries = {q["query_id"]: q for q in load_jsonl(queries_path) if q.get("query_id")}
    gold_list = load_jsonl(gold_path)
    gold_by_id = {g["query_id"]: g for g in gold_list if g.get("query_id")}

    metrics_summary = load_csv(metrics_summary_path)
    focus_config = _determine_focus_config(
        metrics_summary, args.config_focus, per_query
    )
    if not focus_config:
        logger.error("Could not determine focus config")
        return False

    logger.info("Focus config: %s", focus_config)

    cases = _select_cases(per_query, focus_config, args.num_cases)
    if not cases:
        logger.error("No cases selected")
        return False

    # Snippets
    chunk_snippets: dict[str, str] = {}
    if args.include_snippets and chunks_path.exists():
        chunk_snippets = _load_chunk_snippets(chunks_path, args.snippet_max_chars)
        logger.info("Loaded %d chunk snippets", len(chunk_snippets))

    eval_level = metadata.get("eval_level", "doc")
    gold_key = "relevant_doc_ids" if eval_level == "doc" else "relevant_chunk_ids"

    # Build Markdown
    lines: list[str] = []
    lines.append("# Retrieval Case Studies")
    lines.append("")
    lines.append(f"*Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}*")
    lines.append("")

    # Metadata
    lines.append("## Run Metadata")
    lines.append("")
    meta_items = [
        ("collection_name", metadata.get("collection_name")),
        ("top_k", metadata.get("top_k")),
        ("initial_limit", metadata.get("initial_limit")),
        ("score_threshold", metadata.get("score_threshold")),
        ("eval_level", metadata.get("eval_level")),
        ("seed", metadata.get("seed")),
    ]
    for k, v in meta_items:
        if v is not None:
            lines.append(f"- **{k}:** {v}")
    if metadata.get("rerank_models_loaded"):
        lines.append(f"- **rerank_models_loaded:** {metadata['rerank_models_loaded']}")
    lines.append("")
    lines.append(
        "This appendix shows concrete retrieval examples: question, retrieved sources, "
        "metrics, and brief interpretation. Cases include best- and worst-performing "
        "queries, latency outliers, and config disagreements."
    )
    lines.append("")

    # Per case
    for idx, (query_id, reason) in enumerate(cases, 1):
        qrow = queries.get(query_id, {})
        gold_row = gold_by_id.get(query_id, {})
        query_text = qrow.get("query_text", "(no query text)")
        gold_ids = gold_row.get(gold_key) or []

        focus_rows = [
            r for r in per_query
            if r.get("query_id") == query_id and r.get("config_name") == focus_config and r.get("status") == "ok"
        ]
        focus_metrics = focus_rows[0] if focus_rows else {}

        recall = focus_metrics.get("recall_at_k")
        ndcg = focus_metrics.get("ndcg_at_k")
        lat = focus_metrics.get("latency_ms")
        recall_s = f"{float(recall):.4f}" if recall is not None and recall != "" else "N/A"
        ndcg_s = f"{float(ndcg):.4f}" if ndcg is not None and ndcg != "" else "N/A"
        lat_s = f"{float(lat):.1f}" if lat is not None and lat != "" else "N/A"

        gold_fmt = ", ".join(str(x) for x in gold_ids) if isinstance(gold_ids, list) else str(gold_ids)

        lines.append(f"## Case {idx} — {query_id}")
        lines.append("")
        lines.append(f"**Question:** {query_text}")
        lines.append("")
        lines.append(f"**Gold ({gold_key}):** {gold_fmt}")
        lines.append("")
        lines.append(f"**Focus config:** {focus_config}")
        lines.append("")
        lines.append(f"**Metrics (focus config):** recall@k={recall_s}, nDCG@k={ndcg_s}, latency_ms={lat_s}")
        lines.append("")

        # Top hits table
        focus_hits = [
            h for h in hits
            if h.get("query_id") == query_id and h.get("config_name") == focus_config
        ][: args.top_k_hits]

        lines.append("### Top hits (focus config, top K)")
        lines.append("")
        col_doc = "doc_id" if any(h.get("doc_id") for h in focus_hits) else "source"
        headers = ["rank", col_doc, "title", "score", "rerank_score"]
        if chunk_snippets:
            headers.append("snippet")
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("| " + " | ".join("---" for _ in headers) + " |")

        for h in focus_hits:
            rank = h.get("rank", "")
            doc = h.get("doc_id") or h.get("source") or ""
            title = (h.get("title") or "")[:60]
            score = _round_val(h.get("score"), 3)
            rr = _round_val(h.get("rerank_score"), 3)
            row = [str(rank), doc, title, score, rr]
            if chunk_snippets:
                cid = h.get("chunk_id") or h.get("uid")
                snip = chunk_snippets.get(cid, "") if cid else ""
                row.append(snip[:70] + "…" if len(snip) > 70 else snip)
            lines.append("| " + " | ".join(str(c).replace("|", "\\|") for c in row) + " |")
        lines.append("")

        # Comparison table
        all_cfg_rows = [r for r in per_query if r.get("query_id") == query_id and r.get("status") == "ok"]
        other_configs_succeeded = any(
            float(r.get("recall_at_k") or 0) > 0
            for r in all_cfg_rows
            if r.get("config_name") != focus_config
        )
        if all_cfg_rows:
            lines.append("### Comparison (all configs)")
            lines.append("")
            lines.append("| config_name | recall@k | nDCG@k | latency_ms |")
            lines.append("| --- | --- | --- | --- |")
            for r in all_cfg_rows:
                rc = r.get("recall_at_k")
                nd = r.get("ndcg_at_k")
                lt = r.get("latency_ms")
                rc_s = f"{float(rc):.4f}" if rc not in (None, "") else "N/A"
                nd_s = f"{float(nd):.4f}" if nd not in (None, "") else "N/A"
                lt_s = f"{float(lt):.1f}" if lt not in (None, "") else "N/A"
                lines.append(f"| {r.get('config_name', '')} | {rc_s} | {nd_s} | {lt_s} |")
            lines.append("")

        # Interpretation
        lines.append("### Interpretation")
        lines.append("")
        bullets: list[str] = []
        if recall is not None and recall != "":
            rv = float(recall)
            if rv >= 1.0:
                bullets.append("- **Success:** All gold documents/chunks were retrieved in top-k.")
            elif rv > 0:
                bullets.append(f"- **Partial:** {rv:.0%} of gold items retrieved (recall@k={rv:.2f}).")
            else:
                bullets.append("- **Failure:** No gold items in top-k (recall@k=0).")
        if ndcg is not None and ndcg != "":
            nv = float(ndcg)
            if nv >= 0.9:
                bullets.append("- Gold was ranked highly (nDCG@k ≥ 0.9).")
            elif nv > 0:
                bullets.append("- Gold appeared but ranking could be improved.")
            else:
                bullets.append("- Gold did not appear in top-k or was ranked very low.")
        if "latency_outlier" in reason and lat:
            bullets.append("- **Latency outlier:** High latency may be due to cold start, reranker load, or hardware variance.")
        if reason == "disagreement":
            bullets.append("- **Config disagreement:** Different configs produced different recall; worth comparing.")
        if recall is not None and float(recall or 0) == 0 and other_configs_succeeded:
            bullets.append("- **Config disagreement:** Another config retrieved the gold; focus config (e.g. reranker) pushed it out of top-k.")
        if len(bullets) < 2:
            bullets.append("- See comparison table for config-wise metrics.")
        for b in bullets[:5]:
            lines.append(b)
        lines.append("")
        lines.append("---")
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")

    # Summary
    print(f"\nGenerated: {out_path}")
    print("\nSelected cases:")
    for qid, reason in cases:
        print(f"  {qid}: {reason}")

    return True


def main() -> None:
    args = parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(levelname)s: %(message)s",
    )
    ok = run_generate(args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

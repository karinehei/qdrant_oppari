#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run Retrieval Experiments Script

Runs ablation experiments (baseline, MMR, rerank, dedupe) on annotated queries.
Computes recall@k, nDCG@k, latency; saves results for reporting.

Supports comparing multiple reranker models for C2/C3 configs via --rerank-models.

Usage:
    python scripts/run_experiments.py --dry-run
    python scripts/run_experiments.py --limit-queries 3
    python scripts/run_experiments.py --rerank-models cross-encoder/ms-marco-MiniLM-L-6-v2 BAAI/bge-reranker-v2-m3
    python scripts/run_experiments.py
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Add project root to path
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger(__name__)

# Ablation configs: C0=baseline, C1=+MMR, C2=+rerank, C3=+dedupe
# eval uses doc-level (relevant_doc_ids) or chunk-level (relevant_chunk_ids) per --eval-level
CONFIGS = {
    "C0_baseline": {
        "diversity": 0.0,
        "use_rerank": False,
        "skip_dedupe": True,
    },
    "C1_mmr": {
        "diversity": 0.35,
        "use_rerank": False,
        "skip_dedupe": True,
    },
    "C2_mmr_rerank": {
        "diversity": 0.35,
        "use_rerank": True,
        "skip_dedupe": True,
    },
    "C3_mmr_rerank_dedupe": {
        "diversity": 0.35,
        "use_rerank": True,
        "skip_dedupe": False,
        "dedupe_by_source": False,  # uid-based dedupe
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run retrieval ablation experiments"
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
        "--collection-name",
        default="rag_thesis_fi",
        help="Qdrant collection name (default: rag_thesis_fi)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-K results per query (default: 5)",
    )
    parser.add_argument(
        "--initial-limit",
        type=int,
        default=20,
        help="Initial retrieval limit for MMR (default: 20)",
    )
    parser.add_argument(
        "--score-threshold",
        type=float,
        default=0.0,
        help="Minimum similarity score (default: 0.0)",
    )
    parser.add_argument(
        "--eval-level",
        choices=["doc", "chunk"],
        default="doc",
        help="Eval level: doc=relevant_doc_ids, chunk=relevant_chunk_ids (default: doc)",
    )
    parser.add_argument(
        "--limit-queries",
        type=int,
        default=None,
        help="Limit number of queries (debug)",
    )
    parser.add_argument(
        "--configs",
        nargs="+",
        default=None,
        choices=list(CONFIGS.keys()),
        metavar="CONFIG",
        help="Run only these configs (default: all). E.g. --configs C0_baseline C1_mmr skips rerank.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only, no Qdrant searches",
    )
    parser.add_argument(
        "--output-dir",
        default="outputs/experiments",
        help="Output directory (default: outputs/experiments)",
    )
    parser.add_argument(
        "--qdrant-url",
        default="http://localhost:6333",
        help="Qdrant server URL (default: http://localhost:6333)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose logging",
    )
    parser.add_argument(
        "--debug-query-id",
        default=None,
        metavar="QUERY_ID",
        help="Enable rerank diagnostics for this query (e.g. q4). Saves to outputs/experiments/rerank_diagnostics_<id>.json",
    )
    parser.add_argument(
        "--rerank-models",
        nargs="+",
        default=None,
        metavar="MODEL",
        help="Compare multiple reranker models for C2/C3 configs. E.g. --rerank-models cross-encoder/ms-marco-MiniLM-L-6-v2 BAAI/bge-reranker-v2-m3",
    )
    parser.add_argument(
        "--compare-rerankers",
        action="store_true",
        help="Alias: same as --rerank-models with config default. Use --rerank-models for explicit list.",
    )
    return parser.parse_args()


def resolve_path(p: str) -> Path:
    path = Path(p)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _sanitize_rerank_suffix(model_name: str) -> str:
    """Filesystem-safe suffix from model name. E.g. cross-encoder/ms-marco-MiniLM-L-6-v2 -> msmarco_minilm."""
    s = model_name.replace("/", "_").replace("-", "_")
    s = "".join(c if c.isalnum() or c == "_" else "" for c in s)
    return s.lower()[:48] if s else "unknown"


_reranker_cache: dict[str, Any] = {}


def _get_reranker(model_name: str) -> tuple[Any | None, str | None]:
    """Load reranker lazily, cache by model name. Returns (instance, None) or (None, error_msg)."""
    if model_name in _reranker_cache:
        return _reranker_cache[model_name], None
    try:
        from sentence_transformers import CrossEncoder
        ce = CrossEncoder(model_name)
        _reranker_cache[model_name] = ce
        return ce, None
    except Exception as e:
        err = str(e)
        logger.warning("Failed to load reranker %s: %s", model_name, err)
        return None, err


def _expand_configs_for_rerankers(
    configs: dict[str, dict],
    rerank_models: list[str] | None,
    default_rerank_model: str,
) -> list[tuple[str, dict, str | None]]:
    """
    Expand configs for reranker comparison.
    Returns list of (effective_config_name, config_dict, reranker_model_name | None).
    For non-rerank configs: (name, cfg, None).
    For rerank configs with --rerank-models: (name__suffix, cfg, model) per model.
    """
    result: list[tuple[str, dict, str | None]] = []
    models = rerank_models if rerank_models else [default_rerank_model]

    for name, cfg in configs.items():
        if not cfg.get("use_rerank"):
            result.append((name, cfg, None))
            continue
        if rerank_models:
            for m in rerank_models:
                suffix = _sanitize_rerank_suffix(m)
                result.append((f"{name}__{suffix}", cfg, m))
        else:
            result.append((name, cfg, default_rerank_model))
    return result


def run_retrieval_config(
    client: Any,
    model: Any,
    cross_encoder: Any | None,
    query: str,
    config: dict[str, Any],
    top_k: int,
    initial_limit: int,
    score_threshold: float,
    collection_name: str,
    diagnostics: dict | None = None,
    eval_level: str = "doc",
) -> list[dict]:
    """Adapter: run retrieval with given config. Returns list of hit dicts."""
    from retrieval import search

    kwargs: dict[str, Any] = {
        "top_k": top_k,
        "initial_limit": initial_limit,
        "score_threshold": score_threshold,
        "collection_name": collection_name,
        "diversity": config.get("diversity", 0.35),
        "skip_dedupe": config.get("skip_dedupe", False),
        "diagnostics": diagnostics,
        "eval_level": eval_level,
    }
    if config.get("dedupe_by_source") is not None:
        kwargs["dedupe_by_source"] = config["dedupe_by_source"]
    if config.get("use_rerank") and cross_encoder is not None:
        kwargs["cross_encoder"] = cross_encoder
    else:
        kwargs["cross_encoder"] = None

    return search(client, model, query, **kwargs)


def _get_eval_id(r: dict, id_key: str | tuple[str, ...]) -> str | None:
    """Extract eval ID from result. id_key: 'source' for doc, ('chunk_id','uid') for chunk."""
    if isinstance(id_key, str):
        v = r.get(id_key)
        return str(v) if v is not None else None
    for k in id_key:
        v = r.get(k)
        if v:
            return str(v)
    return None


def compute_recall_ndcg(
    results: list[dict],
    expected: set[str],
    k: int,
    id_key: str | tuple[str, ...],
) -> tuple[float, float]:
    """Compute recall@k and nDCG@k. id_key: 'source' for doc, ('chunk_id','uid') for chunk.
    Recall@k = (# unique relevant IDs in top-k) / (# unique gold relevant IDs).
    """
    preds = [v for r in results if (v := _get_eval_id(r, id_key))]
    rel = [1 if p in expected else 0 for p in preds]
    # Unique relevant IDs in top-k (no duplicate counting)
    unique_hits = len(set(p for p in preds[:k] if p in expected))
    recall = unique_hits / len(expected) if expected else 0.0
    # Pad rel to k for ndcg (missing positions = 0)
    rel_padded = rel[:k] + [0] * max(0, k - len(rel))
    from utils.metrics_relevance import ndcg_at_k
    ndcg = ndcg_at_k(rel_padded, k)
    return recall, ndcg


def percentile_ms(times: list[float], p: float) -> float:
    """Compute percentile from list of times in ms."""
    if not times:
        return 0.0
    s = sorted(times)
    if p <= 0:
        return s[0]
    if p >= 100:
        return s[-1]
    idx = (p / 100) * (len(s) - 1)
    i = int(idx)
    if i >= len(s) - 1:
        return s[-1]
    return s[i] + (idx - i) * (s[i + 1] - s[i])


def run_experiments(args: argparse.Namespace) -> bool:
    """Run experiments. Returns True if successful."""
    queries_path = resolve_path(args.queries_path)
    gold_path = resolve_path(args.gold_path)
    out_dir = resolve_path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load queries + gold
    from annotations import load_queries_with_gold

    if not queries_path.exists():
        logger.error("Queries file not found: %s", queries_path)
        return False
    if not gold_path.exists():
        logger.error("Gold file not found: %s", gold_path)
        return False

    combined = load_queries_with_gold(queries_path, gold_path)
    if not combined:
        logger.error("No queries with gold found")
        return False

    # Set seed early for reproducibility
    from reproducibility import set_global_seed, build_reproducibility_metadata, get_git_commit_hash

    set_global_seed(args.seed)
    git_hash = get_git_commit_hash()
    git_short = (git_hash[:7] + "...") if git_hash and len(git_hash) > 7 else (git_hash or "n/a")

    if args.limit_queries:
        combined = combined[: args.limit_queries]
        logger.info("Limited to %d queries", len(combined))

    id_key: str | tuple[str, ...] = ("doc_id", "source") if args.eval_level == "doc" else ("chunk_id", "uid")
    expected_key = "relevant_doc_ids" if args.eval_level == "doc" else "relevant_chunk_ids"

    from config import EMBED_MODEL, RERANK_MODEL

    configs_to_run = {k: CONFIGS[k] for k in (args.configs or CONFIGS.keys())}
    rerank_models_arg = args.rerank_models
    if args.compare_rerankers and not rerank_models_arg:
        rerank_models_arg = [RERANK_MODEL]
    expanded = _expand_configs_for_rerankers(
        configs_to_run, rerank_models_arg, RERANK_MODEL
    )
    # base_config_name: C2_mmr_rerank__msmarco -> C2_mmr_rerank
    def _base_name(eff: str) -> str:
        return eff.split("__")[0] if "__" in eff else eff

    # Startup log summary
    logger.info(
        "Startup: seed=%d collection=%s qdrant_url=%s eval_level=%s query_count=%d configs=%s git=%s",
        args.seed,
        args.collection_name,
        args.qdrant_url,
        args.eval_level,
        len(combined),
        [e[0] for e in expanded],
        git_short,
    )

    if args.dry_run:
        logger.info("DRY RUN: would run %d queries × %d configs", len(combined), len(expanded))
        for eff_name, cfg, rerank_m in expanded:
            logger.info("  Config %s: diversity=%.2f, rerank=%s, reranker=%s",
                        eff_name, cfg.get("diversity", 0), cfg.get("use_rerank"),
                        rerank_m or "n/a")
        return True

    # Load deps (imports can take 30–60 s on first run)
    logger.info("Loading dependencies (qdrant-client, sentence-transformers)...")
    try:
        from qdrant_client import QdrantClient
        from sentence_transformers import SentenceTransformer, CrossEncoder
    except ImportError as e:
        logger.error("Missing dependency: %s", e)
        return False

    qdrant_url = args.qdrant_url
    try:
        logger.info("Connecting to Qdrant at %s...", qdrant_url)
        client = QdrantClient(url=qdrant_url)
        client.get_collections()
        logger.info("Qdrant connected")
    except Exception as e:
        logger.error("Cannot connect to Qdrant: %s", e)
        return False

    try:
        logger.info("Loading embedding model %s (may take a minute on first run)...", EMBED_MODEL)
        model = SentenceTransformer(EMBED_MODEL)
        # Reranker loaded lazily per config via _get_reranker()
        if rerank_models_arg:
            logger.info("Reranker comparison: %s", rerank_models_arg)
        elif any(cfg.get("use_rerank") for cfg in configs_to_run.values()):
            logger.info("Reranker: %s (loaded on first use)", RERANK_MODEL)
    except Exception as e:
        logger.error("Failed to load embedding model: %s", e)
        return False

    # Run experiments
    t0 = time.perf_counter()
    all_hits: list[dict] = []
    per_query_metrics: list[dict] = []
    config_latencies: dict[str, list[float]] = {e[0]: [] for e in expanded}
    rerank_loaded: list[str] = []
    rerank_failed: list[tuple[str, str]] = []
    chunk_warned = False

    for qrow in combined:
        qid = qrow["query_id"]
        query_text = qrow["query_text"]
        expected = set(qrow.get(expected_key) or [])
        query_diagnostics: dict[str, dict] = {}

        for effective_name, config, reranker_model_name in expanded:
            diag: dict[str, Any] | None = {} if (args.debug_query_id and qid == args.debug_query_id) else None
            base_name = _base_name(effective_name)

            # Resolve cross_encoder for rerank configs
            cross_encoder: Any | None = None
            if reranker_model_name:
                ce, err = _get_reranker(reranker_model_name)
                if err:
                    if reranker_model_name not in {m for m, _ in rerank_failed}:
                        rerank_failed.append((reranker_model_name, err))
                    logger.warning("Skipping %s (reranker %s failed): %s", effective_name, reranker_model_name, err)
                    per_query_metrics.append({
                        "query_id": qid,
                        "config_name": effective_name,
                        "rerank_model_name": reranker_model_name,
                        "base_config_name": base_name,
                        "recall_at_k": None,
                        "ndcg_at_k": None,
                        "latency_ms": None,
                        "status": "error",
                        "error": f"reranker load failed: {err}",
                    })
                    continue
                cross_encoder = ce
                if reranker_model_name not in rerank_loaded:
                    rerank_loaded.append(reranker_model_name)

            try:
                t_start = time.perf_counter()
                results = run_retrieval_config(
                    client, model, cross_encoder,
                    query_text, config,
                    top_k=args.top_k,
                    initial_limit=args.initial_limit,
                    score_threshold=args.score_threshold,
                    collection_name=args.collection_name,
                    diagnostics=diag,
                    eval_level=args.eval_level,
                )
                latency_ms = (time.perf_counter() - t_start) * 1000
                config_latencies[effective_name].append(latency_ms)

                recall, ndcg = compute_recall_ndcg(
                    results, expected, args.top_k, id_key
                )
                # Sanity check: recall must be in [0, 1]
                _RECALL_EPS = 1e-6
                if recall < 0 or recall > 1.0 + _RECALL_EPS:
                    logger.warning(
                        "recall@k out of range [0,1]: %.4f (query_id=%s config=%s)",
                        recall, qid, effective_name,
                    )

                per_query_metrics.append({
                    "query_id": qid,
                    "config_name": effective_name,
                    "rerank_model_name": reranker_model_name or "",
                    "base_config_name": base_name,
                    "recall_at_k": recall,
                    "ndcg_at_k": ndcg,
                    "latency_ms": round(latency_ms, 2),
                    "status": "ok",
                })

                if diag:
                    query_diagnostics[effective_name] = dict(diag)

                for rank, r in enumerate(results, 1):
                    all_hits.append({
                        "query_id": qid,
                        "config_name": effective_name,
                        "rerank_model_name": reranker_model_name or "",
                        "base_config_name": base_name,
                        "rank": rank,
                        "doc_id": r.get("doc_id") or r.get("source"),
                        "chunk_id": r.get("chunk_id") or r.get("uid"),
                        "uid": r.get("uid"),
                        "source": r.get("source"),
                        "score": r.get("score"),
                        "rerank_score": r.get("rerank_score"),
                        "title": (r.get("title") or "")[:80],
                    })

                # Startup warning: chunk-level eval but no chunk identifiers in first result
                if (
                    not chunk_warned
                    and args.eval_level == "chunk"
                    and results
                    and not any(r.get("chunk_id") or r.get("uid") for r in results)
                ):
                    logger.warning(
                        "eval_level=chunk but first retrieval result has no chunk_id/uid; "
                        "chunk-level metrics may be incorrect"
                    )
                    chunk_warned = True

            except Exception as e:
                logger.warning("Query %s config %s failed: %s", qid, effective_name, e)
                per_query_metrics.append({
                    "query_id": qid,
                    "config_name": effective_name,
                    "rerank_model_name": reranker_model_name or "",
                    "base_config_name": base_name,
                    "recall_at_k": None,
                    "ndcg_at_k": None,
                    "latency_ms": None,
                    "status": "error",
                    "error": str(e),
                })

        if args.debug_query_id and qid == args.debug_query_id and query_diagnostics:
            gold_ids = list(expected)
            full_diag: dict[str, Any] = {
                "query_id": qid,
                "eval_level": args.eval_level,
                "gold_ids": gold_ids,
                "initial_candidate_ids": next(
                    (d["initial_candidate_ids"] for d in query_diagnostics.values() if "initial_candidate_ids" in d),
                    [],
                ),
                "configs": {},
            }
            for c, d in query_diagnostics.items():
                final_ids = d.get("final_ids", [])
                overlap = list(set(final_ids) & expected)
                full_diag["configs"][c] = {
                    "final_ids": final_ids,
                    "pre_rerank_ids": d.get("pre_rerank_ids"),
                    "post_rerank_ids": d.get("post_rerank_ids"),
                    "overlap_with_gold": overlap,
                }
            diag_path = out_dir / f"rerank_diagnostics_{qid}.json"
            with open(diag_path, "w", encoding="utf-8") as f:
                json.dump(full_diag, f, indent=2, ensure_ascii=False)
            logger.info("Rerank diagnostics saved to %s", diag_path)

    duration = time.perf_counter() - t0

    # Write retrieval_hits.csv
    hits_path = out_dir / "retrieval_hits.csv"
    if all_hits:
        with open(hits_path, "w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=[
                "query_id", "config_name", "rerank_model_name", "base_config_name",
                "rank", "doc_id", "chunk_id", "uid",
                "source", "score", "rerank_score", "title"
            ])
            w.writeheader()
            w.writerows(all_hits)

    # Write per_query_metrics.csv
    metrics_path = out_dir / "per_query_metrics.csv"
    with open(metrics_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "query_id", "config_name", "rerank_model_name", "base_config_name",
            "recall_at_k", "ndcg_at_k",
            "latency_ms", "status", "error"
        ])
        w.writeheader()
        w.writerows(per_query_metrics)

    # Compute and write metrics_summary.csv
    summary_rows: list[dict] = []
    for config_name, latencies in config_latencies.items():
        rows = [p for p in per_query_metrics if p["config_name"] == config_name and p["status"] == "ok"]
        recalls = [r["recall_at_k"] for r in rows if r["recall_at_k"] is not None]
        ndcgs = [r["ndcg_at_k"] for r in rows if r["ndcg_at_k"] is not None]
        mean_recall = sum(recalls) / len(recalls) if recalls else 0
        mean_ndcg = sum(ndcgs) / len(ndcgs) if ndcgs else 0
        p50 = percentile_ms(latencies, 50) if latencies else 0
        p95 = percentile_ms(latencies, 95) if latencies else 0
        p99 = percentile_ms(latencies, 99) if latencies else 0
        first_row = rows[0] if rows else {}
        summary_rows.append({
            "config_name": config_name,
            "rerank_model_name": first_row.get("rerank_model_name", ""),
            "base_config_name": first_row.get("base_config_name", _base_name(config_name)),
            "query_count": len(rows),
            "mean_recall_at_k": round(mean_recall, 4),
            "mean_ndcg_at_k": round(mean_ndcg, 4),
            "p50_latency_ms": round(p50, 2),
            "p95_latency_ms": round(p95, 2),
            "p99_latency_ms": round(p99, 2),
        })

    summary_path = out_dir / "metrics_summary.csv"
    with open(summary_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=[
            "config_name", "rerank_model_name", "base_config_name",
            "query_count", "mean_recall_at_k", "mean_ndcg_at_k",
            "p50_latency_ms", "p95_latency_ms", "p99_latency_ms"
        ])
        w.writeheader()
        w.writerows(summary_rows)

    # Write run_metadata.json
    repro_meta = build_reproducibility_metadata(seed=args.seed)
    config_expansion = {
        "base_configs": list(configs_to_run.keys()),
        "expanded_configs": [e[0] for e in expanded],
        "rerank_models_used": list(set(reranker_model for _, _, reranker_model in expanded if reranker_model)),
    }
    metadata = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "seed": args.seed,
        "git_commit_hash": repro_meta.get("git_commit_hash"),
        "git_branch": repro_meta.get("git_branch"),
        "environment_info": repro_meta.get("environment_info"),
        "collection_name": args.collection_name,
        "qdrant_url": args.qdrant_url,
        "top_k": args.top_k,
        "initial_limit": args.initial_limit,
        "score_threshold": args.score_threshold,
        "eval_level": args.eval_level,
        "configs_run": list(configs_to_run.keys()),
        "rerank_models_requested": rerank_models_arg or [],
        "rerank_models_loaded": rerank_loaded,
        "rerank_models_failed": [{"model": m, "error": e} for m, e in rerank_failed],
        "config_expansion_summary": config_expansion,
        "queries_path": str(queries_path),
        "gold_path": str(gold_path),
        "query_count": len(combined),
        "duration_seconds": round(duration, 2),
    }
    with open(out_dir / "run_metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    # Console summary
    def _truncate(s: str, max_len: int = 40) -> str:
        return (s[:max_len] + "…") if len(s) > max_len else s

    print("\n" + "=" * 60)
    print("EXPERIMENT SUMMARY")
    print("=" * 60)
    for row in summary_rows:
        print(f"\n{row['config_name']}:")
        if row.get("rerank_model_name"):
            print(f"  reranker: {_truncate(row['rerank_model_name'])}")
        print(f"  mean recall@k: {row['mean_recall_at_k']:.4f}")
        print(f"  mean nDCG@k:  {row['mean_ndcg_at_k']:.4f}")
        print(f"  p50/p95/p99:  {row['p50_latency_ms']:.1f} / {row['p95_latency_ms']:.1f} / {row['p99_latency_ms']:.1f} ms")
    if rerank_failed:
        print("\n⚠ Reranker load failures:", [m for m, _ in rerank_failed])
    print("\n" + "=" * 60)
    print(f"Output: {out_dir}")

    return True


def main() -> None:
    args = parse_args()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    ok = run_experiments(args)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()

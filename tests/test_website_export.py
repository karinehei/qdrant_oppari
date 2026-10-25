# -*- coding: utf-8 -*-
"""Tests for the recorded-results website export."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("website_export", ROOT / "scripts" / "website_export.py")
assert spec and spec.loader
website_export = importlib.util.module_from_spec(spec)
spec.loader.exec_module(website_export)


def test_export_preserves_originals_and_schema(tmp_path: Path) -> None:
    before = website_export.original_hashes(ROOT)
    code = website_export.main(["--root", str(ROOT)])
    after = website_export.original_hashes(ROOT)
    assert code == 0
    assert before == after
    dataset = json.loads((ROOT / "web" / "src" / "data" / "research-dataset.json").read_text(encoding="utf-8"))
    assert dataset["schema_version"] == "1.0.0"
    assert dataset["original_experiment_commit"] != dataset["website_export_revision"]
    assert [run["id"] for run in dataset["runs"]] == ["ablation", "rerank"]
    assert dataset["annotations"]["evaluation_level"] == "doc"
    assert dataset["models"]["top_k"] == 5
    assert len(dataset["questions"]) == 30
    for run in dataset["runs"]:
        assert {row["query_count"] for row in run["aggregates"]} == {30}
        assert "subset_mean_recall_at_k" not in run
    text = json.dumps(dataset)
    assert "/mnt/" not in text
    assert "hostname" not in text
    assert "cleaned_text\"" not in text
    assert "snippet" not in text
    assert dataset["groundedness"]["included_in_main_results"] is False
    assert dataset["excluded_snapshots"][0]["included_in_website_results"] is False
    assert dataset["excluded_snapshots"][0]["query_count"] == 6
    q5 = next(case for case in dataset["case_studies"] if case.get("query_id") == "q5")
    assert q5["show_as_thesis_verified"] is False
    assert dataset["validation"]["release_blocked"] is True
    trace = (ROOT / "docs" / "publication_traceability.md").read_text(encoding="utf-8")
    assert "Taulukko 3" in trace
    assert "q5" in trace
    del tmp_path


def test_strict_publication_check_fails() -> None:
    assert website_export.main(["--strict-publication", "--root", str(ROOT)]) == 1


def test_runs_keep_separate_latency() -> None:
    dataset = website_export.build_dataset(ROOT)
    ablation = next(row for row in dataset["runs"][0]["aggregates"] if row["config_name"] == "C0_baseline")
    rerank = next(row for row in dataset["runs"][1]["aggregates"] if row["config_name"] == "C0_baseline")
    assert ablation["p50_latency_ms"] == 26.09
    assert rerank["p50_latency_ms"] == 20.23
    assert ablation["quality_publication_status"] == "verified_table_3"
    assert rerank["latency_publication_status"] == "repository_only_separate_run"
    bge = next(row for row in dataset["runs"][1]["aggregates"] if row["config_name"] == "C2_mmr_rerank__baai_bge_reranker_v2_m3")
    marco = next(row for row in dataset["runs"][1]["aggregates"] if "ms_marco" in row["config_name"] and row["base_config_name"] == "C2_mmr_rerank")
    assert bge["mean_ndcg_at_k"] > marco["mean_ndcg_at_k"]
    assert bge["quality_publication_status"] == "verified_table_5"
    assert marco["latency_publication_status"] == "verified_table_6"


def test_duplicate_documents_follow_recorded_evaluator() -> None:
    results = [{"doc_id": "A", "source": "A"}, {"doc_id": "A", "source": "A"}]
    recall, ndcg = website_export.compute_recall_ndcg(results, {"A", "B"}, 2, ("doc_id", "source"))
    assert recall == 0.5
    assert ndcg == 1.0


def test_invalid_rows_are_material() -> None:
    metadata = {
        "eval_level": "chunk",
        "top_k": 3,
        "query_count": 1,
        "git_commit_hash": "not-the-run",
    }
    summary = [{
        "config_name": "C0_baseline",
        "query_count": "1",
        "mean_recall_at_k": "2",
        "mean_ndcg_at_k": "0.5",
        "p50_latency_ms": "1",
        "p95_latency_ms": "1",
        "p99_latency_ms": "1",
    }]
    per_query = [{
        "query_id": "q1",
        "config_name": "C0_baseline",
        "status": "ok",
        "recall_at_k": "2",
        "ndcg_at_k": "0.5",
        "latency_ms": "1",
    }]
    hits = [
        {"query_id": "q1", "config_name": "C0_baseline", "rank": "1", "chunk_id": "a"},
        {"query_id": "q1", "config_name": "C0_baseline", "rank": "1", "chunk_id": "a"},
    ]
    ablation = [{
        "config_name": "C0_baseline",
        "mean_recall_at_k": "0.5",
        "mean_ndcg_at_k": "0.5",
        "std_recall_at_k": "0",
        "std_ndcg_at_k": "0",
    }]
    latency = [{"config_name": "C0_baseline", "p50_latency_ms": "1", "p95_latency_ms": "1", "p99_latency_ms": "1"}]
    findings = website_export.validate_run_tables(
        "fixture", metadata, summary, per_query, hits, ablation, latency, {"C0_baseline"}
    )
    codes = {item["code"] for item in findings}
    assert "eval_level" in codes
    assert "top_k" in codes
    assert "metric_range" in codes
    assert "duplicate_rank" in codes
    assert any(item["material"] for item in findings)


def test_exporter_does_not_load_model_stack() -> None:
    assert "qdrant_client" not in sys.modules
    assert "sentence_transformers" not in sys.modules

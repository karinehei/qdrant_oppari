# -*- coding: utf-8 -*-
"""Validate recorded thesis experiments and export a static website dataset.

The script reads research artifacts and writes only derived website files.
It does not modify experiment outputs, annotations, or metric definitions,
and it does not import Qdrant, embedding models, or rerankers.
"""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import math
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.metrics_relevance import ndcg_at_k  # noqa: E402

SCHEMA_VERSION = "1.0.0"
RUNTIME_COMMIT = "0bf114886e687ca706f027d81fd20bd1822b07a9"
OUTPUT_COMMIT = "e619a3e714485ff2e6c9a833e6df317804e7e03a"
PILOT_QUERY_COUNT = 6

PUBLICATION = {
    "title": "Hakustrategioiden vaikutus suomenkielisen RAG-järjestelmän tiedonhaun laatuun ja suorituskykyyn",
    "author": "Karine Heinonen",
    "year": 2026,
    "page_count": 56,
    "institution": "LAB-ammattikorkeakoulu",
    "degree": "Insinööri (AMK)",
    "theseus_item_url": "https://www.theseus.fi/items/4c5b8d64-c921-47f4-9c9a-52866778055a",
    "theseus_handle_url": "https://www.theseus.fi/handle/10024/914330",
    "urn": "URN:NBN:fi:amk-202604156494",
    "page_basis_fi": "Sivunumerot ovat opinnäytetyön sisällysluettelon numerointia, eivät PDF-tiedoston sivupaikkoja.",
}

CONFIGS = {
    "C0_baseline": {
        "code": "C0",
        "order": 0,
        "label_fi": "Perusvektorihaku",
        "mmr": False,
        "diversity": 0.0,
        "rerank": False,
        "dedupe": False,
        "description_fi": (
            "Perusvektorihaku. Koodi kutsuu MMR-valintaa parametrilla λ = 0, "
            "jolloin valinta vastaa relevanssijärjestystä. Uudelleenjärjestämistä ja "
            "kaksoiskappaleiden poistoa ei käytetä."
        ),
    },
    "C1_mmr": {
        "code": "C1",
        "order": 1,
        "label_fi": "MMR",
        "mmr": True,
        "diversity": 0.35,
        "rerank": False,
        "dedupe": False,
        "description_fi": "Perusvektorihakuun lisätään Maximal Marginal Relevance -monipuolistus, λ = 0,35.",
    },
    "C2_mmr_rerank": {
        "code": "C2",
        "order": 2,
        "label_fi": "MMR ja uudelleenjärjestäminen",
        "mmr": True,
        "diversity": 0.35,
        "rerank": True,
        "dedupe": False,
        "description_fi": "MMR-vaiheen jälkeen cross-encoder järjestää ehdokkaat uudelleen. Kaksoiskappaleiden poisto ei ole käytössä.",
    },
    "C3_mmr_rerank_dedupe": {
        "code": "C3",
        "order": 3,
        "label_fi": "MMR, uudelleenjärjestäminen ja kaksoiskappaleiden poisto",
        "mmr": True,
        "diversity": 0.35,
        "rerank": True,
        "dedupe": True,
        "dedupe_rule_fi": "Tunnistepohjainen poisto: yksi osuma tekstikatkelman uid-tunnistetta kohden, ei yksi osuma dokumenttia kohden.",
        "description_fi": (
            "C2:n päälle lisätään tunnistepohjainen kaksoiskappaleiden poisto. "
            "Sääntö säilyttää yhden osuman kutakin tekstikatkelmatunnistetta kohden. "
            "Saman dokumentin eri tekstikatkelmat voivat jäädä tuloslistalle."
        ),
    },
}

# Thesis table values after the publication's reported rounding.
THESIS_ABLATION_QUALITY = {
    "C0_baseline": {"recall": 0.65, "ndcg": 0.58, "std_recall": 0.438, "std_ndcg": 0.408},
    "C1_mmr": {"recall": 0.717, "ndcg": 0.615, "std_recall": 0.409, "std_ndcg": 0.370},
    "C2_mmr_rerank": {"recall": 0.783, "ndcg": 0.693, "std_recall": 0.364, "std_ndcg": 0.355},
    "C3_mmr_rerank_dedupe": {"recall": 0.783, "ndcg": 0.693, "std_recall": 0.364, "std_ndcg": 0.355},
}
THESIS_ABLATION_LATENCY = {
    "C0_baseline": {"p50": 26.09, "p95": 46.91, "p99": 1319.23},
    "C1_mmr": {"p50": 26.35, "p95": 44.26, "p99": 47.27},
    "C2_mmr_rerank": {"p50": 258.42, "p95": 1269.12, "p99": 1349.25},
    "C3_mmr_rerank_dedupe": {"p50": 242.69, "p95": 1234.77, "p99": 1342.11},
}
THESIS_RERANK_QUALITY = {
    "C2_mmr_rerank__cross_encoder_ms_marco_minilm_l_6_v2": {"recall": 0.733, "ndcg": 0.659, "std_recall": 0.388, "std_ndcg": 0.366},
    "C2_mmr_rerank__baai_bge_reranker_v2_m3": {"recall": 0.783, "ndcg": 0.693, "std_recall": 0.364, "std_ndcg": 0.355},
    "C3_mmr_rerank_dedupe__cross_encoder_ms_marco_minilm_l_6_v2": {"recall": 0.733, "ndcg": 0.659, "std_recall": 0.388, "std_ndcg": 0.366},
    "C3_mmr_rerank_dedupe__baai_bge_reranker_v2_m3": {"recall": 0.783, "ndcg": 0.693, "std_recall": 0.364, "std_ndcg": 0.355},
}
THESIS_RERANK_LATENCY = {
    "C2_mmr_rerank__cross_encoder_ms_marco_minilm_l_6_v2": {"p50": 54.25, "p95": 68.80, "p99": 379.36},
    "C2_mmr_rerank__baai_bge_reranker_v2_m3": {"p50": 231.38, "p95": 294.92, "p99": 382.21},
    "C3_mmr_rerank_dedupe__cross_encoder_ms_marco_minilm_l_6_v2": {"p50": 50.46, "p95": 65.20, "p99": 68.70},
    "C3_mmr_rerank_dedupe__baai_bge_reranker_v2_m3": {"p50": 229.82, "p95": 276.10, "p99": 310.60},
}

PRIVATE_METADATA_KEYS = {
    "hostname",
    "executable",
    "current_working_directory",
    "queries_path",
    "gold_path",
}

ORIGINAL_PATHS = [
    "outputs/experiments/retrieval_hits.csv",
    "outputs/experiments/per_query_metrics.csv",
    "outputs/experiments/metrics_summary.csv",
    "outputs/experiments/run_metadata.json",
    "outputs/experiments/report_table_ablation.csv",
    "outputs/experiments/report_table_latency.csv",
    "outputs/experiments/report_table_best_config.csv",
    "outputs/experiments/report_table_groundedness.csv",
    "outputs/experiments/groundedness_summary.csv",
    "outputs/experiments/case_studies.md",
    "outputs/experiments_rerank/retrieval_hits.csv",
    "outputs/experiments_rerank/per_query_metrics.csv",
    "outputs/experiments_rerank/metrics_summary.csv",
    "outputs/experiments_rerank/run_metadata.json",
    "outputs/experiments_rerank/report_table_ablation.csv",
    "outputs/experiments_rerank/report_table_latency.csv",
    "data/annotations/queries.jsonl",
    "data/annotations/gold_annotations.jsonl",
    "utils/metrics_relevance.py",
    "scripts/run_experiments.py",
    "config.py",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def original_hashes(root: Path | None = None) -> dict[str, str]:
    root = root or PROJECT_ROOT
    hashes: dict[str, str] = {}
    for relative in ORIGINAL_PATHS:
        path = root / relative
        if path.exists():
            hashes[relative] = sha256_file(path)
    return hashes


def _load_experiment_module():
    path = PROJECT_ROOT / "scripts" / "run_experiments.py"
    spec = importlib.util.spec_from_file_location("recorded_run_experiments", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("run_experiments.py ei ole ladattavissa")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_EXPERIMENT = _load_experiment_module()
compute_recall_ndcg = _EXPERIMENT.compute_recall_ndcg
percentile_ms = _EXPERIMENT.percentile_ms


def issue(severity: str, code: str, message: str, material: bool = False, **extra: Any) -> dict[str, Any]:
    item = {"severity": severity, "code": code, "message": message, "material": material}
    item.update(extra)
    return item


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"Odotettiin objektia: {path}")
    return data


def parse_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def sample_std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return math.sqrt(variance)


def close(left: float, right: float, tolerance: float) -> bool:
    return abs(left - right) <= tolerance


def git_output(args: list[str], root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def current_commit(root: Path) -> str | None:
    return git_output(["rev-parse", "HEAD"], root)


def file_in_commit(root: Path, commit: str, relative: str) -> bool:
    return git_output(["cat-file", "-e", f"{commit}:{relative}"], root) is not None or git_output(
        ["ls-tree", "--name-only", commit, relative], root
    ) not in (None, "")


def working_tree_matches_commit(root: Path, commit: str, relative: str) -> bool | None:
    status = subprocess.run(
        ["git", "diff", "--quiet", commit, "--", relative],
        cwd=root,
        capture_output=True,
        timeout=8,
        check=False,
    )
    if status.returncode == 0:
        return True
    if status.returncode == 1:
        return False
    return None


def public_environment(metadata: dict[str, Any]) -> dict[str, Any]:
    env = metadata.get("environment_info") or {}
    gpu = env.get("gpu_info") or {}
    packages = env.get("package_versions") or {}
    return {
        "python_version": env.get("python_version"),
        "platform": env.get("platform"),
        "cpu_info": env.get("cpu_info"),
        "gpu_device_name": gpu.get("device_name"),
        "gpu_device_count": gpu.get("device_count"),
        "package_versions": {
            "sentence_transformers": packages.get("sentence_transformers"),
            "transformers": packages.get("transformers"),
            "torch": packages.get("torch"),
            "numpy": packages.get("numpy"),
            "qdrant_client": packages.get("qdrant_client"),
        },
    }


def public_run_provenance(metadata: dict[str, Any], source_dir: str, root: Path) -> dict[str, Any]:
    files = [
        "retrieval_hits.csv",
        "per_query_metrics.csv",
        "metrics_summary.csv",
        "run_metadata.json",
        "report_table_ablation.csv",
        "report_table_latency.csv",
    ]
    links = []
    for name in files:
        relative = f"{source_dir}/{name}"
        in_runtime = file_in_commit(root, RUNTIME_COMMIT, relative)
        in_output = file_in_commit(root, OUTPUT_COMMIT, relative)
        same = working_tree_matches_commit(root, OUTPUT_COMMIT, relative)
        same_runtime = working_tree_matches_commit(root, RUNTIME_COMMIT, relative)
        links.append(
            {
                "path": relative,
                "present_in_runtime_commit": bool(in_runtime),
                "working_tree_matches_runtime_commit": same_runtime,
                "present_in_output_commit": bool(in_output),
                "working_tree_matches_output_commit": same,
                "github_url": (
                    f"https://github.com/karinehei/qdrant_oppari/blob/{OUTPUT_COMMIT}/{relative}"
                    if in_output
                    else None
                ),
            }
        )
    return {
        "source_dir": source_dir,
        "timestamp_utc": metadata.get("timestamp_utc"),
        "seed": metadata.get("seed"),
        "runtime_git_commit": metadata.get("git_commit_hash"),
        "runtime_git_branch": metadata.get("git_branch"),
        "output_files_commit": OUTPUT_COMMIT,
        "collection_name": metadata.get("collection_name"),
        "top_k": metadata.get("top_k"),
        "initial_limit": metadata.get("initial_limit"),
        "score_threshold": metadata.get("score_threshold"),
        "eval_level": metadata.get("eval_level"),
        "query_count": metadata.get("query_count"),
        "duration_seconds": metadata.get("duration_seconds"),
        "configs_run": metadata.get("configs_run"),
        "rerank_models_requested": metadata.get("rerank_models_requested"),
        "rerank_models_loaded": metadata.get("rerank_models_loaded"),
        "embedding_model": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        "environment": public_environment(metadata),
        "files": links,
        "omitted_fi": "Konekohtaiset polut, isäntänimi ja Python-tulkin polku on jätetty pois.",
    }


def load_documents(root: Path) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []
    path = root / "data" / "processed" / "documents.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        raw.pop("cleaned_text", None)
        raw.pop("filepath", None)
        documents.append(
            {
                "doc_id": raw.get("id"),
                "author": raw.get("author"),
                "filename_derived_label": raw.get("title"),
                "year": raw.get("year"),
                "theseus_url": None,
                "language": raw.get("language"),
                "source_type": raw.get("source_type"),
                "chunk_count": raw.get("chunk_count"),
                "cleaned_text_length": raw.get("cleaned_text_length"),
                "bibliographic_status": "filename_derived_unverified",
                "bibliographic_note_fi": (
                    "Tekijä ja näyttönimi on johdettu tiedostonimestä putken oletusheuristiikalla. "
                    "Varmennettua Theseus-osoitetta ei ole tallennettu, eikä nimeä esitetä julkaisun virallisena nimenä."
                ),
            }
        )
    return documents


def load_chunk_lengths(root: Path) -> list[int]:
    lengths: list[int] = []
    path = root / "data" / "processed" / "chunks.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        text = raw.get("text") or ""
        lengths.append(len(text))
    return lengths


def round_half_up(value: float) -> int:
    """Match the thesis integer presentation of positive halves."""
    return int(math.floor(value + 0.5))


def median(values: list[float]) -> float:
    ordered = sorted(values)
    count = len(ordered)
    if count == 0:
        return 0.0
    middle = count // 2
    if count % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2


def load_annotations(root: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    from annotations import load_gold_annotations, load_queries

    queries = load_queries(root / "data" / "annotations" / "queries.jsonl")
    gold = load_gold_annotations(root / "data" / "annotations" / "gold_annotations.jsonl")
    return queries, gold


def validate_annotations(queries: list[dict[str, Any]], gold: list[dict[str, Any]], documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    query_ids = [item.get("query_id") for item in queries]
    if len(query_ids) != len(set(query_ids)):
        findings.append(issue("error", "duplicate_query_id", "Kyselytunnisteet eivät ole yksilöllisiä.", True))
    if len(queries) != 30:
        findings.append(issue("error", "query_count", f"Kyselyitä on {len(queries)}, julkaisu ilmoittaa 30.", True))
    gold_ids = [item.get("query_id") for item in gold]
    if set(gold_ids) != set(query_ids):
        findings.append(issue("error", "gold_coverage", "Gold-annotaatiot eivät kata täsmälleen kyselyjoukkoa.", True))
    known_docs = {item["doc_id"] for item in documents}
    for item in gold:
        for doc_id in item.get("relevant_doc_ids") or []:
            if doc_id not in known_docs:
                findings.append(issue("error", "unknown_doc", f"Relevantti dokumentti puuttuu korpuksesta: {doc_id}", True, query_id=item.get("query_id")))
        chunks = item.get("relevant_chunk_ids")
        if chunks is not None and not isinstance(chunks, list):
            findings.append(issue("error", "chunk_annotation_type", "relevant_chunk_ids ei ole lista.", True))
    return findings


def group_rows(rows: list[dict[str, str]], key: str) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row[key], []).append(row)
    return grouped


def validate_run_tables(
    run_id: str,
    metadata: dict[str, Any],
    summary_rows: list[dict[str, str]],
    per_query_rows: list[dict[str, str]],
    hit_rows: list[dict[str, str]],
    ablation_rows: list[dict[str, str]],
    latency_rows: list[dict[str, str]],
    expected_configs: set[str],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if metadata.get("eval_level") != "doc":
        findings.append(issue("error", "eval_level", f"{run_id}: eval_level ei ole doc.", True))
    if metadata.get("top_k") != 5:
        findings.append(issue("error", "top_k", f"{run_id}: top_k ei ole 5.", True))
    if metadata.get("query_count") != 30:
        findings.append(issue("error", "metadata_query_count", f"{run_id}: metatiedon kyselymäärä ei ole 30.", True))
    if metadata.get("git_commit_hash") != RUNTIME_COMMIT:
        findings.append(issue("error", "runtime_commit", f"{run_id}: ajometatiedon commit poikkeaa odotetusta.", True))

    summary_names = {row["config_name"] for row in summary_rows}
    if summary_names != expected_configs:
        findings.append(issue("error", "config_set", f"{run_id}: konfiguraatiot eivät vastaa odotettua joukkoa.", True, found=sorted(summary_names)))

    per_ok = [row for row in per_query_rows if row.get("status") == "ok"]
    if any(row.get("status") != "ok" for row in per_query_rows):
        findings.append(issue("error", "metric_status", f"{run_id}: kaikilla kyselyriveillä ei ole tilaa ok.", True))

    by_config = group_rows(per_ok, "config_name")
    hits_by_config = group_rows(hit_rows, "config_name")
    for config_name in expected_configs:
        rows = by_config.get(config_name, [])
        query_ids = [row["query_id"] for row in rows]
        if len(query_ids) != 30 or len(set(query_ids)) != 30:
            findings.append(issue("error", "per_query_count", f"{run_id}/{config_name}: kyselyitä {len(query_ids)}.", True))
        recalls = [parse_float(row["recall_at_k"]) for row in rows]
        ndcgs = [parse_float(row["ndcg_at_k"]) for row in rows]
        latencies = [parse_float(row["latency_ms"]) for row in rows]
        if any(value is None or value < 0 or value > 1 for value in recalls + ndcgs):
            findings.append(issue("error", "metric_range", f"{run_id}/{config_name}: recall tai nDCG on alueen ulkopuolella.", True))
        if any(value is None or value < 0 for value in latencies):
            findings.append(issue("error", "latency_range", f"{run_id}/{config_name}: latenssi puuttuu tai on negatiivinen.", True))
        summary = next(row for row in summary_rows if row["config_name"] == config_name)
        if int(summary["query_count"]) != len(rows):
            findings.append(issue("error", "summary_count", f"{run_id}/{config_name}: kooste ja kyselyrivit eroavat.", True))
        recall_values = [value for value in recalls if value is not None]
        ndcg_values = [value for value in ndcgs if value is not None]
        latency_values = [value for value in latencies if value is not None]
        if not close(float(summary["mean_recall_at_k"]), round(mean(recall_values), 4), 0.0001):
            findings.append(issue("error", "recall_aggregate", f"{run_id}/{config_name}: recall-keskiarvo ei täsmää.", True))
        if not close(float(summary["mean_ndcg_at_k"]), round(mean(ndcg_values), 4), 0.0001):
            findings.append(issue("error", "ndcg_aggregate", f"{run_id}/{config_name}: nDCG-keskiarvo ei täsmää.", True))
        recomputed = {
            "p50": round(percentile_ms(latency_values, 50), 2),
            "p95": round(percentile_ms(latency_values, 95), 2),
            "p99": round(percentile_ms(latency_values, 99), 2),
        }
        recorded = {
            "p50": float(summary["p50_latency_ms"]),
            "p95": float(summary["p95_latency_ms"]),
            "p99": float(summary["p99_latency_ms"]),
        }
        for key in recomputed:
            delta = abs(recomputed[key] - recorded[key])
            if delta > 0.05:
                findings.append(
                    issue(
                        "error" if delta > 1 else "warning",
                        "latency_percentile",
                        f"{run_id}/{config_name}: {key} eroaa {delta:.4f} ms tallennetusta.",
                        delta > 1,
                    )
                )
        ablation = next(row for row in ablation_rows if row["config_name"] == config_name)
        if not close(round(float(summary["mean_recall_at_k"]), 3), float(ablation["mean_recall_at_k"]), 0.0005):
            findings.append(issue("error", "report_recall", f"{run_id}/{config_name}: raporttitaulun recall ei täsmää.", True))
        if not close(round(float(summary["mean_ndcg_at_k"]), 3), float(ablation["mean_ndcg_at_k"]), 0.0005):
            findings.append(issue("error", "report_ndcg", f"{run_id}/{config_name}: raporttitaulun nDCG ei täsmää.", True))
        if not close(round(sample_std(recall_values), 3), float(ablation["std_recall_at_k"]), 0.0005):
            findings.append(issue("error", "report_std_recall", f"{run_id}/{config_name}: recall-hajonta ei täsmää.", True))
        if not close(round(sample_std(ndcg_values), 3), float(ablation["std_ndcg_at_k"]), 0.0005):
            findings.append(issue("error", "report_std_ndcg", f"{run_id}/{config_name}: nDCG-hajonta ei täsmää.", True))

        hit_groups = group_rows(hits_by_config.get(config_name, []), "query_id")
        for query_id, hits in hit_groups.items():
            ranks = [int(hit["rank"]) for hit in hits]
            if ranks != list(range(1, len(ranks) + 1)):
                findings.append(issue("error", "rank_order", f"{run_id}/{config_name}/{query_id}: järjestys ei ole yhtenäinen.", True))
            if len(ranks) != len(set(ranks)):
                findings.append(issue("error", "duplicate_rank", f"{run_id}/{config_name}/{query_id}: sijaluku toistuu.", True))
            chunk_ids = [hit["chunk_id"] for hit in hits]
            if len(chunk_ids) != len(set(chunk_ids)):
                findings.append(issue("warning", "duplicate_chunk", f"{run_id}/{config_name}/{query_id}: sama tekstikatkelma toistuu.", False))
    return findings


def diagnostic_metrics(
    hit_rows: list[dict[str, str]],
    per_query_rows: list[dict[str, str]],
    gold_by_query: dict[str, set[str]],
    k: int,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[dict[str, str]]] = {}
    for hit in hit_rows:
        grouped.setdefault((hit["query_id"], hit["config_name"]), []).append(hit)
    for key, hits in grouped.items():
        hits.sort(key=lambda item: int(item["rank"]))
    for row in per_query_rows:
        key = (row["query_id"], row["config_name"])
        hits = grouped.get(key, [])
        expected = gold_by_query.get(row["query_id"], set())
        results = [{"doc_id": hit.get("doc_id"), "source": hit.get("source")} for hit in hits]
        recall, ndcg = compute_recall_ndcg(results, expected, k, ("doc_id", "source"))
        recorded_recall = parse_float(row["recall_at_k"])
        recorded_ndcg = parse_float(row["ndcg_at_k"])
        if recorded_recall is None or recorded_ndcg is None or not close(recall, recorded_recall, 1e-9) or not close(ndcg, recorded_ndcg, 1e-9):
            findings.append(
                issue(
                    "error",
                    "diagnostic_mismatch",
                    f"{row['config_name']}/{row['query_id']}: osumista laskettu mittari eroaa tallennetusta.",
                    True,
                    recorded_recall=recorded_recall,
                    diagnostic_recall=recall,
                    recorded_ndcg=recorded_ndcg,
                    diagnostic_ndcg=ndcg,
                )
            )
    return findings


def compare_thesis_maps(
    summary_rows: list[dict[str, str]],
    ablation_rows: list[dict[str, str]],
    latency_rows: list[dict[str, str]],
    quality_map: dict[str, dict[str, float]],
    latency_map: dict[str, dict[str, float]],
    label: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    ablation = {row["config_name"]: row for row in ablation_rows}
    latency = {row["config_name"]: row for row in latency_rows}
    summary = {row["config_name"]: row for row in summary_rows}
    for name, expected in quality_map.items():
        row = ablation.get(name)
        if row is None:
            findings.append(issue("error", "missing_thesis_row", f"{label}: puuttuu {name}.", True))
            continue
        for field, key in (("recall", "mean_recall_at_k"), ("ndcg", "mean_ndcg_at_k"), ("std_recall", "std_recall_at_k"), ("std_ndcg", "std_ndcg_at_k")):
            if not close(float(row[key]), expected[field], 0.0005):
                findings.append(issue("error", "thesis_quality_mismatch", f"{label}/{name}/{field}: taulu {row[key]} vs julkaisu {expected[field]}.", True))
        recorded_mean = float(summary[name]["mean_recall_at_k"])
        if not close(round(recorded_mean, 3), expected["recall"], 0.0005):
            findings.append(issue("error", "thesis_rounding", f"{label}/{name}: neljän desimaalin keskiarvo ei pyöristy julkaisuun.", True))
    for name, expected in latency_map.items():
        row = latency.get(name)
        if row is None:
            findings.append(issue("error", "missing_thesis_latency", f"{label}: latenssirivi puuttuu {name}.", True))
            continue
        for field, key in (("p50", "p50_latency_ms"), ("p95", "p95_latency_ms"), ("p99", "p99_latency_ms")):
            if not close(float(row[key]), expected[field], 0.011):
                findings.append(issue("error", "thesis_latency_mismatch", f"{label}/{name}/{field}: {row[key]} vs {expected[field]}.", True))
    return findings


def corpus_checks(documents: list[dict[str, Any]], chunk_lengths: list[int], gold: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    doc_lengths = [int(item["cleaned_text_length"]) for item in documents]
    chunk_counts = [len(item.get("relevant_chunk_ids") or []) for item in gold]
    doc_counts = [len(item.get("relevant_doc_ids") or []) for item in gold]
    stats = {
        "document_count": len(documents),
        "chunk_count": len(chunk_lengths),
        "cleaned_text_characters": sum(doc_lengths),
        "document_length_min": min(doc_lengths),
        "document_length_max": max(doc_lengths),
        "document_length_mean": round_half_up(mean([float(value) for value in doc_lengths])),
        "document_length_median": round_half_up(median([float(value) for value in doc_lengths])),
        "chunk_length_min": min(chunk_lengths),
        "chunk_length_max": max(chunk_lengths),
        "chunk_length_mean": round_half_up(mean([float(value) for value in chunk_lengths])),
        "chunk_length_median": round_half_up(median([float(value) for value in chunk_lengths])),
        "query_count": len(gold),
        "gold_count": len(gold),
        "relevant_docs_per_query_mean": round(mean([float(value) for value in doc_counts]), 2),
        "relevant_chunks_per_query_mean": round(mean([float(value) for value in chunk_counts]), 1),
        "relevant_chunks_per_query_min": min(chunk_counts),
        "relevant_chunks_per_query_max": max(chunk_counts),
    }
    expected = {
        "document_count": 10,
        "chunk_count": 1358,
        "cleaned_text_characters": 861445,
        "document_length_min": 47885,
        "document_length_max": 130478,
        "document_length_mean": 86145,
        "document_length_median": 82471,
        "chunk_length_min": 105,
        "chunk_length_max": 800,
        "chunk_length_mean": 643,
        "chunk_length_median": 709,
        "query_count": 30,
        "gold_count": 30,
        "relevant_docs_per_query_mean": 1.33,
        "relevant_chunks_per_query_mean": 1.9,
        "relevant_chunks_per_query_min": 0,
        "relevant_chunks_per_query_max": 3,
    }
    for key, value in expected.items():
        if stats[key] != value:
            findings.append(issue("error", "corpus_stat", f"Taulukon 1 {key}: laskettu {stats[key]}, julkaisu {value}.", True))
    return stats, findings


def _hit_list_differences(hits: list[dict[str, Any]], left: str, right: str) -> list[str]:
    grouped: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for hit in hits:
        grouped.setdefault((hit["query_id"], hit["config_name"]), []).append((int(hit["rank"]), hit["chunk_id"]))
    queries = {hit["query_id"] for hit in hits}
    different = []
    for query_id in sorted(queries):
        if grouped.get((query_id, left)) != grouped.get((query_id, right)):
            different.append(query_id)
    return different


def question_metric(per_query: list[dict[str, Any]], query_id: str, config_name: str) -> dict[str, Any]:
    return next(row for row in per_query if row["query_id"] == query_id and row["config_name"] == config_name)


def build_cases(per_query: list[dict[str, Any]], hits: list[dict[str, Any]] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []

    def values(query_id: str) -> dict[str, dict[str, float]]:
        return {
            config: {
                "recall": question_metric(per_query, query_id, config)["recall_at_k"],
                "ndcg": question_metric(per_query, query_id, config)["ndcg_at_k"],
                "latency_ms": question_metric(per_query, query_id, config)["latency_ms"],
            }
            for config in ("C0_baseline", "C1_mmr", "C2_mmr_rerank", "C3_mmr_rerank_dedupe")
        }

    q5 = values("q5")
    prose_matches = (
        close(q5["C0_baseline"]["recall"], 0, 1e-9)
        and close(q5["C1_mmr"]["recall"], 0, 1e-9)
        and close(q5["C2_mmr_rerank"]["recall"], 0.5, 1e-9)
        and close(q5["C3_mmr_rerank_dedupe"]["recall"], 0.5, 1e-9)
    )
    if prose_matches:
        findings.append(issue("info", "q5_prose", "Luvun 6.4 q5-virke vastaa tallennettuja mittareita."))
    else:
        findings.append(
            issue(
                "error",
                "thesis_prose_mismatch",
                "Luku 6.4 sanoo kyselyn q5 recall-arvoiksi C0 = C1 = 0 ja C2 = C3 = 0,5. "
                "Liite 3 ja tallennetut mittarit ovat C0 = 1,00, C1 = 0,00, C2 = 1,00 ja C3 = 1,00.",
                True,
                query_id="q5",
                thesis_prose={"C0": 0, "C1": 0, "C2": 0.5, "C3": 0.5},
                appendix_and_repository={config: q5[config]["recall"] for config in q5},
            )
        )

    identical_c2_c3 = []
    changed_c2_c3 = []
    for query_id in sorted({row["query_id"] for row in per_query}):
        c2 = question_metric(per_query, query_id, "C2_mmr_rerank")
        c3 = question_metric(per_query, query_id, "C3_mmr_rerank_dedupe")
        same = close(c2["recall_at_k"], c3["recall_at_k"], 1e-12) and close(c2["ndcg_at_k"], c3["ndcg_at_k"], 1e-12)
        (identical_c2_c3 if same else changed_c2_c3).append(query_id)

    cases = [
        {
            "query_id": "q6",
            "kind": "improvement",
            "publication_status": "verified",
            "reference": {"section": "6.4", "page": "42", "appendix": "Liite 3"},
            "summary_fi": "C2 nostaa nDCG@5-arvon tasolle 1,000, kun recall@5 on jo C0:ssa ja C1:ssä 1,000. Relevantti dokumentti sijoittuu uudelleenjärjestämisen jälkeen listan kärkeen.",
        },
        {
            "query_id": "q2",
            "kind": "improvement",
            "publication_status": "verified",
            "reference": {"section": "6.4", "page": "42", "appendix": "Liite 3"},
            "summary_fi": "C0 ja C1 eivät tuo kumpaakaan relevanttia dokumenttia top-5-listalle. C2 ja C3 saavuttavat recall@5-arvon 0,500.",
        },
        {
            "query_id": "q1",
            "kind": "tradeoff",
            "publication_status": "verified_partial",
            "reference": {"section": "6.4", "page": "42", "appendix": "Liite 3"},
            "summary_fi": "Recall@5 nousee arvosta 0,500 arvoon 1,000, kuten luku 6.4 kuvaa. Samalla nDCG@5 laskee arvosta 1,000 arvoon 0,544. Kattavuus paranee ja järjestys heikkenee.",
        },
        {
            "query_id": "q29",
            "kind": "regression",
            "publication_status": "verified",
            "reference": {"section": "6.4", "page": "42", "appendix": "Liite 3"},
            "summary_fi": "C0 löytää toisen relevantin dokumentin ja C1 molemmat. C2 ja C3 putoavat recall@5-arvoon 0. Uudelleenjärjestäminen siirtää relevantit dokumentit top-5-listan ulkopuolelle.",
        },
        {
            "query_id": "q24",
            "kind": "unchanged_failure",
            "publication_status": "verified",
            "reference": {"section": "6.4", "page": "42", "appendix": "Liite 3"},
            "summary_fi": "Recall@5 ja nDCG@5 ovat 0 kaikissa neljässä konfiguraatiossa. Gold-dokumentit eivät nouse top-5-listalle.",
        },
        {
            "query_id": "q7",
            "kind": "partial_and_latency",
            "publication_status": "verified",
            "reference": {"section": "6.4", "page": "42", "appendix": "Liite 3"},
            "summary_fi": "C2:n recall@5 on 0,500 ja nDCG@5 on 1,000. Latenssi on 1365,79 ms. nDCG voi olla 1, vaikka kaikkia relevantteja dokumentteja ei löydy, koska järjestyspisteytys käsittelee osumat sijainneittain eikä tiivistä toistuvia dokumentteja.",
        },
        {
            "query_id": "q4",
            "kind": "tradeoff",
            "publication_status": "verified_with_rounding",
            "reference": {"section": "6.4", "page": "42", "appendix": "Liite 3"},
            "summary_fi": "Recall@5 pysyy arvossa 1,000. C2:n nDCG@5 on 0,9675, joka pyöristyy kahteen desimaaliin arvoksi 0,97 ja täyttää luvun 6.4 rajan ≥ 0,97. C1:n nDCG@5 on kuitenkin 1,000, joten uudelleenjärjestäminen ei paranna tämän kyselyn järjestystä.",
        },
        {
            "query_id": "q5",
            "kind": "discrepancy",
            "publication_status": "unverified_prose_discrepancy",
            "show_as_thesis_verified": False,
            "reference": {"section": "6.4", "page": "42", "appendix": "Liite 3"},
            "summary_fi": (
                "Tallennettu ja liitteen 3 mukainen recall@5 on C0 = 1,000, C1 = 0,000, C2 = 1,000 ja C3 = 1,000. "
                "Luvun 6.4 virke (C0 = C1 = 0 ja C2 = C3 = 0,5) ei vastaa näitä lukuja, eikä sitä esitetä varmennettuna tuloksena."
            ),
        },
    ]
    for case in cases:
        case["metrics"] = values(case["query_id"])
        case.setdefault("show_as_thesis_verified", case["publication_status"] != "unverified_prose_discrepancy")
    cases.append(
        {
            "query_id": None,
            "kind": "unchanged_aggregate",
            "publication_status": "verified",
            "reference": {"section": "6.2.1", "page": "37", "table": "Taulukko 3"},
            "show_as_thesis_verified": True,
            "summary_fi": (
                f"C2 ja C3 tuottavat samat dokumenttitason keskiarvot. Kyselykohtainen recall ja nDCG ovat samat "
                f"{len(identical_c2_c3)} kyselyssä"
                + (f" ja eroavat {len(changed_c2_c3)} kyselyssä." if changed_c2_c3 else " eikä yhdessäkään kyselyssä ole eroa.")
                + (
                    " Myös tallennetut top-5-tekstikatkelmalistat ovat samat, joten tunnistepohjainen poisto ei muuttanut tämän ajon palautettuja osumia."
                    if hits is not None and not _hit_list_differences(hits, "C2_mmr_rerank", "C3_mmr_rerank_dedupe")
                    else ""
                )
            ),
            "identical_query_ids": identical_c2_c3,
            "changed_query_ids": changed_c2_c3,
        }
    )
    return cases, findings


def number_or_none(value: Any) -> float | None:
    parsed = parse_float(value)
    return None if parsed is None else parsed


def serialize_hits(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    hits = []
    for row in rows:
        hits.append(
            {
                "query_id": row["query_id"],
                "config_name": row["config_name"],
                "rank": int(row["rank"]),
                "doc_id": row["doc_id"],
                "chunk_id": row["chunk_id"],
                "uid": row.get("uid") or None,
                "retrieval_score": number_or_none(row.get("score")),
                "rerank_score": number_or_none(row.get("rerank_score")),
            }
        )
    return hits


def serialize_per_query(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    serialized = []
    for row in rows:
        serialized.append(
            {
                "query_id": row["query_id"],
                "config_name": row["config_name"],
                "base_config_name": row["base_config_name"],
                "rerank_model_name": row.get("rerank_model_name") or None,
                "recall_at_k": number_or_none(row.get("recall_at_k")),
                "ndcg_at_k": number_or_none(row.get("ndcg_at_k")),
                "latency_ms": number_or_none(row.get("latency_ms")),
                "status": row.get("status"),
            }
        )
    return serialized


def serialize_aggregates(
    summary_rows: list[dict[str, str]],
    ablation_rows: list[dict[str, str]],
    per_query: list[dict[str, Any]],
    quality_status: dict[str, str],
    latency_status: dict[str, str],
    references: dict[str, list[str]],
) -> list[dict[str, Any]]:
    ablation = {row["config_name"]: row for row in ablation_rows}
    aggregates = []
    for row in summary_rows:
        name = row["config_name"]
        values = [item for item in per_query if item["config_name"] == name]
        aggregates.append(
            {
                "config_name": name,
                "base_config_name": row["base_config_name"],
                "rerank_model_name": row.get("rerank_model_name") or None,
                "query_count": int(row["query_count"]),
                "mean_recall_at_k": float(row["mean_recall_at_k"]),
                "mean_ndcg_at_k": float(row["mean_ndcg_at_k"]),
                "std_recall_at_k": float(ablation[name]["std_recall_at_k"]),
                "std_ndcg_at_k": float(ablation[name]["std_ndcg_at_k"]),
                "underlying_mean_recall_at_k": mean([item["recall_at_k"] for item in values]),
                "underlying_mean_ndcg_at_k": mean([item["ndcg_at_k"] for item in values]),
                "p50_latency_ms": float(row["p50_latency_ms"]),
                "p95_latency_ms": float(row["p95_latency_ms"]),
                "p99_latency_ms": float(row["p99_latency_ms"]),
                "quality_publication_status": quality_status[name],
                "latency_publication_status": latency_status[name],
                "publication_reference_ids": references[name],
            }
        )
    return aggregates


def pilot_snapshot(root: Path) -> dict[str, Any]:
    show = git_output(["show", f"{RUNTIME_COMMIT}:outputs/experiments/metrics_summary.csv"], root)
    rows = []
    if show:
        reader = csv.DictReader(show.splitlines())
        rows = [dict(row) for row in reader]
    return {
        "included_in_website_results": False,
        "commit": RUNTIME_COMMIT,
        "path": "outputs/experiments/metrics_summary.csv",
        "query_count": PILOT_QUERY_COUNT,
        "reason_fi": (
            "Ajometatiedon commitin puussa on aiempi kuuden kyselyn tuloste. "
            "Julkaistu 30 kyselyn aineisto on työpuussa ja commitissa e619a3e. "
            "Kuuden kyselyn lukuja ei piirretä tulosesittelyyn."
        ),
        "recorded_summary": rows,
    }


def annotation_identity(root: Path) -> dict[str, Any]:
    queries = "data/annotations/queries.jsonl"
    gold = "data/annotations/gold_annotations.jsonl"
    return {
        "queries_match_runtime_commit": working_tree_matches_commit(root, RUNTIME_COMMIT, queries),
        "gold_match_runtime_commit": working_tree_matches_commit(root, RUNTIME_COMMIT, gold),
        "queries_sha256": sha256_file(root / queries),
        "gold_sha256": sha256_file(root / gold),
        "uncertainty_fi": (
            "Ajometatieto ei tallentanut annotaatiotiedostojen tiivistettä. "
            "Nykyiset kysely- ja gold-tiedostot ovat samat kuin ajometatietoon kirjatun commitin puussa, "
            "mutta ajonaikaista levytilannetta ei voida todistaa jälkikäteen, jos tiedostoja olisi muutettu commitoimatta."
        ),
    }


def traceability_rows() -> list[dict[str, Any]]:
    return [
        {"id": "table-1", "label_fi": "Taulukko 1", "section": "3.3", "page": "17", "repository": "documents.jsonl, chunks.jsonl, queries.jsonl, gold_annotations.jsonl", "website_view": "yleiskuva", "status": "verified"},
        {"id": "table-2", "label_fi": "Taulukko 2", "section": "5.4", "page": "30", "repository": "scripts/run_experiments.py CONFIGS", "website_view": "vertailu", "status": "verified"},
        {"id": "table-3", "label_fi": "Taulukko 3", "section": "6.2.1", "page": "37", "repository": "outputs/experiments/report_table_ablation.csv", "columns": "mean_recall_at_k, mean_ndcg_at_k, std_recall_at_k, std_ndcg_at_k", "website_view": "vertailu", "status": "verified"},
        {"id": "table-4", "label_fi": "Taulukko 4", "section": "6.2.2", "page": "38", "repository": "outputs/experiments/report_table_latency.csv", "columns": "p50_latency_ms, p95_latency_ms, p99_latency_ms", "website_view": "laatu", "status": "verified"},
        {"id": "figure-4", "label_fi": "Kuvio 4", "section": "6.2.2", "page": "38–39", "repository": "Taulukoiden 3 ja 4 nDCG@5 ja p50", "website_view": "laatu", "status": "verified"},
        {"id": "table-5", "label_fi": "Taulukko 5", "section": "6.3", "page": "40", "repository": "outputs/experiments_rerank/report_table_ablation.csv (C2–C3)", "website_view": "vertailu", "status": "verified"},
        {"id": "table-6", "label_fi": "Taulukko 6", "section": "6.3", "page": "40", "repository": "outputs/experiments_rerank/report_table_latency.csv (C2–C3)", "website_view": "laatu", "status": "verified"},
        {"id": "figure-5", "label_fi": "Kuvio 5", "section": "6.3", "page": "40–41", "repository": "Taulukoiden 5 ja 6 nDCG@5 ja p50", "website_view": "laatu", "status": "verified"},
        {"id": "appendix-3", "label_fi": "Liite 3", "section": "Liite 3", "page": "liite", "repository": "outputs/experiments/per_query_metrics.csv", "website_view": "kysymykset", "status": "verified"},
        {"id": "section-6.4-q5", "label_fi": "Luku 6.4, q5-virke", "section": "6.4", "page": "42", "repository": "outputs/experiments/per_query_metrics.csv ja liite 3", "website_view": "menetelmat", "status": "unresolved_prose_discrepancy"},
        {"id": "groundedness", "label_fi": "Groundedness-kooste", "section": "5.6", "page": "34", "repository": "outputs/experiments/groundedness_summary.csv", "website_view": "ei näytetä päätuloksissa", "status": "excluded_unverified_provenance"},
        {"id": "pilot-snapshot", "label_fi": "Aiempi 6 kyselyn tuloste", "section": "ei julkaistu taulu", "page": "–", "repository": f"{RUNTIME_COMMIT}:outputs/experiments/metrics_summary.csv", "website_view": "ei näytetä", "status": "repository_history_not_publication"},
    ]


def render_traceability(dataset: dict[str, Any]) -> str:
    lines = [
        "# Julkaisun ja repositorion jäljitettävyys",
        "",
        "Tämä asiakirja on johdettu tarkistusviennistä. Se ei korvaa alkuperäisiä tulostiedostoja eikä opinnäytetyötä.",
        "",
        f"- Opinnäytetyö: {PUBLICATION['author']} ({PUBLICATION['year']}). {PUBLICATION['title']}.",
        f"- Theseus: {PUBLICATION['theseus_item_url']}",
        f"- URN: {PUBLICATION['urn']}",
        f"- Ajonaikainen commit tallennetuissa metatiedoissa: `{RUNTIME_COMMIT}`",
        f"- Commit, jossa 30 kyselyn tulostiedostot ovat puussa: `{OUTPUT_COMMIT}`",
        f"- Sivuston vientiversio: `{dataset['website_export_revision']}`",
        "",
        PUBLICATION["page_basis_fi"],
        "",
        "## Tilat",
        "",
        "- **verified**: repositorion luku vastaa julkaistua taulua tai liitettä pyöristystarkkuuden puitteissa.",
        "- **repository_only**: tieto on tallennetussa ajossa, mutta sitä ei ole julkaistu kyseisenä tauluna.",
        "- **unresolved_prose_discrepancy**: julkaisun leipäteksti ja julkaisun oma liite sekä repositorio eroavat. Lukua ei esitetä varmennettuna.",
        "- **excluded**: aineisto on repositoriossa, mutta sitä ei oteta päätuloksiin.",
        "",
        "## Kuvaukset",
        "",
        "| Tunnus | Julkaisu | Repositorio | Näkymä | Tila |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in dataset["traceability"]:
        lines.append(
            f"| {row['label_fi']} | {row['section']}, s. {row['page']} | `{row['repository']}` | {row['website_view']} | {row['status']} |"
        )
    lines.extend(["", "## Pääablaation laatu ja latenssi", ""])
    lines.append("Lähde: `outputs/experiments`. Julkaisu: taulukot 3 ja 4, kuviot 4.")
    lines.append("")
    for row in dataset["runs"][0]["aggregates"]:
        lines.append(
            f"- `{row['config_name']}`: recall {row['mean_recall_at_k']}, nDCG {row['mean_ndcg_at_k']}, "
            f"p50 {row['p50_latency_ms']} ms. Laatu: {row['quality_publication_status']}. Latenssi: {row['latency_publication_status']}."
        )
    lines.extend(
        [
            "",
            "## Uudelleenjärjestäjien vertailu",
            "",
            "Lähde: `outputs/experiments_rerank`. Julkaistut taulukot 5 ja 6 kattavat C2- ja C3-rivit. "
            "Saman ajon C0- ja C1-latenssit ovat erillinen mittaus, eivät taulukon 4 lukuja.",
            "",
            "## Kyselyn q5 ristiriita",
            "",
            "Luku 6.4: C0 ja C1 recall@k = 0, C2 ja C3 recall@k = 0,5.",
            "",
            "Liite 3 ja `per_query_metrics.csv`: C0 = 1,00, C1 = 0,00, C2 = 1,00, C3 = 1,00.",
            "",
            "Sivusto näyttää liitteen ja repositorion luvut ja merkitsee leipätekstin virkkeen varmentamattomaksi. "
            "Ristiriita estää julkaisutyönkulun tiukan tarkistuksen, kunnes virke on tarkistettu.",
            "",
            "## Aiempi tuloste samassa commit-hashissa",
            "",
            dataset["excluded_snapshots"][0]["reason_fi"],
            "",
            "Kuuden kyselyn kooste kyseisessä puussa:",
            "",
        ]
    )
    for row in dataset["excluded_snapshots"][0]["recorded_summary"]:
        lines.append(f"- `{row.get('config_name')}`: kyselyitä {row.get('query_count')}, recall {row.get('mean_recall_at_k')}, nDCG {row.get('mean_ndcg_at_k')}.")
    lines.extend(
        [
            "",
            "## Groundedness",
            "",
            dataset["groundedness"]["reason_fi"],
            "",
            "## Toistuvat dokumentit",
            "",
            "Recall@k laskee top-k-listan yksilölliset relevantit dokumenttitunnisteet ja jakaa ne gold-joukon koolla. "
            "nDCG@k pisteyttää jokaisen sijainnin erikseen. Saman dokumentin toinen tekstikatkelma voi siis olla "
            "relevanssilistassa uusi ykkönen, eikä nDCG tiivistä dokumentteja. Diagnostinen tarkistus käyttää "
            "`scripts/run_experiments.py`-funktion `compute_recall_ndcg` -toteutusta eikä kirjoita lukuja takaisin.",
            "",
            "## Annotaatiot",
            "",
            dataset["annotations"]["identity"]["uncertainty_fi"],
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def build_dataset(root: Path | None = None) -> dict[str, Any]:
    root = root or PROJECT_ROOT
    findings: list[dict[str, Any]] = []
    documents = load_documents(root)
    chunk_lengths = load_chunk_lengths(root)
    queries, gold = load_annotations(root)
    findings.extend(validate_annotations(queries, gold, documents))
    corpus, corpus_findings = corpus_checks(documents, chunk_lengths, gold)
    findings.extend(corpus_findings)

    runs_spec = [
        {
            "id": "ablation",
            "label_fi": "Pääablaatio",
            "source_dir": "outputs/experiments",
            "expected": set(THESIS_ABLATION_QUALITY),
            "quality_status": {name: "verified_table_3" for name in THESIS_ABLATION_QUALITY},
            "latency_status": {name: "verified_table_4" for name in THESIS_ABLATION_LATENCY},
            "references": {name: ["table-3", "table-4", "figure-4"] for name in THESIS_ABLATION_QUALITY},
            "quality_map": THESIS_ABLATION_QUALITY,
            "latency_map": THESIS_ABLATION_LATENCY,
            "measurement_fi": "Pääablaation latenssi. Taulukko 4.",
        },
        {
            "id": "rerank",
            "label_fi": "Uudelleenjärjestäjien vertailu",
            "source_dir": "outputs/experiments_rerank",
            "expected": set(THESIS_RERANK_QUALITY) | {"C0_baseline", "C1_mmr"},
            "quality_status": {
                "C0_baseline": "repository_only_separate_run",
                "C1_mmr": "repository_only_separate_run",
                **{name: "verified_table_5" for name in THESIS_RERANK_QUALITY},
            },
            "latency_status": {
                "C0_baseline": "repository_only_separate_run",
                "C1_mmr": "repository_only_separate_run",
                **{name: "verified_table_6" for name in THESIS_RERANK_LATENCY},
            },
            "references": {
                "C0_baseline": [],
                "C1_mmr": [],
                **{name: ["table-5", "table-6", "figure-5"] for name in THESIS_RERANK_QUALITY},
            },
            "quality_map": THESIS_RERANK_QUALITY,
            "latency_map": THESIS_RERANK_LATENCY,
            "measurement_fi": "Erillinen ajo noin 15 minuuttia pääablaation jälkeen. Taulukot 5–6 koskevat vain C2- ja C3-rivejä.",
        },
    ]

    gold_by_query = {item["query_id"]: set(item.get("relevant_doc_ids") or []) for item in gold}
    runs = []
    ablation_per_query: list[dict[str, Any]] = []
    ablation_hits: list[dict[str, Any]] = []
    for spec in runs_spec:
        directory = root / spec["source_dir"]
        metadata = load_json(directory / "run_metadata.json")
        summary_rows = load_csv(directory / "metrics_summary.csv")
        per_query_rows = load_csv(directory / "per_query_metrics.csv")
        hit_rows = load_csv(directory / "retrieval_hits.csv")
        ablation_rows = load_csv(directory / "report_table_ablation.csv")
        latency_rows = load_csv(directory / "report_table_latency.csv")
        findings.extend(validate_run_tables(spec["id"], metadata, summary_rows, per_query_rows, hit_rows, ablation_rows, latency_rows, spec["expected"]))
        findings.extend(diagnostic_metrics(hit_rows, per_query_rows, gold_by_query, int(metadata["top_k"])))
        findings.extend(compare_thesis_maps(summary_rows, ablation_rows, latency_rows, spec["quality_map"], spec["latency_map"], spec["id"]))
        per_query = serialize_per_query(per_query_rows)
        if spec["id"] == "ablation":
            ablation_per_query = per_query
            ablation_hits = serialize_hits(hit_rows)
        runs.append(
            {
                "id": spec["id"],
                "label_fi": spec["label_fi"],
                "measurement_context_fi": spec["measurement_fi"],
                "provenance": public_run_provenance(metadata, spec["source_dir"], root),
                "aggregates": serialize_aggregates(summary_rows, ablation_rows, per_query, spec["quality_status"], spec["latency_status"], spec["references"]),
                "per_query": per_query,
                "hits": serialize_hits(hit_rows),
            }
        )
        runs[-1]["aggregates"].sort(key=lambda item: (CONFIGS.get(item["base_config_name"], {}).get("order", 9), item["config_name"]))

    cases, case_findings = build_cases(ablation_per_query, ablation_hits)
    findings.extend(case_findings)
    c0_latency = next(row["p50_latency_ms"] for row in runs[0]["aggregates"] if row["config_name"] == "C0_baseline")
    c0_rerank_latency = next(row["p50_latency_ms"] for row in runs[1]["aggregates"] if row["config_name"] == "C0_baseline")
    if close(c0_latency, c0_rerank_latency, 0.01):
        findings.append(issue("warning", "latency_runs_not_separated", "Pääablaation ja rerank-ajon C0-latenssit eivät eroa.", False))

    material = [item for item in findings if item.get("material")]
    categories = []
    for query in queries:
        if query.get("category") not in categories:
            categories.append(query.get("category"))
    questions = []
    gold_by_id = {item["query_id"]: item for item in gold}
    for query in queries:
        annotation = gold_by_id[query["query_id"]]
        questions.append(
            {
                "query_id": query["query_id"],
                "query_text": query["query_text"],
                "category": query.get("category"),
                "language": query.get("language") or "fi",
                "relevant_doc_ids": annotation.get("relevant_doc_ids") or [],
                "relevant_chunk_ids": annotation.get("relevant_chunk_ids") or [],
                "notes": annotation.get("notes") or "",
                "negative_judgments": False,
            }
        )

    dataset = {
        "schema_version": SCHEMA_VERSION,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "website_export_revision": current_commit(root) or "unknown",
        "original_experiment_commit": RUNTIME_COMMIT,
        "output_files_commit": OUTPUT_COMMIT,
        "language": "fi",
        "boundary": {
            "kind": "recorded_results",
            "title_fi": "Julkaistun opinnäytetyön interaktiivinen tulosesittely",
            "statement_fi": "Opinnäytetyön tallennetut tutkimustulokset · Ei reaaliaikaista hakua",
        },
        "publication": PUBLICATION,
        "purpose_fi": (
            "Työ vertailee Qdrant-pohjaisen suomenkielisen RAG-putken hakuvaiheen strategioita: "
            "perusvektorihakua, MMR-monipuolistusta, cross-encoder-uudelleenjärjestämistä ja "
            "tunnistepohjaista kaksoiskappaleiden poistoa. Arviointi koskee tiedonhaun relevanssia ja latenssia, "
            "ei generoitujen vastausten oikeellisuutta."
        ),
        "corpus": corpus,
        "documents": documents,
        "categories": categories,
        "questions": questions,
        "annotations": {
            "evaluation_level": "doc",
            "k": 5,
            "negative_judgments_present": False,
            "chunk_annotations_available": True,
            "identity": annotation_identity(root),
            "absence_label_fi": "Ei merkitty relevantiksi käytettävissä olevissa arvioissa",
        },
        "configs": CONFIGS,
        "models": {
            "embedding": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            "embedding_dimension": 384,
            "distance": "cosine",
            "collection_name": "rag_thesis_fi",
            "default_reranker": "BAAI/bge-reranker-v2-m3",
            "comparison_reranker": "cross-encoder/ms-marco-MiniLM-L-6-v2",
            "initial_limit": 20,
            "top_k": 5,
            "score_threshold": 0.0,
            "seed": 42,
        },
        "metric_definitions": {
            "k": 5,
            "evaluation_level_fi": "dokumenttitaso",
            "recall_fi": "Recall@5 on top-5-listassa olevien yksilöllisten relevanttien dokumenttien määrä jaettuna gold-dokumenttien määrällä.",
            "ndcg_fi": "nDCG@5 vertaa sijainneittain diskontattua relevanssia ihanteelliseen järjestykseen. Toistuvaa dokumenttia ei tiivistetä ennen pisteytystä.",
            "latency_fi": (
                "Latenssi on yhden hakukutsun kelloaika millisekunteina. Upotusmalli ladataan ennen silmukkaa ja "
                "uudelleenjärjestäjä ennen kyseisen kutsun kelloa. Lämmittelytoistoja tai toistettuja yrityksiä ei ole. "
                "p50, p95 ja p99 interpoloidaan kyselykohtaisista ajoista. Eri ajojen latensseja ei yhdistetä."
            ),
            "score_fi": "Vektorihaun pisteet ja cross-encoderin pisteet ovat eri mallien lukuja. Niitä ei verrata toisiinsa eikä tulkita prosenteiksi.",
            "no_significance_fi": "Opinnäytetyö ei raportoi tilastollisia testejä eikä luottamusvälejä. Erot esitetään kuvailevina.",
        },
        "runs": runs,
        "case_studies": cases,
        "groundedness": {
            "included_in_main_results": False,
            "source": "outputs/experiments/groundedness_summary.csv",
            "reason_fi": (
                "Tiedosto sisältää C0- ja C2-rivit, mutta repositoriossa ei ole sen tuottanutta generointiajoa "
                "eikä opinnäytetyön taulukot 3–6 raportoi lukuja. Luku 5.6 käsittelee groundednessia valinnaisena "
                "lisämittarina ydinkokeen ulkopuolella. Alkuperäistä tiedostoa ei ole poistettu."
            ),
        },
        "conclusions": [
            {"text_fi": "MMR nostaa pääablaatiossa recall@5-arvon 0,650:stä 0,717:ään ja nDCG@5-arvon 0,580:stä 0,615:een. Mediaanilatenssi pysyy noin 26 millisekunnissa.", "references": ["table-3", "table-4"], "status": "verified"},
            {"text_fi": "C2 ja C3 jakavat parhaan keskimääräisen laadun: recall@5 = 0,783 ja nDCG@5 = 0,693. Kumpikaan ei ole yksinään paras, eikä tilastollista merkitsevyyttä ole raportoitu.", "references": ["table-3"], "status": "verified"},
            {"text_fi": "Uudelleenjärjestäminen kasvattaa pääablaation mediaanilatenssin noin 26 millisekunnista noin 240–260 millisekuntiin.", "references": ["table-4"], "status": "verified"},
            {"text_fi": "Rerank-vertailussa BAAI/bge-reranker-v2-m3 saavuttaa korkeamman recall@5- ja nDCG@5-arvon kuin cross-encoder/ms-marco-MiniLM-L-6-v2. ms-marco on mediaaniltaan nopeampi.", "references": ["table-5", "table-6"], "status": "verified"},
            {"text_fi": "Kaksoiskappaleiden poisto ei muuta tämän aineiston dokumenttitason keskiarvoja.", "references": ["table-3", "table-5"], "status": "verified"},
        ],
        "limitations": [
            "Korpus on 10 suomenkielistä Theseus-opinnäytettä ja 1 358 tekstikatkelmaa. Tulokset eivät sellaisinaan kuvaa muita kieliä tai tekstilajeja.",
            "Gold-annotointi on manuaalista ja tulkinnanvaraista. Negatiivisia relevanssituomioita ei ole: puuttuva tunniste ei ole todistettu epärelevantiksi.",
            "PDF-poiminta ja kappalepohjainen pilkkominen voivat katkoa tai yhdistää tekstiä. Tavutus ja sivuarjefaktit on siivottu vain rajatusti.",
            "Arviointi on dokumenttitasoista, vaikka haku palauttaa tekstikatkelmia. Oikea dokumentti ei tarkoita, että palautettu katkelma olisi vastauksen kannalta paras kohta.",
            "Latenssi on yhden kutsun mittaus ilman lämmittelytoistoja. Kylmäkäynnistys, välimuisti ja GPU-kuorma voivat näkyä erityisesti p99-arvossa.",
            "Pääablaation ja uudelleenjärjestäjävertailun latenssit ovat eri ajoista, eikä niitä pidä lukea samaksi mittaukseksi.",
            "Recall ja nDCG mittaavat haun relevanssia. Ne eivät mittaa generoidun vastauksen oikeellisuutta tai lähdeankkuroitumista.",
            "Sivusto näyttää tallennetut tulokset. Sen selaaminen ei toista kokeita eikä käynnistä Qdrantia tai malleja.",
        ],
        "excluded_snapshots": [pilot_snapshot(root)],
        "traceability": traceability_rows(),
        "validation": {
            "findings": findings,
            "material_discrepancies": material,
            "release_blocked": bool(material),
            "release_block_reason_fi": (
                "Luvun 6.4 q5-virke eroaa liitteestä 3 ja tallennetuista mittareista. "
                "Päätulostauluja ei ole merkitty tämän vuoksi vääriksi, mutta virkettä ei saa esittää varmennettuna "
                "ja Pages-julkaisu odottaa tarkistusta."
                if material
                else ""
            ),
        },
    }
    return dataset


def csv_download(dataset: dict[str, Any], run_id: str) -> str:
    run = next(item for item in dataset["runs"] if item["id"] == run_id)
    provenance = run["provenance"]
    lines = [
        "record_type,note,run_id,eval_level,k,unit,source_dir,experiment_commit,output_files_commit,website_export_revision,config_name,query_count,mean_recall_at_k,mean_ndcg_at_k,std_recall_at_k,std_ndcg_at_k,p50_latency_ms,p95_latency_ms,p99_latency_ms,quality_publication_status,latency_publication_status",
        (
            "metadata,\"Johdettu vientitiedosto. Ei alkuperäinen opinnäytetyön tiedosto. "
            f"Suodatukset eivät sisälly tähän koosteeseen.\",{run_id},doc,5,recall_ndcg_unitless_and_latency_ms,"
            f"{provenance['source_dir']},{provenance['runtime_git_commit']},{provenance['output_files_commit']},"
            f"{dataset['website_export_revision']},,,,,,,,,,,,"
        ),
    ]
    for row in run["aggregates"]:
        lines.append(
            "aggregate,Julkaistun ajon koko kooste ei muutu kysymyssuodatuksesta.,"
            f"{run_id},doc,5,recall_ndcg_unitless_and_latency_ms,{provenance['source_dir']},"
            f"{provenance['runtime_git_commit']},{provenance['output_files_commit']},{dataset['website_export_revision']},"
            f"{row['config_name']},{row['query_count']},{row['mean_recall_at_k']},{row['mean_ndcg_at_k']},"
            f"{row['std_recall_at_k']},{row['std_ndcg_at_k']},{row['p50_latency_ms']},{row['p95_latency_ms']},{row['p99_latency_ms']},"
            f"{row['quality_publication_status']},{row['latency_publication_status']}"
        )
    return "\n".join(lines) + "\n"


def write_dataset(dataset: dict[str, Any], root: Path | None = None) -> dict[str, Path]:
    root = root or PROJECT_ROOT
    data_dir = root / "web" / "src" / "data"
    download_dir = root / "web" / "public" / "downloads"
    docs_dir = root / "docs"
    data_dir.mkdir(parents=True, exist_ok=True)
    download_dir.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    dataset_path = data_dir / "research-dataset.json"
    trace_path = docs_dir / "publication_traceability.md"
    dataset_path.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    trace_path.write_text(render_traceability(dataset), encoding="utf-8")
    written = {"dataset": dataset_path, "traceability": trace_path}
    for run in dataset["runs"]:
        path = download_dir / f"{run['id']}_aggregates.csv"
        path.write_text(csv_download(dataset, run["id"]), encoding="utf-8")
        written[run["id"]] = path
    return written


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Vie tallennetut opinnäytetulokset staattiselle sivustolle.")
    parser.add_argument("--strict-publication", action="store_true", help="Palauta virhekoodi, jos aineellinen julkaisuristiriita on auki.")
    parser.add_argument("--root", default=str(PROJECT_ROOT))
    args = parser.parse_args(argv)
    root = Path(args.root)
    before = original_hashes(root)
    dataset = build_dataset(root)
    written = write_dataset(dataset, root)
    after = original_hashes(root)
    if before != after:
        print("Virhe: vienti muutti alkuperäistä tutkimustiedostoa.", file=sys.stderr)
        return 2
    material = dataset["validation"]["material_discrepancies"]
    print(f"Vienti kirjoitti {written['dataset']}")
    print(f"Jäljitettävyys: {written['traceability']}")
    print(f"Aineellisia havaintoja: {len(material)}")
    for item in material:
        print(f"- {item['code']}: {item['message']}")
    if args.strict_publication and material:
        print("Tiukka julkaisutarkistus epäonnistui. Sivustodata on silti kirjoitettu paikallista esikatselua varten.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Retrieval Experiment Report Tables

*Generated: 2026-02-27 10:29:57 UTC*

## Run Summary

| Parameter | Value |
|-----------|-------|
| collection_name | rag_thesis_fi |
| top_k | 5 |
| eval_level | doc |
| queries_path | /mnt/d/amk/oppari/qdrant_oppari/qdrant_oppari/data/annotations/queries.jsonl |
| gold_path | /mnt/d/amk/oppari/qdrant_oppari/qdrant_oppari/data/annotations/gold_annotations.jsonl |
| configs_run | C0_baseline, C1_mmr, C2_mmr_rerank, C3_mmr_rerank_dedupe |
| query_count | 30 |

## Ablation Comparison (Recall & nDCG)

| config_name | query_count | mean_recall_at_k | mean_ndcg_at_k | std_recall_at_k | std_ndcg_at_k |
|-------------|-------------|------------------|----------------|-----------------|---------------|
| C0_baseline | 30 | 0.65 | 0.58 | 0.438 | 0.408 |
| C1_mmr | 30 | 0.717 | 0.615 | 0.409 | 0.37 |
| C2_mmr_rerank | 30 | 0.783 | 0.693 | 0.364 | 0.355 |
| C3_mmr_rerank_dedupe | 30 | 0.783 | 0.693 | 0.364 | 0.355 |

## Latency Comparison

| config_name | p50_latency_ms | p95_latency_ms | p99_latency_ms | query_count |
|-------------|---------------|---------------|---------------|-------------|
| C0_baseline | 26.09 | 46.91 | 1319.23 | 30 |
| C1_mmr | 26.35 | 44.26 | 47.27 | 30 |
| C2_mmr_rerank | 258.42 | 1269.12 | 1349.25 | 30 |
| C3_mmr_rerank_dedupe | 242.69 | 1234.77 | 1342.11 | 30 |

## Groundedness Summary

| config_name | prompt_variant | groundedness_score | answer_count |
|---|---|---|---|
| C0_baseline | default | 0.85 | 10 |
| C2_mmr_rerank | default | 0.92 | 10 |

## Best Configurations (Auto-generated)

| Criterion | Best Config | Value |
|-----------|-------------|-------|
| best_ndcg_at_k | C2_mmr_rerank | 0.693 |
| best_recall_at_k | C2_mmr_rerank | 0.783 |
| best_p50_latency_ms | C0_baseline | 26.09 |

## Text Summary

- **Paras nDCG@k** saavutettiin konfiguraatiolla **C2_mmr_rerank** (mean nDCG@k = 0.693).
- **Paras recall@k** saavutettiin konfiguraatiolla **C2_mmr_rerank** (mean recall@k = 0.783).
- **Pienin p50-latenssi** havaittiin konfiguraatiolla **C0_baseline** (p50 = 26.09 ms).

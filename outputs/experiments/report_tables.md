# Retrieval Experiment Report Tables

*Generated: 2026-02-24 09:52:34 UTC*

## Run Summary

| Parameter | Value |
|-----------|-------|
| collection_name | rag_thesis_fi |
| top_k | 5 |
| eval_level | doc |
| queries_path | data/annotations/queries.jsonl |
| gold_path | data/annotations/gold_annotations.jsonl |
| configs_run | C0_baseline, C1_mmr, C2_mmr_rerank, C3_mmr_rerank_dedupe |
| query_count | 10 |

## Ablation Comparison (Recall & nDCG)

| config_name | query_count | mean_recall_at_k | mean_ndcg_at_k | std_recall_at_k | std_ndcg_at_k |
|-------------|-------------|------------------|----------------|-----------------|---------------|
| C0_baseline | 10 | 0.45 | 0.52 | 0.07 | 0.04 |
| C1_mmr | 10 | 0.48 | 0.55 | 0.0 | 0.02 |
| C2_mmr_rerank | 10 | 0.52 | 0.61 | 0.07 | 0.04 |
| C3_mmr_rerank_dedupe | 10 | 0.5 | 0.58 | 0.0 | 0.01 |

## Latency Comparison

| config_name | p50_latency_ms | p95_latency_ms | p99_latency_ms | query_count |
|-------------|---------------|---------------|---------------|-------------|
| C0_baseline | 120.5 | 180.2 | 210.3 | 10 |
| C1_mmr | 135.1 | 195.4 | 225.1 | 10 |
| C2_mmr_rerank | 245.8 | 320.5 | 380.2 | 10 |
| C3_mmr_rerank_dedupe | 240.2 | 310.1 | 365.0 | 10 |

## Groundedness Summary

| config_name | prompt_variant | groundedness_score | answer_count |
|---|---|---|---|
| C0_baseline | default | 0.85 | 10 |
| C2_mmr_rerank | default | 0.92 | 10 |

## Best Configurations (Auto-generated)

| Criterion | Best Config | Value |
|-----------|-------------|-------|
| best_ndcg_at_k | C2_mmr_rerank | 0.61 |
| best_recall_at_k | C2_mmr_rerank | 0.52 |
| best_p50_latency_ms | C0_baseline | 120.5 |

## Text Summary

- **Paras nDCG@k** saavutettiin konfiguraatiolla **C2_mmr_rerank** (mean nDCG@k = 0.61).
- **Paras recall@k** saavutettiin konfiguraatiolla **C2_mmr_rerank** (mean recall@k = 0.52).
- **Pienin p50-latenssi** havaittiin konfiguraatiolla **C0_baseline** (p50 = 120.5 ms).

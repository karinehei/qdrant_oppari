# Retrieval Experiment Report Tables

*Generated: 2026-02-27 09:57:33 UTC*

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
| C2_mmr_rerank__baai_bge_reranker_v2_m3 | 30 | 0.783 | 0.693 | 0.364 | 0.355 |
| C2_mmr_rerank__cross_encoder_ms_marco_minilm_l_6_v2 | 30 | 0.733 | 0.659 | 0.388 | 0.366 |
| C3_mmr_rerank_dedupe__baai_bge_reranker_v2_m3 | 30 | 0.783 | 0.693 | 0.364 | 0.355 |
| C3_mmr_rerank_dedupe__cross_encoder_ms_marco_minilm_l_6_v2 | 30 | 0.733 | 0.659 | 0.388 | 0.366 |

## Latency Comparison

| config_name | p50_latency_ms | p95_latency_ms | p99_latency_ms | query_count |
|-------------|---------------|---------------|---------------|-------------|
| C0_baseline | 20.23 | 34.54 | 1333.38 | 30 |
| C1_mmr | 21.05 | 35.84 | 42.98 | 30 |
| C2_mmr_rerank__baai_bge_reranker_v2_m3 | 231.38 | 294.92 | 382.21 | 30 |
| C2_mmr_rerank__cross_encoder_ms_marco_minilm_l_6_v2 | 54.25 | 68.8 | 379.36 | 30 |
| C3_mmr_rerank_dedupe__baai_bge_reranker_v2_m3 | 229.82 | 276.1 | 310.6 | 30 |
| C3_mmr_rerank_dedupe__cross_encoder_ms_marco_minilm_l_6_v2 | 50.46 | 65.2 | 68.7 | 30 |

## Best Configurations (Auto-generated)

| Criterion | Best Config | Value |
|-----------|-------------|-------|
| best_ndcg_at_k | C2_mmr_rerank__baai_bge_reranker_v2_m3 | 0.693 |
| best_recall_at_k | C2_mmr_rerank__baai_bge_reranker_v2_m3 | 0.783 |
| best_p50_latency_ms | C0_baseline | 20.23 |

## Text Summary

- **Paras nDCG@k** saavutettiin konfiguraatiolla **C2_mmr_rerank__baai_bge_reranker_v2_m3** (mean nDCG@k = 0.693).
- **Paras recall@k** saavutettiin konfiguraatiolla **C2_mmr_rerank__baai_bge_reranker_v2_m3** (mean recall@k = 0.783).
- **Pienin p50-latenssi** havaittiin konfiguraatiolla **C0_baseline** (p50 = 20.23 ms).

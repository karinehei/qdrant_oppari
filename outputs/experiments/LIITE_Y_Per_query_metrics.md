# Liite Y. Per-kysely-mittarit (recall@k, nDCG@k, latenssi)

*Lähde: per_query_metrics.csv. Kokoelma: rag_thesis_fi. top_k: 5, eval_level: doc, n = 30 kyselyä.*

---

## Taulukko Y.1. Per-kysely-mittarit ablaatiokonfiguraatioittain

| Kysely | Konfiguraatio | recall@k | nDCG@k | latenssi (ms) |
|--------|---------------|----------|--------|---------------|
| q1 | C0_baseline | 0,50 | 1,000 | 1837,8 |
| q1 | C1_mmr | 0,50 | 1,000 | 45,5 |
| q1 | C2_mmr_rerank | 1,00 | 0,544 | 664,5 |
| q1 | C3_mmr_rerank_dedupe | 1,00 | 0,544 | 206,9 |
| q2 | C0_baseline | 0,00 | 0,000 | 49,7 |
| q2 | C1_mmr | 0,00 | 0,000 | 27,9 |
| q2 | C2_mmr_rerank | 0,50 | 0,387 | 207,9 |
| q2 | C3_mmr_rerank_dedupe | 0,50 | 0,387 | 204,4 |
| q3 | C0_baseline | 1,00 | 1,000 | 26,0 |
| q3 | C1_mmr | 1,00 | 0,920 | 25,8 |
| q3 | C2_mmr_rerank | 1,00 | 0,967 | 256,4 |
| q3 | C3_mmr_rerank_dedupe | 1,00 | 0,967 | 241,8 |
| q4 | C0_baseline | 1,00 | 0,983 | 26,2 |
| q4 | C1_mmr | 1,00 | 1,000 | 29,5 |
| q4 | C2_mmr_rerank | 1,00 | 0,967 | 223,0 |
| q4 | C3_mmr_rerank_dedupe | 1,00 | 0,967 | 227,9 |
| q5 | C0_baseline | 1,00 | 0,387 | 34,0 |
| q5 | C1_mmr | 0,00 | 0,000 | 30,1 |
| q5 | C2_mmr_rerank | 1,00 | 0,850 | 251,4 |
| q5 | C3_mmr_rerank_dedupe | 1,00 | 0,850 | 228,8 |
| q6 | C0_baseline | 1,00 | 0,544 | 35,8 |
| q6 | C1_mmr | 1,00 | 0,544 | 34,5 |
| q6 | C2_mmr_rerank | 1,00 | 1,000 | 1141,8 |
| q6 | C3_mmr_rerank_dedupe | 1,00 | 1,000 | 1140,6 |
| q7 | C0_baseline | 0,00 | 0,000 | 26,0 |
| q7 | C1_mmr | 0,50 | 0,631 | 31,3 |
| q7 | C2_mmr_rerank | 0,50 | 1,000 | 1365,8 |
| q7 | C3_mmr_rerank_dedupe | 0,50 | 1,000 | 1372,9 |
| q8 | C0_baseline | 1,00 | 1,000 | 33,6 |
| q8 | C1_mmr | 1,00 | 0,885 | 48,0 |
| q8 | C2_mmr_rerank | 1,00 | 0,967 | 1308,7 |
| q8 | C3_mmr_rerank_dedupe | 1,00 | 0,967 | 1266,7 |
| q9 | C0_baseline | 0,50 | 0,947 | 30,0 |
| q9 | C1_mmr | 0,50 | 1,000 | 42,7 |
| q9 | C2_mmr_rerank | 0,50 | 0,983 | 1220,7 |
| q9 | C3_mmr_rerank_dedupe | 0,50 | 0,983 | 1195,8 |
| q10 | C0_baseline | 0,00 | 0,000 | 35,7 |
| q10 | C1_mmr | 0,00 | 0,000 | 35,9 |
| q10 | C2_mmr_rerank | 0,00 | 0,000 | 972,9 |
| q10 | C3_mmr_rerank_dedupe | 0,00 | 0,000 | 488,8 |
| q11 | C0_baseline | 1,00 | 0,631 | 23,6 |
| q11 | C1_mmr | 1,00 | 0,387 | 24,4 |
| q11 | C2_mmr_rerank | 1,00 | 0,387 | 384,7 |
| q11 | C3_mmr_rerank_dedupe | 1,00 | 0,387 | 359,6 |
| q12 | C0_baseline | 1,00 | 1,000 | 43,5 |
| q12 | C1_mmr | 1,00 | 1,000 | 35,0 |
| q12 | C2_mmr_rerank | 1,00 | 0,680 | 277,8 |
| q12 | C3_mmr_rerank_dedupe | 1,00 | 0,680 | 227,1 |
| q13 | C0_baseline | 0,00 | 0,000 | 31,8 |
| q13 | C1_mmr | 0,00 | 0,000 | 23,8 |
| q13 | C2_mmr_rerank | 0,00 | 0,000 | 216,0 |
| q13 | C3_mmr_rerank_dedupe | 0,00 | 0,000 | 216,2 |
| q14 | C0_baseline | 1,00 | 1,000 | 21,4 |
| q14 | C1_mmr | 1,00 | 0,956 | 21,3 |
| q14 | C2_mmr_rerank | 1,00 | 1,000 | 228,5 |
| q14 | C3_mmr_rerank_dedupe | 1,00 | 1,000 | 232,0 |
| q15 | C0_baseline | 1,00 | 0,387 | 27,7 |
| q15 | C1_mmr | 1,00 | 0,631 | 34,4 |
| q15 | C2_mmr_rerank | 1,00 | 1,000 | 256,5 |
| q15 | C3_mmr_rerank_dedupe | 1,00 | 1,000 | 294,6 |
| q16 | C0_baseline | 1,00 | 1,000 | 31,4 |
| q16 | C1_mmr | 1,00 | 1,000 | 23,3 |
| q16 | C2_mmr_rerank | 1,00 | 1,000 | 223,8 |
| q16 | C3_mmr_rerank_dedupe | 1,00 | 1,000 | 215,8 |
| q17 | C0_baseline | 1,00 | 0,693 | 27,5 |
| q17 | C1_mmr | 1,00 | 0,693 | 27,0 |
| q17 | C2_mmr_rerank | 1,00 | 1,000 | 197,5 |
| q17 | C3_mmr_rerank_dedupe | 1,00 | 1,000 | 204,1 |
| q18 | C0_baseline | 1,00 | 0,906 | 28,4 |
| q18 | C1_mmr | 1,00 | 0,906 | 25,7 |
| q18 | C2_mmr_rerank | 1,00 | 0,905 | 216,5 |
| q18 | C3_mmr_rerank_dedupe | 1,00 | 0,905 | 215,3 |
| q19 | C0_baseline | 0,00 | 0,000 | 19,1 |
| q19 | C1_mmr | 1,00 | 0,500 | 19,9 |
| q19 | C2_mmr_rerank | 1,00 | 0,500 | 228,9 |
| q19 | C3_mmr_rerank_dedupe | 1,00 | 0,500 | 225,5 |
| q20 | C0_baseline | 1,00 | 1,000 | 16,8 |
| q20 | C1_mmr | 1,00 | 0,877 | 20,1 |
| q20 | C2_mmr_rerank | 1,00 | 1,000 | 208,0 |
| q20 | C3_mmr_rerank_dedupe | 1,00 | 1,000 | 216,9 |
| q21 | C0_baseline | 0,50 | 1,000 | 25,7 |
| q21 | C1_mmr | 0,50 | 1,000 | 23,2 |
| q21 | C2_mmr_rerank | 1,00 | 1,000 | 219,4 |
| q21 | C3_mmr_rerank_dedupe | 1,00 | 1,000 | 231,5 |
| q22 | C0_baseline | 0,50 | 0,877 | 19,2 |
| q22 | C1_mmr | 0,50 | 1,000 | 20,3 |
| q22 | C2_mmr_rerank | 0,50 | 0,631 | 297,8 |
| q22 | C3_mmr_rerank_dedupe | 0,50 | 0,631 | 302,6 |
| q23 | C0_baseline | 1,00 | 0,500 | 19,6 |
| q23 | C1_mmr | 1,00 | 0,500 | 16,8 |
| q23 | C2_mmr_rerank | 1,00 | 0,967 | 260,3 |
| q23 | C3_mmr_rerank_dedupe | 1,00 | 0,967 | 230,2 |
| q24 | C0_baseline | 0,00 | 0,000 | 21,2 |
| q24 | C1_mmr | 0,00 | 0,000 | 18,6 |
| q24 | C2_mmr_rerank | 0,00 | 0,000 | 267,9 |
| q24 | C3_mmr_rerank_dedupe | 0,00 | 0,000 | 274,8 |
| q25 | C0_baseline | 1,00 | 0,624 | 24,3 |
| q25 | C1_mmr | 1,00 | 0,501 | 35,7 |
| q25 | C2_mmr_rerank | 1,00 | 0,618 | 267,6 |
| q25 | C3_mmr_rerank_dedupe | 1,00 | 0,618 | 254,1 |
| q26 | C0_baseline | 1,00 | 0,920 | 28,6 |
| q26 | C1_mmr | 1,00 | 0,920 | 30,0 |
| q26 | C2_mmr_rerank | 1,00 | 1,000 | 251,0 |
| q26 | C3_mmr_rerank_dedupe | 1,00 | 1,000 | 243,6 |
| q27 | C0_baseline | 0,00 | 0,000 | 17,6 |
| q27 | C1_mmr | 1,00 | 0,544 | 21,3 |
| q27 | C2_mmr_rerank | 0,50 | 0,387 | 274,4 |
| q27 | C3_mmr_rerank_dedupe | 0,50 | 0,387 | 296,9 |
| q28 | C0_baseline | 0,00 | 0,000 | 24,1 |
| q28 | C1_mmr | 0,00 | 0,000 | 21,4 |
| q28 | C2_mmr_rerank | 1,00 | 0,431 | 338,0 |
| q28 | C3_mmr_rerank_dedupe | 1,00 | 0,431 | 341,5 |
| q29 | C0_baseline | 0,50 | 0,500 | 23,4 |
| q29 | C1_mmr | 1,00 | 0,544 | 21,9 |
| q29 | C2_mmr_rerank | 0,00 | 0,000 | 283,1 |
| q29 | C3_mmr_rerank_dedupe | 0,00 | 0,000 | 269,8 |
| q30 | C0_baseline | 1,00 | 0,500 | 24,7 |
| q30 | C1_mmr | 1,00 | 0,500 | 27,2 |
| q30 | C2_mmr_rerank | 1,00 | 0,631 | 253,5 |
| q30 | C3_mmr_rerank_dedupe | 1,00 | 0,631 | 244,6 |

---

*Huom: Desimaalierottimena käytetty pilkkua. Reranker: BAAI/bge-reranker-v2-m3.*

# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Callable, Dict, List, Iterable
import math

__all__ = ["dcg", "ndcg_at_k", "recall_at_k", "eval_query"]

def dcg(relevances: List[float], k: int) -> float:
    return sum((relevances[i] / math.log2(i + 2)) for i in range(min(k, len(relevances))))

def ndcg_at_k(relevances: List[float], k: int) -> float:
    ideal = sorted(relevances, reverse=True)
    idcg = dcg(ideal, k)
    return 0.0 if idcg == 0 else dcg(relevances, k) / idcg

def recall_at_k(relevances: List[int], k: int) -> float:
    tot_rel = sum(1 for r in relevances if r > 0)
    hit_rel = sum(relevances[:k])
    return 0.0 if tot_rel == 0 else hit_rel / tot_rel

def eval_query(
    search_fn: Callable[[str, int], List[Dict]],
    query: str,
    expected_sources: Iterable[str],
    k: int = 5
) -> Dict:
    results = search_fn(query, k)
    preds = [r.get("source") for r in results]
    rel = [1 if s in expected_sources else 0 for s in preds]
    return {
        "preds": preds,
        f"recall@{k}": recall_at_k(rel, k),
        f"ndcg@{k}": ndcg_at_k(rel, k),
    }

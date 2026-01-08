# -*- coding: utf-8 -*-
"""
Relevance Evaluation Metrics

Provides standard information retrieval metrics for evaluating search quality:
- DCG (Discounted Cumulative Gain)
- nDCG@k (Normalized DCG at k)
- Recall@k
- Query evaluation wrapper

These metrics are essential for measuring RAG system performance and comparing
different retrieval strategies.

Functions:
    dcg: Calculate Discounted Cumulative Gain
    ndcg_at_k: Calculate normalized DCG at position k
    recall_at_k: Calculate recall at position k
    eval_query: Evaluate a search function on a query with expected sources
"""
from __future__ import annotations
from typing import Callable, Dict, List, Iterable
import math

__all__ = ["dcg", "ndcg_at_k", "recall_at_k", "eval_query"]

def dcg(relevances: List[float], k: int) -> float:
    """
    Calculate Discounted Cumulative Gain (DCG).
    
    DCG measures ranking quality by summing relevance scores with logarithmic
    discounting based on position. Higher positions contribute more to the score.
    
    Args:
        relevances: List of relevance scores (typically 0 or 1 for binary relevance)
        k: Number of top positions to consider
    
    Returns:
        DCG score (higher is better)
    
    Formula:
        DCG@k = sum(rel[i] / log2(i + 2)) for i in [0, k)
    
    Example:
        >>> dcg([1, 1, 0, 1], k=3)
        1.6309297535714573
    """
    return sum((relevances[i] / math.log2(i + 2)) for i in range(min(k, len(relevances))))

def ndcg_at_k(relevances: List[float], k: int) -> float:
    """
    Calculate Normalized Discounted Cumulative Gain at position k.
    
    nDCG normalizes DCG by the ideal DCG (perfect ranking), resulting in
    a score between 0 and 1. This makes it comparable across different queries.
    
    Args:
        relevances: List of relevance scores for items in ranked order
        k: Number of top positions to consider
    
    Returns:
        nDCG@k score (0.0 to 1.0, where 1.0 is perfect ranking)
    
    Example:
        >>> ndcg_at_k([1, 0, 1, 0], k=3)  # Not ideal order
        0.9197207891481875
        >>> ndcg_at_k([1, 1, 0, 0], k=3)  # Ideal order
        1.0
    """
    ideal = sorted(relevances, reverse=True)
    idcg = dcg(ideal, k)
    return 0.0 if idcg == 0 else dcg(relevances, k) / idcg

def recall_at_k(relevances: List[int], k: int) -> float:
    """
    Calculate Recall at position k.
    
    Recall measures the fraction of relevant items that were retrieved
    in the top k results.
    
    Args:
        relevances: List of binary relevance labels (0 or 1) for ranked items
        k: Number of top positions to consider
    
    Returns:
        Recall@k score (0.0 to 1.0, where 1.0 means all relevant items retrieved)
    
    Formula:
        Recall@k = (relevant items in top k) / (total relevant items)
    
    Example:
        >>> recall_at_k([1, 0, 1, 0, 1], k=3)  # 2 relevant in top 3, 3 total
        0.6666666666666666
    """
    tot_rel = sum(1 for r in relevances if r > 0)
    hit_rel = sum(relevances[:k])
    return 0.0 if tot_rel == 0 else hit_rel / tot_rel

def eval_query(
    search_fn: Callable[[str, int], List[Dict]],
    query: str,
    expected_sources: Iterable[str],
    k: int = 5
) -> Dict:
    """
    Evaluate a search function on a query with expected relevant sources.
    
    Runs the search function, compares results against expected sources,
    and computes recall@k and nDCG@k metrics.
    
    Args:
        search_fn: Search function that takes (query: str, top_k: int) and
                   returns list of dicts with 'source' key
        query: Search query string
        expected_sources: Set or iterable of source IDs that are relevant to the query
        k: Number of results to evaluate (default: 5)
    
    Returns:
        Dictionary containing:
            - preds: List of predicted source IDs from search results
            - recall@{k}: Recall at k score
            - ndcg@{k}: Normalized DCG at k score
    
    Example:
        >>> def my_search(q, top_k):
        ...     return [{"source": "doc1"}, {"source": "doc2"}]
        >>> metrics = eval_query(
        ...     my_search, "test query", {"doc1", "doc3"}, k=2
        ... )
        >>> "recall@2" in metrics
        True
        >>> metrics["recall@2"] == 0.5  # 1 of 2 relevant found
        True
    """
    results = search_fn(query, k)
    preds = [r.get("source") for r in results]
    rel = [1 if s in expected_sources else 0 for s in preds]
    return {
        "preds": preds,
        f"recall@{k}": recall_at_k(rel, k),
        f"ndcg@{k}": ndcg_at_k(rel, k),
    }

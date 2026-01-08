# -*- coding: utf-8 -*-
"""
Latency Measurement Utilities

Provides functions for measuring and analyzing latency/performance metrics
of functions, particularly useful for search and retrieval operations.

Functions:
    measure_latency: Measure function execution time and compute percentile metrics
"""
from __future__ import annotations
from typing import Callable, Dict
import time
from statistics import median, quantiles

__all__ = ["measure_latency"]

def measure_latency(fn: Callable[[], None], runs: int = 30, warmup: int = 3) -> Dict[str, float]:
    """
    Measure function execution latency and compute percentile metrics.
    
    Executes the function multiple times (with warmup runs) and computes
    p50 (median), p95, and p99 latency percentiles in milliseconds.
    
    Args:
        fn: Function to measure (must take no arguments)
        runs: Number of measurement runs (default: 30)
        warmup: Number of warmup runs to exclude from measurements (default: 3)
    
    Returns:
        Dictionary with latency metrics:
            - p50_ms: 50th percentile (median) latency in milliseconds
            - p95_ms: 95th percentile latency in milliseconds
            - p99_ms: 99th percentile latency in milliseconds
    
    Example:
        >>> def search_operation():
        ...     # Simulate search
        ...     time.sleep(0.01)
        >>> metrics = measure_latency(search_operation, runs=20, warmup=2)
        >>> "p50_ms" in metrics
        True
        >>> metrics["p50_ms"] > 0
        True
    
    Note:
        Uses time.perf_counter() for high-resolution timing.
        Warmup runs help account for cold-start effects (model loading, etc.).
    """
    times = []
    for i in range(runs + warmup):
        t0 = time.perf_counter()
        fn()
        dt = (time.perf_counter() - t0) * 1000.0
        if i >= warmup:
            times.append(dt)

    times_sorted = sorted(times)
    p50 = median(times_sorted)
    q = quantiles(times_sorted, n=100)
    p95 = q[94] if len(q) >= 95 else times_sorted[max(0, int(0.95*len(times_sorted))-1)]
    p99 = q[98] if len(q) >= 99 else times_sorted[max(0, int(0.99*len(times_sorted))-1)]
    return {"p50_ms": p50, "p95_ms": p95, "p99_ms": p99}

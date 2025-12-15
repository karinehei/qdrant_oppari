# -*- coding: utf-8 -*-
from __future__ import annotations
from typing import Callable, Dict
import time
from statistics import median, quantiles

__all__ = ["measure_latency"]

def measure_latency(fn: Callable[[], None], runs: int = 30, warmup: int = 3) -> Dict[str, float]:
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

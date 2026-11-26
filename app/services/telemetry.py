"""Lightweight, privacy-safe telemetry for the AI features.

Records counts and latencies only, never prompts, answers, or visitor data.
State is per process and resets on restart; it answers "is it slow, is the
cache working, how often do we refuse or block output" without a vendor.
"""

from __future__ import annotations

import time
from collections import Counter, defaultdict, deque
from statistics import median
from threading import Lock

MAX_SAMPLES = 500
# Rough English average used only for the labelled *estimate* of token volume.
CHARS_PER_TOKEN = 4

_lock = Lock()
_started = time.time()
_counters: Counter[str] = Counter()
_latencies: dict[str, deque[float]] = defaultdict(lambda: deque(maxlen=MAX_SAMPLES))
_estimated_tokens: Counter[str] = Counter()


def record_llm_metric(name: str, value: int = 1) -> None:
    with _lock:
        _counters[name] += value


def record_latency(feature: str, milliseconds: float) -> None:
    with _lock:
        _latencies[feature].append(milliseconds)


def record_text_volume(feature: str, prompt_chars: int, output_chars: int) -> None:
    with _lock:
        _estimated_tokens[f"{feature}.input"] += prompt_chars // CHARS_PER_TOKEN
        _estimated_tokens[f"{feature}.output"] += output_chars // CHARS_PER_TOKEN


class Timer:
    """`with Timer("assistant.generate"):` records wall-clock latency."""

    def __init__(self, feature: str) -> None:
        self.feature = feature
        self.started = 0.0

    def __enter__(self) -> "Timer":
        self.started = time.perf_counter()
        return self

    def __exit__(self, *_exc) -> None:
        record_latency(self.feature, (time.perf_counter() - self.started) * 1000)


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round(fraction * (len(ordered) - 1))))
    return ordered[index]


def snapshot() -> dict:
    with _lock:
        counters = dict(_counters)
        latencies = {name: list(samples) for name, samples in _latencies.items()}
        tokens = dict(_estimated_tokens)
    answered = counters.get("assistant.answered", 0)
    cache_hits = counters.get("assistant.cache_hit", 0)
    return {
        "since": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(_started)),
        "counters": counters,
        "rates": {
            "cache_hit_rate": round(cache_hits / (answered + cache_hits), 3) if answered + cache_hits else None,
            "refusal_rate": round(counters.get("assistant.refused", 0) / max(1, answered + cache_hits + counters.get("assistant.refused", 0)), 3),
        },
        "latency_ms": {
            name: {
                "count": len(values),
                "p50": round(median(values)),
                "p95": round(_percentile(values, 0.95)),
                "max": round(max(values)),
            }
            for name, values in sorted(latencies.items()) if values
        },
        "estimated_tokens": tokens,
        "notes": "Per-process since last restart. Token figures are estimates (characters / 4); no content is recorded.",
    }


def reset_for_tests() -> None:
    with _lock:
        _counters.clear()
        _latencies.clear()
        _estimated_tokens.clear()

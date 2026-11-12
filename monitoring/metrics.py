"""Dependency-free, thread-safe metric registry with Prometheus text exposition.

Labels are restricted to bounded vocabularies (route template, status class, error code, variant).
No request payloads, feature values, credentials or filesystem paths are ever stored.
"""
import math
import threading
from collections import defaultdict

LATENCY_BUCKETS_MS = (5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000)

class Registry:
    def __init__(self):
        self._lock = threading.Lock()
        self.reset()

    def reset(self):
        with getattr(self, "_lock", threading.Lock()):
            self.counters = defaultdict(float)      # (name, labels) -> value
            self.gauges = {}                        # (name, labels) -> value
            self.histograms = defaultdict(lambda: {"count": 0, "sum": 0.0, "buckets": defaultdict(int), "values": []})
            self.info = {}

    @staticmethod
    def _key(name, labels):
        return name, tuple(sorted((labels or {}).items()))

    def inc(self, name, value=1.0, **labels):
        with self._lock:
            self.counters[self._key(name, labels)] += value

    def set_gauge(self, name, value, **labels):
        with self._lock:
            self.gauges[self._key(name, labels)] = float(value)

    def observe(self, name, value, buckets=LATENCY_BUCKETS_MS, keep=2048, **labels):
        with self._lock:
            h = self.histograms[self._key(name, labels)]
            h["count"] += 1
            h["sum"] += value
            for b in buckets:
                if value <= b:
                    h["buckets"][b] += 1
            h["values"].append(value)
            del h["values"][:-keep]          # bounded memory; used for p95/p99

    def counter(self, name, **labels):
        with self._lock:
            return self.counters.get(self._key(name, labels), 0.0)

    def counter_sum(self, name, **match):
        with self._lock:
            return sum(v for (n, lab), v in self.counters.items() if n == name and all(dict(lab).get(k) == str(x) for k, x in match.items()))

    def percentile(self, name, q, **labels):
        with self._lock:
            vals = sorted(self.histograms[self._key(name, labels)]["values"]) if self._key(name, labels) in self.histograms else []
        if not vals:
            return None
        return vals[min(len(vals) - 1, math.ceil(q * len(vals)) - 1)]

    def histogram_count(self, name, **labels):
        with self._lock:
            h = self.histograms.get(self._key(name, labels))
            return h["count"] if h else 0

    def snapshot(self):
        with self._lock:
            return {"counters": {f"{n}{dict(l)}": v for (n, l), v in self.counters.items()},
                    "gauges": {f"{n}{dict(l)}": v for (n, l), v in self.gauges.items()},
                    "histograms": {f"{n}{dict(l)}": {"count": h["count"], "sum": h["sum"]} for (n, l), h in self.histograms.items()}}

    def render_prometheus(self):
        def fmt(labels, extra=None):
            items = list(labels) + list((extra or {}).items())
            return "{" + ",".join(f'{k}="{str(v).replace(chr(34), "")}"' for k, v in items) + "}" if items else ""
        lines = []
        with self._lock:
            for (n, l), v in sorted(self.counters.items()):
                lines.append(f"{n}{fmt(l)} {v}")
            for (n, l), v in sorted(self.gauges.items()):
                lines.append(f"{n}{fmt(l)} {v}")
            for (n, l), h in sorted(self.histograms.items()):
                for b in sorted(h["buckets"]):
                    lines.append(f"{n}_bucket{fmt(l, {'le': b})} {h['buckets'][b]}")
                lines.append(f"{n}_bucket{fmt(l, {'le': '+Inf'})} {h['count']}")
                lines.append(f"{n}_sum{fmt(l)} {h['sum']}")
                lines.append(f"{n}_count{fmt(l)} {h['count']}")
            for n, labels in sorted(self.info.items()):
                lines.append(f"{n}{fmt(sorted(labels.items()))} 1")
        return "\n".join(lines) + "\n"

REGISTRY = Registry()

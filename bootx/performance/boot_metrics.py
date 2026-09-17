"""Boot performance measurement.

Runs the same boot configuration multiple times and reports min/max/mean/
median for each canonical stage-to-stage latency, plus total boot time.
All numbers come from actually-executed QEMU boots (bootx.tracing) -- see
docs/limitations.md for why this measures BOOTX/QEMU-observed timing, not
real Snapdragon silicon timing.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from bootx.tracing.timeline import BootTimeline


@dataclass(frozen=True)
class MetricSummary:
    name: str
    samples: list[float]

    @property
    def min(self) -> float:
        return min(self.samples)

    @property
    def max(self) -> float:
        return max(self.samples)

    @property
    def mean(self) -> float:
        return statistics.mean(self.samples)

    @property
    def median(self) -> float:
        return statistics.median(self.samples)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "n": len(self.samples),
            "min_ms": round(self.min, 3),
            "max_ms": round(self.max, 3),
            "mean_ms": round(self.mean, 3),
            "median_ms": round(self.median, 3),
        }


class BootPerformanceReport:
    def __init__(self, timelines: list[BootTimeline]):
        self.timelines = timelines

    def summarize(self) -> list[MetricSummary]:
        by_metric: dict[str, list[float]] = {}
        for tl in self.timelines:
            for sl in tl.stage_latencies():
                key = f"{sl.from_event.value}->{sl.to_event.value}"
                by_metric.setdefault(key, []).append(sl.latency_ms)
            total = tl.total_boot_ms()
            if total is not None:
                by_metric.setdefault("TOTAL_BOOT", []).append(total)

        return [MetricSummary(name=k, samples=v) for k, v in by_metric.items() if v]

    def to_dict(self) -> dict:
        return {"iterations": len(self.timelines), "metrics": [m.to_dict() for m in self.summarize()]}

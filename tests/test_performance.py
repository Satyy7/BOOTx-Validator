"""Boot performance measurement: multiple real boots, real timing.

See docs/limitations.md: this measures BOOTX/QEMU host-observed wall-clock
latency, which is useful for regression tracking but is explicitly NOT
representative of real Snapdragon silicon boot timing.
"""

from __future__ import annotations

import dataclasses

import pytest

from bootx.orchestrator.runner import BootRunner
from bootx.performance.boot_metrics import BootPerformanceReport


@pytest.mark.performance
@pytest.mark.regression
def test_boot_performance_report_over_multiple_iterations(require_firmware, basic_boot_config):
    iterations = 3
    timelines = []
    for i in range(iterations):
        # BootConfig is a frozen dataclass (intentionally immutable -- see
        # bootx/orchestrator/config.py), so each iteration needs its own copy.
        iteration_config = dataclasses.replace(basic_boot_config, run_label=f"perf-{i}")
        run = BootRunner().run(iteration_config)
        assert not run.qemu_result.timed_out
        timelines.append(run.timeline)

    report = BootPerformanceReport(timelines)
    summary = report.summarize()

    assert len(summary) > 0
    total_metric = next((m for m in summary if m.name == "TOTAL_BOOT"), None)
    assert total_metric is not None
    assert total_metric.min <= total_metric.mean <= total_metric.max
    assert len(total_metric.samples) == iterations

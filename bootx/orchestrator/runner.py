"""BootRunner: the high-level API that ties together QEMU launch, serial
capture, event parsing, timeline construction, and on-disk run artifacts.

This is what the CLI and pytest test suite call; individual layers
(QemuRunner, parser, BootTimeline, ...) stay independently testable.
"""

from __future__ import annotations

from dataclasses import dataclass

from bootx.orchestrator.config import BootConfig
from bootx.orchestrator.lifecycle import REPORTS_ROOT, RunDirectory
from bootx.orchestrator.qemu import QemuResult, QemuRunner
from bootx.tracing.parser import parse_timestamped_lines
from bootx.tracing.timeline import BootTimeline


@dataclass
class BootRun:
    run_dir: RunDirectory
    qemu_result: QemuResult
    timeline: BootTimeline


class BootRunner:
    def __init__(self, reports_root=REPORTS_ROOT):
        self.reports_root = reports_root

    def run(self, config: BootConfig, firmware_versions: dict[str, str] | None = None) -> BootRun:
        run_dir = RunDirectory(self.reports_root, label=config.run_label)
        qemu = QemuRunner(config, run_dir.qemu_log)

        run_dir.write_metadata(
            command=qemu.command(),
            config={
                "cpus": config.cpus,
                "ram_mb": config.ram_mb,
                "machine": config.machine,
                "cpu_model": config.cpu_model,
                "timeout_s": config.timeout_s,
                "bootargs": config.bootargs,
                "firmware": {
                    "bios": str(config.firmware.bios),
                    "kernel": str(config.firmware.kernel) if config.firmware.kernel else None,
                    "initrd": str(config.firmware.initrd) if config.firmware.initrd else None,
                    "dtb": str(config.firmware.dtb) if config.firmware.dtb else None,
                },
            },
            firmware_versions=firmware_versions or {},
        )

        result = qemu.run()
        events = parse_timestamped_lines(result.timestamped_lines)
        timeline = BootTimeline(events)

        run_dir.write_events(events)
        run_dir.write_result(
            {
                "returncode": result.returncode,
                "timed_out": result.timed_out,
                "duration_s": result.duration_s,
                "timeline": timeline.to_dict(),
            }
        )

        return BootRun(run_dir=run_dir, qemu_result=result, timeline=timeline)

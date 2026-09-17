"""Boot log parser: turns raw serial lines into structured BootEvents.

Patterns target the real console output of TF-A, U-Boot and Linux as
built by this project (see docs/boot-flow.md for the exact strings
captured from a live BOOTX run). A rule only fires on a genuine
substring/regex match against a raw line -- nothing here invents an
event that wasn't printed by the firmware or kernel.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from bootx.tracing.events import BootEvent, EventSource, EventType


@dataclass(frozen=True)
class _Rule:
    event: EventType
    stage: str
    pattern: re.Pattern
    cpu_group: str | None = None


_RULES: list[_Rule] = [
    _Rule(EventType.BL1_ENTRY, "BL1", re.compile(r"NOTICE:\s*BL1:\s*v\d")),
    _Rule(EventType.BL2_ENTRY, "BL2", re.compile(r"NOTICE:\s*BL2:\s*v\d")),
    _Rule(EventType.BL2_INIT_COMPLETE, "BL2", re.compile(r"BL2:\s*Booting BL31")),
    _Rule(EventType.BL31_ENTRY, "BL31", re.compile(r"NOTICE:\s*BL31:\s*v\d")),
    _Rule(EventType.PSCI_INIT, "BL31", re.compile(r"PSCI:.*(init|Init)")),
    _Rule(EventType.BL31_INIT_COMPLETE, "BL31", re.compile(r"BL31:\s*Preparing for EL3 exit")),
    _Rule(EventType.BL33_ENTRY, "BL33", re.compile(r"^U-Boot \d{4}\.\d{2}")),
    _Rule(EventType.DTB_LOADED, "BL33", re.compile(r"Flattened Device Tree blob at|Booting using the fdt")),
    _Rule(EventType.KERNEL_LOADING, "BL33", re.compile(r"Loading Kernel Image|Starting kernel")),
    _Rule(EventType.KERNEL_ENTRY, "KERNEL", re.compile(r"Booting Linux on physical CPU")),
    _Rule(EventType.LINUX_VERSION, "KERNEL", re.compile(r"Linux version \d")),
    _Rule(
        EventType.CPU_ON,
        "KERNEL",
        re.compile(r"CPU(?P<cpu>\d+):\s*Booted secondary processor"),
        cpu_group="cpu",
    ),
    _Rule(EventType.USERSPACE_READY, "USERSPACE", re.compile(r"BOOTX_USERSPACE_READY")),
    _Rule(EventType.KERNEL_PANIC, "KERNEL", re.compile(r"Kernel panic")),
    _Rule(EventType.FIRMWARE_PANIC, "FIRMWARE", re.compile(r"PANIC AT|ERROR:\s*BL\d")),
]


def parse_line(elapsed_ms: float, line: str) -> BootEvent | None:
    """Return a BootEvent if `line` matches a known firmware/kernel marker."""
    for rule in _RULES:
        m = rule.pattern.search(line)
        if not m:
            continue
        cpu = int(m.group(rule.cpu_group)) if rule.cpu_group else None
        return BootEvent(
            event=rule.event,
            stage=rule.stage,
            timestamp_ms=elapsed_ms,
            raw_line=line,
            source=EventSource.UART,
            cpu=cpu,
        )
    return None


def parse_timestamped_lines(timestamped_lines: list[tuple[float, str]]) -> list[BootEvent]:
    """Parse a full captured serial session into an ordered event list.

    Always prepends a synthetic BOOT_START at t=0 and appends a synthetic
    BOOT_COMPLETE if USERSPACE_READY was observed -- both are clearly
    marked source=SYNTHETIC, never confused with directly observed events.
    """
    events: list[BootEvent] = [
        BootEvent(
            event=EventType.BOOT_START,
            stage="RESET",
            timestamp_ms=0.0,
            raw_line="<qemu process launch>",
            source=EventSource.SYNTHETIC,
        )
    ]
    for elapsed_ms, line in timestamped_lines:
        evt = parse_line(elapsed_ms, line)
        if evt is not None:
            events.append(evt)

    if any(e.event == EventType.USERSPACE_READY for e in events):
        last_ts = events[-1].timestamp_ms
        events.append(
            BootEvent(
                event=EventType.BOOT_COMPLETE,
                stage="USERSPACE",
                timestamp_ms=last_ts,
                raw_line="<inferred from USERSPACE_READY>",
                source=EventSource.SYNTHETIC,
            )
        )
    return events

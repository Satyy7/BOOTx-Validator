"""Unit tests for the boot log parser (bootx/tracing/parser.py).

These test the parser against real, literal console lines TF-A/U-Boot/
Linux are known to print (see docs/boot-flow.md), without needing QEMU.
"""

from __future__ import annotations

import pytest

from bootx.tracing.events import EventType
from bootx.tracing.parser import parse_line, parse_timestamped_lines


@pytest.mark.smoke
@pytest.mark.parametrize(
    "line,expected_event,expected_stage",
    [
        ("NOTICE:  BL1: v2.15.0(release):v2.15.0", EventType.BL1_ENTRY, "BL1"),
        ("NOTICE:  BL2: v2.15.0(release):v2.15.0", EventType.BL2_ENTRY, "BL2"),
        ("NOTICE:  BL31: v2.15.0(release):v2.15.0", EventType.BL31_ENTRY, "BL31"),
        ("INFO:    BL31: Preparing for EL3 exit to normal world", EventType.BL31_INIT_COMPLETE, "BL31"),
        ("U-Boot 2026.07 (Sep 18 2026 - 00:00:00 +0000)", EventType.BL33_ENTRY, "BL33"),
        ("   Booting using the fdt blob at 0x40000000", EventType.DTB_LOADED, "BL33"),
        ("Booting Linux on physical CPU 0x0000000000 [0x410fd083]", EventType.KERNEL_ENTRY, "KERNEL"),
        ("Linux version 6.12.0 (build@bootx)", EventType.LINUX_VERSION, "KERNEL"),
        ("CPU1: Booted secondary processor 0x0000000001 [0x410fd083]", EventType.CPU_ON, "KERNEL"),
        ("BOOTX_USERSPACE_READY", EventType.USERSPACE_READY, "USERSPACE"),
        ("Kernel panic - not syncing: Attempted to kill init!", EventType.KERNEL_PANIC, "KERNEL"),
    ],
)
def test_parse_line_matches_known_markers(line, expected_event, expected_stage):
    event = parse_line(1.0, line)
    assert event is not None, f"expected a match for: {line!r}"
    assert event.event == expected_event
    assert event.stage == expected_stage
    assert event.raw_line == line


@pytest.mark.smoke
def test_parse_line_no_match_returns_none():
    assert parse_line(1.0, "this is not a boot log line") is None


@pytest.mark.smoke
def test_cpu_on_extracts_cpu_number():
    event = parse_line(1.0, "CPU3: Booted secondary processor 0x0000000003 [0x410fd083]")
    assert event is not None
    assert event.cpu == 3


@pytest.mark.boot
def test_parse_timestamped_lines_synthesizes_boot_start_and_complete():
    lines = [
        (0.5, "NOTICE:  BL1: v2.15.0(release):v2.15.0"),
        (10.0, "U-Boot 2026.07 (Sep 18 2026 - 00:00:00 +0000)"),
        (200.0, "Booting Linux on physical CPU 0x0000000000 [0x410fd083]"),
        (400.0, "BOOTX_USERSPACE_READY"),
    ]
    events = parse_timestamped_lines(lines)

    assert events[0].event == EventType.BOOT_START
    assert events[0].timestamp_ms == 0.0
    assert events[-1].event == EventType.BOOT_COMPLETE
    assert any(e.event == EventType.USERSPACE_READY for e in events)


@pytest.mark.boot
def test_parse_timestamped_lines_no_completion_event_without_userspace_ready():
    lines = [(0.5, "NOTICE:  BL1: v2.15.0(release):v2.15.0")]
    events = parse_timestamped_lines(lines)
    assert all(e.event != EventType.BOOT_COMPLETE for e in events)

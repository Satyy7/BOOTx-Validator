"""Structured boot event model.

An event is only ever emitted when a parser rule matches an actual raw
line of serial console output -- see docs/limitations.md ("No fabricated
events"). Each event carries the raw evidence line so any downstream
consumer (contract engine, classifier, human) can verify the claim.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EventType(str, Enum):
    BOOT_START = "BOOT_START"
    BL1_ENTRY = "BL1_ENTRY"
    BL2_ENTRY = "BL2_ENTRY"
    BL2_INIT_COMPLETE = "BL2_INIT_COMPLETE"
    BL31_ENTRY = "BL31_ENTRY"
    PSCI_INIT = "PSCI_INIT"
    BL31_INIT_COMPLETE = "BL31_INIT_COMPLETE"
    BL33_ENTRY = "BL33_ENTRY"
    """BL33 entry, evidenced by the U-Boot banner. BL33 and U-Boot are the
    same stage in BOOTX's boot flow (docs/boot-flow.md), so this is the
    single canonical event -- there is deliberately no separate
    UBOOT_ENTRY, since a duplicate event backed by the same log line would
    be redundant and, worse, would only ever be emitted by whichever rule
    happens to be checked first in the parser."""
    DTB_LOADED = "DTB_LOADED"
    KERNEL_LOADING = "KERNEL_LOADING"
    KERNEL_ENTRY = "KERNEL_ENTRY"
    LINUX_VERSION = "LINUX_VERSION"
    CPU_ON = "CPU_ON"
    CPU_OFF = "CPU_OFF"
    USERSPACE_READY = "USERSPACE_READY"
    BOOT_COMPLETE = "BOOT_COMPLETE"
    KERNEL_PANIC = "KERNEL_PANIC"
    FIRMWARE_PANIC = "FIRMWARE_PANIC"


class EventSource(str, Enum):
    UART = "uart"
    """Directly observed in the captured serial console stream."""
    SYNTHETIC = "synthetic"
    """Derived by BOOTX (e.g. BOOT_START at process launch, BOOT_COMPLETE
    inferred from USERSPACE_READY), not itself a raw log line."""


@dataclass(frozen=True)
class BootEvent:
    event: EventType
    stage: str
    timestamp_ms: float
    raw_line: str
    source: EventSource = EventSource.UART
    cpu: int | None = None

    def to_dict(self) -> dict:
        return {
            "event": self.event.value,
            "stage": self.stage,
            "timestamp_ms": round(self.timestamp_ms, 3),
            "raw_line": self.raw_line,
            "source": self.source.value,
            "cpu": self.cpu,
        }

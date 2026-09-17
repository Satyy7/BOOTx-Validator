"""Fault: feed QEMU/U-Boot a malformed or semantically invalid DTB."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bootx.faults.base import Fault, FaultExpectation


class InvalidDtbFault(Fault):
    name = "invalid_dtb"
    description = "Truncate a real DTB so it is no longer a structurally valid FDT blob."

    def __init__(self, source_dtb: Path, truncate_fraction: float = 0.3):
        self.source_dtb = source_dtb
        self.truncate_fraction = truncate_fraction

    def expectation(self) -> FaultExpectation:
        return FaultExpectation(
            category="DTB_FAILURE",
            description="Truncated/malformed DTB should be rejected by dtc validation and/or fail to boot.",
        )

    def inject(self, workdir: Path) -> dict[str, Any]:
        target = workdir / self.source_dtb.name
        data = self.source_dtb.read_bytes()
        cut = int(len(data) * self.truncate_fraction)
        target.write_bytes(data[:cut])
        return {"mutated_dtb": target, "original_size": len(data), "truncated_size": cut}


class MissingDtbFault(Fault):
    name = "missing_dtb"
    description = "Point the boot configuration at a DTB path that does not exist."

    def expectation(self) -> FaultExpectation:
        return FaultExpectation(
            category="DTB_FAILURE",
            description="Missing DTB should be caught before or during QEMU launch.",
        )

    def inject(self, workdir: Path) -> dict[str, Any]:
        missing_path = workdir / "does-not-exist.dtb"
        return {"mutated_dtb": missing_path}

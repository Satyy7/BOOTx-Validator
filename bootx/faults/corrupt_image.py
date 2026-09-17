"""Fault: corrupt a firmware image payload byte.

Flips bytes inside a real firmware binary (e.g. BL33/U-Boot) after
copying it to a scratch directory, leaving the original untouched. This
mirrors bit-flip / storage-corruption style failures rather than
byte-for-byte reproducing any specific real-world attack.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bootx.faults.base import Fault, FaultExpectation


class CorruptImageFault(Fault):
    name = "corrupt_image"
    description = "Flip bytes inside a firmware image payload to simulate storage/transfer corruption."

    def __init__(self, source_image: Path, offset_fraction: float = 0.5, num_bytes: int = 64):
        self.source_image = source_image
        self.offset_fraction = offset_fraction
        self.num_bytes = num_bytes

    def expectation(self) -> FaultExpectation:
        return FaultExpectation(
            category="IMAGE_FAILURE",
            description="Corrupted image should fail integrity validation and/or crash the boot stage that loads it.",
        )

    def inject(self, workdir: Path) -> dict[str, Any]:
        target = workdir / self.source_image.name
        target.write_bytes(self.source_image.read_bytes())

        data = bytearray(target.read_bytes())
        offset = int(len(data) * self.offset_fraction)
        end = min(offset + self.num_bytes, len(data))
        for i in range(offset, end):
            data[i] ^= 0xFF
        target.write_bytes(data)

        return {"mutated_image": target, "offset": offset, "length": end - offset}

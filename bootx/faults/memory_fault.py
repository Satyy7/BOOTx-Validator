"""Fault: construct an overlapping/out-of-range memory map for the
memory validator (bootx.validation.memory) to catch.

This fault does not touch QEMU at all -- it exercises the memory model
validator directly with a deliberately invalid MemoryRegion set, the same
way a real corrupted linker script or misconfigured load address would
produce an invalid map. It's a validator-level negative test, not a
boot-level one.
"""

from __future__ import annotations

from bootx.validation.memory import MemoryRegion

OVERLAPPING_REGIONS = [
    MemoryRegion("BL31", start=0x41000000, size=0x00200000),
    MemoryRegion("BL33", start=0x41100000, size=0x00200000),
]

def out_of_range_regions(ram_start: int, ram_size: int) -> list[MemoryRegion]:
    return [MemoryRegion("BL33", start=ram_start + ram_size - 0x1000, size=0x00400000)]

MISALIGNED_REGIONS = [
    MemoryRegion("BL31", start=0x41000001, size=0x00200000),
]

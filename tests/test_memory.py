"""Unit tests for the memory map validator (bootx/validation/memory.py)."""

from __future__ import annotations

import pytest

from bootx.faults.memory_fault import MISALIGNED_REGIONS, OVERLAPPING_REGIONS, out_of_range_regions
from bootx.validation.memory import MemoryIssue, MemoryMapValidator, MemoryRegion

RAM_START = 0x40000000
RAM_SIZE = 0x80000000  # 2GiB


@pytest.mark.memory
def test_valid_non_overlapping_regions_pass():
    validator = MemoryMapValidator(RAM_START, RAM_SIZE)
    regions = [
        MemoryRegion("BL31", start=0x40100000, size=0x00040000),
        MemoryRegion("BL33", start=0x40200000, size=0x00200000),
    ]
    result = validator.validate(regions)
    assert result.passed
    assert result.findings == []


@pytest.mark.memory
def test_overlapping_regions_detected():
    validator = MemoryMapValidator(RAM_START, RAM_SIZE)
    result = validator.validate(OVERLAPPING_REGIONS)
    assert not result.passed
    assert any(f.issue == MemoryIssue.OVERLAP for f in result.findings)


@pytest.mark.memory
def test_out_of_range_region_detected():
    validator = MemoryMapValidator(RAM_START, RAM_SIZE)
    result = validator.validate(out_of_range_regions(RAM_START, RAM_SIZE))
    assert not result.passed
    assert any(f.issue == MemoryIssue.OUT_OF_RANGE for f in result.findings)


@pytest.mark.memory
def test_misaligned_region_detected():
    validator = MemoryMapValidator(RAM_START, RAM_SIZE)
    result = validator.validate(MISALIGNED_REGIONS)
    assert not result.passed
    assert any(f.issue == MemoryIssue.MISALIGNED for f in result.findings)


@pytest.mark.memory
def test_region_end_and_overlap_helper():
    a = MemoryRegion("A", start=0x1000, size=0x1000)
    b = MemoryRegion("B", start=0x1800, size=0x1000)
    c = MemoryRegion("C", start=0x3000, size=0x1000)
    assert a.end == 0x2000
    assert a.overlaps(b)
    assert not a.overlaps(c)

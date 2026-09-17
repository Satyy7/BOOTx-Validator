"""Memory map validation: detects overlap, out-of-RAM, and misalignment
across the memory regions occupied by each firmware/boot stage.

This validates the region model BOOTX builds from known load addresses
(from the build configuration / image manifests), not a live memory dump
from the guest -- QEMU does not expose a supported introspection API for
that without significant additional instrumentation. See
docs/limitations.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class MemoryIssue(str, Enum):
    OVERLAP = "MEMORY_OVERLAP"
    OUT_OF_RANGE = "MEMORY_OUT_OF_RANGE"
    MISALIGNED = "MEMORY_MISALIGNED"


@dataclass(frozen=True)
class MemoryRegion:
    name: str
    start: int
    size: int
    alignment: int = 0x1000

    @property
    def end(self) -> int:
        return self.start + self.size

    def overlaps(self, other: "MemoryRegion") -> bool:
        return self.start < other.end and other.start < self.end


@dataclass(frozen=True)
class MemoryFinding:
    issue: MemoryIssue
    regions: tuple[str, ...]
    detail: str


@dataclass(frozen=True)
class MemoryValidationResult:
    passed: bool
    findings: list[MemoryFinding]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "findings": [
                {"issue": f.issue.value, "regions": list(f.regions), "detail": f.detail}
                for f in self.findings
            ],
        }


class MemoryMapValidator:
    def __init__(self, ram_start: int, ram_size: int):
        self.ram_start = ram_start
        self.ram_size = ram_size
        self.ram_end = ram_start + ram_size

    def validate(self, regions: list[MemoryRegion]) -> MemoryValidationResult:
        findings: list[MemoryFinding] = []

        for r in regions:
            if r.start % r.alignment != 0:
                findings.append(
                    MemoryFinding(
                        MemoryIssue.MISALIGNED,
                        (r.name,),
                        f"{r.name} start 0x{r.start:x} is not aligned to 0x{r.alignment:x}",
                    )
                )
            if r.start < self.ram_start or r.end > self.ram_end:
                findings.append(
                    MemoryFinding(
                        MemoryIssue.OUT_OF_RANGE,
                        (r.name,),
                        f"{r.name} [0x{r.start:x}-0x{r.end:x}) falls outside RAM "
                        f"[0x{self.ram_start:x}-0x{self.ram_end:x})",
                    )
                )

        for i, a in enumerate(regions):
            for b in regions[i + 1 :]:
                if a.overlaps(b):
                    findings.append(
                        MemoryFinding(
                            MemoryIssue.OVERLAP,
                            (a.name, b.name),
                            f"{a.name} [0x{a.start:x}-0x{a.end:x}) overlaps "
                            f"{b.name} [0x{b.start:x}-0x{b.end:x})",
                        )
                    )

        return MemoryValidationResult(passed=len(findings) == 0, findings=findings)

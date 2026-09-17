"""Fault injection base interface.

Every fault: (1) mutates a real, working boot artifact or configuration
in a controlled, reversible way, (2) is expected to make the boot fail in
a *specific*, documented manner, and (3) is scored PASS when BOOTX's own
classifier correctly detects that failure -- not when the boot merely
fails. An undetected or misclassified failure is a fault-injection test
FAILURE, even though the underlying boot also failed.
"""

from __future__ import annotations

import shutil
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FaultExpectation:
    category: str
    """Expected bootx.analysis.failure_classifier.FailureCategory value."""
    description: str


@dataclass(frozen=True)
class FaultResult:
    fault_name: str
    injected: bool
    expected_category: str
    actual_category: str | None
    detected: bool
    passed: bool
    detail: str

    def to_dict(self) -> dict:
        return {
            "fault_name": self.fault_name,
            "injected": self.injected,
            "expected_category": self.expected_category,
            "actual_category": self.actual_category,
            "detected": self.detected,
            "passed": self.passed,
            "detail": self.detail,
        }


class Fault(ABC):
    name: str
    description: str

    @abstractmethod
    def expectation(self) -> FaultExpectation: ...

    @abstractmethod
    def inject(self, workdir: Path) -> dict[str, Any]:
        """Mutate artifacts under `workdir` (a scratch copy). Returns context
        the caller needs to point QEMU at the mutated artifacts."""

    def backup(self, path: Path) -> Path:
        backup_path = path.with_suffix(path.suffix + ".bootx-orig")
        shutil.copy2(path, backup_path)
        return backup_path

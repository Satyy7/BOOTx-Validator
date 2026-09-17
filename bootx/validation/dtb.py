"""Device tree validation.

Wraps the real ``dtc`` (device-tree-compiler) binary to decompile the
actual DTB used for a boot into DTS text, then inspects it for the nodes
and properties BOOTX cares about (memory, cpus, interrupt controller,
UART). This inspects the real DTB blob, not a hand-written JSON stand-in.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

DTC_BINARY = "dtc"


class DtcNotFoundError(RuntimeError):
    pass


def _find_dtc() -> str:
    path = shutil.which(DTC_BINARY)
    if path is None:
        raise DtcNotFoundError(
            "dtc not found on PATH. Install device-tree-compiler to run DTB validation."
        )
    return path


def decompile(dtb_path: Path) -> str:
    """Run `dtc -I dtb -O dts` and return the DTS text."""
    dtc = _find_dtc()
    result = subprocess.run(
        [dtc, "-I", "dtb", "-O", "dts", "-o", "-", str(dtb_path)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise ValueError(f"dtc failed to decompile {dtb_path}: {result.stderr.strip()}")
    return result.stdout


@dataclass(frozen=True)
class DtbFinding:
    check: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class DtbValidationResult:
    passed: bool
    findings: list[DtbFinding] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "findings": [{"check": f.check, "passed": f.passed, "detail": f.detail} for f in self.findings],
        }


_MEMORY_NODE_RE = re.compile(r"memory@[0-9a-fA-F]+\s*{([^}]*)}", re.DOTALL)
_CPUS_NODE_RE = re.compile(r"\bcpus\s*{(.*?)\n\t};", re.DOTALL)
_CPU_CHILD_RE = re.compile(r"cpu@[0-9a-fA-F]+\s*{")
# GICv3+ nodes use an "arm,gic-v3"-style compatible string; QEMU's virt
# GICv2 node instead uses "arm,cortex-a15-gic" (verified against a real
# QEMU-generated DTB -- see docs/boot-flow.md), so both forms are matched.
_GIC_RE = re.compile(r'compatible\s*=\s*"[^"]*(arm,gic|arm,cortex-a15-gic|arm,gic-400)')
_UART_RE = re.compile(r'compatible\s*=\s*"[^"]*(arm,pl011|ns16550)')
_REG_PROP_RE = re.compile(r"\breg\s*=\s*<([^>]*)>")


class DtbValidator:
    """Validates a DTB against expected QEMU virt platform properties."""

    def __init__(self, expected_cpu_count: int, expected_ram_mb: int):
        self.expected_cpu_count = expected_cpu_count
        self.expected_ram_mb = expected_ram_mb

    def validate(self, dtb_path: Path) -> DtbValidationResult:
        try:
            dts = decompile(dtb_path)
        except (DtcNotFoundError, ValueError) as exc:
            return DtbValidationResult(
                passed=False, findings=[DtbFinding("decompile", False, str(exc))]
            )

        findings: list[DtbFinding] = []

        mem_match = _MEMORY_NODE_RE.search(dts)
        if mem_match is None:
            findings.append(DtbFinding("memory_node", False, "no /memory node found in DTB"))
        else:
            reg = _REG_PROP_RE.search(mem_match.group(1))
            if reg is None:
                findings.append(DtbFinding("memory_node", False, "/memory node has no reg property"))
            else:
                findings.append(DtbFinding("memory_node", True, "/memory node present with reg property"))

        cpus_match = _CPUS_NODE_RE.search(dts)
        if cpus_match is None:
            findings.append(DtbFinding("cpus_node", False, "no /cpus node found in DTB"))
        else:
            cpu_count = len(_CPU_CHILD_RE.findall(cpus_match.group(1)))
            ok = cpu_count == self.expected_cpu_count
            findings.append(
                DtbFinding(
                    "cpus_node",
                    ok,
                    f"/cpus declares {cpu_count} cpu node(s), expected {self.expected_cpu_count}",
                )
            )

        gic_ok = _GIC_RE.search(dts) is not None
        findings.append(
            DtbFinding("interrupt_controller", gic_ok, "GIC node " + ("found" if gic_ok else "NOT found"))
        )

        uart_ok = _UART_RE.search(dts) is not None
        findings.append(DtbFinding("uart", uart_ok, "UART node " + ("found" if uart_ok else "NOT found")))

        passed = all(f.passed for f in findings)
        return DtbValidationResult(passed=passed, findings=findings)

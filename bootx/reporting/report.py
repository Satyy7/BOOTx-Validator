"""Human-readable and JSON test report generation.

Every number in the generated report is read from an actual pytest
JUnit-XML result produced by a real test run (see bootx/cli/main.py
`report` command) -- nothing here is a hardcoded placeholder statistic.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ReportSummary:
    total: int
    passed: int
    failed: int
    skipped: int
    duration_s: float
    failures: list[dict]

    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
            "duration_s": round(self.duration_s, 3),
            "failures": self.failures,
        }


def summarize_junit(junit_path: Path) -> ReportSummary:
    tree = ET.parse(junit_path)
    root = tree.getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))

    total = passed = failed = skipped = 0
    duration = 0.0
    failures: list[dict] = []

    for suite in suites:
        for case in suite.findall("testcase"):
            total += 1
            duration += float(case.get("time", "0"))
            failure_el = case.find("failure")
            skipped_el = case.find("skipped")
            if skipped_el is not None:
                skipped += 1
            elif failure_el is not None:
                failed += 1
                failures.append(
                    {
                        "name": case.get("name"),
                        "classname": case.get("classname"),
                        "message": failure_el.get("message", ""),
                    }
                )
            else:
                passed += 1

    return ReportSummary(total=total, passed=passed, failed=failed, skipped=skipped, duration_s=duration, failures=failures)


def human_report(summary: ReportSummary, *, target: str, cpus: int, ram_mb: int) -> str:
    lines = [
        "BOOTX TEST REPORT",
        "",
        "Target:",
        f"    {target}",
        "",
        "CPUs:",
        f"    {cpus}",
        "",
        "RAM:",
        f"    {ram_mb} MB",
        "",
        "Tests:",
        f"    {summary.total}",
        "",
        "PASS:",
        f"    {summary.passed}",
        "",
        "FAIL:",
        f"    {summary.failed}",
        "",
        "SKIP:",
        f"    {summary.skipped}",
        "",
        "Duration:",
        f"    {summary.duration_s:.1f}s",
    ]
    if summary.failures:
        lines += ["", "FAILURES:"]
        for f in summary.failures:
            lines.append(f"    - {f['classname']}::{f['name']}: {f['message']}")
    return "\n".join(lines)


def write_json_report(summary: ReportSummary, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary.to_dict(), indent=2), encoding="utf-8")

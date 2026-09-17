"""JUnit XML report writer, for CI integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement


@dataclass
class JUnitCase:
    classname: str
    name: str
    passed: bool
    time_s: float = 0.0
    failure_message: str | None = None
    skipped: bool = False


@dataclass
class JUnitSuite:
    name: str
    cases: list[JUnitCase] = field(default_factory=list)


def write_junit(suites: list[JUnitSuite], out_path: Path) -> None:
    root = Element("testsuites")
    for suite in suites:
        total = len(suite.cases)
        failures = sum(1 for c in suite.cases if not c.passed and not c.skipped)
        skipped = sum(1 for c in suite.cases if c.skipped)
        suite_el = SubElement(
            root,
            "testsuite",
            {
                "name": suite.name,
                "tests": str(total),
                "failures": str(failures),
                "skipped": str(skipped),
                "time": f"{sum(c.time_s for c in suite.cases):.3f}",
            },
        )
        for case in suite.cases:
            case_el = SubElement(
                suite_el,
                "testcase",
                {"classname": suite.name, "name": case.name, "time": f"{case.time_s:.3f}"},
            )
            if case.skipped:
                SubElement(case_el, "skipped")
            elif not case.passed:
                fail_el = SubElement(case_el, "failure", {"message": case.failure_message or "assertion failed"})
                fail_el.text = case.failure_message or ""

    out_path.parent.mkdir(parents=True, exist_ok=True)
    ElementTree(root).write(out_path, encoding="utf-8", xml_declaration=True)

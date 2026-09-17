"""Boot contract engine: the signature BOOTX validation feature.

A boot contract declares, in YAML, what a boot run is *expected* to look
like -- required stages, their order, required events, and a timeout.
The engine checks a captured BootTimeline against that contract and
produces a structured pass/fail verdict with per-clause evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

from bootx.tracing.events import EventType
from bootx.tracing.timeline import BootTimeline


@dataclass(frozen=True)
class BootContract:
    name: str
    required_stages: list[EventType]
    order: list[EventType]
    required_events: list[EventType]
    timeout_ms: float

    @staticmethod
    def from_yaml(path: Path) -> "BootContract":
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        boot = data["boot"]
        return BootContract(
            name=data.get("name", path.stem),
            required_stages=[EventType(s) for s in boot.get("required_stages", [])],
            order=[EventType(s) for s in boot.get("order", [])],
            required_events=[EventType(s) for s in boot.get("required_events", [])],
            timeout_ms=float(boot.get("timeout_ms", 30000)),
        )


@dataclass(frozen=True)
class ClauseResult:
    clause: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ContractResult:
    contract_name: str
    passed: bool
    clauses: list[ClauseResult] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "contract_name": self.contract_name,
            "passed": self.passed,
            "clauses": [{"clause": c.clause, "passed": c.passed, "detail": c.detail} for c in self.clauses],
        }

    def human_report(self) -> str:
        lines = ["BOOT CONTRACT", ""]
        for c in self.clauses:
            tag = "[PASS]" if c.passed else "[FAIL]"
            lines.append(f"{tag} {c.detail}")
        lines.append("")
        lines.append(f"CONTRACT RESULT: {'PASS' if self.passed else 'FAIL'}")
        return "\n".join(lines)


class ContractEngine:
    def evaluate(self, contract: BootContract, timeline: BootTimeline) -> ContractResult:
        clauses: list[ClauseResult] = []

        for stage_event in contract.required_stages:
            present = timeline.has_event(stage_event)
            clauses.append(
                ClauseResult(
                    clause=f"required_stage:{stage_event.value}",
                    passed=present,
                    detail=f"{stage_event.value} {'detected' if present else 'NOT detected'}",
                )
            )

        if contract.order:
            observed_indices = []
            order_ok = True
            missing_for_order = None
            for evt in contract.order:
                e = timeline.first(evt)
                if e is None:
                    order_ok = False
                    missing_for_order = evt
                    break
                observed_indices.append(e.timestamp_ms)
            if order_ok:
                order_ok = observed_indices == sorted(observed_indices)
            detail = (
                f"order {' -> '.join(e.value for e in contract.order)} "
                f"{'holds' if order_ok else 'VIOLATED'}"
            )
            if missing_for_order is not None:
                detail += f" (missing {missing_for_order.value})"
            clauses.append(ClauseResult(clause="order", passed=order_ok, detail=detail))

        for req_event in contract.required_events:
            present = timeline.has_event(req_event)
            clauses.append(
                ClauseResult(
                    clause=f"required_event:{req_event.value}",
                    passed=present,
                    detail=f"{req_event.value} {'detected' if present else 'NOT detected'}",
                )
            )

        last = timeline.events[-1] if timeline.events else None
        timeout_ok = last is None or last.timestamp_ms <= contract.timeout_ms
        clauses.append(
            ClauseResult(
                clause="timeout",
                passed=timeout_ok,
                detail=(
                    f"boot finished within {contract.timeout_ms:.0f}ms budget"
                    if timeout_ok
                    else f"boot exceeded {contract.timeout_ms:.0f}ms budget "
                    f"(last event at {last.timestamp_ms:.1f}ms)"
                ),
            )
        )

        passed = all(c.passed for c in clauses)
        return ContractResult(contract_name=contract.name, passed=passed, clauses=clauses)

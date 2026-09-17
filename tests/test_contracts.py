"""Unit tests for the boot contract engine against synthetic timelines --
no QEMU required. Real end-to-end contract evaluation against a live boot
is covered by test_boot.py."""

from __future__ import annotations

import pytest

from bootx.tracing.events import BootEvent, EventSource, EventType
from bootx.tracing.timeline import BootTimeline
from bootx.validation.boot_contract import BootContract, ContractEngine


def _event(event: EventType, ms: float, stage: str = "X") -> BootEvent:
    return BootEvent(event=event, stage=stage, timestamp_ms=ms, raw_line=f"<synthetic {event.value}>")


HEALTHY_CONTRACT = BootContract(
    name="test_contract",
    required_stages=[EventType.BL31_ENTRY, EventType.BL33_ENTRY, EventType.KERNEL_ENTRY],
    order=[EventType.BL31_ENTRY, EventType.BL33_ENTRY, EventType.KERNEL_ENTRY],
    required_events=[EventType.DTB_LOADED],
    timeout_ms=1000,
)


@pytest.mark.contract
def test_contract_passes_for_healthy_ordered_boot():
    timeline = BootTimeline(
        [
            _event(EventType.BL31_ENTRY, 10),
            _event(EventType.BL33_ENTRY, 20),
            _event(EventType.DTB_LOADED, 25),
            _event(EventType.KERNEL_ENTRY, 30),
        ]
    )
    result = ContractEngine().evaluate(HEALTHY_CONTRACT, timeline)
    assert result.passed
    assert all(c.passed for c in result.clauses)


@pytest.mark.contract
def test_contract_fails_when_required_stage_missing():
    timeline = BootTimeline([_event(EventType.BL31_ENTRY, 10), _event(EventType.DTB_LOADED, 25)])
    result = ContractEngine().evaluate(HEALTHY_CONTRACT, timeline)
    assert not result.passed
    stage_clauses = {c.clause: c.passed for c in result.clauses}
    assert stage_clauses["required_stage:BL33_ENTRY"] is False
    assert stage_clauses["required_stage:KERNEL_ENTRY"] is False


@pytest.mark.contract
def test_contract_fails_when_order_violated():
    timeline = BootTimeline(
        [
            _event(EventType.BL33_ENTRY, 5),   # out of order: before BL31
            _event(EventType.BL31_ENTRY, 10),
            _event(EventType.DTB_LOADED, 25),
            _event(EventType.KERNEL_ENTRY, 30),
        ]
    )
    result = ContractEngine().evaluate(HEALTHY_CONTRACT, timeline)
    assert not result.passed
    order_clause = next(c for c in result.clauses if c.clause == "order")
    assert not order_clause.passed


@pytest.mark.contract
def test_contract_fails_when_timeout_budget_exceeded():
    timeline = BootTimeline(
        [
            _event(EventType.BL31_ENTRY, 10),
            _event(EventType.BL33_ENTRY, 20),
            _event(EventType.DTB_LOADED, 25),
            _event(EventType.KERNEL_ENTRY, 5000),  # exceeds 1000ms budget
        ]
    )
    result = ContractEngine().evaluate(HEALTHY_CONTRACT, timeline)
    assert not result.passed
    timeout_clause = next(c for c in result.clauses if c.clause == "timeout")
    assert not timeout_clause.passed


@pytest.mark.contract
def test_contract_human_report_shows_pass_and_fail_tags():
    timeline = BootTimeline([_event(EventType.BL31_ENTRY, 10)])
    result = ContractEngine().evaluate(HEALTHY_CONTRACT, timeline)
    report = result.human_report()
    assert "CONTRACT RESULT: FAIL" in report
    assert "[FAIL]" in report

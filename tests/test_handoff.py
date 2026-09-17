"""Unit tests for stage handoff validation (bootx/validation/handoff.py)
against synthetic timelines."""

from __future__ import annotations

import pytest

from bootx.tracing.events import BootEvent, EventType
from bootx.tracing.timeline import BootTimeline
from bootx.validation.handoff import Handoff, HandoffValidator


def _event(event: EventType, ms: float) -> BootEvent:
    return BootEvent(event=event, stage="X", timestamp_ms=ms, raw_line=f"<synthetic {event.value}>")


HANDOFF = Handoff("BL31_to_BL33", EventType.BL31_INIT_COMPLETE, EventType.BL33_ENTRY, timeout_ms=100.0)


@pytest.mark.handoff
def test_handoff_passes_within_budget():
    timeline = BootTimeline([_event(EventType.BL31_INIT_COMPLETE, 10), _event(EventType.BL33_ENTRY, 50)])
    result = HandoffValidator().validate(HANDOFF, timeline)
    assert result.passed
    assert result.waited_ms == pytest.approx(40.0)


@pytest.mark.handoff
def test_handoff_fails_when_destination_exceeds_budget():
    timeline = BootTimeline([_event(EventType.BL31_INIT_COMPLETE, 10), _event(EventType.BL33_ENTRY, 500)])
    result = HandoffValidator().validate(HANDOFF, timeline)
    assert not result.passed


@pytest.mark.handoff
@pytest.mark.hang_detection
def test_handoff_timeout_when_destination_never_seen():
    timeline = BootTimeline([_event(EventType.BL31_INIT_COMPLETE, 10)])
    result = HandoffValidator().validate(HANDOFF, timeline)
    assert not result.passed
    assert result.last_successful_event == EventType.BL31_INIT_COMPLETE.value
    assert result.expected_event == EventType.BL33_ENTRY.value
    assert "HANDOFF_TIMEOUT" in result.detail


@pytest.mark.handoff
def test_handoff_source_never_seen_is_not_validatable():
    timeline = BootTimeline([_event(EventType.BL1_ENTRY, 5)])
    result = HandoffValidator().validate(HANDOFF, timeline)
    assert not result.passed
    assert result.last_successful_event is None

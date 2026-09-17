"""Stage handoff validation.

A "handoff" is one firmware stage transferring control to the next
(BL31 -> BL33, BL33/U-Boot -> Linux, ...). BOOTX validates a handoff by
requiring that the destination stage's entry event appears in the
timeline within a bounded time of the source stage's completion event.
If it never appears, that's a HANDOFF_TIMEOUT with full diagnostic
context (last successful stage, what was expected, how long we waited).
"""

from __future__ import annotations

from dataclasses import dataclass

from bootx.tracing.events import EventType
from bootx.tracing.timeline import BootTimeline


@dataclass(frozen=True)
class Handoff:
    name: str
    source_event: EventType
    dest_event: EventType
    timeout_ms: float


@dataclass(frozen=True)
class HandoffResult:
    name: str
    passed: bool
    last_successful_event: str | None
    expected_event: str
    waited_ms: float | None
    detail: str

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "passed": self.passed,
            "last_successful_event": self.last_successful_event,
            "expected_event": self.expected_event,
            "waited_ms": self.waited_ms,
            "detail": self.detail,
        }


DEFAULT_HANDOFFS: list[Handoff] = [
    Handoff("BL31_to_BL33", EventType.BL31_INIT_COMPLETE, EventType.BL33_ENTRY, 5000.0),
    Handoff("BL33_to_KERNEL", EventType.BL33_ENTRY, EventType.KERNEL_ENTRY, 15000.0),
    Handoff("KERNEL_to_USERSPACE", EventType.KERNEL_ENTRY, EventType.USERSPACE_READY, 15000.0),
]


class HandoffValidator:
    def validate(self, handoff: Handoff, timeline: BootTimeline) -> HandoffResult:
        src = timeline.first(handoff.source_event)
        dst = timeline.first(handoff.dest_event)

        if src is None:
            return HandoffResult(
                name=handoff.name,
                passed=False,
                last_successful_event=None,
                expected_event=handoff.dest_event.value,
                waited_ms=None,
                detail=f"source event {handoff.source_event.value} never observed; cannot validate handoff",
            )

        if dst is not None:
            waited = dst.timestamp_ms - src.timestamp_ms
            passed = waited <= handoff.timeout_ms
            return HandoffResult(
                name=handoff.name,
                passed=passed,
                last_successful_event=handoff.source_event.value,
                expected_event=handoff.dest_event.value,
                waited_ms=waited,
                detail=(
                    f"{handoff.dest_event.value} observed {waited:.1f}ms after "
                    f"{handoff.source_event.value} (budget {handoff.timeout_ms:.0f}ms)"
                ),
            )

        # Destination never appeared. Waited time is bounded by the last
        # event actually observed in the whole session (best evidence we have).
        last_overall = timeline.events[-1] if timeline.events else src
        waited = last_overall.timestamp_ms - src.timestamp_ms
        return HandoffResult(
            name=handoff.name,
            passed=False,
            last_successful_event=handoff.source_event.value,
            expected_event=handoff.dest_event.value,
            waited_ms=waited,
            detail=(
                f"HANDOFF_TIMEOUT: {handoff.dest_event.value} not observed within "
                f"{waited:.1f}ms of {handoff.source_event.value} (budget {handoff.timeout_ms:.0f}ms)"
            ),
        )

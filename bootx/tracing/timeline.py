"""Boot timeline: ordered events plus stage-to-stage latency."""

from __future__ import annotations

from dataclasses import dataclass

from bootx.tracing.events import BootEvent, EventType


@dataclass(frozen=True)
class StageLatency:
    from_event: EventType
    to_event: EventType
    latency_ms: float


class BootTimeline:
    def __init__(self, events: list[BootEvent]):
        self.events = sorted(events, key=lambda e: e.timestamp_ms)

    def has_event(self, event: EventType) -> bool:
        return any(e.event == event for e in self.events)

    def first(self, event: EventType) -> BootEvent | None:
        for e in self.events:
            if e.event == event:
                return e
        return None

    def all(self, event: EventType) -> list[BootEvent]:
        return [e for e in self.events if e.event == event]

    def stage_order(self) -> list[EventType]:
        """The order in which distinct stage-marking events were first seen."""
        seen: list[EventType] = []
        for e in self.events:
            if e.event not in seen:
                seen.append(e.event)
        return seen

    def latency_between(self, a: EventType, b: EventType) -> float | None:
        ea, eb = self.first(a), self.first(b)
        if ea is None or eb is None:
            return None
        return eb.timestamp_ms - ea.timestamp_ms

    def stage_latencies(self) -> list[StageLatency]:
        """Latency between each canonical boot milestone, in chain order."""
        chain = [
            EventType.BOOT_START,
            EventType.BL1_ENTRY,
            EventType.BL2_ENTRY,
            EventType.BL31_ENTRY,
            EventType.BL33_ENTRY,
            EventType.KERNEL_ENTRY,
            EventType.USERSPACE_READY,
        ]
        present = [e for e in chain if self.has_event(e)]
        latencies = []
        for a, b in zip(present, present[1:]):
            lat = self.latency_between(a, b)
            if lat is not None:
                latencies.append(StageLatency(a, b, lat))
        return latencies

    def total_boot_ms(self) -> float | None:
        return self.latency_between(EventType.BOOT_START, EventType.USERSPACE_READY)

    def to_dict(self) -> dict:
        return {
            "events": [e.to_dict() for e in self.events],
            "stage_order": [e.value for e in self.stage_order()],
            "stage_latencies": [
                {"from": sl.from_event.value, "to": sl.to_event.value, "latency_ms": round(sl.latency_ms, 3)}
                for sl in self.stage_latencies()
            ],
            "total_boot_ms": self.total_boot_ms(),
        }

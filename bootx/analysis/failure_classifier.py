"""Failure classification engine.

Takes the full evidence available after a boot run -- timeline, contract
result, memory/dtb/image validator results, handoff results, and the raw
QEMU exit info -- and produces one structured diagnosis. Classification
is evidence-driven: every category is backed by a specific observation,
never guessed from the overall pass/fail bit alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from bootx.orchestrator.qemu import QemuResult
from bootx.tracing.events import EventType
from bootx.tracing.timeline import BootTimeline
from bootx.validation.handoff import HandoffResult


class FailureCategory(str, Enum):
    IMAGE_FAILURE = "IMAGE_FAILURE"
    DTB_FAILURE = "DTB_FAILURE"
    MEMORY_FAILURE = "MEMORY_FAILURE"
    HANDOFF_FAILURE = "HANDOFF_FAILURE"
    PSCI_FAILURE = "PSCI_FAILURE"
    TIMEOUT_FAILURE = "TIMEOUT_FAILURE"
    KERNEL_FAILURE = "KERNEL_FAILURE"
    SERIAL_FAILURE = "SERIAL_FAILURE"
    CONTRACT_FAILURE = "CONTRACT_FAILURE"
    CONFIGURATION_FAILURE = "CONFIGURATION_FAILURE"
    NONE = "NONE"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


@dataclass(frozen=True)
class Diagnosis:
    status: str
    stage: str | None
    category: FailureCategory
    last_successful_event: str | None
    expected_event: str | None
    diagnosis: str

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "stage": self.stage,
            "category": self.category.value,
            "last_successful_event": self.last_successful_event,
            "expected_event": self.expected_event,
            "diagnosis": self.diagnosis,
        }


class FailureClassifier:
    _LAUNCH_ERROR_MARKERS = (
        "could not load kernel",
        "could not open disk image",
        "Could not open",
        "No such file or directory",
        "qemu-system-aarch64:",
    )

    def _extract_qemu_launch_error(self, log_text: str) -> str | None:
        for line in log_text.splitlines():
            for marker in self._LAUNCH_ERROR_MARKERS:
                if marker in line:
                    return line.strip()
        return None

    def classify(
        self,
        *,
        qemu_result: QemuResult,
        timeline: BootTimeline,
        image_failed: bool = False,
        dtb_failed: bool = False,
        memory_failed: bool = False,
        handoff_results: list[HandoffResult] | None = None,
        contract_passed: bool | None = None,
    ) -> Diagnosis:
        handoff_results = handoff_results or []
        last_event = timeline.events[-1] if timeline.events else None
        last_event_name = last_event.event.value if last_event else None

        if timeline.has_event(EventType.USERSPACE_READY) and not image_failed and not dtb_failed:
            if contract_passed is False:
                return Diagnosis(
                    status="FAIL",
                    stage="CONTRACT",
                    category=FailureCategory.CONTRACT_FAILURE,
                    last_successful_event=last_event_name,
                    expected_event=None,
                    diagnosis="Boot reached userspace but violated the boot contract (order/required-event clause).",
                )
            return Diagnosis(
                status="PASS",
                stage="USERSPACE",
                category=FailureCategory.NONE,
                last_successful_event=last_event_name,
                expected_event=None,
                diagnosis="Boot completed: USERSPACE_READY observed.",
            )

        if image_failed:
            return Diagnosis(
                status="FAIL",
                stage=last_event.stage if last_event else "UNKNOWN",
                category=FailureCategory.IMAGE_FAILURE,
                last_successful_event=last_event_name,
                expected_event=None,
                diagnosis="Firmware image failed integrity validation (size/hash mismatch or missing artifact).",
            )

        if dtb_failed:
            return Diagnosis(
                status="FAIL",
                stage=last_event.stage if last_event else "UNKNOWN",
                category=FailureCategory.DTB_FAILURE,
                last_successful_event=last_event_name,
                expected_event=None,
                diagnosis="Device tree failed validation (malformed, missing required node/property).",
            )

        if memory_failed:
            return Diagnosis(
                status="FAIL",
                stage=last_event.stage if last_event else "UNKNOWN",
                category=FailureCategory.MEMORY_FAILURE,
                last_successful_event=last_event_name,
                expected_event=None,
                diagnosis="Memory map validation failed (overlap, out-of-range, or misalignment).",
            )

        if timeline.has_event(EventType.KERNEL_PANIC):
            panic_event = timeline.first(EventType.KERNEL_PANIC)
            # Substrings verified against init/main.c and init/do_mounts.c: a
            # panic containing any of these is caused by the bootarg/rootfs
            # configuration the kernel was launched with, not a kernel bug.
            config_panic_markers = ("Unable to mount root", "VFS:", "Requested init", "No working init found")
            config_failure = any(marker in panic_event.raw_line for marker in config_panic_markers)
            return Diagnosis(
                status="FAIL",
                stage="KERNEL",
                category=FailureCategory.CONFIGURATION_FAILURE if config_failure else FailureCategory.KERNEL_FAILURE,
                last_successful_event=last_event_name,
                expected_event=None,
                diagnosis=(
                    f"Kernel panic: {panic_event.raw_line.strip()}"
                    + (" (root filesystem/bootargs misconfiguration)" if config_failure else "")
                ),
            )

        failed_handoffs = [h for h in handoff_results if not h.passed]
        if failed_handoffs:
            h = failed_handoffs[0]
            return Diagnosis(
                status="FAIL",
                stage=h.last_successful_event or "UNKNOWN",
                category=FailureCategory.HANDOFF_FAILURE,
                last_successful_event=h.last_successful_event,
                expected_event=h.expected_event,
                diagnosis=h.detail,
            )

        if qemu_result.timed_out:
            return Diagnosis(
                status="FAIL",
                stage=last_event.stage if last_event else "RESET",
                category=FailureCategory.TIMEOUT_FAILURE,
                last_successful_event=last_event_name,
                expected_event=None,
                diagnosis=f"QEMU boot timed out after {qemu_result.duration_s:.1f}s with no further progress.",
            )

        if last_event is None or last_event.event == EventType.BOOT_START:
            launch_error = self._extract_qemu_launch_error(qemu_result.log_text)
            if launch_error is not None:
                return Diagnosis(
                    status="FAIL",
                    stage="RESET",
                    category=FailureCategory.CONFIGURATION_FAILURE,
                    last_successful_event=last_event_name,
                    expected_event=None,
                    diagnosis=f"QEMU rejected the launch configuration: {launch_error}",
                )
            return Diagnosis(
                status="FAIL",
                stage="RESET",
                category=FailureCategory.SERIAL_FAILURE,
                last_successful_event=last_event_name,
                expected_event=EventType.BL1_ENTRY.value,
                diagnosis="No firmware output observed on the serial console after QEMU launch.",
            )

        return Diagnosis(
            status="FAIL",
            stage=last_event.stage,
            category=FailureCategory.UNKNOWN_FAILURE,
            last_successful_event=last_event_name,
            expected_event=None,
            diagnosis=(
                f"Boot stopped after {last_event.event.value} with no further recognized events "
                "and no matching failure signature."
            ),
        )

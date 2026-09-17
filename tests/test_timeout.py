"""Timeout / hang detection.

test_timeout_fault_triggers_and_is_classified is the real end-to-end
case: U-Boot's autoboot is disabled (bootdelay=-1 via -append env
override is not applicable to U-Boot directly, so this fault instead
gives QEMU no -kernel/-initrd at all, which lands U-Boot at its
interactive prompt with nothing to autoboot into) so BOOTX's own
wall-clock timeout in QemuRunner must fire, and the classifier must
correctly call it TIMEOUT_FAILURE, not something else.
"""

from __future__ import annotations

import pytest

from bootx.analysis.failure_classifier import FailureCategory, FailureClassifier
from bootx.orchestrator.config import BootConfig, FirmwareImages
from bootx.orchestrator.runner import BootRunner


@pytest.mark.hang_detection
@pytest.mark.fault
@pytest.mark.regression
def test_timeout_fault_triggers_and_is_classified(require_firmware, images_dir):
    config = BootConfig(
        firmware=FirmwareImages(bios=images_dir / "flash.bin"),  # no kernel/initrd -> nothing to autoboot
        cpus=1,
        ram_mb=512,
        timeout_s=8.0,
        run_label="fault-timeout",
    )
    run = BootRunner().run(config)

    assert run.qemu_result.timed_out, "expected BOOTX's own timeout handler to fire"

    diagnosis = FailureClassifier().classify(qemu_result=run.qemu_result, timeline=run.timeline)
    assert diagnosis.category == FailureCategory.TIMEOUT_FAILURE
    assert diagnosis.status == "FAIL"


@pytest.mark.hang_detection
@pytest.mark.regression
def test_qemu_process_is_not_orphaned_after_timeout(require_firmware, images_dir):
    """No orphan QEMU process should survive a timeout (section 44: test execution safety)."""
    import os

    config = BootConfig(
        firmware=FirmwareImages(bios=images_dir / "flash.bin"),
        cpus=1,
        ram_mb=512,
        timeout_s=5.0,
        run_label="fault-timeout-orphan-check",
    )
    run = BootRunner().run(config)
    assert run.qemu_result.timed_out

    with pytest.raises(ProcessLookupError):
        os.kill(run.qemu_result.pid, 0)

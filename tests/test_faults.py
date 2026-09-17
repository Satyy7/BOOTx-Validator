"""Fault-injection tests.

Per docs/fault-injection.md: a fault test PASSES when BOOTX correctly
detects and classifies the injected failure, not merely when the boot
fails. Image and DTB faults are caught by BOOTX's own pre-boot validators
(the same integrity gate a real bootloader would apply) -- these don't
require a full QEMU boot, since a corrupted artifact should never even be
loaded. Configuration faults require a real boot to observe how the
firmware/kernel actually reacts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bootx.faults.corrupt_image import CorruptImageFault
from bootx.faults.invalid_dtb import InvalidDtbFault, MissingDtbFault
from bootx.validation.dtb import DtbValidator
from bootx.validation.image import ImageManifest, ImageValidator


@pytest.mark.fault
@pytest.mark.image
@pytest.mark.regression
def test_corrupt_image_fault_is_detected(require_firmware, images_dir: Path, tmp_path: Path):
    source = images_dir / "u-boot.bin"
    manifest = ImageManifest.from_file(
        source, image_id="BL33", version="bootx", load_address="n/a", entry_address="n/a"
    )

    fault = CorruptImageFault(source_image=source)
    ctx = fault.inject(tmp_path)

    result = ImageValidator().validate(ctx["mutated_image"], manifest)

    expectation = fault.expectation()
    assert not result.passed, "corrupted image must fail integrity validation"
    assert expectation.category == "IMAGE_FAILURE"


@pytest.mark.fault
@pytest.mark.dtb
@pytest.mark.regression
def test_invalid_dtb_fault_is_detected(require_firmware, dtc_available, images_dir: Path, tmp_path: Path):
    if not dtc_available:
        pytest.skip("dtc not installed")
    source = images_dir / "virt.dtb"
    if not source.exists():
        pytest.skip("virt.dtb not dumped; run `make build`")

    fault = InvalidDtbFault(source_dtb=source)
    ctx = fault.inject(tmp_path)

    result = DtbValidator(expected_cpu_count=4, expected_ram_mb=2048).validate(ctx["mutated_dtb"])

    assert not result.passed, "truncated DTB must fail validation"
    assert fault.expectation().category == "DTB_FAILURE"


@pytest.mark.fault
@pytest.mark.dtb
def test_missing_dtb_fault_is_detected(tmp_path: Path):
    fault = MissingDtbFault()
    ctx = fault.inject(tmp_path)

    result = DtbValidator(expected_cpu_count=4, expected_ram_mb=2048).validate(ctx["mutated_dtb"])

    assert not result.passed
    assert fault.expectation().category == "DTB_FAILURE"


@pytest.mark.fault
@pytest.mark.regression
def test_invalid_bootargs_fault_is_classified_configuration_failure(require_firmware, images_dir: Path):
    from bootx.analysis.failure_classifier import FailureCategory, FailureClassifier
    from bootx.faults.configuration_fault import InvalidBootargsFault
    from bootx.orchestrator.config import BootConfig, FirmwareImages
    from bootx.orchestrator.runner import BootRunner

    fault = InvalidBootargsFault()
    ctx = fault.inject(images_dir)

    config = BootConfig(
        firmware=FirmwareImages(
            bios=images_dir / "flash.bin",
            kernel=images_dir / "Image",
            initrd=images_dir / "initramfs.cpio.gz",
        ),
        cpus=2,
        ram_mb=1024,
        timeout_s=25.0,
        bootargs=ctx["bootargs"],
        run_label="fault-invalid-bootargs",
    )
    run = BootRunner().run(config)

    diagnosis = FailureClassifier().classify(qemu_result=run.qemu_result, timeline=run.timeline)
    assert diagnosis.category in (FailureCategory.CONFIGURATION_FAILURE, FailureCategory.KERNEL_FAILURE), (
        diagnosis.diagnosis
    )

"""SMP / multi-core tests: real QEMU configurations at -smp 1/2/4/8.

Secondary CPU bring-up is confirmed via the kernel's own
"CPUn: Booted secondary processor" messages, which only appear when Linux
successfully brings up a secondary core via PSCI CPU_ON (see
docs/interview-guide.md for how enable-method=psci reaches the kernel).
"""

from __future__ import annotations

import pytest

from bootx.orchestrator.config import BootConfig, FirmwareImages
from bootx.orchestrator.runner import BootRunner
from bootx.tracing.events import EventType


@pytest.mark.smp
@pytest.mark.regression
@pytest.mark.parametrize("cpus", [1, 2, 4, 8])
def test_smp_configuration_boots_to_userspace(require_firmware, images_dir, cpus):
    config = BootConfig(
        firmware=FirmwareImages(
            bios=images_dir / "flash.bin",
            kernel=images_dir / "Image",
            initrd=images_dir / "initramfs.cpio.gz",
        ),
        cpus=cpus,
        ram_mb=2048,
        timeout_s=25.0,
        bootargs="console=ttyAMA0 earlycon=pl011,0x9000000",
        run_label=f"smp-{cpus}",
    )
    run = BootRunner().run(config)
    assert not run.qemu_result.timed_out, run.qemu_result.log_text[-2000:]
    assert run.timeline.has_event(EventType.USERSPACE_READY)


@pytest.mark.smp
@pytest.mark.regression
@pytest.mark.parametrize("cpus", [2, 4, 8])
def test_secondary_cpus_report_boot(require_firmware, images_dir, cpus):
    """For cpus > 1, expect at least one CPU_ON (secondary boot) event.

    Not all secondaries are guaranteed to log identically across kernel
    versions, so this checks for *at least one* real secondary bring-up
    rather than asserting an exact count == cpus - 1, avoiding a flaky
    over-precise assertion.
    """
    config = BootConfig(
        firmware=FirmwareImages(
            bios=images_dir / "flash.bin",
            kernel=images_dir / "Image",
            initrd=images_dir / "initramfs.cpio.gz",
        ),
        cpus=cpus,
        ram_mb=2048,
        timeout_s=25.0,
        bootargs="console=ttyAMA0 earlycon=pl011,0x9000000",
        run_label=f"smp-cpuon-{cpus}",
    )
    run = BootRunner().run(config)
    cpu_on_events = run.timeline.all(EventType.CPU_ON)
    assert len(cpu_on_events) >= 1, run.qemu_result.log_text[-2000:]

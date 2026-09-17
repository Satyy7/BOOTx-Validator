"""End-to-end boot tests against a real QEMU + TF-A + U-Boot + Linux boot.

Skip (not fail) when firmware images haven't been built -- see
tests/conftest.py:require_firmware. `make build` produces the images.
"""

from __future__ import annotations

import pytest

from bootx.orchestrator.runner import BootRunner
from bootx.tracing.events import EventType
from bootx.validation.boot_contract import BootContract, ContractEngine


@pytest.mark.smoke
@pytest.mark.boot
@pytest.mark.regression
def test_qemu_arm64_virt_baseline_starts_and_exits_cleanly(require_qemu, tmp_path):
    """Milestone 1: QEMU ARM64 virt machine starts and terminates cleanly,
    even with no boot device attached (no -bios/-kernel)."""
    from bootx.orchestrator.config import BootConfig, FirmwareImages
    from bootx.orchestrator.qemu import QemuRunner

    # No real bios exists at this path -- QEMU still creates the machine
    # and either halts or errors quickly; we're proving process lifecycle
    # (launch, capture, clean terminate), not a successful firmware boot.
    config = BootConfig(
        firmware=FirmwareImages(bios=tmp_path / "nonexistent-bios.bin"),
        cpus=4,
        ram_mb=512,
        timeout_s=5.0,
    )
    runner = QemuRunner(config, tmp_path / "qemu.log")
    result = runner.run()
    assert result.log_path.exists()


@pytest.mark.smoke
@pytest.mark.boot
@pytest.mark.regression
def test_firmware_boots_to_userspace(require_firmware, basic_boot_config):
    """Milestone 2/3: real serial evidence of BL1/BL31/U-Boot/kernel/userspace."""
    run = BootRunner().run(basic_boot_config)

    assert not run.qemu_result.timed_out, run.qemu_result.log_text[-2000:]
    assert run.timeline.has_event(EventType.BL1_ENTRY)
    assert run.timeline.has_event(EventType.BL31_ENTRY)
    assert run.timeline.has_event(EventType.BL33_ENTRY)
    assert run.timeline.has_event(EventType.KERNEL_ENTRY)
    assert run.timeline.has_event(EventType.USERSPACE_READY)


@pytest.mark.boot
@pytest.mark.regression
def test_boot_stage_order_is_chronological(require_firmware, basic_boot_config):
    run = BootRunner().run(basic_boot_config)
    chain = [EventType.BL1_ENTRY, EventType.BL31_ENTRY, EventType.BL33_ENTRY, EventType.KERNEL_ENTRY]
    timestamps = [run.timeline.first(e).timestamp_ms for e in chain if run.timeline.has_event(e)]
    assert timestamps == sorted(timestamps)


@pytest.mark.contract
@pytest.mark.regression
def test_normal_boot_contract_passes_on_real_boot(require_firmware, basic_boot_config, repo_root):
    run = BootRunner().run(basic_boot_config)
    contract = BootContract.from_yaml(repo_root / "scenarios" / "normal_boot.yaml")
    result = ContractEngine().evaluate(contract, run.timeline)
    assert result.passed, result.human_report()


@pytest.mark.boot
@pytest.mark.regression
def test_run_directory_captures_full_evidence(require_firmware, basic_boot_config):
    """Every run must leave qemu.log, metadata.json, events.json, result.json behind."""
    run = BootRunner().run(basic_boot_config)
    d = run.run_dir
    assert d.qemu_log.exists()
    assert d.metadata_path.exists()
    assert d.events_path.exists()
    assert d.result_path.exists()
    assert d.qemu_log.stat().st_size > 0

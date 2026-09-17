"""PSCI-related validation.

- SYSTEM_OFF: BOOTX's minimal userspace (firmware/linux/initramfs/init.c)
  calls reboot(RB_POWER_OFF) after printing its marker, which the kernel
  turns into a real PSCI SYSTEM_OFF SMC to TF-A/EL3. On QEMU virt this
  actually terminates the QEMU process, so we confirm the process exits
  on its own rather than being force-killed by our timeout.
- EL3 exit SPSR: TF-A's own BL31 exit-path log (see
  bootx/validation/exception_level.py) is parsed to confirm the exception
  level BL33 is entered at.

CPU_ON is covered in test_smp.py (it's most naturally exercised per-CPU-count).
Deeper PSCI states (CPU_OFF, SYSTEM_RESET) are not exercised here: BOOTX's
minimal init never requests them, and Linux's own use of them mid-boot
isn't reliably observable from the console alone -- see docs/limitations.md.
"""

from __future__ import annotations

import pytest

from bootx.orchestrator.runner import BootRunner
from bootx.tracing.events import EventType
from bootx.validation.exception_level import observe_bl31_exit


@pytest.mark.psci
@pytest.mark.regression
def test_system_off_terminates_qemu_without_forced_timeout(require_firmware, basic_boot_config):
    run = BootRunner().run(basic_boot_config)
    assert run.timeline.has_event(EventType.USERSPACE_READY)
    assert not run.qemu_result.timed_out, "PSCI SYSTEM_OFF should end the session before the timeout fires"
    assert run.qemu_result.returncode is not None


@pytest.mark.psci
@pytest.mark.regression
def test_el3_exit_spsr_is_observed(require_firmware, basic_boot_config):
    run = BootRunner().run(basic_boot_config)
    observation = observe_bl31_exit(run.qemu_result.log_text)
    assert observation is not None, "expected TF-A's 'Preparing for EL3 exit' + SPSR trace in the log"
    assert observation.security_state == "normal"
    assert observation.target_el in ("EL2h", "EL2t", "EL1h", "EL1t")

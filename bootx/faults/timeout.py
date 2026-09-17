"""Fault: force a boot hang by giving U-Boot bootargs/behavior that never
reaches the kernel (e.g. drop into the U-Boot prompt instead of
autobooting), so the run is expected to hit BOOTX's own timeout handler.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bootx.faults.base import Fault, FaultExpectation


class BootTimeoutFault(Fault):
    name = "boot_timeout"
    description = "Disable U-Boot autoboot so the boot deliberately never reaches the kernel."

    def expectation(self) -> FaultExpectation:
        return FaultExpectation(
            category="TIMEOUT_FAILURE",
            description="Boot should hang at the U-Boot prompt and be caught by the timeout/hang detector.",
        )

    def inject(self, workdir: Path) -> dict[str, Any]:
        # Signals to the orchestrator to pass bootdelay=-1 / no bootcmd via
        # QEMU's -append is not applicable to U-Boot itself; instead this is
        # applied by the caller setting BootConfig.extra_qemu_args to feed
        # an environment that disables autoboot (see tests/test_timeout.py).
        return {"disable_autoboot": True}

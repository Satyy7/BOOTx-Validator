"""Fault: pass an invalid kernel command line / boot configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from bootx.faults.base import Fault, FaultExpectation


class InvalidBootargsFault(Fault):
    name = "invalid_bootargs"
    description = "Set a kernel bootargs string pointing rdinit= at a nonexistent executable."

    def expectation(self) -> FaultExpectation:
        return FaultExpectation(
            category="CONFIGURATION_FAILURE",
            description=(
                "Kernel should fail its init_eaccess() check on rdinit, fall back to "
                "prepare_namespace(), and panic with 'VFS: Unable to mount root fs' "
                "(init/main.c) since no root= device is configured either -- a real, "
                "observable consequence of a bad bootarg."
            ),
        )

    def inject(self, workdir: Path) -> dict[str, Any]:
        # BOOTX boots from an initramfs directly (see
        # firmware/linux/initramfs/init.c). Two bootargs were tried and
        # rejected empirically before this one:
        #   - root=<bogus device>: silently ignored. The kernel only consults
        #     root= via prepare_namespace(), which never runs because our
        #     initramfs's own /init is found and takes priority.
        #   - init=<bogus path>: also silently ignored. The kernel checks
        #     ramdisk_execute_command (default "/init", which exists in our
        #     initramfs) BEFORE it ever looks at init='s execute_command.
        # rdinit= is the one bootarg that actually overrides
        # ramdisk_execute_command itself, so pointing it at a path that
        # doesn't exist forces init_eaccess() to fail, which routes the
        # kernel into prepare_namespace() -- and since no root= is set
        # either, that reliably panics.
        return {"bootargs": "console=ttyAMA0 earlycon=pl011,0x9000000 rdinit=/nonexistent-init"}


class MissingKernelFault(Fault):
    name = "missing_kernel"
    description = "Point the boot configuration at a kernel Image path that does not exist."

    def expectation(self) -> FaultExpectation:
        return FaultExpectation(
            category="CONFIGURATION_FAILURE",
            description="U-Boot should fail to load the kernel image and report a load error.",
        )

    def inject(self, workdir: Path) -> dict[str, Any]:
        return {"kernel_path": workdir / "does-not-exist-Image"}

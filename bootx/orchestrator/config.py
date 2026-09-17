"""Boot configuration model for a BOOTX QEMU ARM64 run."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class FirmwareImages:
    """Paths to the firmware images that make up one boot.

    ``bios`` is what QEMU loads via ``-bios`` (TF-A's BL1, acting as the
    BootROM stage on the QEMU virt platform). BL2/BL31/BL33 are built into
    the same flash image by the TF-A build system when
    ``ARM_LINUX_KERNEL_AS_BL33`` / U-Boot-as-BL33 is configured, so there is
    normally a single ``bios`` artifact rather than separate ``-kernel``
    load for each stage. ``kernel``/``initrd``/``dtb`` are populated when
    U-Boot (BL33) hands off to Linux rather than QEMU injecting them itself.
    """

    bios: Path
    kernel: Path | None = None
    initrd: Path | None = None
    dtb: Path | None = None


@dataclass(frozen=True)
class BootConfig:
    """Everything needed to launch one QEMU ARM64 boot."""

    firmware: FirmwareImages
    cpus: int = 4
    ram_mb: int = 2048
    machine: str = "virt,secure=on,gic-version=2"
    """gic-version=2 matches TF-A's default GIC driver for PLAT=qemu
    (plat/qemu/qemu/platform.mk: QEMU_USE_GIC_DRIVER := QEMU_GICV2).
    QEMU's own default for -machine virt is GICv3; leaving this
    unspecified would give TF-A's GICv2 driver a GICv3 distributor to
    talk to, corrupting interrupt delivery (SMP wake, timers) in ways
    that only show up once secondary CPUs or interrupts are exercised."""
    cpu_model: str = "cortex-a72"
    timeout_s: float = 30.0
    extra_qemu_args: tuple[str, ...] = field(default_factory=tuple)
    bootargs: str | None = None
    run_label: str = "boot"

    def qemu_args(self) -> list[str]:
        args = [
            "-machine", self.machine,
            "-cpu", self.cpu_model,
            "-smp", str(self.cpus),
            "-m", f"{self.ram_mb}",
            "-nographic",
            "-bios", str(self.firmware.bios),
        ]
        if self.firmware.kernel is not None:
            args += ["-kernel", str(self.firmware.kernel)]
        if self.firmware.initrd is not None:
            args += ["-initrd", str(self.firmware.initrd)]
        if self.firmware.dtb is not None:
            args += ["-dtb", str(self.firmware.dtb)]
        if self.bootargs:
            args += ["-append", self.bootargs]
        args += list(self.extra_qemu_args)
        return args

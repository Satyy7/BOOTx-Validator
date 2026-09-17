"""Shared pytest fixtures for the BOOTX test suite.

Tests that need a real QEMU boot skip cleanly (not fail) when the
firmware images haven't been built yet, so `pytest` remains runnable on a
machine that only has the Python framework installed. `bootx doctor` /
`make build` explain how to produce the missing artifacts.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
IMAGES_DIR = REPO_ROOT / "qemu" / "images"


@pytest.fixture(scope="session")
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture(scope="session")
def images_dir() -> Path:
    return IMAGES_DIR


@pytest.fixture(scope="session")
def qemu_available() -> bool:
    return shutil.which("qemu-system-aarch64") is not None


@pytest.fixture(scope="session")
def dtc_available() -> bool:
    return shutil.which("dtc") is not None


@pytest.fixture(scope="session")
def firmware_built(images_dir: Path) -> bool:
    return (images_dir / "flash.bin").exists()


@pytest.fixture()
def require_qemu(qemu_available: bool) -> None:
    if not qemu_available:
        pytest.skip("qemu-system-aarch64 not installed; run `bootx doctor`")


@pytest.fixture()
def require_firmware(firmware_built: bool, require_qemu: None) -> None:
    if not firmware_built:
        pytest.skip("firmware images not built; run `make build`")


@pytest.fixture()
def basic_boot_config(images_dir: Path):
    from bootx.orchestrator.config import BootConfig, FirmwareImages

    return BootConfig(
        firmware=FirmwareImages(
            bios=images_dir / "flash.bin",
            kernel=images_dir / "Image",
            initrd=images_dir / "initramfs.cpio.gz",
        ),
        cpus=4,
        ram_mb=2048,
        timeout_s=25.0,
        bootargs="console=ttyAMA0 earlycon=pl011,0x9000000",
        run_label="pytest",
    )

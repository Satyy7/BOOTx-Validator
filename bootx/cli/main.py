"""BOOTX command-line interface.

    bootx doctor              check host tooling (qemu, cross-gcc, dtc, ...)
    bootx build                build TF-A + U-Boot + Linux + initramfs
    bootx boot                 run a single boot and print its trace
    bootx test [-m MARKER]     run the pytest suite
    bootx report                render the latest JUnit result as text/JSON
    bootx clean                remove build outputs and run artifacts
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import click

REPO_ROOT = Path(__file__).resolve().parents[2]


@click.group()
def cli() -> None:
    """BOOTX -- ARM64 SoC boot firmware validation and fault-injection lab."""


@cli.command()
def doctor() -> None:
    """Check that required host tooling is present."""
    checks = [
        ("qemu-system-aarch64", "QEMU ARM64 system emulator"),
        ("aarch64-linux-gnu-gcc", "AArch64 cross-compiler"),
        ("dtc", "device-tree-compiler"),
        ("git", "git"),
        ("make", "make"),
    ]
    ok = True
    for binary, description in checks:
        path = shutil.which(binary)
        status = f"OK  ({path})" if path else "MISSING"
        if not path:
            ok = False
        click.echo(f"[{'PASS' if path else 'FAIL'}] {binary:<24} {description:<30} {status}")

    for label, rel in [
        ("TF-A source", "firmware/tf-a/src"),
        ("U-Boot source", "firmware/u-boot/src"),
        ("Linux source", "firmware/linux/src"),
    ]:
        exists = (REPO_ROOT / rel).exists()
        click.echo(f"[{'PASS' if exists else 'FAIL'}] {label:<24} {'present' if exists else 'missing (run `make setup`)'}")
        ok = ok and exists

    for label, rel in [
        ("BL1 (bl1.bin)", "qemu/images/bl1.bin"),
        ("Combined bios (flash.bin)", "qemu/images/flash.bin"),
        ("U-Boot (u-boot.bin)", "qemu/images/u-boot.bin"),
        ("Kernel Image", "qemu/images/Image"),
        ("DTB", "qemu/images/virt.dtb"),
        ("Initramfs", "qemu/images/initramfs.cpio.gz"),
    ]:
        exists = (REPO_ROOT / rel).exists()
        tag = "PASS" if exists else "SKIP"
        click.echo(f"[{tag}] {label:<24} {'present' if exists else 'not built yet'}")

    sys.exit(0 if ok else 1)


@cli.command()
@click.option("--target", type=click.Choice(["all", "tf-a", "u-boot", "linux", "initramfs"]), default="all")
def build(target: str) -> None:
    """Build the firmware stack via the Makefile."""
    rc = subprocess.run(["make", f"build-{target}" if target != "all" else "build"], cwd=REPO_ROOT).returncode
    sys.exit(rc)


@cli.command()
@click.option("--cpus", default=4, show_default=True)
@click.option("--ram", "ram_mb", default=2048, show_default=True)
@click.option("--timeout", "timeout_s", default=30.0, show_default=True)
def boot(cpus: int, ram_mb: int, timeout_s: float) -> None:
    """Run a single boot with the current qemu/images/ artifacts and print the trace."""
    from bootx.orchestrator.config import BootConfig, FirmwareImages
    from bootx.orchestrator.runner import BootRunner

    images = REPO_ROOT / "qemu" / "images"
    bios = images / "flash.bin"
    if not bios.exists():
        click.echo(f"FAIL: {bios} not found. Run `bootx build` first.", err=True)
        sys.exit(1)

    config = BootConfig(
        firmware=FirmwareImages(bios=bios, kernel=images / "Image", initrd=images / "initramfs.cpio.gz"),
        cpus=cpus,
        ram_mb=ram_mb,
        timeout_s=timeout_s,
        bootargs="console=ttyAMA0 earlycon=pl011,0x9000000",
        run_label="cli-boot",
    )
    result = BootRunner().run(config)

    click.echo(f"Run directory: {result.run_dir.path}")
    click.echo(f"QEMU exit: returncode={result.qemu_result.returncode} timed_out={result.qemu_result.timed_out}")
    click.echo("")
    click.echo("BOOT TRACE:")
    for e in result.timeline.events:
        click.echo(f"  [{e.timestamp_ms:9.2f}ms] {e.event.value:<20} ({e.stage}) {e.raw_line}")


@cli.command()
@click.option("-m", "--marker", default=None, help="pytest -m marker expression, e.g. smoke")
@click.option("--junit", "junit_path", default="reports/junit.xml", show_default=True)
def test(marker: str | None, junit_path: str) -> None:
    """Run the pytest suite."""
    cmd = [sys.executable, "-m", "pytest", f"--junitxml={junit_path}"]
    if marker:
        cmd += ["-m", marker]
    rc = subprocess.run(cmd, cwd=REPO_ROOT).returncode
    sys.exit(rc)


@cli.command()
@click.option("--junit", "junit_path", default="reports/junit.xml", show_default=True)
def report(junit_path: str) -> None:
    """Render the latest JUnit result as a human-readable summary."""
    from bootx.reporting.report import human_report, summarize_junit

    path = REPO_ROOT / junit_path
    if not path.exists():
        click.echo(f"FAIL: {path} not found. Run `bootx test` first.", err=True)
        sys.exit(1)
    summary = summarize_junit(path)
    click.echo(human_report(summary, target="QEMU ARM64 virt", cpus=4, ram_mb=2048))
    sys.exit(0 if summary.failed == 0 else 1)


@cli.command()
def clean() -> None:
    """Remove build outputs and run artifacts (keeps firmware source checkouts)."""
    for rel in ["qemu/images", "reports/runs", "reports/junit.xml", "artifacts"]:
        p = REPO_ROOT / rel
        if p.is_dir():
            shutil.rmtree(p, ignore_errors=True)
            p.mkdir(parents=True, exist_ok=True)
        elif p.exists():
            p.unlink()
    click.echo("Cleaned build outputs and run artifacts.")


if __name__ == "__main__":
    cli()

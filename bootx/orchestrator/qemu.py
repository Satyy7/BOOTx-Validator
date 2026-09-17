"""QEMU ARM64 process manager.

Launches ``qemu-system-aarch64`` as a subprocess, captures its serial
console (stdout, since we run with ``-nographic``/``-serial stdio``-style
PL011 output on stdout) to a log file, enforces a wall-clock timeout, and
guarantees the process is terminated -- no orphan QEMU processes are left
behind even when a test fails or times out.
"""

from __future__ import annotations

import os
import selectors
import shutil
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from bootx.orchestrator.config import BootConfig

QEMU_BINARY = "qemu-system-aarch64"


class QemuNotFoundError(RuntimeError):
    pass


@dataclass
class QemuResult:
    command: list[str]
    returncode: int | None
    timed_out: bool
    duration_s: float
    log_path: Path
    log_text: str
    pid: int
    timestamped_lines: list[tuple[float, str]]
    """(elapsed_ms_since_launch, raw_line) for every line of serial output,
    as observed by the host. This is BOOTX/host wall-clock time, not guest
    virtual time -- see docs/limitations.md."""


def find_qemu() -> str:
    path = shutil.which(QEMU_BINARY)
    if path is None:
        raise QemuNotFoundError(
            f"{QEMU_BINARY} not found on PATH. Install qemu-system-arm "
            "(apt-get install qemu-system-arm) to run BOOTX boot tests."
        )
    return path


def qemu_version() -> str:
    binary = find_qemu()
    out = subprocess.run([binary, "--version"], capture_output=True, text=True, check=True)
    return out.stdout.strip().splitlines()[0]


class QemuRunner:
    """Runs a single QEMU boot to completion or timeout, capturing serial output."""

    def __init__(self, config: BootConfig, log_path: Path):
        self.config = config
        self.log_path = log_path
        self._proc: subprocess.Popen | None = None

    def command(self) -> list[str]:
        binary = find_qemu()
        return [binary, *self.config.qemu_args()]

    def run(self) -> QemuResult:
        binary = find_qemu()
        cmd = [binary, *self.config.qemu_args()]

        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        start = time.monotonic()
        timed_out = False
        timestamped_lines: list[tuple[float, str]] = []
        buffer = ""

        with open(self.log_path, "w", encoding="utf-8", errors="replace") as logf:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                bufsize=0,
                start_new_session=True,
            )
            assert self._proc.stdout is not None
            stdout_fd = self._proc.stdout.fileno()
            os.set_blocking(stdout_fd, False)

            sel = selectors.DefaultSelector()
            sel.register(stdout_fd, selectors.EVENT_READ)

            def _emit(line: str) -> None:
                elapsed_ms = (time.monotonic() - start) * 1000.0
                timestamped_lines.append((elapsed_ms, line))
                logf.write(line + "\n")
                logf.flush()

            try:
                deadline = start + self.config.timeout_s
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        timed_out = True
                        break
                    # A blocking readline() would ignore the deadline entirely
                    # once QEMU stops producing output (e.g. sitting idle at a
                    # bootloader prompt) but hasn't exited -- select() with a
                    # bounded wait is what actually makes the timeout real.
                    ready = sel.select(timeout=min(remaining, 0.5))
                    if not ready:
                        if self._proc.poll() is not None:
                            break
                        continue
                    chunk = os.read(stdout_fd, 65536)
                    if chunk == b"":
                        break  # EOF: process closed stdout
                    buffer += chunk.decode("utf-8", errors="replace")
                    while "\n" in buffer:
                        line, buffer = buffer.split("\n", 1)
                        _emit(line)
                if buffer:
                    _emit(buffer)
                    buffer = ""
            finally:
                sel.close()
                if timed_out or self._proc.poll() is None:
                    self._terminate()
                self._proc.wait(timeout=5)

        duration = time.monotonic() - start
        log_text = self.log_path.read_text(encoding="utf-8", errors="replace")
        return QemuResult(
            command=cmd,
            returncode=None if timed_out else self._proc.returncode,
            timed_out=timed_out,
            duration_s=duration,
            log_path=self.log_path,
            log_text=log_text,
            pid=self._proc.pid,
            timestamped_lines=timestamped_lines,
        )

    def _terminate(self) -> None:
        """Kill the QEMU process group so no orphan process survives."""
        if self._proc is None or self._proc.poll() is not None:
            return
        try:
            import os

            pgid = os.getpgid(self._proc.pid)
            os.killpg(pgid, signal.SIGTERM)
            try:
                self._proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                os.killpg(pgid, signal.SIGKILL)
                self._proc.wait(timeout=3)
        except ProcessLookupError:
            pass

"""Run-directory lifecycle: every boot gets a unique, fully observable directory.

reports/runs/<timestamp>_<label>/
    qemu.log        raw serial console output (never discarded)
    metadata.json   command line, config, firmware versions
    events.json     parsed boot events (written by the tracing layer)
    result.json     final BootResult (written by the runner)
"""

from __future__ import annotations

import json
import os
import platform
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPORTS_ROOT = Path("reports/runs")


def _json_default(obj: Any) -> Any:
    if is_dataclass(obj) and not isinstance(obj, type):
        return asdict(obj)
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class RunDirectory:
    """A single boot run's on-disk artifact directory."""

    def __init__(self, root: Path, label: str = "boot"):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        self.path = root / f"{timestamp}_{label}"
        self.path.mkdir(parents=True, exist_ok=True)

    @property
    def qemu_log(self) -> Path:
        return self.path / "qemu.log"

    @property
    def metadata_path(self) -> Path:
        return self.path / "metadata.json"

    @property
    def events_path(self) -> Path:
        return self.path / "events.json"

    @property
    def result_path(self) -> Path:
        return self.path / "result.json"

    def write_metadata(self, *, command: list[str], config: Any, firmware_versions: dict[str, str]) -> None:
        metadata = {
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "host": {
                "platform": platform.platform(),
                "python": platform.python_version(),
                "pid": os.getpid(),
            },
            "command": command,
            "config": config,
            "firmware_versions": firmware_versions,
        }
        self.metadata_path.write_text(
            json.dumps(metadata, indent=2, default=_json_default), encoding="utf-8"
        )

    def write_events(self, events: list[Any]) -> None:
        self.events_path.write_text(
            json.dumps([_json_default(e) for e in events], indent=2, default=_json_default),
            encoding="utf-8",
        )

    def write_result(self, result: Any) -> None:
        self.result_path.write_text(
            json.dumps(result, indent=2, default=_json_default), encoding="utf-8"
        )

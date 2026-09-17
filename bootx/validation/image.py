"""Firmware/test image integrity validation.

Real firmware image formats (TF-A raw BL2/BL31/BL33 binaries, the FIP
container, U-Boot's own image) do not uniformly expose fields like
"image_id" or "version" outside of TF-A's FIP metadata. To make integrity
checking testable end-to-end, BOOTX wraps each artifact this project
tracks in a documented **BOOTX validation manifest** (JSON, generated at
build time) recording the fields we can actually and honestly compute:
size, SHA-256, and the load/entry addresses BOOTX configured QEMU/TF-A
with. This is explicitly a BOOTX-authored integrity layer around the
artifacts, not a claim that the upstream image format carries this
metadata natively.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ImageManifest:
    image_id: str
    version: str
    load_address: str
    entry_address: str
    size: int
    sha256: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_file(
        path: Path, *, image_id: str, version: str, load_address: str, entry_address: str
    ) -> "ImageManifest":
        data = path.read_bytes()
        return ImageManifest(
            image_id=image_id,
            version=version,
            load_address=load_address,
            entry_address=entry_address,
            size=len(data),
            sha256=hashlib.sha256(data).hexdigest(),
        )

    @staticmethod
    def load(path: Path) -> "ImageManifest":
        data = json.loads(path.read_text(encoding="utf-8"))
        return ImageManifest(**data)

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")


class ImageIntegrityError(str):
    MISSING = "IMAGE_MISSING"
    SIZE_MISMATCH = "IMAGE_SIZE_MISMATCH"
    HASH_MISMATCH = "IMAGE_HASH_MISMATCH"
    ADDRESS_MISMATCH = "IMAGE_ADDRESS_MISMATCH"


@dataclass(frozen=True)
class ImageValidationResult:
    passed: bool
    image_id: str
    errors: list[str]

    def to_dict(self) -> dict:
        return {"passed": self.passed, "image_id": self.image_id, "errors": self.errors}


class ImageValidator:
    def validate(self, image_path: Path, manifest: ImageManifest) -> ImageValidationResult:
        errors: list[str] = []

        if not image_path.exists():
            return ImageValidationResult(
                passed=False, image_id=manifest.image_id, errors=[ImageIntegrityError.MISSING]
            )

        data = image_path.read_bytes()

        if len(data) != manifest.size:
            errors.append(
                f"{ImageIntegrityError.SIZE_MISMATCH}: expected {manifest.size} bytes, got {len(data)}"
            )

        actual_hash = hashlib.sha256(data).hexdigest()
        if actual_hash != manifest.sha256:
            errors.append(
                f"{ImageIntegrityError.HASH_MISMATCH}: expected {manifest.sha256}, got {actual_hash}"
            )

        return ImageValidationResult(passed=len(errors) == 0, image_id=manifest.image_id, errors=errors)

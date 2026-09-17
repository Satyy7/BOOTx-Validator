"""Unit tests for firmware/test image integrity validation
(bootx/validation/image.py). Pure Python, no QEMU/build required."""

from __future__ import annotations

from pathlib import Path

import pytest

from bootx.validation.image import ImageManifest, ImageValidator


@pytest.fixture()
def sample_image(tmp_path: Path) -> Path:
    path = tmp_path / "bl33.bin"
    path.write_bytes(b"\xde\xad\xbe\xef" * 1024)
    return path


@pytest.mark.image
def test_manifest_roundtrip_and_valid_image_passes(tmp_path: Path, sample_image: Path):
    manifest = ImageManifest.from_file(
        sample_image, image_id="BL33", version="2026.07", load_address="0x40200000", entry_address="0x40200000"
    )
    manifest_path = tmp_path / "bl33.manifest.json"
    manifest.save(manifest_path)

    loaded = ImageManifest.load(manifest_path)
    assert loaded == manifest

    result = ImageValidator().validate(sample_image, loaded)
    assert result.passed
    assert result.errors == []


@pytest.mark.image
@pytest.mark.fault
def test_corrupted_image_fails_hash_check(tmp_path: Path, sample_image: Path):
    manifest = ImageManifest.from_file(
        sample_image, image_id="BL33", version="2026.07", load_address="0x40200000", entry_address="0x40200000"
    )

    data = bytearray(sample_image.read_bytes())
    data[10] ^= 0xFF
    sample_image.write_bytes(data)

    result = ImageValidator().validate(sample_image, manifest)
    assert not result.passed
    assert any("IMAGE_HASH_MISMATCH" in e for e in result.errors)


@pytest.mark.image
@pytest.mark.fault
def test_truncated_image_fails_size_and_hash_check(tmp_path: Path, sample_image: Path):
    manifest = ImageManifest.from_file(
        sample_image, image_id="BL33", version="2026.07", load_address="0x40200000", entry_address="0x40200000"
    )

    sample_image.write_bytes(sample_image.read_bytes()[:100])

    result = ImageValidator().validate(sample_image, manifest)
    assert not result.passed
    assert any("IMAGE_SIZE_MISMATCH" in e for e in result.errors)
    assert any("IMAGE_HASH_MISMATCH" in e for e in result.errors)


@pytest.mark.image
@pytest.mark.fault
def test_missing_image_reported(tmp_path: Path, sample_image: Path):
    manifest = ImageManifest.from_file(
        sample_image, image_id="BL33", version="2026.07", load_address="0x40200000", entry_address="0x40200000"
    )
    sample_image.unlink()

    result = ImageValidator().validate(sample_image, manifest)
    assert not result.passed
    assert "IMAGE_MISSING" in result.errors

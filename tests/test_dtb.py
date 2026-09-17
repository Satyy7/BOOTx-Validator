"""Unit tests for the device tree validator (bootx/validation/dtb.py).

Compiles small, hand-written .dts fixtures with the real `dtc` binary into
.dtb files, then validates those real blobs -- this exercises the actual
dtc-decompile-and-inspect path, not a mocked DTB.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from bootx.validation.dtb import DtbValidator

VALID_DTS = """
/dts-v1/;
/ {
    #address-cells = <2>;
    #size-cells = <2>;
    memory@40000000 {
        device_type = "memory";
        reg = <0x0 0x40000000 0x0 0x80000000>;
    };
    cpus {
        #address-cells = <1>;
        #size-cells = <0>;
        cpu@0 { device_type = "cpu"; compatible = "arm,cortex-a72"; reg = <0>; };
        cpu@1 { device_type = "cpu"; compatible = "arm,cortex-a72"; reg = <1>; };
    };
    intc: interrupt-controller@8000000 {
        compatible = "arm,gic-v3";
        reg = <0x0 0x8000000 0x0 0x10000>;
        interrupt-controller;
        #interrupt-cells = <3>;
    };
    pl011@9000000 {
        compatible = "arm,pl011", "arm,primecell";
        reg = <0x0 0x9000000 0x0 0x1000>;
    };
};
"""

MISSING_MEMORY_DTS = """
/dts-v1/;
/ {
    #address-cells = <2>;
    #size-cells = <2>;
    cpus {
        #address-cells = <1>;
        #size-cells = <0>;
        cpu@0 { device_type = "cpu"; compatible = "arm,cortex-a72"; reg = <0>; };
    };
};
"""


def _compile_dtb(dts_text: str, out_path: Path) -> None:
    dts_path = out_path.with_suffix(".dts")
    dts_path.write_text(dts_text, encoding="utf-8")
    subprocess.run(["dtc", "-I", "dts", "-O", "dtb", "-o", str(out_path), str(dts_path)], check=True, capture_output=True)


@pytest.fixture()
def require_dtc(dtc_available: bool):
    if not dtc_available:
        pytest.skip("dtc not installed")


@pytest.mark.dtb
def test_valid_dtb_passes_all_checks(tmp_path: Path, require_dtc):
    dtb_path = tmp_path / "valid.dtb"
    _compile_dtb(VALID_DTS, dtb_path)

    result = DtbValidator(expected_cpu_count=2, expected_ram_mb=2048).validate(dtb_path)
    assert result.passed, result.to_dict()


@pytest.mark.dtb
def test_missing_memory_node_detected(tmp_path: Path, require_dtc):
    dtb_path = tmp_path / "missing_memory.dtb"
    _compile_dtb(MISSING_MEMORY_DTS, dtb_path)

    result = DtbValidator(expected_cpu_count=1, expected_ram_mb=2048).validate(dtb_path)
    assert not result.passed
    memory_finding = next(f for f in result.findings if f.check == "memory_node")
    assert not memory_finding.passed


@pytest.mark.dtb
def test_cpu_count_mismatch_detected(tmp_path: Path, require_dtc):
    dtb_path = tmp_path / "valid.dtb"
    _compile_dtb(VALID_DTS, dtb_path)

    # DTB has 2 cpu nodes; assert against an expectation of 4.
    result = DtbValidator(expected_cpu_count=4, expected_ram_mb=2048).validate(dtb_path)
    assert not result.passed
    cpu_finding = next(f for f in result.findings if f.check == "cpus_node")
    assert not cpu_finding.passed


@pytest.mark.dtb
def test_missing_dtb_file_reported_cleanly(tmp_path: Path, require_dtc):
    result = DtbValidator(expected_cpu_count=2, expected_ram_mb=2048).validate(tmp_path / "does-not-exist.dtb")
    assert not result.passed

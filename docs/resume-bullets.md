# Resume Bullets

Written after implementation and verification, not before. Every claim
below is backed by a specific source location and a specific passing
test, both listed. All numbers are from an actual run of the full suite
(`pytest`, 58 items, 58 passed, 0 failed, 0 skipped, ~110s) against a
real built firmware stack -- not estimated or aspirational.

---

**Claim:** Built a QEMU-based ARM64 SoC boot validation framework
integrating a real, unmodified TF-A + U-Boot + Linux firmware stack
(BL1/BL2/BL31/BL33/kernel), with every reported boot stage backed by a
literal, regex-matched line of captured serial console output.

**Evidence:**
`bootx/orchestrator/`, `qemu/scripts/build_tfa.sh`, `qemu/scripts/build_uboot.sh`,
`qemu/scripts/build_linux.sh`, `docs/boot-flow.md` (evidence table).

**Test proving it:**
`tests/test_boot.py::test_firmware_boots_to_userspace` -- asserts
BL1_ENTRY, BL31_ENTRY, BL33_ENTRY, KERNEL_ENTRY, and USERSPACE_READY are
all observed on a real boot.

---

**Claim:** Implemented a contract-based boot validation engine: boots are
declared as YAML (required stages, order, required events, timeout
budget) and checked against a real captured timeline with a per-clause
PASS/FAIL breakdown.

**Evidence:** `bootx/validation/boot_contract.py`, `scenarios/normal_boot.yaml`.

**Test proving it:**
`tests/test_boot.py::test_normal_boot_contract_passes_on_real_boot` (real
boot) and `tests/test_contracts.py` (5 cases covering pass, missing
stage, order violation, timeout violation, and report formatting).

---

**Claim:** Built a fault-injection framework where a negative test passes
only when the framework itself correctly detects and classifies an
injected failure, not merely when the boot breaks -- covering firmware
image corruption, DTB corruption, memory-map violations, boot timeouts,
and kernel command-line misconfiguration.

**Evidence:** `bootx/faults/`, `bootx/analysis/failure_classifier.py`,
`docs/fault-injection.md`.

**Test proving it:** `tests/test_faults.py` (4 cases, all against real
artifacts/boots) and `tests/test_timeout.py::test_timeout_fault_triggers_and_is_classified`.
One of these faults (`invalid_bootargs`) went through two iterations
before landing on a mechanism (`rdinit=`) that actually produces the
claimed failure on this specific initramfs-based boot -- documented in
`docs/fault-injection.md` as a real debugging narrative, not a
first-try success.

---

**Claim:** Implemented real device-tree validation by decompiling the
actual DTB QEMU generates for a given CPU/RAM configuration (via QEMU's
own `dumpdtb` option) with the real `dtc` compiler, checking memory,
CPU count, interrupt controller, and UART nodes.

**Evidence:** `bootx/validation/dtb.py`, `qemu/scripts/dump_dtb.sh`.

**Test proving it:** `tests/test_dtb.py` (4 cases against `dtc`-compiled
fixtures) plus `tests/test_faults.py::test_invalid_dtb_fault_is_detected`
against a real, QEMU-dumped DTB. Also caught and fixed a real bug here:
the validator's GIC-detection regex missed QEMU's actual GICv2 compatible
string (`arm,cortex-a15-gic`), found only by inspecting a real dumped DTB.

---

**Claim:** Verified real SMP/PSCI behavior across multiple core counts:
parameterized real boots at `-smp 1/2/4/8`, confirming secondary-CPU
bring-up via the kernel's own PSCI-driven `CPUn: Booted secondary
processor` messages, and confirming a real PSCI `SYSTEM_OFF` request
(triggered by the boot's own init calling `reboot()`) actually terminates
QEMU.

**Evidence:** `bootx/faults/`, `firmware/linux/initramfs/init.c`,
`docs/interview-guide.md` (PSCI section).

**Test proving it:** `tests/test_smp.py` (7 parameterized cases, all
passing against real boots) and `tests/test_psci.py` (2 cases). Also
caught and fixed a real bug here: TF-A was built against a GICv2 driver
by default while the QEMU machine string requested GICv3, a mismatch
that would have broken interrupt delivery for SMP -- found by reading
TF-A's own build configuration, not by guessing.

---

**Claim:** Implemented reliable timeout/hang detection for automated
boot testing, verified to actually terminate a hung QEMU process and
leave no orphan process behind.

**Evidence:** `bootx/orchestrator/qemu.py` (`QemuRunner`).

**Test proving it:** `tests/test_timeout.py::test_qemu_process_is_not_orphaned_after_timeout`
(checks the OS-level process is actually dead via `os.kill(pid, 0)`).
This required fixing a real, serious bug: the original implementation
used a blocking `readline()` that never returned once QEMU stopped
producing new output (e.g. idling at a bootloader prompt) without
exiting, so the configured timeout was silently never enforced -- caught
by noticing a QEMU process still running 16+ minutes after a 12-second
timeout was configured, root-caused, and fixed with a `select()`-based
read loop, then verified against a synthetic hung-process test before
being trusted against real firmware.

---

**Claim:** Built a full pytest-based regression suite (58 tests) split
between fast, QEMU-independent unit tests and real end-to-end boot
tests, with JUnit XML and human-readable reporting, runnable via a
dedicated CLI (`bootx doctor/build/boot/test/report/clean`).

**Evidence:** `tests/` (13 files), `bootx/cli/main.py`,
`bootx/reporting/`, `pyproject.toml` (marker registration).

**Test proving it:** the suite itself -- `pytest`, 58 passed, 0 failed,
0 skipped, ~110s, against a real built firmware stack on 2026-09-18.
`bootx report` renders this as a human-readable summary from the real
JUnit output.

# Interview Guide

This page maps BOOTX's implemented features to the concepts a Qualcomm
Bootloader SDET interview would probe, and is intentionally scoped to
**only what this repository actually does** -- no aspirational claims.
Every "How BOOTX implements it" line names the actual file.

## ARM64 reset and the BootROM concept

**What it is:** on real silicon, reset vectors the core into mask-ROM
code (the boot ROM / PBL on Qualcomm parts) that has no dependency on
external memory being initialized yet.

**How BOOTX relates to it:** QEMU's `virt` machine doesn't model a real
boot ROM. TF-A's BL1, loaded via `-bios`, plays the architectural role a
boot ROM would hand off to. See `docs/limitations.md` for exactly what's
real vs. conceptual here -- this is the single biggest thing to be
precise about in an interview.

## BL1 / BL2 / BL31 / BL33 (TF-A's boot stage model)

**What it is:** TF-A splits EL3 firmware bring-up into BL1 (trusted boot
ROM stage), BL2 (trusted boot firmware -- loads the rest), BL31 (EL3
runtime firmware / secure monitor), and BL33 (non-trusted firmware,
typically a bootloader like U-Boot or UEFI).

**How BOOTX implements it:** `firmware/tf-a/` builds real upstream TF-A
for `PLAT=qemu`; all four stages execute for real (see
`docs/boot-flow.md`'s evidence table). `bootx/tracing/parser.py` detects
each stage's entry from its actual NOTICE-level log line.

**Tested by:** `tests/test_boot.py::test_firmware_boots_to_userspace`,
`tests/test_boot.py::test_boot_stage_order_is_chronological`.

**Limitation:** BL1's "boot ROM" role is QEMU's approximation, not a
mask-ROM's actual immutability/robustness guarantees.

## EL3, the secure monitor, and SMC/ERET

**What it is:** EL3 is the highest ARM64 exception level, where the
secure monitor arbitrates between secure and non-secure worlds via `SMC`
(request) and returns via `ERET`. PSCI calls are the standard SMC-based
API for power management.

**How BOOTX observes it:** `bootx/validation/exception_level.py` parses
TF-A's own `BL31: Preparing for EL3 exit to normal world` +
`SPSR = 0x...` trace and decodes the SPSR "M" field per the Armv8-A ARM
into the target exception level BL33 is entered at.

**Tested by:** `tests/test_psci.py::test_el3_exit_spsr_is_observed`.

**Limitation:** this is one data point at one moment (the initial EL3
exit). BOOTX does not trace every SMC/ERET pair over the session -- see
`docs/limitations.md`.

## PSCI (Power State Coordination Interface)

**What it is:** the standard firmware API ARM64 OSes use to bring up
secondary CPUs (`CPU_ON`), power them down (`CPU_OFF`), and control
system power (`SYSTEM_OFF`, `SYSTEM_RESET`).

**How BOOTX exercises it:** TF-A's BL2 adds `enable-method = "psci"` to
the FDT's `/cpus` nodes; Linux's SMP bring-up issues real `CPU_ON` SMCs
for each secondary core as a direct consequence, observed via
`CPUn: Booted secondary processor` (`tests/test_smp.py`). BOOTX's
minimal init calls `reboot(RB_POWER_OFF)`, which the kernel turns into a
real `SYSTEM_OFF` SMC -- QEMU's process exit proves TF-A/PSCI actually
handled it (`tests/test_psci.py::test_system_off_terminates_qemu_without_forced_timeout`).

**Limitation:** `CPU_OFF` and `SYSTEM_RESET` aren't exercised by BOOTX's
current boot flow.

## GIC and SMP

**What it is:** the Generic Interrupt Controller routes interrupts
(including the inter-processor interrupts SMP bring-up depends on)
across cores; `-smp N` plus a correctly-configured GIC is what makes
multi-core Linux boot at all.

**How BOOTX exercises it:** `qemu,gic-version=3` in the machine string;
`tests/test_smp.py` parameterizes real boots across `-smp 1/2/4/8` and
checks both full boot success and secondary-CPU bring-up evidence.

## Device Tree

**What it is:** the data structure describing hardware to firmware/OS --
memory ranges, CPU topology, interrupt controller, peripherals.

**How BOOTX validates it:** `bootx/validation/dtb.py` decompiles the
*actual* DTB for a given `-smp`/`-m` configuration (extracted via QEMU's
own `dumpdtb` option -- see `qemu/scripts/dump_dtb.sh`) with the real
`dtc` binary and inspects `/memory`, `/cpus`, the GIC node, and the UART
node.

**Tested by:** `tests/test_dtb.py` (valid tree, missing `/memory`, CPU
count mismatch, missing file) plus the fault-injection case in
`tests/test_faults.py::test_invalid_dtb_fault_is_detected`.

## Memory map validation

**What it is:** verifying firmware stage load addresses don't overlap,
fall outside RAM, or violate alignment -- a class of bug that's easy to
introduce via linker-script or Kconfig mistakes and very hard to debug
from symptoms alone.

**How BOOTX implements it:** `bootx/validation/memory.py`'s
`MemoryMapValidator` checks a `MemoryRegion` list for pairwise overlap,
RAM-bounds, and alignment.

**Tested by:** `tests/test_memory.py` (positive case, overlap,
out-of-range, misalignment, all using deliberately-crafted region sets in
`bootx/faults/memory_fault.py`).

**Limitation:** this validates a region *model* BOOTX is told about, not
a live memory dump read out of the running guest.

## Image integrity / secure boot concepts

**What it is:** production secure boot authenticates every stage before
executing it, backed by a hardware root of trust (fuses, ROM-resident
public keys), with rollback protection.

**How BOOTX implements it (explicitly scoped down):**
`bootx/validation/image.py`'s `ImageManifest`/`ImageValidator` computes
SHA-256 + size over BOOTX-tracked artifacts and rejects mismatches. This
is named and documented as a **BOOTX validation manifest**, not a claim
of reproducing TF-A's Trusted Board Boot or any hardware root of trust.

**Tested by:** `tests/test_images.py`, plus
`tests/test_faults.py::test_corrupt_image_fault_is_detected`.

## Linux handoff and userspace

**What it is:** the bootloader's final responsibility -- placing the
kernel, DTB, and initramfs in memory correctly and jumping to the kernel
entry point with the right register state (`x0` = DTB address per the
Linux/arm64 boot protocol).

**How BOOTX exercises it:** U-Boot's `qfw` command reads the
`-kernel`/`-initrd`/`-append` QEMU was launched with out of QEMU's fw_cfg
device and performs the actual handoff; `bootx/tracing/parser.py` detects
`Booting Linux on physical CPU ...` as direct evidence the jump
succeeded.

## UART / serial console as the evidence channel

**What it is:** on most bring-up and CI boot-test setups (QEMU included),
the serial console is the only observable channel into early boot --
there's no debugger attached by default.

**How BOOTX uses it:** `bootx/orchestrator/qemu.py`'s `QemuRunner`
captures every line with a host-relative timestamp; nothing downstream
(parser, timeline, contract engine, classifier) ever sees anything BOOTX
didn't actually read off that channel.

## Timeout / hang detection

**What it is:** a boot that never reaches its next expected stage is a
real, common bring-up failure mode (bad handoff, wrong entry address,
crashed secure monitor) and needs to be caught deterministically, not by
a human watching a terminal.

**How BOOTX implements it:** `QemuRunner.run()` enforces a wall-clock
deadline and guarantees process cleanup (process-group `SIGTERM` then
`SIGKILL`) even on timeout; `bootx/validation/handoff.py` additionally
detects a *specific* missing handoff (source stage seen, destination
stage never seen) with the exact wait time and expected event.

**Tested by:** `tests/test_timeout.py` (including verifying no orphan
QEMU process survives), `tests/test_handoff.py`.

## Fault injection and test automation

See `docs/fault-injection.md` for the full treatment;
`bootx/faults/`, `bootx/analysis/failure_classifier.py`, and
`tests/test_faults.py` are the implementation.

## CI

`.github/workflows/ci.yml` splits a fast QEMU-independent unit-test lane
from a slower firmware-build-and-regression lane with cached build
artifacts -- see `docs/testing-strategy.md`.

## QEMU vs. physical hardware

Covered in depth in `docs/limitations.md` and
`docs/architecture.md#why-the-testrunner-boundary-matters-hardware-portability`.
The short answer for an interview: BOOTX's validators/contract
engine/classifier operate on a hardware-independent `BootTimeline`
abstraction; only `bootx/orchestrator/qemu.py` and `config.py` know QEMU
exists, which is deliberate scoping for a future physical-board backend.

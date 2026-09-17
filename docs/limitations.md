# Limitations

Honesty about scope is part of BOOTX's engineering discipline. This page
is not a disclaimer buried at the bottom of a pitch -- it is a primary
document, and every claim elsewhere in this repository should be read
against it.

## The hardware target is not a Qualcomm SoC

BOOTX targets **QEMU's `virt` ARM64 machine**, not any real silicon.
`virt` is QEMU's own generic, paravirtual ARM64 platform: it does not
model Qualcomm's Snapdragon bus fabric, PMIC/power sequencing, clock
trees, boot ROM, eFuses, XBL/PBL boot chain, or any other Qualcomm-
specific IP. No proprietary Qualcomm firmware is implemented, referenced,
decompiled, or emulated anywhere in this project.

What BOOTX demonstrates is *transferable*: the engineering discipline of
validating a multi-stage ARM64 firmware boot -- structured tracing,
contract-based pass/fail, memory/DTB/image integrity checks, fault
injection, timeout handling, and failure classification -- applies to any
ARM64 SoC boot chain, Qualcomm's included. The specific bytes, addresses,
and register layouts do not.

## The firmware is real, but the chain is QEMU's variant of it

TF-A, U-Boot, and Linux are built from real upstream source (pinned
versions in `docs/boot-flow.md`) for TF-A's `qemu` platform port. On this
platform:

- **BL1 genuinely executes** as the boot ROM stage, loaded by QEMU via
  `-bios`.
- **BL2 genuinely executes**, loaded by BL1, and edits the FDT QEMU
  generates at runtime (adds the PSCI node) before handing off to BL31.
- **BL31 genuinely executes** as the EL3 runtime firmware / secure
  monitor.
- **BL33 is U-Boot**, genuinely executing in the non-secure world after
  BL31's `ERET`.

None of BL1/BL2/BL31/BL33 are stand-ins that merely print a fake banner.
See `docs/boot-flow.md` for exactly which log lines BOOTX treats as
evidence of each stage, captured from real runs.

What is **not** real: QEMU's `virt` platform is not a faithful model of
any physical boot ROM's mask-programmed logic, its "reset" is a QEMU
machine reset rather than a physical power sequencing event, and there is
no real hardware root of trust (eFuses, OTP keys) backing any of this.

## Timing is not representative of physical hardware

Every timestamp BOOTX records (`bootx/tracing`, `bootx/performance`) is
**host wall-clock time**, measured by the Python harness as it reads
QEMU's serial output. This is real, measured, non-fabricated data -- and
it is useful for catching *regressions* in this specific QEMU
configuration on this specific host. It says nothing about how fast a
real Snapdragon part would boot: QEMU's CPU model is not cycle-accurate,
host scheduling jitter affects every measurement, and there is no DVFS,
cold-boot power sequencing, or real memory controller training to model.

## Secure-world / EL2 / EL1 observability is partial

TF-A's own BL31 exit-path log (`bootx/validation/exception_level.py`)
gives BOOTX one genuine, directly-observed data point: the SPSR value
BL31 programs before `ERET` into BL33, decoded into an exception level
per the Armv8-A architecture reference. That is the extent of BOOTX's EL
observability. BOOTX does **not** observe:

- EL2/EL1 transitions inside U-Boot or Linux (would require kernel/U-Boot
  instrumentation reading `CurrentEL`, or a GDB-stub session against
  QEMU's `-s -S`, neither of which is currently implemented).
- Secure/non-secure world switches after the initial BL31 exit.
- Any TrustZone-style secure-world runtime behavior beyond what TF-A's
  own boot-time log emits.

## PSCI coverage

- **SYSTEM_OFF** is genuinely exercised: BOOTX's minimal userspace
  (`firmware/linux/initramfs/init.c`) calls `reboot(RB_POWER_OFF)`, which
  the kernel turns into a real PSCI `SYSTEM_OFF` SMC to TF-A/EL3, which
  QEMU's `virt` platform honors by exiting the process.
- **CPU_ON** is indirectly but genuinely exercised: Linux's own SMP
  bring-up issues PSCI `CPU_ON` calls (via the `enable-method = "psci"`
  property BL2 adds to the FDT's `/cpus` nodes) for every secondary CPU;
  BOOTX observes the *result* of this through the kernel's own
  `CPUn: Booted secondary processor` console messages, not the SMC call
  itself.
- **CPU_OFF** and **SYSTEM_RESET** are not exercised: BOOTX's boot flow
  never requests them, and detecting them from console output alone
  would not be reliable evidence.

## Image integrity is a BOOTX-authored layer, not production secure boot

`bootx/validation/image.py` computes SHA-256/size/address manifests over
build artifacts this project controls. This is **not** a reproduction of
TF-A's Trusted Board Boot (certificate chains, ROTPK, rollback counters)
or any Qualcomm secure-boot infrastructure (fuses, hardware root of
trust, signed images enforced by boot ROM). Call it what it is: an
educational integrity-checking layer BOOTX puts around its own artifacts
to make fault injection testable end-to-end.

## Memory map validation is a model, not a live memory dump

`bootx/validation/memory.py` validates a region model BOOTX builds from
known/configured load addresses. It does not read QEMU guest physical
memory at runtime -- doing that reliably would require a GDB-stub session
or QMP memory-read support, which BOOTX does not currently use.

## No physical hardware was used or is required

There is no development board involved anywhere in this project. Section
`docs/architecture.md` explains how the test/runner boundary is kept
narrow enough that a physical-hardware backend (serial/JTAG transport,
board power control, hardware-specific boot log parsing) could replace
the QEMU backend without touching validator/contract/classifier logic --
but no such backend is implemented here.

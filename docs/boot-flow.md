# Boot Flow

## Pinned firmware versions

| Component | Version | Upstream |
|---|---|---|
| Trusted Firmware-A | v2.15.0 | https://github.com/ARM-software/arm-trusted-firmware |
| U-Boot | v2026.07 | https://github.com/u-boot/u-boot |
| Linux | v6.12 (LTS) | https://github.com/torvalds/linux |

Fetched as shallow clones by `make setup` into `firmware/{tf-a,u-boot,linux}/src`
(gitignored -- not vendored into this repository; see `.gitignore`).

## Platform / target configuration

- QEMU machine: `virt,secure=on,gic-version=3`
- CPU model: `cortex-a72`
- TF-A platform: `PLAT=qemu` (`firmware/tf-a/src/plat/qemu/`)
- U-Boot defconfig: `qemu_arm64_defconfig`
- Linux defconfig: `defconfig` (arm64)

## Stage-by-stage: what actually executes, and how BOOTX knows

| Stage | Executes? | Evidence BOOTX matches (`bootx/tracing/parser.py`) |
|---|---|---|
| BL1 | Real TF-A code, loaded by QEMU via `-bios` | `NOTICE:  BL1: v<version>` |
| BL2 | Real TF-A code, loaded by BL1 | `NOTICE:  BL2: v<version>` |
| BL31 | Real TF-A code (EL3 runtime firmware) | `NOTICE:  BL31: v<version>` |
| BL31 EL3 exit | Real TF-A code path | `BL31: Preparing for EL3 exit to normal world` + `SPSR = 0x...` (decoded by `bootx/validation/exception_level.py`) |
| BL33 / U-Boot | Real U-Boot build, entered directly by BL31's `ERET` | `U-Boot 2026.07 (...)` banner |
| DTB handoff | U-Boot relocates/uses the FDT TF-A's BL2 patched (added the PSCI node) | `Booting using the fdt blob at ...` |
| Kernel load | U-Boot's `qfw` command reads the `-kernel`/`-initrd`/`-append` QEMU was launched with, out of QEMU's fw_cfg device, and boots them | `Loading Kernel Image` / `Starting kernel ...` |
| Kernel entry | Real Linux, built from the pinned source | `Booting Linux on physical CPU 0x...` |
| Secondary CPU bring-up | Real PSCI `CPU_ON` SMCs from Linux's SMP bring-up path | `CPUn: Booted secondary processor ...` |
| Userspace | BOOTX's own minimal init (`firmware/linux/initramfs/init.c`), the initramfs's PID 1 | literal marker `BOOTX_USERSPACE_READY` |
| Clean shutdown | Real PSCI `SYSTEM_OFF` SMC, triggered by `reboot(RB_POWER_OFF)` in BOOTX's init | QEMU process exits on its own (no forced kill) |

Every row above is a **regex match against an actual captured line of
serial output** (`bootx/tracing/parser.py`) -- BOOTX never fabricates an
event for a stage that didn't print evidence of running.

## Why U-Boot is loaded as BL33 rather than Linux directly

TF-A's `qemu` platform documents an `ARM_LINUX_KERNEL_AS_BL33` mode that
skips a bootloader and lets TF-A hand off straight to a Linux `Image`.
BOOTX deliberately does **not** use that shortcut: a Qualcomm-relevant
boot validation framework needs to exercise a *bootloader* stage (image
loading, environment/boot-script evaluation, kernel/DTB/initrd handoff),
which is exactly the role U-Boot plays here as BL33. Skipping it would
remove the stage most directly analogous to what a bootloader SDET team
actually tests.

## Assembling the flash image QEMU loads

Per TF-A's own documentation for the `qemu` platform
(`firmware/tf-a/src/docs/plat/qemu.rst`, "Booting via flash based
firmware"):

```sh
make CROSS_COMPILE=aarch64-linux-gnu- PLAT=qemu BL33=u-boot.bin all fip
dd if=build/qemu/release/bl1.bin of=flash.bin bs=4096 conv=notrunc
dd if=build/qemu/release/fip.bin  of=flash.bin bs=4096 seek=64 conv=notrunc
qemu-system-aarch64 -bios flash.bin ...
```

BOOTX's `qemu/scripts/build_tfa.sh` implements exactly this. BL1 lives at
the start of the flash image (QEMU's `-bios` entrypoint); the FIP
(BL2+BL31+BL33 packaged together) sits at a fixed 256 KiB offset.

## Device tree

QEMU's `virt` board generates its FDT at runtime from the `-smp`/`-m`
parameters it was launched with; TF-A's BL2 patches that FDT (adds the
PSCI node) before passing it on. `bootx/validation/dtb.py` inspects the
**real** DTB for a given configuration by asking QEMU itself to dump it
(`qemu-system-aarch64 -machine virt,...,dumpdtb=out.dtb`, a real,
deterministic, non-fabricated extraction -- see
`qemu/scripts/dump_dtb.sh`), not a hand-authored stand-in.

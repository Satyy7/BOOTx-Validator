#!/usr/bin/env bash
# Build Trusted Firmware-A for the QEMU virt platform.
#
# Real execution model (see docs/boot-flow.md):
#   BL1  -> acts as the BootROM, loaded by QEMU via -bios
#   BL2  -> loaded by BL1, edits the QEMU-generated FDT (PSCI node etc.)
#   BL31 -> EL3 runtime firmware / secure monitor
#   BL33 -> U-Boot (built separately, then linked in as BL33 here)
#
# All four stages are the actual upstream TF-A code for plat=qemu; nothing
# here is a stand-in or simulation of BL1/BL2/BL31.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT/firmware/tf-a/src"
OUT="$ROOT/firmware/tf-a/build"
IMAGES="$ROOT/qemu/images"

UBOOT_BIN="$IMAGES/u-boot.bin"
if [[ ! -f "$UBOOT_BIN" ]]; then
    echo "FAIL: $UBOOT_BIN not found. Build U-Boot first (build_uboot.sh)." >&2
    exit 1
fi

mkdir -p "$IMAGES"

make -C "$SRC" \
    CROSS_COMPILE=aarch64-linux-gnu- \
    PLAT=qemu \
    ARCH=aarch64 \
    DEBUG=0 \
    LOG_LEVEL=40 \
    BL33="$UBOOT_BIN" \
    BUILD_BASE="$OUT" \
    all fip

QEMU_OUT="$OUT/qemu/release"
cp "$QEMU_OUT/bl1.bin" "$IMAGES/bl1.bin"
cp "$QEMU_OUT/fip.bin" "$IMAGES/fip.bin"

# Per TF-A docs (docs/plat/qemu.rst, "Booting via flash based firmware"):
# concatenate bl1.bin and fip.bin at a fixed 256KiB (64 * 4096) offset to
# form the flash image QEMU loads whole via -bios. BL1 is the BootROM
# entrypoint; FIP (BL2+BL31+BL33) sits right after it.
rm -f "$IMAGES/flash.bin"
dd if="$IMAGES/bl1.bin" of="$IMAGES/flash.bin" bs=4096 conv=notrunc
dd if="$IMAGES/fip.bin" of="$IMAGES/flash.bin" bs=4096 seek=64 conv=notrunc

echo "TF-A build complete:"
echo "  $IMAGES/bl1.bin"
echo "  $IMAGES/fip.bin"
echo "  $IMAGES/flash.bin (bl1 @ 0, fip @ 256KiB)"

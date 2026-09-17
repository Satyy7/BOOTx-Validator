#!/usr/bin/env bash
# Build U-Boot for the QEMU ARM64 virt platform. This becomes BL33: TF-A's
# EL3 firmware hands off directly into this binary in the non-secure world.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT/firmware/u-boot/src"
OUT="$ROOT/firmware/u-boot/build"
IMAGES="$ROOT/qemu/images"

mkdir -p "$OUT" "$IMAGES"

make -C "$SRC" O="$OUT" CROSS_COMPILE=aarch64-linux-gnu- qemu_arm64_defconfig
make -C "$SRC" O="$OUT" CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)"

cp "$OUT/u-boot.bin" "$IMAGES/u-boot.bin"

echo "U-Boot build complete: $IMAGES/u-boot.bin"

#!/usr/bin/env bash
# Build a minimal arm64 Linux kernel Image for QEMU virt.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT/firmware/linux/src"
OUT="$ROOT/firmware/linux/build"
IMAGES="$ROOT/qemu/images"

mkdir -p "$OUT" "$IMAGES"

make -C "$SRC" O="$OUT" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- defconfig
make -C "$SRC" O="$OUT" ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- -j"$(nproc)" Image

cp "$OUT/arch/arm64/boot/Image" "$IMAGES/Image"

echo "Linux build complete: $IMAGES/Image"

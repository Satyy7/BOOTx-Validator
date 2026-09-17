#!/usr/bin/env bash
# Build a minimal statically-linked initramfs whose sole job is proving
# Linux reached userspace (see firmware/linux/initramfs/init.c).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SRC="$ROOT/firmware/linux/initramfs"
OUT="$ROOT/firmware/linux/build/initramfs"
IMAGES="$ROOT/qemu/images"

mkdir -p "$OUT" "$IMAGES"

aarch64-linux-gnu-gcc -static -O2 -o "$OUT/init" "$SRC/init.c"

( cd "$OUT" && echo init | cpio -o -H newc | gzip -9 > "$IMAGES/initramfs.cpio.gz" )

echo "Initramfs build complete: $IMAGES/initramfs.cpio.gz"

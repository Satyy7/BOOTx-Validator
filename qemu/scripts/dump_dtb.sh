#!/usr/bin/env bash
# Extract the real device tree QEMU's virt machine generates for a given
# -smp/-m configuration, via QEMU's own `dumpdtb` machine option. This is
# the actual DTB the firmware/kernel would receive for that configuration
# -- not a hand-authored stand-in -- because QEMU's virt board FDT
# generation is a deterministic function of the machine parameters given.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CPUS="${1:-4}"
RAM="${2:-2G}"
OUT="${3:-$ROOT/qemu/images/virt.dtb}"

mkdir -p "$(dirname "$OUT")"

qemu-system-aarch64 \
    -machine "virt,secure=on,gic-version=2,dumpdtb=$OUT" \
    -cpu cortex-a72 \
    -smp "$CPUS" \
    -m "$RAM" \
    -nographic

echo "Dumped DTB: $OUT"

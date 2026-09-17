#!/usr/bin/env bash
# Phase 1 baseline: prove QEMU can create and tear down an ARM64 virt
# machine before any firmware is involved. No -bios/-kernel is passed, so
# QEMU will halt immediately with no boot device -- that's expected; this
# script only checks that the *machine* itself starts and exits cleanly.
set -euo pipefail

CPUS="${1:-4}"
RAM="${2:-2G}"
TIMEOUT="${3:-5}"

echo "Launching QEMU ARM64 virt baseline: -smp $CPUS -m $RAM -cpu cortex-a72"

timeout "$TIMEOUT" qemu-system-aarch64 \
    -machine virt \
    -cpu cortex-a72 \
    -smp "$CPUS" \
    -m "$RAM" \
    -nographic \
    -d guest_errors 2>&1 | head -20 || true

echo "QEMU baseline invocation returned (timeout=${TIMEOUT}s is expected without -bios/-kernel)."

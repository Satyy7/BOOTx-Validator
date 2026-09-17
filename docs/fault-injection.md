# Fault Injection

## Philosophy

A fault-injection test in BOOTX is not "does the boot fail" -- an
untested boot fails in plenty of uninteresting ways. It is:

```
real, working boot artifact/config
        +
a specific, controlled, reversible mutation
        =
a specific, predicted failure signature
        +
BOOTX correctly detecting and classifying it
        =
TEST PASS
```

If BOOTX fails to detect the injected fault, or classifies it into the
wrong category, that is a **test FAILURE** -- even though the underlying
boot also failed. Detection is what's under test, not breakage.

## Interface

`bootx/faults/base.py:Fault` is the contract every fault implements:

- `expectation() -> FaultExpectation`: the failure category and human
  description this fault is expected to produce.
- `inject(workdir) -> dict`: mutate a **copy** of a real artifact under a
  scratch directory (originals are never touched) and return whatever
  context the caller needs to point QEMU/the validator at the mutated
  artifact.

## Implemented faults

| Fault | Module | Mechanism | Expected category |
|---|---|---|---|
| `corrupt_image` | `bootx/faults/corrupt_image.py` | XOR-flip a byte range inside a real firmware binary | `IMAGE_FAILURE` |
| `invalid_dtb` | `bootx/faults/invalid_dtb.py` | Truncate a real, QEMU-dumped DTB | `DTB_FAILURE` |
| `missing_dtb` | `bootx/faults/invalid_dtb.py` | Point at a DTB path that doesn't exist | `DTB_FAILURE` |
| `overlapping_regions` / `out_of_range_regions` / `misaligned_regions` | `bootx/faults/memory_fault.py` | Construct an invalid `MemoryRegion` set directly | `MEMORY_FAILURE` |
| `boot_timeout` | `bootx/faults/timeout.py` | Boot with no kernel/initrd attached, so nothing to autoboot into | `TIMEOUT_FAILURE` |
| `invalid_bootargs` | `bootx/faults/configuration_fault.py` | Kernel `rdinit=` pointed at a nonexistent executable | `CONFIGURATION_FAILURE` |
| `missing_kernel` | `bootx/faults/configuration_fault.py` | QEMU `-kernel` path that doesn't exist | `CONFIGURATION_FAILURE` |

## Why image/DTB faults don't need a QEMU boot

`bootx/validation/image.py` and `bootx/validation/dtb.py` are pre-boot
integrity gates -- exactly the kind of check a real bootloader applies
*before* executing an image, not after watching it fail on the console.
So the corresponding fault tests (`tests/test_faults.py`) inject the
mutation and run the validator directly: this is faster, more
deterministic (no dependency on how a corrupted binary happens to crash
inside QEMU), and matches how production firmware validation actually
gates untrusted images.

## Why configuration/timeout faults do need one

There's no validator that can predict how U-Boot or Linux will react to
a bad `rdinit=` argument or a hung autoboot prompt without actually
running them -- that reaction (`Kernel panic: VFS: Unable to mount root
fs on unknown-block(0,0)`, or silence at the U-Boot prompt) *is* the
evidence. These tests run a real, deliberately-misconfigured boot and
check that `bootx/analysis/failure_classifier.py` reads that evidence
correctly.

`invalid_bootargs`'s exact mechanism went through two failed attempts
before landing on `rdinit=`, and it's worth recording why, since both
failures were only caught by actually running the fault and watching it
have no effect:

1. **`root=<bogus device>`** (the original design): silently ignored.
   `root=` is only consulted inside `prepare_namespace()`, which never
   runs, because BOOTX's initramfs (`firmware/linux/initramfs/init.c`)
   always has its own `/init`, and the kernel finds and runs that first.
2. **`init=<bogus path>`**: also silently ignored, for a subtler reason:
   the kernel checks `ramdisk_execute_command` (which defaults to
   `"/init"` and exists in our initramfs) *before* it ever looks at what
   `init=` set. `init=` is only a fallback for when the initramfs has no
   `/init` at all.
3. **`rdinit=<bogus path>`** (what's actually implemented): this is the
   one bootarg that directly overrides `ramdisk_execute_command` itself.
   Pointing it at a path that doesn't exist makes the kernel's
   `init_eaccess()` check fail, which routes it into `prepare_namespace()`
   -- and since no `root=` is set either, that reliably panics.

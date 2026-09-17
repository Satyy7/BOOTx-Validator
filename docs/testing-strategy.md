# Testing Strategy

## Layers

BOOTX's test suite is deliberately split into tests that need a real QEMU
boot and tests that don't, so the fast majority of the suite can run
anywhere Python runs:

1. **Unit tests against synthetic/crafted evidence** (no QEMU): the boot
   log parser against literal known-good log lines
   (`tests/test_stages.py`), the contract engine against hand-built
   `BootTimeline`s (`tests/test_contracts.py`), the memory validator
   against hand-built region sets (`tests/test_memory.py`), the DTB
   validator against `.dts` fixtures compiled with the real `dtc` binary
   (`tests/test_dtb.py`), image manifest/integrity checks against
   temp-file fixtures (`tests/test_images.py`), and the handoff validator
   against synthetic timelines (`tests/test_handoff.py`).
2. **Real end-to-end boot tests** (`tests/test_boot.py`,
   `tests/test_smp.py`, `tests/test_psci.py`, `tests/test_performance.py`,
   the boot-requiring cases in `tests/test_faults.py` /
   `tests/test_timeout.py`): these launch actual `qemu-system-aarch64`
   with the actual built firmware stack and assert on the actual parsed
   evidence.

Layer 2 tests skip (via `tests/conftest.py:require_firmware` /
`require_qemu`) rather than fail when the host doesn't have QEMU
installed or the firmware hasn't been built yet -- `pytest` remains
runnable everywhere; `bootx doctor` explains what's missing.

## Markers

Defined in `pyproject.toml`: `smoke`, `boot`, `contract`, `memory`,
`dtb`, `image`, `handoff`, `psci`, `smp`, `fault`, `hang_detection`,
`performance`, `regression`.

```sh
pytest -m smoke        # fast sanity subset, safe for every commit
pytest -m fault         # fault-injection tests only
pytest -m smp           # -smp 1/2/4/8 parameterized boots
pytest -m regression    # full suite
```

## Assertion style

Tests assert on parsed, structured evidence (`assert
timeline.has_event(EventType.KERNEL_ENTRY)`), not on process exit code
alone -- an exit code doesn't tell you *which* stage the boot reached.
Where exit-code-only checks are actually appropriate (process lifecycle:
"did QEMU terminate cleanly, did it leave an orphan process"), that's
what's being tested and the test says so
(`tests/test_timeout.py:test_qemu_process_is_not_orphaned_after_timeout`).

## Negative test philosophy

See `docs/fault-injection.md` for the full treatment. The short version:
a negative test passes when BOOTX correctly detects and classifies an
injected failure, not merely when the boot fails.

## Observability

Every boot run -- pass, fail, or crash mid-suite -- leaves a complete
`reports/runs/<timestamp>_<label>/` directory behind (raw log, metadata,
parsed events, timeline/result). A failing test should be diagnosable by
reading that directory, without rerunning anything. See
`docs/architecture.md#data-flow-per-run`.

## CI

`.github/workflows/ci.yml` runs the QEMU-independent unit-test layer on
every push (fast, no build required). Firmware build + full end-to-end
suite runs as a separate, cacheable job -- see the workflow file's
comments for the split rationale.

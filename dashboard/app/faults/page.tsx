"use client";

import PageHeader from "@/components/PageHeader";
import { usePolling } from "@/lib/hooks";
import type { JunitSummary } from "@/lib/types";
import { CheckCircle2, XCircle, MinusCircle, FlaskConical } from "lucide-react";

interface FaultDef {
  name: string;
  module: string;
  mechanism: string;
  expected: string;
  testName: string | null;
}

const FAULTS: FaultDef[] = [
  {
    name: "corrupt_image",
    module: "bootx/faults/corrupt_image.py",
    mechanism: "XOR-flip a byte range inside a real firmware binary (U-Boot/BL33)",
    expected: "IMAGE_FAILURE",
    testName: "test_corrupt_image_fault_is_detected",
  },
  {
    name: "invalid_dtb",
    module: "bootx/faults/invalid_dtb.py",
    mechanism: "Truncate a real, QEMU-dumped DTB so it's no longer structurally valid",
    expected: "DTB_FAILURE",
    testName: "test_invalid_dtb_fault_is_detected",
  },
  {
    name: "missing_dtb",
    module: "bootx/faults/invalid_dtb.py",
    mechanism: "Point the boot configuration at a DTB path that doesn't exist",
    expected: "DTB_FAILURE",
    testName: "test_missing_dtb_fault_is_detected",
  },
  {
    name: "overlapping / out-of-range / misaligned regions",
    module: "bootx/faults/memory_fault.py",
    mechanism: "Construct a deliberately invalid MemoryRegion set for the validator",
    expected: "MEMORY_FAILURE",
    testName: null,
  },
  {
    name: "boot_timeout",
    module: "bootx/faults/timeout.py",
    mechanism: "Boot with no kernel/initrd attached — nothing for U-Boot to autoboot into",
    expected: "TIMEOUT_FAILURE",
    testName: "test_timeout_fault_triggers_and_is_classified",
  },
  {
    name: "invalid_bootargs (rdinit=)",
    module: "bootx/faults/configuration_fault.py",
    mechanism: "rdinit= pointed at a nonexistent executable — verified empirically after two failed designs (root=, init=) had no effect on this initramfs-based boot",
    expected: "CONFIGURATION_FAILURE",
    testName: "test_invalid_bootargs_fault_is_classified_configuration_failure",
  },
  {
    name: "missing_kernel",
    module: "bootx/faults/configuration_fault.py",
    mechanism: "QEMU -kernel path that doesn't exist",
    expected: "CONFIGURATION_FAILURE",
    testName: null,
  },
];

export default function FaultsPage() {
  const { data: junit } = usePolling<JunitSummary>("/api/junit", 6000);

  return (
    <div>
      <PageHeader
        eyebrow="Negative Testing"
        title="Fault Injection"
        description="A fault test PASSES when BOOTX correctly detects and classifies the injected failure — not merely when the boot breaks. Detection is what's under test."
      />

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {FAULTS.map((f) => {
          const testCase = f.testName ? junit?.cases.find((c) => c.name === f.testName) : undefined;
          const status = testCase?.status ?? (f.testName ? "unknown" : "unit-only");

          return (
            <div key={f.name} className="card-glow rounded-2xl border border-border bg-surface/70 p-5">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div className="flex items-center gap-2.5">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-status-fail/10 text-status-fail">
                    <FlaskConical size={16} />
                  </div>
                  <div>
                    <p className="font-mono-tight text-sm font-semibold text-foreground">{f.name}</p>
                    <p className="text-[10px] text-muted-2">{f.module}</p>
                  </div>
                </div>
                {status === "passed" && (
                  <span className="flex items-center gap-1 rounded-full bg-status-pass/15 px-2.5 py-1 text-xs font-semibold text-status-pass">
                    <CheckCircle2 size={13} /> Detected
                  </span>
                )}
                {status === "failed" && (
                  <span className="flex items-center gap-1 rounded-full bg-status-fail/15 px-2.5 py-1 text-xs font-semibold text-status-fail">
                    <XCircle size={13} /> Failed
                  </span>
                )}
                {status === "unit-only" && (
                  <span className="flex items-center gap-1 rounded-full bg-status-skip/15 px-2.5 py-1 text-xs font-semibold text-status-skip">
                    <MinusCircle size={13} /> Unit-covered
                  </span>
                )}
              </div>

              <p className="text-sm text-muted">{f.mechanism}</p>

              <div className="mt-3 flex items-center gap-2 text-xs">
                <span className="text-muted-2">Expected classification:</span>
                <span className="rounded-md bg-surface-2 px-2 py-0.5 font-mono-tight text-accent-2">{f.expected}</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-8 rounded-2xl border border-border-soft bg-surface/40 p-5 text-sm text-muted">
        <span className="font-semibold text-foreground">Note:</span> memory-map faults and{" "}
        <code className="font-mono-tight text-accent-2">missing_kernel</code> are validated at the unit level
        (<code className="font-mono-tight text-accent-2">tests/test_memory.py</code>) rather than via a full
        real boot — see <code className="font-mono-tight text-accent-2">docs/fault-injection.md</code> in the
        repo for why that&apos;s the right level for each fault.
      </div>
    </div>
  );
}

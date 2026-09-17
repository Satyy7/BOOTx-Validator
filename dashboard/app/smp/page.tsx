"use client";

import { useEffect, useState } from "react";
import PageHeader from "@/components/PageHeader";
import StatusBadge from "@/components/StatusBadge";
import { usePolling } from "@/lib/hooks";
import type { RunDetail, RunSummary } from "@/lib/types";
import { formatMs } from "@/lib/stage";
import { Cpu, Power, ShieldCheck, Zap } from "lucide-react";

const CPU_COUNTS = [1, 2, 4, 8];

function latestByLabel(runs: RunSummary[], label: string): RunSummary | null {
  return runs.find((r) => r.label === label) ?? null;
}

export default function SmpPsciPage() {
  const { data: runs } = usePolling<RunSummary[]>("/api/runs", 6000);
  const [details, setDetails] = useState<Record<string, RunDetail>>({});

  const bootRunIds = CPU_COUNTS.map((c) => latestByLabel(runs ?? [], `smp-${c}`)?.id).filter(Boolean) as string[];
  const cpuOnRunIds = CPU_COUNTS.map((c) => latestByLabel(runs ?? [], `smp-cpuon-${c}`)?.id).filter(Boolean) as string[];
  const pypiRun = (runs ?? []).find((r) => r.label === "pytest" && r.reachedUserspace) ?? null;
  const idsToFetch = Array.from(new Set([...bootRunIds, ...cpuOnRunIds, pypiRun?.id].filter(Boolean) as string[]));

  useEffect(() => {
    idsToFetch.forEach((id) => {
      if (details[id]) return;
      fetch(`/api/runs/${id}`)
        .then((r) => r.json())
        .then((d: RunDetail) => setDetails((prev) => ({ ...prev, [id]: d })));
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsToFetch.join(",")]);

  const psciRun = pypiRun ? details[pypiRun.id] : null;

  return (
    <div>
      <PageHeader
        eyebrow="Multi-Core & Power Management"
        title="SMP & PSCI"
        description="Real QEMU -smp 1/2/4/8 configurations. Secondary CPUs come up via genuine PSCI CPU_ON SMCs (TF-A's BL2 adds enable-method=psci to the FDT); shutdown is a real PSCI SYSTEM_OFF triggered by BOOTX's own init."
      />

      <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted">CPU Configurations</h2>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {CPU_COUNTS.map((cpus) => {
          const bootRun = latestByLabel(runs ?? [], `smp-${cpus}`);
          const cpuOnRun = latestByLabel(runs ?? [], `smp-cpuon-${cpus}`);
          const cpuOnDetail = cpuOnRun ? details[cpuOnRun.id] : null;
          const cpuOnEvents = cpuOnDetail?.result?.timeline.events.filter((e) => e.event === "CPU_ON") ?? [];

          return (
            <div key={cpus} className="card-glow relative overflow-hidden rounded-2xl border border-border bg-surface/70 p-5">
              <div className="mb-4 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-accent-2/10 text-accent-2">
                    <Cpu size={16} />
                  </div>
                  <div>
                    <p className="text-lg font-bold text-foreground">-smp {cpus}</p>
                    <p className="text-[10px] uppercase tracking-wide text-muted-2">cortex-a72</p>
                  </div>
                </div>
                {bootRun ? <StatusBadge status={bootRun.outcome} /> : <StatusBadge status="UNKNOWN" />}
              </div>

              <div className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted">Boot time</span>
                  <span className="font-mono-tight text-foreground">{formatMs(bootRun?.totalBootMs ?? null)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Secondary CPUs booted</span>
                  <span className="font-mono-tight text-foreground">
                    {cpus === 1 ? "n/a" : cpuOnRun ? `${cpuOnEvents.length} / ${cpus - 1}` : "—"}
                  </span>
                </div>
              </div>

              {cpuOnEvents.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {cpuOnEvents.map((e) => (
                    <span
                      key={e.cpu}
                      className="flex items-center gap-1 rounded-full bg-stage-kernel/10 px-2 py-0.5 text-[10px] font-mono-tight text-stage-kernel"
                    >
                      <Zap size={9} /> CPU{e.cpu} @ {formatMs(e.timestamp_ms)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <h2 className="mb-3 mt-10 text-sm font-semibold uppercase tracking-wider text-muted">PSCI Evidence</h2>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-border bg-surface/70 p-5">
          <div className="mb-3 flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-status-pass/10 text-status-pass">
              <Power size={15} />
            </div>
            <h3 className="text-sm font-semibold text-foreground">SYSTEM_OFF</h3>
          </div>
          <p className="text-sm text-muted">
            BOOTX&apos;s minimal init (<code className="font-mono-tight text-accent-2">firmware/linux/initramfs/init.c</code>)
            calls <code className="font-mono-tight text-accent-2">reboot(RB_POWER_OFF)</code> after printing its marker. The
            kernel turns this into a real PSCI SYSTEM_OFF SMC to TF-A/EL3.
          </p>
          {psciRun && (
            <div className="mt-4 flex items-center gap-2 rounded-lg border border-border-soft bg-background/50 px-3 py-2 text-xs">
              {!psciRun.timed_out && psciRun.returncode !== null ? (
                <>
                  <ShieldCheck size={14} className="text-status-pass" />
                  <span className="text-foreground">
                    Verified: QEMU exited on its own (returncode {psciRun.returncode}), no forced kill needed.
                  </span>
                </>
              ) : (
                <span className="text-muted">No clean-shutdown evidence in latest run.</span>
              )}
            </div>
          )}
        </div>

        <div className="rounded-2xl border border-border bg-surface/70 p-5">
          <div className="mb-3 flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-stage-bl31/10 text-stage-bl31">
              <ShieldCheck size={15} />
            </div>
            <h3 className="text-sm font-semibold text-foreground">EL3 Exit — Exception Level</h3>
          </div>
          <p className="mb-3 text-sm text-muted">
            Decoded directly from TF-A&apos;s own SPSR trace right before <code className="font-mono-tight text-accent-2">ERET</code> out
            of EL3 (SPSR bits[3:0], the AArch64 &quot;M&quot; field, per the Armv8-A architecture reference).
          </p>
          {psciRun?.elObservation ? (
            <div className="space-y-1.5 rounded-lg border border-border-soft bg-background/50 p-3 text-xs">
              <div className="flex justify-between">
                <span className="text-muted">Security state</span>
                <span className="font-mono-tight text-foreground">{psciRun.elObservation.securityState}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">SPSR</span>
                <span className="font-mono-tight text-foreground">{psciRun.elObservation.spsrHex}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted">Target EL</span>
                <span className="font-mono-tight font-bold text-accent-2">{psciRun.elObservation.targetEl}</span>
              </div>
            </div>
          ) : (
            <p className="text-xs text-muted-2">No EL3 exit evidence found in latest run.</p>
          )}
        </div>
      </div>
    </div>
  );
}

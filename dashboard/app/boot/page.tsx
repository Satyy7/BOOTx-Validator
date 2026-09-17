"use client";

import { useEffect, useState } from "react";
import PageHeader from "@/components/PageHeader";
import StatusBadge from "@/components/StatusBadge";
import BootTimeline from "@/components/BootTimeline";
import { usePolling } from "@/lib/hooks";
import type { RunDetail, RunSummary } from "@/lib/types";
import { formatMs } from "@/lib/stage";
import { Cpu, MemoryStick, Clock } from "lucide-react";

export default function BootTracePage() {
  const { data: runs } = usePolling<RunSummary[]>("/api/runs?limit=40", 5000);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<RunDetail | null>(null);

  const meaningfulRuns = (runs ?? []).filter((r) => r.stageCount > 3);
  const activeId = selectedId ?? meaningfulRuns[0]?.id ?? null;

  useEffect(() => {
    if (!activeId) return;
    fetch(`/api/runs/${activeId}`)
      .then((r) => r.json())
      .then(setDetail)
      .catch(() => setDetail(null));
  }, [activeId]);

  return (
    <div>
      <PageHeader
        eyebrow="Real Boot Evidence"
        title="Boot Trace"
        description="Every event below was matched against a literal line of captured QEMU serial console output — see the raw evidence by expanding a row."
        actions={
          <select
            value={activeId ?? ""}
            onChange={(e) => setSelectedId(e.target.value)}
            className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-foreground outline-none focus:border-accent"
          >
            {meaningfulRuns.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label} · {r.outcome} · {r.timestamp}
              </option>
            ))}
          </select>
        }
      />

      {detail ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-4">
          <div className="lg:col-span-3 rounded-2xl border border-border bg-surface/70 p-5">
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <StatusBadge status={detail.outcome} />
              <span className="text-xs text-muted-2 font-mono-tight">{detail.id}</span>
            </div>
            <BootTimeline timeline={detail.result!.timeline} />
          </div>

          <div className="space-y-4">
            <div className="rounded-2xl border border-border bg-surface/70 p-4">
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Run Config</h3>
              <div className="space-y-2.5 text-sm">
                <div className="flex items-center gap-2 text-muted">
                  <Cpu size={14} /> {detail.cpus} vCPU (cortex-a72)
                </div>
                <div className="flex items-center gap-2 text-muted">
                  <MemoryStick size={14} /> {detail.ram_mb} MB RAM
                </div>
                <div className="flex items-center gap-2 text-muted">
                  <Clock size={14} /> timeout {detail.metadata?.config.timeout_s ?? "—"}s
                </div>
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-surface/70 p-4">
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Stage Latencies</h3>
              <div className="space-y-2">
                {detail.result?.timeline.stage_latencies.map((l) => (
                  <div key={`${l.from}-${l.to}`} className="flex items-center justify-between text-xs">
                    <span className="truncate text-muted">
                      {l.from.replace(/_ENTRY|_INIT_COMPLETE/g, "")} → {l.to.replace(/_ENTRY|_INIT_COMPLETE/g, "")}
                    </span>
                    <span className="font-mono-tight text-foreground">{formatMs(l.latency_ms)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-2xl border border-border bg-surface/70 p-4">
              <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">QEMU Command</h3>
              <pre className="overflow-x-auto whitespace-pre-wrap break-all font-mono-tight text-[11px] leading-relaxed text-muted-2">
                {detail.metadata?.command.join(" ")}
              </pre>
            </div>
          </div>
        </div>
      ) : (
        <div className="rounded-2xl border border-border-soft bg-surface/50 p-10 text-center text-sm text-muted">
          No boot runs with a full timeline yet. Run <code className="font-mono-tight text-accent-2">bootx boot</code> or{" "}
          <code className="font-mono-tight text-accent-2">bootx test</code> to generate one.
        </div>
      )}
    </div>
  );
}

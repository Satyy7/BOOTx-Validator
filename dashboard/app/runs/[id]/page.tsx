"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import PageHeader from "@/components/PageHeader";
import StatusBadge from "@/components/StatusBadge";
import BootTimeline from "@/components/BootTimeline";
import type { RunDetail } from "@/lib/types";
import { ArrowLeft, Terminal } from "lucide-react";

export default function RunDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [detail, setDetail] = useState<RunDetail | null>(null);
  const [showLog, setShowLog] = useState(false);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    fetch(`/api/runs/${params.id}`)
      .then((r) => {
        if (!r.ok) throw new Error("404");
        return r.json();
      })
      .then(setDetail)
      .catch(() => setNotFound(true));
  }, [params.id]);

  if (notFound) {
    return <div className="text-sm text-muted">Run not found.</div>;
  }
  if (!detail) {
    return <div className="text-sm text-muted">Loading…</div>;
  }

  return (
    <div>
      <button
        onClick={() => router.push("/runs")}
        className="mb-4 flex items-center gap-1.5 text-xs text-muted-2 transition-colors hover:text-foreground"
      >
        <ArrowLeft size={13} /> Back to run history
      </button>

      <PageHeader
        eyebrow={detail.timestamp}
        title={detail.label}
        description={detail.id}
        actions={<StatusBadge status={detail.outcome} className="text-sm" />}
      />

      {detail.result && detail.result.timeline.events.length > 0 && (
        <div className="mb-6 rounded-2xl border border-border bg-surface/70 p-5">
          <BootTimeline timeline={detail.result.timeline} />
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="rounded-2xl border border-border bg-surface/70 p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Configuration</h3>
          <dl className="space-y-1.5 text-sm">
            <div className="flex justify-between">
              <dt className="text-muted">CPUs</dt>
              <dd className="font-mono-tight text-foreground">{detail.cpus}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">RAM</dt>
              <dd className="font-mono-tight text-foreground">{detail.ram_mb} MB</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Timeout budget</dt>
              <dd className="font-mono-tight text-foreground">{detail.metadata?.config.timeout_s ?? "—"}s</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Duration</dt>
              <dd className="font-mono-tight text-foreground">{detail.duration_s?.toFixed(2) ?? "—"}s</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Return code</dt>
              <dd className="font-mono-tight text-foreground">{detail.returncode ?? "—"}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Timed out</dt>
              <dd className="font-mono-tight text-foreground">{String(detail.timed_out)}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-muted">Bootargs</dt>
              <dd className="max-w-[60%] truncate text-right font-mono-tight text-foreground">
                {detail.metadata?.config.bootargs ?? "—"}
              </dd>
            </div>
          </dl>
        </div>

        <div className="rounded-2xl border border-border bg-surface/70 p-4">
          <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Firmware Paths</h3>
          <dl className="space-y-1.5 text-xs">
            {detail.metadata &&
              Object.entries(detail.metadata.config.firmware).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-2">
                  <dt className="shrink-0 text-muted">{k}</dt>
                  <dd className="truncate font-mono-tight text-foreground">{v ?? "—"}</dd>
                </div>
              ))}
          </dl>

          {detail.elObservation && (
            <>
              <h3 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wider text-muted">EL3 Exit</h3>
              <div className="flex items-center gap-3 text-xs">
                <span className="rounded-md bg-surface-2 px-2 py-1 font-mono-tight text-accent-2">
                  {detail.elObservation.targetEl}
                </span>
                <span className="text-muted">{detail.elObservation.spsrHex}</span>
              </div>
            </>
          )}
        </div>
      </div>

      {detail.logAvailable && (
        <div className="mt-6 rounded-2xl border border-border bg-surface/70">
          <button
            onClick={() => setShowLog(!showLog)}
            className="flex w-full items-center gap-2 px-5 py-4 text-left text-sm font-semibold text-foreground"
          >
            <Terminal size={15} className="text-accent-2" />
            Raw QEMU Serial Log
            <span className="ml-auto text-xs font-normal text-muted-2">{showLog ? "hide" : "show"}</span>
          </button>
          {showLog && (
            <pre className="max-h-[500px] overflow-auto border-t border-border-soft bg-background/60 p-4 font-mono-tight text-[11px] leading-relaxed text-muted">
              {detail.logTail}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  CartesianGrid,
} from "recharts";
import PageHeader from "@/components/PageHeader";
import { usePolling } from "@/lib/hooks";
import type { RunDetail, RunSummary } from "@/lib/types";
import { formatMs, stageColor } from "@/lib/stage";
import { Info } from "lucide-react";

interface HopStat {
  hop: string;
  label: string;
  stage: string;
  samples: number[];
  min: number;
  max: number;
  mean: number;
  median: number;
}

function guessStage(eventName: string): string {
  if (eventName.startsWith("BL1")) return "BL1";
  if (eventName.startsWith("BL2")) return "BL2";
  if (eventName.startsWith("BL31")) return "BL31";
  if (eventName.startsWith("BL33") || eventName === "UBOOT_ENTRY") return "BL33";
  if (eventName.startsWith("KERNEL")) return "KERNEL";
  if (eventName.startsWith("USERSPACE")) return "USERSPACE";
  return "RESET";
}

function median(nums: number[]): number {
  const s = [...nums].sort((a, b) => a - b);
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { payload: HopStat }[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border border-border bg-surface-2 px-3 py-2 text-xs shadow-xl">
      <p className="mb-1.5 font-semibold text-foreground">{d.label}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 font-mono-tight text-muted">
        <span>min</span> <span className="text-right text-foreground">{formatMs(d.min)}</span>
        <span>median</span> <span className="text-right text-foreground">{formatMs(d.median)}</span>
        <span>mean</span> <span className="text-right text-foreground">{formatMs(d.mean)}</span>
        <span>max</span> <span className="text-right text-foreground">{formatMs(d.max)}</span>
      </div>
      <p className="mt-1.5 text-[10px] text-muted-2">n={d.samples.length} real boots</p>
    </div>
  );
}

export default function PerformancePage() {
  const { data: runs } = usePolling<RunSummary[]>("/api/runs", 8000);
  const [details, setDetails] = useState<RunDetail[]>([]);

  const perfRunIds = (runs ?? []).filter((r) => r.label.startsWith("perf-")).map((r) => r.id);

  useEffect(() => {
    if (perfRunIds.length === 0) return;
    Promise.all(perfRunIds.map((id) => fetch(`/api/runs/${id}`).then((r) => r.json()))).then(setDetails);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [perfRunIds.join(",")]);

  const hopMap = new Map<string, HopStat>();
  for (const d of details) {
    for (const l of d.result?.timeline.stage_latencies ?? []) {
      const key = `${l.from}->${l.to}`;
      const label = `${l.from.replace(/_ENTRY|_INIT_COMPLETE/g, "")} → ${l.to.replace(/_ENTRY|_INIT_COMPLETE/g, "")}`;
      if (!hopMap.has(key)) {
        hopMap.set(key, { hop: key, label, stage: guessStage(l.to), samples: [], min: 0, max: 0, mean: 0, median: 0 });
      }
      hopMap.get(key)!.samples.push(l.latency_ms);
    }
  }
  const hops: HopStat[] = Array.from(hopMap.values()).map((h) => ({
    ...h,
    min: Math.min(...h.samples),
    max: Math.max(...h.samples),
    mean: h.samples.reduce((a, b) => a + b, 0) / h.samples.length,
    median: median(h.samples),
  }));

  const totalSamples = details.map((d) => d.result?.timeline.total_boot_ms ?? 0).filter((n) => n > 0);
  const totalMean = totalSamples.length ? totalSamples.reduce((a, b) => a + b, 0) / totalSamples.length : null;

  return (
    <div>
      <PageHeader
        eyebrow={`${details.length} real boot iterations`}
        title="Performance"
        description="Host wall-clock timing from repeated real QEMU boots — useful for catching regressions on this exact configuration, not representative of real Snapdragon silicon timing."
      />

      {hops.length > 0 ? (
        <>
          <div className="rounded-2xl border border-border bg-surface/70 p-5">
            <div className="mb-1 flex items-baseline justify-between">
              <h3 className="text-sm font-semibold text-foreground">Mean Stage-to-Stage Latency</h3>
              {totalMean !== null && (
                <span className="font-mono-tight text-sm text-muted">avg total: {formatMs(totalMean)}</span>
              )}
            </div>
            <div style={{ width: "100%", height: hops.length * 46 + 40 }}>
              <ResponsiveContainer>
                <BarChart data={hops} layout="vertical" margin={{ left: 8, right: 24, top: 8, bottom: 8 }}>
                  <CartesianGrid horizontal={false} stroke="var(--border-soft)" />
                  <XAxis
                    type="number"
                    scale="log"
                    domain={[1, "auto"]}
                    allowDataOverflow
                    tickFormatter={(v) => formatMs(v)}
                    ticks={[1, 10, 100, 1000, 10000]}
                    stroke="var(--muted-2)"
                    fontSize={11}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="label"
                    width={170}
                    stroke="var(--muted)"
                    fontSize={11}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip content={<CustomTooltip />} cursor={{ fill: "var(--surface-2)" }} />
                  <Bar dataKey="mean" radius={[0, 4, 4, 0]} maxBarSize={22}>
                    {hops.map((h) => (
                      <Cell key={h.hop} fill={stageColor(h.stage)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="mt-4 flex items-start gap-2 rounded-xl border border-border-soft bg-surface/40 p-3 text-xs text-muted-2">
            <Info size={14} className="mt-0.5 shrink-0" />
            Bar length is the mean of {details.length} real boots on a log axis (hops span ms to multi-second
            latencies); hover a bar for min / median / mean / max.
          </div>

          <h3 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-wider text-muted">Per-Iteration Totals</h3>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {details.map((d, i) => (
              <div key={d.id} className="rounded-xl border border-border bg-surface/70 p-4">
                <p className="text-xs uppercase tracking-wide text-muted-2">Iteration {i + 1}</p>
                <p className="mt-1 font-mono-tight text-xl font-bold text-foreground">
                  {formatMs(d.result?.timeline.total_boot_ms ?? null)}
                </p>
                <p className="mt-1 text-[10px] text-muted-2">{d.id}</p>
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="rounded-2xl border border-border-soft bg-surface/50 p-10 text-center text-sm text-muted">
          No performance runs recorded yet. Run{" "}
          <code className="font-mono-tight text-accent-2">pytest -m performance</code> to generate them.
        </div>
      )}
    </div>
  );
}

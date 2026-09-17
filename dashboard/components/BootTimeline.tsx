"use client";

import { useState } from "react";
import clsx from "clsx";
import type { Timeline } from "@/lib/types";
import { stageColor, eventLabel, formatMs, STAGE_LABELS } from "@/lib/stage";
import { Radio, Cpu as CpuIcon } from "lucide-react";

function GanttRail({ timeline }: { timeline: Timeline }) {
  const latencies = timeline.stage_latencies;
  if (latencies.length === 0) return null;

  // log-scale segment widths so a 0.1ms and a 1000ms hop are both legible
  const weights = latencies.map((l) => Math.log10(Math.max(l.latency_ms, 0.05) + 1) + 0.4);
  const totalWeight = weights.reduce((a, b) => a + b, 0);

  return (
    <div className="mb-6">
      <div className="flex h-10 w-full overflow-hidden rounded-lg border border-border-soft">
        {latencies.map((l, i) => {
          const width = (weights[i] / totalWeight) * 100;
          return (
            <div
              key={`${l.from}-${l.to}`}
              className="group relative flex items-center justify-center border-r border-background/40 text-[10px] font-semibold text-background transition-all hover:brightness-110"
              style={{ width: `${width}%`, background: stageColor(guessStage(l.to)) }}
              title={`${l.from} → ${l.to}: ${formatMs(l.latency_ms)}`}
            >
              <span className="truncate px-1 font-mono-tight">{formatMs(l.latency_ms)}</span>
            </div>
          );
        })}
      </div>
      <div className="mt-1.5 flex justify-between text-[10px] text-muted-2">
        <span>RESET</span>
        <span className="font-mono-tight text-muted">total: {formatMs(timeline.total_boot_ms)}</span>
        <span>USERSPACE_READY</span>
      </div>
    </div>
  );
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

export default function BootTimeline({ timeline }: { timeline: Timeline }) {
  const [expanded, setExpanded] = useState<number | null>(null);

  return (
    <div>
      <GanttRail timeline={timeline} />

      <div className="relative">
        <div className="absolute bottom-2 left-[18px] top-2 w-px bg-border" />
        <ul className="space-y-1">
          {timeline.events.map((e, i) => {
            const color = stageColor(e.stage);
            const isOpen = expanded === i;
            return (
              <li key={i}>
                <button
                  onClick={() => setExpanded(isOpen ? null : i)}
                  className={clsx(
                    "relative flex w-full items-center gap-3 rounded-lg px-2.5 py-2 text-left transition-colors",
                    isOpen ? "bg-surface-2" : "hover:bg-surface/70",
                  )}
                >
                  <span
                    className="relative z-10 h-3 w-3 shrink-0 rounded-full border-2 border-background"
                    style={{ background: color }}
                  />
                  <span className="w-20 shrink-0 font-mono-tight text-xs text-muted-2">
                    {formatMs(e.timestamp_ms)}
                  </span>
                  <span className="w-16 shrink-0 text-[10px] font-semibold uppercase tracking-wide" style={{ color }}>
                    {e.stage}
                  </span>
                  <span className="flex-1 truncate text-sm font-medium text-foreground">{eventLabel(e.event)}</span>
                  {e.cpu !== null && (
                    <span className="flex shrink-0 items-center gap-1 rounded-full bg-surface-2 px-2 py-0.5 text-[10px] text-muted">
                      <CpuIcon size={10} /> CPU{e.cpu}
                    </span>
                  )}
                  <span
                    className={clsx(
                      "flex shrink-0 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] uppercase",
                      e.source === "uart" ? "bg-accent-2/10 text-accent-2" : "bg-muted-2/10 text-muted-2",
                    )}
                  >
                    <Radio size={9} />
                    {e.source}
                  </span>
                </button>
                {isOpen && (
                  <div className="ml-[52px] mr-2 mb-2 mt-1 rounded-lg border border-border-soft bg-background/60 p-3">
                    {STAGE_LABELS[e.stage] && (
                      <p className="mb-1.5 text-xs text-muted-2">{STAGE_LABELS[e.stage]}</p>
                    )}
                    <pre className="overflow-x-auto whitespace-pre-wrap font-mono-tight text-xs text-accent-2/90">
                      {e.raw_line}
                    </pre>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

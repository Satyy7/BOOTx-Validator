"use client";

import { useState } from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import StatusBadge from "@/components/StatusBadge";
import { usePolling } from "@/lib/hooks";
import type { RunSummary } from "@/lib/types";
import { formatMs } from "@/lib/stage";
import { Search, ChevronRight } from "lucide-react";

export default function RunsPage() {
  const { data: runs } = usePolling<RunSummary[]>("/api/runs", 5000);
  const [query, setQuery] = useState("");

  const filtered = (runs ?? []).filter((r) => r.label.toLowerCase().includes(query.toLowerCase()) || r.id.includes(query));

  return (
    <div>
      <PageHeader
        eyebrow={`${runs?.length ?? 0} runs on record`}
        title="Run History"
        description="Every boot BOOTX has ever launched gets its own directory under reports/runs/ — raw log, metadata, parsed events, result. Nothing here is summarized away."
        actions={
          <div className="relative">
            <Search size={14} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-2" />
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Filter by label…"
              className="rounded-lg border border-border bg-surface py-2 pl-8 pr-3 text-sm text-foreground outline-none focus:border-accent"
            />
          </div>
        }
      />

      <div className="overflow-hidden rounded-2xl border border-border bg-surface/70">
        <div className="grid grid-cols-[1fr_auto_auto_auto_auto_auto] gap-3 border-b border-border-soft px-5 py-3 text-[10px] font-semibold uppercase tracking-wider text-muted-2">
          <span>Label / ID</span>
          <span>Outcome</span>
          <span className="text-right">CPUs</span>
          <span className="text-right">RAM</span>
          <span className="text-right">Boot Time</span>
          <span className="w-4" />
        </div>
        <div className="max-h-[70vh] overflow-y-auto">
          {filtered.map((r) => (
            <Link
              key={r.id}
              href={`/runs/${r.id}`}
              className="grid grid-cols-[1fr_auto_auto_auto_auto_auto] items-center gap-3 border-b border-border-soft/60 px-5 py-3 text-sm transition-colors last:border-b-0 hover:bg-surface-2/60"
            >
              <div className="min-w-0">
                <p className="truncate font-medium text-foreground">{r.label}</p>
                <p className="truncate font-mono-tight text-[10px] text-muted-2">{r.timestamp}</p>
              </div>
              <StatusBadge status={r.outcome} />
              <span className="text-right font-mono-tight text-xs text-muted">{r.cpus || "—"}</span>
              <span className="text-right font-mono-tight text-xs text-muted">{r.ram_mb ? `${r.ram_mb}MB` : "—"}</span>
              <span className="text-right font-mono-tight text-xs text-muted">{formatMs(r.totalBootMs)}</span>
              <ChevronRight size={14} className="text-muted-2" />
            </Link>
          ))}
          {filtered.length === 0 && (
            <div className="px-5 py-10 text-center text-sm text-muted-2">No runs match &quot;{query}&quot;</div>
          )}
        </div>
      </div>
    </div>
  );
}

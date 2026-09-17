"use client";

import { useState } from "react";
import clsx from "clsx";
import PageHeader from "@/components/PageHeader";
import { usePolling } from "@/lib/hooks";
import type { JunitSummary } from "@/lib/types";
import { categoryLabel } from "@/lib/stage";
import { CheckCircle2, XCircle, MinusCircle, ChevronDown } from "lucide-react";

export default function TestsPage() {
  const { data: junit } = usePolling<JunitSummary>("/api/junit", 6000);
  const [openCategory, setOpenCategory] = useState<string | null>(null);

  const categories = junit ? Object.entries(junit.categories).sort((a, b) => b[1].total - a[1].total) : [];

  return (
    <div>
      <PageHeader
        eyebrow="pytest · 58-item regression suite"
        title="Test Results"
        description={
          junit
            ? `${junit.total} tests · ${junit.passed} passed · ${junit.failed} failed · ${junit.skipped} skipped · ${junit.duration_s.toFixed(1)}s total`
            : "Run `bootx test` to generate reports/junit.xml"
        }
      />

      {!junit && (
        <div className="rounded-2xl border border-border-soft bg-surface/50 p-10 text-center text-sm text-muted">
          No JUnit report found yet.
        </div>
      )}

      <div className="space-y-3">
        {categories.map(([category, stats]) => {
          const cases = junit!.cases.filter((c) => c.category === category);
          const isOpen = openCategory === category;
          return (
            <div key={category} className="overflow-hidden rounded-2xl border border-border bg-surface/70">
              <button
                onClick={() => setOpenCategory(isOpen ? null : category)}
                className="flex w-full items-center justify-between px-5 py-4 text-left transition-colors hover:bg-surface-2/60"
              >
                <div className="flex items-center gap-3">
                  <ChevronDown size={16} className={clsx("text-muted-2 transition-transform", isOpen && "rotate-180")} />
                  <span className="text-sm font-semibold text-foreground">{categoryLabel(category)}</span>
                  <span className="rounded-full bg-surface-2 px-2 py-0.5 text-[10px] text-muted-2">{stats.total}</span>
                </div>
                <div className="flex items-center gap-4 text-xs">
                  {stats.passed > 0 && (
                    <span className="flex items-center gap-1 text-status-pass">
                      <CheckCircle2 size={13} /> {stats.passed}
                    </span>
                  )}
                  {stats.failed > 0 && (
                    <span className="flex items-center gap-1 text-status-fail">
                      <XCircle size={13} /> {stats.failed}
                    </span>
                  )}
                  {stats.skipped > 0 && (
                    <span className="flex items-center gap-1 text-status-skip">
                      <MinusCircle size={13} /> {stats.skipped}
                    </span>
                  )}
                  <span className="font-mono-tight text-muted-2">{stats.duration_s.toFixed(2)}s</span>
                </div>
              </button>
              {isOpen && (
                <div className="border-t border-border-soft">
                  {cases.map((c) => (
                    <div
                      key={c.name}
                      className="flex items-center justify-between gap-4 border-b border-border-soft/60 px-5 py-2.5 text-sm last:border-b-0"
                    >
                      <span className="min-w-0 truncate font-mono-tight text-xs text-foreground">{c.name}</span>
                      <div className="flex shrink-0 items-center gap-3">
                        <span className="font-mono-tight text-[10px] text-muted-2">{c.time.toFixed(3)}s</span>
                        {c.status === "passed" && <CheckCircle2 size={14} className="text-status-pass" />}
                        {c.status === "failed" && <XCircle size={14} className="text-status-fail" />}
                        {c.status === "skipped" && <MinusCircle size={14} className="text-status-skip" />}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

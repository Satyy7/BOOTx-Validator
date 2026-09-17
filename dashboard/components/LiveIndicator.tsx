"use client";

import { usePolling } from "@/lib/hooks";
import type { LiveStatus } from "@/lib/types";

export default function LiveIndicator() {
  const { data } = usePolling<LiveStatus>("/api/live", 3000);

  const active = data?.active ?? false;

  return (
    <div className="flex items-center gap-2 rounded-xl border border-border-soft bg-surface/60 px-3 py-2.5">
      <span
        className={
          "h-2 w-2 shrink-0 rounded-full " +
          (active ? "live-dot bg-status-pass" : "bg-muted-2")
        }
      />
      <div className="min-w-0">
        <p className="text-xs font-semibold text-foreground">
          {active ? "QEMU boot in progress" : "Idle"}
        </p>
        <p className="truncate text-[10px] text-muted-2">
          {active ? `pid ${data?.pid}` : "no active boot"}
        </p>
      </div>
    </div>
  );
}

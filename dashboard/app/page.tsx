"use client";

import Link from "next/link";
import { usePolling } from "@/lib/hooks";
import type { SummaryResponse, LiveStatus } from "@/lib/types";
import { formatMs } from "@/lib/stage";
import PageHeader from "@/components/PageHeader";
import StatCard from "@/components/StatCard";
import StatusBadge from "@/components/StatusBadge";
import {
  CheckCircle2,
  XCircle,
  Timer,
  Rocket,
  Terminal,
  ArrowRight,
  Waypoints,
  Cpu,
  Bug,
  Gauge,
} from "lucide-react";

const QUICK_LINKS = [
  { href: "/boot", label: "Boot Trace", desc: "Real stage-by-stage timeline", icon: Waypoints, accent: "accent" as const },
  { href: "/smp", label: "SMP & PSCI", desc: "1/2/4/8 CPU configs", icon: Cpu, accent: "accent-2" as const },
  { href: "/faults", label: "Fault Injection", desc: "Detection & classification", icon: Bug, accent: "fail" as const },
  { href: "/performance", label: "Performance", desc: "Real boot timing stats", icon: Gauge, accent: "accent-3" as const },
];

export default function OverviewPage() {
  const { data } = usePolling<SummaryResponse>("/api/summary", 4000);
  const { data: live } = usePolling<LiveStatus>("/api/live", 2000);

  const junit = data?.junit;
  const passRate = junit && junit.total > 0 ? Math.round((junit.passed / junit.total) * 100) : null;

  return (
    <div>
      <PageHeader
        eyebrow="BOOTX · ARM64 SoC Boot Validation Lab"
        title="Overview"
        description="Real Trusted Firmware-A + U-Boot + Linux boot chain, validated end-to-end on QEMU's virt ARM64 platform. Every number on this page is read live from reports/ — nothing here is hardcoded."
      />

      {live?.active && (
        <div className="scan-line relative mb-8 overflow-hidden rounded-2xl border border-accent/40 bg-gradient-to-r from-accent/10 via-surface to-surface p-5">
          <div className="relative flex items-center gap-3">
            <span className="live-dot h-2.5 w-2.5 rounded-full bg-status-pass" />
            <p className="font-mono-tight text-sm font-semibold text-foreground">
              LIVE — QEMU boot in progress (pid {live.pid})
            </p>
          </div>
          {live.tail.length > 0 && (
            <pre className="relative mt-3 max-h-32 overflow-y-auto whitespace-pre-wrap font-mono-tight text-xs text-muted">
              {live.tail.join("\n")}
            </pre>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Tests"
          value={junit ? junit.total : "—"}
          sub={junit ? `${data.runCount} boot runs on record` : "run `bootx test`"}
          icon={<Terminal size={18} />}
          accent="accent"
        />
        <StatCard
          label="Pass Rate"
          value={passRate !== null ? `${passRate}%` : "—"}
          sub={junit ? `${junit.passed} passed · ${junit.failed} failed · ${junit.skipped} skipped` : undefined}
          icon={<CheckCircle2 size={18} />}
          accent="accent-3"
        />
        <StatCard
          label="Last Boot"
          value={
            data?.latestRun ? (
              <StatusBadge status={data.latestRun.outcome} className="text-base" />
            ) : (
              "—"
            )
          }
          sub={data?.latestRun ? `${data.latestRun.label} · ${data.latestRun.cpus} CPUs` : undefined}
          icon={data?.latestRun?.outcome === "FAIL" ? <XCircle size={18} /> : <Rocket size={18} />}
          accent={data?.latestRun?.outcome === "FAIL" ? "fail" : "accent-2"}
        />
        <StatCard
          label="Total Boot Time"
          value={formatMs(data?.latestRun?.totalBootMs ?? null)}
          sub="RESET → USERSPACE_READY, host wall-clock"
          icon={<Timer size={18} />}
          accent="accent-2"
        />
      </div>

      <div className="mt-10 grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted">Firmware Stack</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            {(data?.firmwareVersions ?? [{ name: "TF-A", version: "…" }, { name: "U-Boot", version: "…" }, { name: "Linux", version: "…" }]).map(
              (fw) => (
                <div key={fw.name} className="rounded-xl border border-border bg-surface/70 p-4">
                  <p className="text-xs uppercase tracking-wide text-muted-2">{fw.name}</p>
                  <p className="mt-1 font-mono-tight text-sm font-semibold text-foreground">{fw.version}</p>
                </div>
              ),
            )}
          </div>

          <h2 className="mb-3 mt-8 text-sm font-semibold uppercase tracking-wider text-muted">Explore</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            {QUICK_LINKS.map(({ href, label, desc, icon: Icon, accent }) => (
              <Link
                key={href}
                href={href}
                className="card-glow group flex items-center justify-between rounded-xl border border-border bg-surface/70 p-4 transition-colors hover:border-border-soft"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="flex h-9 w-9 items-center justify-center rounded-lg"
                    style={{
                      color: `var(--${accent})`,
                      background: `color-mix(in srgb, var(--${accent}) 14%, transparent)`,
                    }}
                  >
                    <Icon size={16} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-foreground">{label}</p>
                    <p className="text-xs text-muted-2">{desc}</p>
                  </div>
                </div>
                <ArrowRight size={15} className="text-muted-2 transition-transform group-hover:translate-x-0.5" />
              </Link>
            ))}
          </div>
        </div>

        {/* <div>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted">Host Tooling</h2>
          <div className="space-y-1.5 rounded-xl border border-border bg-surface/70 p-4">
            {(data?.doctor ?? []).slice(0, 5).map((c) => (
              <div key={c.label} className="flex items-center justify-between py-1 text-sm">
                <span className="text-muted">{c.label}</span>
                {c.ok ? (
                  <CheckCircle2 size={15} className="text-status-pass" />
                ) : (
                  <XCircle size={15} className="text-status-fail" />
                )}
              </div>
            ))}
          </div>

          <h2 className="mb-3 mt-6 text-sm font-semibold uppercase tracking-wider text-muted">Build Artifacts</h2>
          <div className="space-y-1.5 rounded-xl border border-border bg-surface/70 p-4">
            {(data?.doctor ?? []).slice(5).map((c) => (
              <div key={c.label} className="flex items-center justify-between py-1 text-sm">
                <span className="text-muted">{c.label}</span>
                {c.ok ? (
                  <CheckCircle2 size={15} className="text-status-pass" />
                ) : (
                  <XCircle size={15} className="text-status-fail" />
                )}
              </div>
            ))}
          </div>
        </div> */}
      </div>
    </div>
  );
}

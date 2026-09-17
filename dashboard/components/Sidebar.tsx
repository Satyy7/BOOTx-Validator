"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import clsx from "clsx";
import {
  LayoutDashboard,
  Waypoints,
  Cpu,
  Bug,
  ListChecks,
  Gauge,
  History,
} from "lucide-react";
import LiveIndicator from "./LiveIndicator";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/boot", label: "Boot Trace", icon: Waypoints },
  { href: "/smp", label: "SMP & PSCI", icon: Cpu },
  { href: "/faults", label: "Fault Injection", icon: Bug },
  { href: "/tests", label: "Test Results", icon: ListChecks },
  { href: "/performance", label: "Performance", icon: Gauge },
  { href: "/runs", label: "Run History", icon: History },
];

export default function Sidebar({ onNavigate }: { onNavigate?: () => void }) {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-border-soft bg-background-alt/60 px-4 py-6">
      <div className="mb-8 flex items-center gap-2.5 px-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-accent-2 font-mono-tight text-sm font-bold text-white shadow-lg shadow-accent/30">
          BX
        </div>
        <div>
          <p className="font-mono-tight text-sm font-bold tracking-tight text-foreground">BOOTX</p>
          <p className="text-[10px] uppercase tracking-widest text-muted-2">Boot Validation Lab</p>
        </div>
      </div>

      <nav className="flex flex-1 flex-col gap-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              onClick={onNavigate}
              className={clsx(
                "group relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-surface-2 text-foreground"
                  : "text-muted hover:bg-surface/60 hover:text-foreground",
              )}
            >
              {active && (
                <span className="absolute left-0 top-1/2 h-5 w-0.5 -translate-y-1/2 rounded-full bg-gradient-to-b from-accent to-accent-2" />
              )}
              <Icon size={17} strokeWidth={2} className={active ? "text-accent-2" : ""} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-4 space-y-3">
        <LiveIndicator />
        <div className="flex items-center gap-2 rounded-xl border border-border-soft px-3 py-2 text-xs text-muted-2">
          QEMU ARM64 virt · 
        </div>
      </div>
    </aside>
  );
}

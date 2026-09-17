import { ReactNode } from "react";
import clsx from "clsx";

export default function StatCard({
  label,
  value,
  sub,
  icon,
  accent = "accent",
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  icon?: ReactNode;
  accent?: "accent" | "accent-2" | "accent-3" | "pass" | "fail";
}) {
  const accentColor = {
    accent: "var(--accent)",
    "accent-2": "var(--accent-2)",
    "accent-3": "var(--accent-3)",
    pass: "var(--status-pass)",
    fail: "var(--status-fail)",
  }[accent];

  return (
    <div
      className={clsx(
        "card-glow relative overflow-hidden rounded-2xl border border-border bg-surface/80 p-5",
        "backdrop-blur-sm transition-transform duration-300 hover:-translate-y-0.5",
      )}
    >
      <div
        className="pointer-events-none absolute -right-8 -top-8 h-28 w-28 rounded-full blur-3xl opacity-20"
        style={{ background: accentColor }}
      />
      <div className="relative flex items-start justify-between">
        <div>
          <p className="text-xs font-medium uppercase tracking-wider text-muted">{label}</p>
          <p className="mt-2 text-3xl font-bold tracking-tight text-foreground">{value}</p>
          {sub && <p className="mt-1 text-xs text-muted-2">{sub}</p>}
        </div>
        {icon && (
          <div
            className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-border-soft"
            style={{ color: accentColor, background: `color-mix(in srgb, ${accentColor} 12%, transparent)` }}
          >
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}

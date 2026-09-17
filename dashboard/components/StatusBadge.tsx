import clsx from "clsx";

type Status = "PASS" | "FAIL" | "TIMEOUT" | "UNKNOWN" | "passed" | "failed" | "skipped";

const STYLES: Record<string, string> = {
  PASS: "bg-status-pass/15 text-status-pass border-status-pass/30",
  passed: "bg-status-pass/15 text-status-pass border-status-pass/30",
  FAIL: "bg-status-fail/15 text-status-fail border-status-fail/30",
  failed: "bg-status-fail/15 text-status-fail border-status-fail/30",
  TIMEOUT: "bg-status-timeout/15 text-status-timeout border-status-timeout/30",
  skipped: "bg-status-skip/15 text-status-skip border-status-skip/30",
  UNKNOWN: "bg-status-skip/15 text-status-skip border-status-skip/30",
};

export default function StatusBadge({ status, className }: { status: Status; className?: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold uppercase tracking-wide",
        STYLES[status] ?? STYLES.UNKNOWN,
        className,
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {status}
    </span>
  );
}

export const STAGE_ORDER = ["RESET", "BL1", "BL2", "BL31", "BL33", "KERNEL", "USERSPACE"] as const;

export const STAGE_COLORS: Record<string, string> = {
  RESET: "var(--stage-reset)",
  BL1: "var(--stage-bl1)",
  BL2: "var(--stage-bl2)",
  BL31: "var(--stage-bl31)",
  BL33: "var(--stage-bl33)",
  KERNEL: "var(--stage-kernel)",
  USERSPACE: "var(--stage-userspace)",
};

export const STAGE_LABELS: Record<string, string> = {
  RESET: "Reset",
  BL1: "BL1 (BootROM)",
  BL2: "BL2 (Trusted Boot FW)",
  BL31: "BL31 (EL3 Runtime / Secure Monitor)",
  BL33: "BL33 (U-Boot)",
  KERNEL: "Linux Kernel",
  USERSPACE: "Userspace",
};

export function stageColor(stage: string): string {
  return STAGE_COLORS[stage] ?? "var(--muted)";
}

export function eventLabel(event: string): string {
  return event
    .split("_")
    .map((w) => w[0] + w.slice(1).toLowerCase())
    .join(" ");
}

export function formatMs(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  if (ms < 1000) return `${ms.toFixed(1)}ms`;
  return `${(ms / 1000).toFixed(2)}s`;
}

const CATEGORY_LABELS: Record<string, string> = {
  boot: "Boot",
  contracts: "Boot Contracts",
  dtb: "Device Tree",
  faults: "Fault Injection",
  handoff: "Stage Handoff",
  images: "Image Integrity",
  memory: "Memory Map",
  performance: "Performance",
  psci: "PSCI",
  smp: "SMP",
  stages: "Log Parser",
  timeout: "Timeout / Hang Detection",
};

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

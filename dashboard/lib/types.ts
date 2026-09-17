export type EventSource = "uart" | "synthetic";

export interface BootEvent {
  event: string;
  stage: string;
  timestamp_ms: number;
  raw_line: string;
  source: EventSource;
  cpu: number | null;
}

export interface StageLatency {
  from: string;
  to: string;
  latency_ms: number;
}

export interface Timeline {
  events: BootEvent[];
  stage_order: string[];
  stage_latencies: StageLatency[];
  total_boot_ms: number | null;
}

export interface RunResult {
  returncode: number | null;
  timed_out: boolean;
  duration_s: number;
  timeline: Timeline;
}

export interface RunMetadata {
  created_utc: string;
  host: {
    platform: string;
    python: string;
    pid: number;
  };
  command: string[];
  config: {
    cpus: number;
    ram_mb: number;
    machine: string;
    cpu_model: string;
    timeout_s: number;
    bootargs: string | null;
    firmware: {
      bios: string;
      kernel: string | null;
      initrd: string | null;
      dtb: string | null;
    };
  };
  firmware_versions: Record<string, string>;
}

export interface RunSummary {
  id: string;
  label: string;
  timestamp: string;
  cpus: number;
  ram_mb: number;
  duration_s: number | null;
  timed_out: boolean;
  returncode: number | null;
  outcome: "PASS" | "FAIL" | "TIMEOUT" | "UNKNOWN";
  stageCount: number;
  totalBootMs: number | null;
  reachedUserspace: boolean;
}

export interface ElObservation {
  securityState: string;
  spsrHex: string;
  targetEl: string;
  evidenceLine: string;
}

export interface RunDetail extends RunSummary {
  metadata: RunMetadata | null;
  result: RunResult | null;
  logTail: string;
  logAvailable: boolean;
  elObservation: ElObservation | null;
}

export interface JunitCase {
  classname: string;
  name: string;
  category: string;
  time: number;
  status: "passed" | "failed" | "skipped";
  message?: string;
}

export interface JunitSummary {
  total: number;
  passed: number;
  failed: number;
  skipped: number;
  duration_s: number;
  timestamp: string | null;
  cases: JunitCase[];
  categories: Record<string, { total: number; passed: number; failed: number; skipped: number; duration_s: number }>;
}

export interface DoctorCheck {
  label: string;
  ok: boolean;
  detail: string;
}

export interface LiveStatus {
  active: boolean;
  pid: number | null;
  command: string | null;
  latestRunId: string | null;
  tail: string[];
}

export interface SummaryResponse {
  junit: JunitSummary | null;
  latestRun: RunSummary | null;
  runCount: number;
  doctor: DoctorCheck[];
  firmwareVersions: { name: string; version: string }[];
}

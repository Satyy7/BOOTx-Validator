import fs from "node:fs";
import path from "node:path";
import { execSync } from "node:child_process";
import type {
  BootEvent,
  DoctorCheck,
  ElObservation,
  JunitCase,
  JunitSummary,
  LiveStatus,
  RunDetail,
  RunMetadata,
  RunResult,
  RunSummary,
} from "./types";

export const REPO_ROOT = path.resolve(process.cwd(), "..");
const RUNS_DIR = path.join(REPO_ROOT, "reports", "runs");
const JUNIT_PATH = path.join(REPO_ROOT, "reports", "junit.xml");
const FIRMWARE_DIR = path.join(REPO_ROOT, "firmware");

function safeReadJson<T>(filePath: string): T | null {
  try {
    return JSON.parse(fs.readFileSync(filePath, "utf-8")) as T;
  } catch {
    return null;
  }
}

function labelFromId(id: string): string {
  // "20260918_010203_123456_pytest" -> "pytest"
  const parts = id.split("_");
  return parts.slice(3).join("_") || id;
}

function timestampFromId(id: string): string {
  // 20260918_010203_123456 -> ISO-ish
  const m = id.match(/^(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})/);
  if (!m) return id;
  const [, y, mo, d, h, mi, s] = m;
  return `${y}-${mo}-${d}T${h}:${mi}:${s}`;
}

export function listRunIds(): string[] {
  if (!fs.existsSync(RUNS_DIR)) return [];
  return fs
    .readdirSync(RUNS_DIR, { withFileTypes: true })
    .filter((d) => d.isDirectory())
    .map((d) => d.name)
    .sort()
    .reverse();
}

function summarizeRun(id: string): RunSummary | null {
  const dir = path.join(RUNS_DIR, id);
  const result = safeReadJson<RunResult>(path.join(dir, "result.json"));
  const metadata = safeReadJson<RunMetadata>(path.join(dir, "metadata.json"));
  if (!result && !metadata) return null;

  const events = result?.timeline?.events ?? [];
  const reachedUserspace = events.some((e) => e.event === "USERSPACE_READY");
  let outcome: RunSummary["outcome"] = "UNKNOWN";
  if (result) {
    if (result.timed_out) outcome = "TIMEOUT";
    else if (reachedUserspace || result.returncode === 0) outcome = "PASS";
    else outcome = "FAIL";
  }

  return {
    id,
    label: labelFromId(id),
    timestamp: metadata?.created_utc ?? timestampFromId(id),
    cpus: metadata?.config?.cpus ?? 0,
    ram_mb: metadata?.config?.ram_mb ?? 0,
    duration_s: result?.duration_s ?? null,
    timed_out: result?.timed_out ?? false,
    returncode: result?.returncode ?? null,
    outcome,
    stageCount: events.length,
    totalBootMs: result?.timeline?.total_boot_ms ?? null,
    reachedUserspace,
  };
}

export function listRunSummaries(limit?: number): RunSummary[] {
  const ids = listRunIds();
  const slice = limit ? ids.slice(0, limit) : ids;
  return slice
    .map(summarizeRun)
    .filter((r): r is RunSummary => r !== null);
}

export function getRunDetail(id: string): RunDetail | null {
  const dir = path.join(RUNS_DIR, id);
  if (!fs.existsSync(dir)) return null;
  const summary = summarizeRun(id);
  if (!summary) return null;

  const metadata = safeReadJson<RunMetadata>(path.join(dir, "metadata.json"));
  const result = safeReadJson<RunResult>(path.join(dir, "result.json"));

  const logPath = path.join(dir, "qemu.log");
  let logTail = "";
  let logAvailable = false;
  let elObservation: ElObservation | null = null;
  if (fs.existsSync(logPath)) {
    logAvailable = true;
    const raw = fs.readFileSync(logPath, "utf-8");
    const lines = raw.split("\n");
    logTail = lines.slice(-400).join("\n");
    elObservation = observeElFromLog(raw);
  }

  return { ...summary, metadata, result, logTail, logAvailable, elObservation };
}

// Mirrors bootx/validation/exception_level.py: decode the AArch64 SPSR "M"
// field TF-A prints right after "BL31: Preparing for EL3 exit to X world".
// Same real log text, reimplemented here so the dashboard doesn't need a
// Python subprocess round-trip for something this small.
const M_FIELD_TO_EL: Record<number, string> = {
  0b0000: "EL0t",
  0b0100: "EL1t",
  0b0101: "EL1h",
  0b1000: "EL2t",
  0b1001: "EL2h",
  0b1100: "EL3t",
  0b1101: "EL3h",
};

export function observeElFromLog(logText: string): ElObservation | null {
  const lines = logText.split("\n");
  const exitRe = /BL31: Preparing for EL3 exit to (\w+) world/;
  const spsrRe = /SPSR\s*=\s*0x([0-9a-fA-F]+)/;

  for (let i = 0; i < lines.length; i++) {
    const ctx = lines[i].match(exitRe);
    if (!ctx) continue;
    for (let j = i; j < Math.min(i + 6, lines.length); j++) {
      const spsrMatch = lines[j].match(spsrRe);
      if (spsrMatch) {
        const spsr = parseInt(spsrMatch[1], 16);
        const mField = spsr & 0xf;
        return {
          securityState: ctx[1],
          spsrHex: spsrMatch[0],
          targetEl: M_FIELD_TO_EL[mField] ?? `UNKNOWN(0b${mField.toString(2).padStart(4, "0")})`,
          evidenceLine: lines[j].trim(),
        };
      }
    }
  }
  return null;
}

function categoryFromClassname(classname: string): string {
  // "tests.test_smp" -> "smp"
  const m = classname.match(/test_([a-z0-9_]+)$/i);
  return m ? m[1] : classname;
}

export function parseJunit(): JunitSummary | null {
  if (!fs.existsSync(JUNIT_PATH)) return null;
  const xml = fs.readFileSync(JUNIT_PATH, "utf-8");

  const suiteMatch = xml.match(/<testsuite\b[^>]*timestamp="([^"]*)"[^>]*>/);
  const timestamp = suiteMatch ? suiteMatch[1] : null;

  const caseRe = /<testcase\b([^>]*?)(\/>|>([\s\S]*?)<\/testcase>)/g;
  const attrRe = /(\w+)="([^"]*)"/g;

  const cases: JunitCase[] = [];
  let match: RegExpExecArray | null;
  while ((match = caseRe.exec(xml)) !== null) {
    const attrsStr = match[1];
    const inner = match[3] ?? "";
    const attrs: Record<string, string> = {};
    let am: RegExpExecArray | null;
    attrRe.lastIndex = 0;
    while ((am = attrRe.exec(attrsStr)) !== null) {
      attrs[am[1]] = am[2];
    }
    let status: JunitCase["status"] = "passed";
    let message: string | undefined;
    if (/<skipped\b/.test(inner)) {
      status = "skipped";
    } else if (/<failure\b/.test(inner)) {
      status = "failed";
      const msgMatch = inner.match(/<failure\b[^>]*message="([^"]*)"/);
      message = msgMatch ? msgMatch[1] : undefined;
    }
    cases.push({
      classname: attrs.classname ?? "",
      name: attrs.name ?? "",
      category: categoryFromClassname(attrs.classname ?? ""),
      time: parseFloat(attrs.time ?? "0"),
      status,
      message,
    });
  }

  const categories: JunitSummary["categories"] = {};
  for (const c of cases) {
    const bucket = (categories[c.category] ??= { total: 0, passed: 0, failed: 0, skipped: 0, duration_s: 0 });
    bucket.total += 1;
    bucket.duration_s += c.time;
    if (c.status === "passed") bucket.passed += 1;
    else if (c.status === "failed") bucket.failed += 1;
    else bucket.skipped += 1;
  }

  return {
    total: cases.length,
    passed: cases.filter((c) => c.status === "passed").length,
    failed: cases.filter((c) => c.status === "failed").length,
    skipped: cases.filter((c) => c.status === "skipped").length,
    duration_s: cases.reduce((sum, c) => sum + c.time, 0),
    timestamp,
    cases,
    categories,
  };
}

function which(bin: string): string | null {
  try {
    const out = execSync(`command -v ${bin}`, { shell: "/bin/bash" }).toString().trim();
    return out || null;
  } catch {
    return null;
  }
}

export function getDoctorChecks(): DoctorCheck[] {
  const checks: DoctorCheck[] = [];
  const tools: [string, string][] = [
    ["qemu-system-aarch64", "QEMU ARM64 system emulator"],
    ["aarch64-linux-gnu-gcc", "AArch64 cross-compiler"],
    ["dtc", "device-tree-compiler"],
    ["git", "git"],
    ["make", "make"],
  ];
  for (const [bin, desc] of tools) {
    const p = which(bin);
    checks.push({ label: `${bin} (${desc})`, ok: !!p, detail: p ?? "not found on PATH" });
  }

  const artifacts: [string, string][] = [
    ["TF-A source", "firmware/tf-a/src"],
    ["U-Boot source", "firmware/u-boot/src"],
    ["Linux source", "firmware/linux/src"],
    ["BL1 (bl1.bin)", "qemu/images/bl1.bin"],
    ["Combined bios (flash.bin)", "qemu/images/flash.bin"],
    ["U-Boot (u-boot.bin)", "qemu/images/u-boot.bin"],
    ["Kernel Image", "qemu/images/Image"],
    ["DTB (virt.dtb)", "qemu/images/virt.dtb"],
    ["Initramfs", "qemu/images/initramfs.cpio.gz"],
  ];
  for (const [label, rel] of artifacts) {
    const full = path.join(REPO_ROOT, rel);
    checks.push({ label, ok: fs.existsSync(full), detail: rel });
  }

  return checks;
}

export function getFirmwareVersions(): { name: string; version: string }[] {
  const repos: [string, string][] = [
    ["TF-A", "tf-a"],
    ["U-Boot", "u-boot"],
    ["Linux", "linux"],
  ];
  const out: { name: string; version: string }[] = [];
  for (const [name, dir] of repos) {
    const srcDir = path.join(FIRMWARE_DIR, dir, "src");
    let version = "not fetched";
    if (fs.existsSync(srcDir)) {
      try {
        version = execSync(`git -C "${srcDir}" describe --tags --always`, { shell: "/bin/bash" })
          .toString()
          .trim();
      } catch {
        version = "unknown";
      }
    }
    out.push({ name, version });
  }
  return out;
}

export function getLiveStatus(): LiveStatus {
  let pid: number | null = null;
  let command: string | null = null;
  try {
    const out = execSync("pgrep -f qemu-system-aarch64", { shell: "/bin/bash" }).toString().trim();
    const pids = out.split("\n").filter(Boolean);
    if (pids.length > 0) {
      pid = parseInt(pids[0], 10);
      try {
        const cmdline = fs.readFileSync(`/proc/${pid}/cmdline`, "utf-8");
        command = cmdline.split("\0").filter(Boolean).join(" ");
      } catch {
        command = null;
      }
    }
  } catch {
    pid = null;
  }

  const ids = listRunIds();
  const latestRunId = ids[0] ?? null;
  let tail: string[] = [];
  if (pid !== null && latestRunId) {
    const logPath = path.join(RUNS_DIR, latestRunId, "qemu.log");
    if (fs.existsSync(logPath)) {
      const raw = fs.readFileSync(logPath, "utf-8");
      tail = raw.split("\n").slice(-40);
    }
  }

  return { active: pid !== null, pid, command, latestRunId: pid !== null ? latestRunId : null, tail };
}

export function getStageEventsForLatestBoot(): { runId: string; events: BootEvent[] } | null {
  const ids = listRunIds();
  for (const id of ids) {
    const detail = getRunDetail(id);
    if (detail?.result?.timeline?.events?.length) {
      return { runId: id, events: detail.result.timeline.events };
    }
  }
  return null;
}

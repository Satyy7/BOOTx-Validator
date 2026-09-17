import { NextResponse } from "next/server";
import { getDoctorChecks, getFirmwareVersions, listRunSummaries, parseJunit } from "@/lib/data";
import type { SummaryResponse } from "@/lib/types";

export async function GET() {
  const junit = parseJunit();
  const runs = listRunSummaries(1);
  const doctor = getDoctorChecks();
  const firmwareVersions = getFirmwareVersions();

  const body: SummaryResponse = {
    junit,
    latestRun: runs[0] ?? null,
    runCount: listRunSummaries().length,
    doctor,
    firmwareVersions,
  };

  return NextResponse.json(body);
}

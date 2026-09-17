import { NextResponse } from "next/server";
import { listRunSummaries } from "@/lib/data";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const limitParam = searchParams.get("limit");
  const limit = limitParam ? parseInt(limitParam, 10) : undefined;
  return NextResponse.json(listRunSummaries(limit));
}

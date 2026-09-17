import { NextResponse } from "next/server";
import { getLiveStatus } from "@/lib/data";

export async function GET() {
  return NextResponse.json(getLiveStatus());
}

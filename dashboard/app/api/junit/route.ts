import { NextResponse } from "next/server";
import { parseJunit } from "@/lib/data";

export async function GET() {
  const junit = parseJunit();
  if (!junit) {
    return NextResponse.json({ error: "no junit.xml found; run `bootx test` first" }, { status: 404 });
  }
  return NextResponse.json(junit);
}

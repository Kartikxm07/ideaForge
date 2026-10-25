import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  const token = process.env.RAGNAROK_API_TOKEN;
  if (!token) return NextResponse.json({ error: "Backend token is not configured on the frontend server." }, { status: 503 });
  const base = process.env.RAGNAROK_API_URL ?? "http://127.0.0.1:8000";
  let origin: URL;
  try {
    origin = new URL(base);
    if (origin.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(origin.hostname)) throw new Error();
  } catch {
    return NextResponse.json({ error: "Backend URL must be a local HTTP address." }, { status: 503 });
  }
  const checkpoint = request.nextUrl.searchParams.get("checkpoint") ?? "2027-03-15";
  if (!/^\d{4}-\d{2}-\d{2}$/.test(checkpoint)) return NextResponse.json({ error: "Invalid checkpoint date." }, { status: 400 });
  try {
    const upstream = await fetch(new URL(`/api/v1/odin/overview?checkpoint=${checkpoint}`, origin), {
      headers: { Authorization: `Bearer ${token}` }, cache: "no-store", signal: AbortSignal.timeout(10000),
    });
    if (!upstream.ok) return NextResponse.json({ error: upstream.status === 401 ? "Backend authentication failed." : `Backend returned ${upstream.status}.` }, { status: upstream.status });
    return NextResponse.json(await upstream.json(), { headers: { "Cache-Control": "no-store" } });
  } catch {
    return NextResponse.json({ error: "Backend is unavailable. Start the local API and retry." }, { status: 503 });
  }
}

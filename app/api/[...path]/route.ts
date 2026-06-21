// ############################################################################
// AI_HEADER: MODULE_API_MOCK_CATCHALL
// ROLE: Next.js route handler — sandbox/preview mock backend.
//   In production this app proxies /api/* to a FastAPI backend (apps/api).
//   In the sandbox we have no Python backend, so this catch-all serves
//   demo data sourced from lib/demo-data.ts. When NEXT_PUBLIC_DEMO_MODE=true
//   the client bypasses most of these calls entirely; this handler covers
//   the remaining server-side and edge-case fetches (e.g. useOnboarded
//   polls GET /api/profile directly, layout ships POST /api/_log, etc.).
// DEPENDENCIES: lib/demo-data
// ############################################################################

import { NextRequest, NextResponse } from "next/server";
import {
  DEMO_TODAY_RESPONSE,
  DEMO_CALENDAR_RESPONSE,
  DEMO_PROFILE,
  DEMO_NATAL_PREVIEW,
  DEMO_NATAL_RESPONSE,
  DEMO_HORARY_QUOTA,
  DEMO_HORARY_QUESTIONS,
  DEMO_CITIES,
  DEMO_CHAT_MESSAGES,
  DEMO_ACCESS,
} from "@/lib/demo-data";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const DEMO_USER_ID = "demo-00000000";
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Credentials": "true",
  "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,PATCH,OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

function json(body: unknown, status = 200) {
  return NextResponse.json(body, { status, headers: CORS });
}

function setSessionCookie(res: NextResponse) {
  res.cookies.set("grace_session_v2", `demo-session-${Date.now()}`, {
    httpOnly: true,
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30,
  });
  return res;
}

export async function OPTIONS() {
  return new NextResponse(null, { status: 204, headers: CORS });
}

export async function GET(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> }
) {
  const { path: segments } = await ctx.params;
  const path = segments.join("/");
  const url = new URL(req.url);
  const q = url.searchParams;

  // ── Profile ──────────────────────────────────────────────
  if (path === "profile") {
    return json({
      ...DEMO_PROFILE,
      isOnboarded: true,
      userId: DEMO_USER_ID,
      displayName: "Астролюбитель",
      username: "demo_astro",
      referralCode: "DEMO123",
    });
  }

  // ── Day (Today) ──────────────────────────────────────────
  if (path.startsWith("day/")) {
    return json(DEMO_TODAY_RESPONSE);
  }
  if (path === "today") {
    return json(DEMO_TODAY_RESPONSE);
  }

  // ── Calendar ─────────────────────────────────────────────
  if (path === "calendar") {
    const month = q.get("month");
    return json({
      ...DEMO_CALENDAR_RESPONSE,
      month: month || (DEMO_CALENDAR_RESPONSE as any).month,
    });
  }

  // ── Horary ───────────────────────────────────────────────
  if (path === "horary/quota") {
    return json(DEMO_HORARY_QUOTA);
  }
  if (path === "horary/questions") {
    const limit = Number(q.get("limit") || 20);
    const offset = Number(q.get("offset") || 0);
    return json((DEMO_HORARY_QUESTIONS as any[]).slice(offset, offset + limit));
  }
  if (path.startsWith("horary/questions/")) {
    const id = path.split("/")[2];
    const found = (DEMO_HORARY_QUESTIONS as any[]).find((x) => String(x.id) === String(id));
    return json(found ?? null, found ? 200 : 404);
  }

  // ── Natal ────────────────────────────────────────────────
  if (path === "natal/preview") {
    return json({ ok: true, data: DEMO_NATAL_PREVIEW });
  }
  if (path === "natal/reports") {
    return json({ items: [] });
  }
  if (path.startsWith("natal/report/")) {
    return json({
      id: path.split("/")[2],
      status: "ready",
      generatedAt: new Date().toISOString(),
      preview: DEMO_NATAL_PREVIEW,
      sections: [],
      payload: DEMO_NATAL_RESPONSE,
    });
  }

  // ── Chat ─────────────────────────────────────────────────
  if (path === "chat/threads") {
    return json({ threadId: `demo-thread-${Date.now()}`, messages: DEMO_CHAT_MESSAGES });
  }
  if (path.startsWith("chat/threads/") && path.endsWith("/messages")) {
    return json({
      messageId: `demo-msg-${Date.now()}`,
      role: "assistant",
      text: "Это демо-ответ ассистента. В реальном режиме здесь будет живой разбор от астролога-ИИ.",
      createdAt: new Date().toISOString(),
    });
  }

  // ── Geo ──────────────────────────────────────────────────
  if (path === "geo/autocomplete") {
    const query = (q.get("q") || "").toLowerCase();
    const limit = Number(q.get("limit") || 8);
    const filtered = query
      ? (DEMO_CITIES as any[]).filter(
          (c) =>
            c.name.toLowerCase().includes(query) ||
            (c.country || "").toLowerCase().includes(query)
        )
      : DEMO_CITIES;
    return json(filtered.slice(0, limit));
  }
  if (path === "geo/timezone") {
    return json({ timezone: "Europe/Moscow", offsetMinutes: 180 });
  }

  // ── Check-in ─────────────────────────────────────────────
  if (path === "checkin/yesterday") {
    const d = new Date();
    d.setDate(d.getDate() - 1);
    return json({
      date: d.toISOString().split("T")[0],
      mood: "calm",
      energy: 4,
      note: "Вчера был спокойный день.",
      submittedAt: d.toISOString(),
    });
  }
  if (path.startsWith("checkin/")) {
    const date = path.split("/")[1];
    return json({ date, mood: null, energy: null, note: "" });
  }
  if (path === "checkin") {
    return json({ items: [] });
  }

  // ── Payment / Subscription ───────────────────────────────
  if (path === "payment/subscription/status") {
    return json({ active: false, expiresAt: null, plan: null });
  }
  if (path === "payment/subscription") {
    return json({ active: false, expiresAt: null, plan: null });
  }

  // ── Referral ─────────────────────────────────────────────
  if (path === "referral") {
    return json({
      code: "DEMO123",
      referralUrl: "/?tgWebAppStartParam=DEMO123",
      referrals: 0,
      bonusDays: 0,
      history: [],
    });
  }

  // ── Access ───────────────────────────────────────────────
  if (path === "access") {
    return json(DEMO_ACCESS);
  }

  // ── Default ──────────────────────────────────────────────
  return json({ ok: true, demo: true, path, message: "Mock catch-all (demo mode)" });
}

export async function POST(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> }
) {
  const { path: segments } = await ctx.params;
  const path = segments.join("/");
  let body: any = {};
  try {
    body = await req.json().catch(() => ({}));
  } catch {
    body = {};
  }

  // ── Logging endpoint (layout error-catcher) ──────────────
  if (path === "_log") {
    return json({ ok: true });
  }

  // ── Auth ─────────────────────────────────────────────────
  if (path === "auth/dev") {
    const res = json({ ok: true, userId: DEMO_USER_ID, sessionId: `demo-session-${Date.now()}` });
    setSessionCookie(res);
    return res;
  }
  if (path === "auth/telegram") {
    const res = json({ ok: true, userId: DEMO_USER_ID, sessionId: `demo-session-${Date.now()}` });
    setSessionCookie(res);
    return res;
  }
  if (path === "auth/logout") {
    const res = json({ ok: true });
    res.cookies.delete("grace_session_v2");
    return res;
  }

  // ── Profile ──────────────────────────────────────────────
  if (path === "profile") {
    return json({ ...DEMO_PROFILE, ...body, isOnboarded: true, userId: DEMO_USER_ID });
  }

  // ── Check-in submit ──────────────────────────────────────
  if (path === "checkin") {
    return json({ ok: true, submittedAt: new Date().toISOString(), ...body });
  }

  // ── Horary: create question ──────────────────────────────
  if (path === "horary/questions") {
    return json({
      id: `hq-demo-${Date.now()}`,
      text: body.text ?? "",
      category: body.category ?? null,
      status: "processing",
      spentCreditSource: "paid",
      creditRefunded: false,
      clientTimezone: body.clientTimezone ?? "Europe/Moscow",
      clientLocalTime: body.clientLocalTime ?? null,
      questionLocationName: body.questionLocationName ?? null,
      createdAt: new Date().toISOString(),
      answer: null,
    });
  }

  // ── Natal ────────────────────────────────────────────────
  if (path === "natal/preview") {
    return json({ ok: true, data: DEMO_NATAL_PREVIEW });
  }
  if (path === "natal/generate") {
    return json({
      ok: true,
      reportId: "demo",
      status: "generating",
      estimatedSeconds: 30,
    });
  }

  // ── Chat ─────────────────────────────────────────────────
  if (path === "chat/threads") {
    return json({ threadId: `demo-thread-${Date.now()}`, messages: [] });
  }
  if (path.startsWith("chat/threads/") && path.endsWith("/messages")) {
    return json({
      messageId: `demo-msg-${Date.now()}`,
      role: "assistant",
      text: "Это демо-ответ ассистента. В реальном режиме здесь будет живой разбор от астролога-ИИ.",
      createdAt: new Date().toISOString(),
    });
  }

  // ── Payment ──────────────────────────────────────────────
  if (path === "payment/subscription/start" || path === "payment/purchase/start") {
    return json({
      ok: true,
      confirmationUrl: "/profile",
      paymentId: `demo-pay-${Date.now()}`,
      status: "pending",
    });
  }

  // ── Referral claim ───────────────────────────────────────
  if (path === "referral/claim") {
    return json({ ok: true, bonusDays: 14, claimedAt: new Date().toISOString() });
  }

  // ── Default ──────────────────────────────────────────────
  return json({ ok: true, demo: true, path, received: body });
}

export async function PUT(
  req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> }
) {
  const { path: segments } = await ctx.params;
  const path = segments.join("/");
  let body: any = {};
  try {
    body = await req.json().catch(() => ({}));
  } catch {
    body = {};
  }

  if (path === "profile") {
    return json({ ...DEMO_PROFILE, ...body, isOnboarded: true, userId: DEMO_USER_ID });
  }

  return json({ ok: true, demo: true, path, received: body });
}

export async function DELETE(
  _req: NextRequest,
  ctx: { params: Promise<{ path: string[] }> }
) {
  const { path: segments } = await ctx.params;
  const path = segments.join("/");
  return json({ ok: true, demo: true, path, deleted: true });
}

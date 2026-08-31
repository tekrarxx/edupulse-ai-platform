import { NextResponse, type NextRequest } from "next/server";

// UX-level route gating only — presence of this cookie is not proof of a
// valid session (it could be expired/revoked), so this only avoids
// flashing a protected page before the client-side check redirects. The
// actual authorization decision is always made by the API against a
// verified access token (§15, §18) — nothing here is a security boundary.
//
// This is deliberately NOT the real refresh token cookie: that one is
// scoped server-side to Path=/auth on the API origin (§78 minimal
// exposure — the API never sends it to unrelated routes), so the
// browser never attaches it to a request for /dashboard on the web
// app's own origin and this check would always see it as absent. The
// API additionally sets this separate, non-sensitive, Path=/ cookie
// (see apps/api/app/api/routes/auth.py, _SESSION_HINT_COOKIE_NAME) with
// the same lifetime, carrying no session material, solely so this
// middleware has something to check.
const SESSION_HINT_COOKIE_NAME = "edupulse_session";
const PROTECTED_PATHS = ["/dashboard"];

export function middleware(request: NextRequest) {
  const isProtected = PROTECTED_PATHS.some((path) => request.nextUrl.pathname.startsWith(path));
  if (!isProtected) {
    return NextResponse.next();
  }

  const hasSessionCookie = request.cookies.has(SESSION_HINT_COOKIE_NAME);
  if (!hasSessionCookie) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*"],
};

import { NextResponse, type NextRequest } from "next/server";

// UX-level route gating only — presence of the refresh cookie is not proof
// of a valid session (it could be expired/revoked), so this only avoids
// flashing a protected page before the client-side check redirects. The
// actual authorization decision is always made by the API against a
// verified access token (§15, §18) — nothing here is a security boundary.
const REFRESH_COOKIE_NAME = "edupulse_refresh_token";
const PROTECTED_PATHS = ["/dashboard"];

export function middleware(request: NextRequest) {
  const isProtected = PROTECTED_PATHS.some((path) => request.nextUrl.pathname.startsWith(path));
  if (!isProtected) {
    return NextResponse.next();
  }

  const hasSessionCookie = request.cookies.has(REFRESH_COOKIE_NAME);
  if (!hasSessionCookie) {
    const loginUrl = new URL("/login", request.url);
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: ["/dashboard/:path*"],
};

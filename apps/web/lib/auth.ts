// Client-side auth API calls. All authorization logic that actually matters
// stays server-side (§15, §18) — this module only shapes requests/responses
// and never decides who is allowed to do what.

export type Role =
  | "SUPER_ADMIN"
  | "TENANT_ADMIN"
  | "SCHOOL_ADMIN"
  | "TEACHER"
  | "STUDENT"
  | "PARENT";

export type AuthUser = {
  id: string;
  tenant_id: string;
  email: string;
  display_name: string;
  role: Role;
  is_active: boolean;
};

export type TokenResponse = {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: AuthUser;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

class AuthApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function postAuth(path: string, body?: unknown): Promise<Response> {
  const response = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    // The refresh token only ever travels as an httpOnly cookie the browser
    // manages on its own — this is what makes that cookie actually get sent.
    credentials: "include",
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new AuthApiError(response.status, detail.detail ?? "request_failed");
  }
  return response;
}

export async function register(input: {
  email: string;
  password: string;
  display_name: string;
}): Promise<TokenResponse> {
  const response = await postAuth("/auth/register", input);
  return response.json();
}

export async function login(input: { email: string; password: string }): Promise<TokenResponse> {
  const response = await postAuth("/auth/login", input);
  return response.json();
}

export async function refreshSession(): Promise<TokenResponse> {
  const response = await postAuth("/auth/refresh");
  return response.json();
}

export async function logout(): Promise<void> {
  await postAuth("/auth/logout");
}

export async function fetchCurrentUser(accessToken: string): Promise<AuthUser> {
  const response = await fetch(`${API_URL}/auth/me`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    credentials: "include",
  });
  if (!response.ok) {
    throw new AuthApiError(response.status, "not_authenticated");
  }
  return response.json();
}

export { AuthApiError };

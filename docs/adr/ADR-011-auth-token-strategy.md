# ADR-011: Password Hashing & Token Strategy

Status: Accepted
Date: 2026-08-28
Related: CLAUDE.md §78, §53

## Context

Phase 2 needs a password hashing algorithm and a session/token strategy that
supports real logout (revocation), not just client-side token deletion.

## Decision

### Password hashing: Argon2id (`argon2-cffi`)

OWASP's current recommendation for password storage, actively maintained,
memory-hard (resists GPU/ASIC cracking better than bcrypt). Considered and
rejected: `passlib[bcrypt]` — bcrypt itself remains secure, but the
`passlib` library has had no release since 2020; taking a dependency on an
unmaintained package for a security-critical primitive was judged the wrong
tradeoff even though it's a more common FastAPI-tutorial choice.

### Tokens: short-lived JWT access token + opaque, revocable refresh token

- **Access token**: JWT (HS256, `pyjwt`), 15-minute TTL, returned in the
  response body. Contains `sub` (user id), `tenant_id`, `role`, `jti`, `iat`,
  `exp`. Never stored server-side — validity is purely cryptographic and
  time-bound, which is fine given the short TTL.
- **Refresh token**: a random 48-byte value (`secrets.token_urlsafe`), never
  itself a JWT. The client only ever holds the raw value, delivered via an
  **httpOnly, samesite=lax, secure-in-production** cookie scoped to
  `/auth/*`. The server stores only its SHA-256 hash in `user_sessions`, so a
  stolen database row cannot be replayed as a live session token, and a
  stolen cookie is invisible to JavaScript (mitigates XSS token theft, §80,
  §81 minor-safety consideration).
- **Rotation**: every `/auth/refresh` call revokes the presented refresh
  token and issues a new one. This bounds how long a leaked refresh token
  remains useful and lets reuse-detection be added later without a schema
  change.
- **Revocation**: `/auth/logout` sets `revoked_at` on the session row. A
  stateless-JWT-only refresh design was rejected specifically because it
  cannot support this — a "logged out" refresh JWT would remain valid until
  its expiry.

### Role model: one role per user (this phase)

`users.role` is a single enum column (§53's six roles). A person acting in
two capacities (e.g. parent and teacher) needs two accounts until multi-role
support is explicitly designed as its own slice — the six roles are not
combined or layered. Documented here rather than left implicit so it isn't
mistaken for an oversight later.

## Alternatives Considered

- **Stateless JWT refresh tokens (no DB row)**: simpler, but no real logout —
  rejected for a product with minors as users (§81).
- **Session-only auth (no access/refresh split)**: simpler still, but couples
  every request to a DB lookup and loses the standard access/refresh
  separation that makes short-TTL access tokens practical.
- **bcrypt via `passlib`**: see above.

## Consequences

- `API_SECRET_KEY` (`.env`) signs access tokens; rotating it invalidates
  every outstanding access token immediately (refresh tokens are unaffected
  since they are not JWTs).
- `user_sessions` grows one row per login/refresh; a cleanup job for expired
  rows is deferred to Phase 11 (§94 background jobs) — not needed at
  current/expected local-dev and pilot scale.
- Any future admin-triggered "log this user out everywhere" feature can be
  built by revoking all of a user's sessions — the data model already
  supports it.

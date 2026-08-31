"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { AuthApiError, useAuth } from "@/lib/auth-context";
import { AuthShell } from "@/components/marketing/auth-shell";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      // Same generic message the API returns — never hint at which field
      // was wrong (§90).
      setError(err instanceof AuthApiError ? "E-posta veya şifre hatalı." : "Bir şeyler ters gitti.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell>
      <div>
        <h1 className="text-2xl font-semibold">Giriş yap</h1>
        <p className="text-sm text-muted">EduPulse AI hesabınla devam et.</p>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm">
          E-posta
          <input
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-md border border-border px-3 py-2 focus:border-primary focus:outline-none"
            autoComplete="email"
          />
        </label>
        <div className="flex flex-col gap-1 text-sm">
          <span className="flex items-center justify-between">
            <label htmlFor="login-password">Şifre</label>
            <a href="/forgot-password" className="text-xs font-normal text-primary underline">
              Şifremi unuttum
            </a>
          </span>
          <input
            id="login-password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-md border border-border px-3 py-2 focus:border-primary focus:outline-none"
            autoComplete="current-password"
          />
        </div>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60"
        >
          {submitting ? "Giriş yapılıyor…" : "Giriş yap"}
        </button>
      </form>

      <p className="mt-6 text-sm text-muted">
        Hesabın yok mu?{" "}
        <a href="/register" className="font-medium text-primary underline">
          Kayıt ol
        </a>
      </p>
    </AuthShell>
  );
}

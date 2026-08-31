"use client";

import { Suspense, useState, type FormEvent } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AuthApiError, confirmPasswordReset } from "@/lib/auth";
import { AuthShell } from "@/components/marketing/auth-shell";

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={null}>
      <ResetPasswordForm />
    </Suspense>
  );
}

function ResetPasswordForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;
    setError(null);
    setSubmitting(true);
    try {
      await confirmPasswordReset({ token, new_password: newPassword });
      setDone(true);
    } catch (err) {
      // §90: same generic message regardless of why the token was rejected
      // (expired, already used, or never existed).
      setError(
        err instanceof AuthApiError
          ? "Bu bağlantı geçersiz veya süresi dolmuş. Yeni bir sıfırlama bağlantısı iste."
          : "Bir şeyler ters gitti."
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (!token) {
    return (
      <AuthShell>
        <h1 className="text-2xl font-semibold">Geçersiz bağlantı</h1>
        <p className="mt-2 text-sm text-muted">
          Bu sayfaya doğrudan gelinmez — e-postandaki sıfırlama bağlantısını kullanmalısın.
        </p>
        <p className="mt-6 text-sm text-muted">
          <a href="/forgot-password" className="font-medium text-primary underline">
            Yeni bağlantı iste
          </a>
        </p>
      </AuthShell>
    );
  }

  if (done) {
    return (
      <AuthShell>
        <h1 className="text-2xl font-semibold">Şifren güncellendi</h1>
        <p className="mt-2 text-sm text-muted">Yeni şifrenle giriş yapabilirsin.</p>
        <button
          onClick={() => router.push("/login")}
          className="mt-6 w-fit rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          Girişe dön
        </button>
      </AuthShell>
    );
  }

  return (
    <AuthShell>
      <div>
        <h1 className="text-2xl font-semibold">Yeni şifre belirle</h1>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm">
          Yeni şifre
          <input
            type="password"
            required
            minLength={10}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="rounded-md border border-border px-3 py-2 focus:border-primary focus:outline-none"
            autoComplete="new-password"
          />
          <span className="text-xs text-muted">En az 10 karakter.</span>
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60"
        >
          {submitting ? "Kaydediliyor…" : "Şifreyi güncelle"}
        </button>
      </form>
    </AuthShell>
  );
}

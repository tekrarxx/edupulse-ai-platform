"use client";

import { useState, type FormEvent } from "react";
import { requestPasswordReset } from "@/lib/auth";
import { AuthShell } from "@/components/marketing/auth-shell";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    try {
      await requestPasswordReset(email);
    } catch {
      // Deliberately ignored: the confirmation below is shown unconditionally,
      // on success or failure alike (§90) — the UI must not reveal whether
      // the email address is registered, or whether sending happened to fail.
    } finally {
      setSubmitting(false);
      setSubmitted(true);
    }
  }

  if (submitted) {
    return (
      <AuthShell>
        <h1 className="text-2xl font-semibold">E-postanı kontrol et</h1>
        <p className="mt-2 text-sm text-muted">
          Bu e-posta bir hesaba aitse, şifreni sıfırlaman için bir bağlantı gönderdik. Bağlantı 1 saat
          geçerlidir.
        </p>
        <p className="mt-6 text-sm text-muted">
          <a href="/login" className="font-medium text-primary underline">
            Girişe dön
          </a>
        </p>
      </AuthShell>
    );
  }

  return (
    <AuthShell>
      <div>
        <h1 className="text-2xl font-semibold">Şifremi unuttum</h1>
        <p className="text-sm text-muted">E-posta adresini gir, sana bir sıfırlama bağlantısı gönderelim.</p>
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

        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-60"
        >
          {submitting ? "Gönderiliyor…" : "Sıfırlama bağlantısı gönder"}
        </button>
      </form>

      <p className="mt-6 text-sm text-muted">
        <a href="/login" className="font-medium text-primary underline">
          Girişe dön
        </a>
      </p>
    </AuthShell>
  );
}

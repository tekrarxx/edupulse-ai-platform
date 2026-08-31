"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { register } from "@/lib/auth";
import { AuthShell } from "@/components/marketing/auth-shell";

export default function RegisterPage() {
  const router = useRouter();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register({ email, password, display_name: displayName });
      router.push("/login");
    } catch {
      setError("Kayıt tamamlanamadı. E-posta zaten kullanılıyor olabilir veya şifre çok kısa.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AuthShell>
      <div>
        <h1 className="text-2xl font-semibold">Hesap oluştur</h1>
        <p className="text-sm text-muted">Birkaç saniyede başla, kredi kartı gerekmez.</p>
      </div>

      <form onSubmit={handleSubmit} className="mt-6 flex flex-col gap-4">
        <label className="flex flex-col gap-1 text-sm">
          Ad Soyad
          <input
            required
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            className="rounded-md border border-border px-3 py-2 focus:border-primary focus:outline-none"
            autoComplete="name"
          />
        </label>
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
        <label className="flex flex-col gap-1 text-sm">
          Şifre
          <input
            type="password"
            required
            minLength={10}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
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
          {submitting ? "Oluşturuluyor…" : "Hesap oluştur"}
        </button>
      </form>

      <p className="mt-6 text-sm text-muted">
        Zaten hesabın var mı?{" "}
        <a href="/login" className="font-medium text-primary underline">
          Giriş yap
        </a>
      </p>
    </AuthShell>
  );
}

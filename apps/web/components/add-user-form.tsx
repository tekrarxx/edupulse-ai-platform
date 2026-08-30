"use client";

import { useState } from "react";
import { createTenantUser, type Role } from "@/lib/auth";

// Only the roles a *tenant-scoped* admin might plausibly need to create
// through this form — SUPER_ADMIN is deliberately excluded here even
// though the backend's creation matrix allows a SUPER_ADMIN caller to
// create one; that is a rare enough operation to not need a one-click form.
const _CREATABLE_ROLES: Role[] = ["STUDENT", "TEACHER", "PARENT", "SCHOOL_ADMIN"];

const _ROLE_LABELS: Record<Role, string> = {
  STUDENT: "Öğrenci",
  TEACHER: "Öğretmen",
  PARENT: "Veli",
  SCHOOL_ADMIN: "Okul Yöneticisi",
  TENANT_ADMIN: "Kurum Yöneticisi",
  SUPER_ADMIN: "Süper Yönetici",
};

export function AddUserForm({ accessToken, onCreated }: { accessToken: string; onCreated: () => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState<Role>("STUDENT");
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);
    setSubmitting(true);
    try {
      await createTenantUser(accessToken, { email, password, display_name: displayName, role });
      setSuccessMessage(`${_ROLE_LABELS[role]} hesabı oluşturuldu: ${email}`);
      setEmail("");
      setPassword("");
      setDisplayName("");
      onCreated();
    } catch {
      // §90: never surface the backend's raw detail string (e.g. a
      // duplicate-email or role-escalation reason) as anything but a
      // single, generic, actionable message.
      setError("Kullanıcı oluşturulamadı. E-posta zaten kayıtlı olabilir veya bu rolü oluşturma yetkiniz olmayabilir.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3 rounded-md border border-border p-4">
      <h2 className="text-lg font-medium">Kullanıcı Ekle</h2>

      {error && <p className="text-sm text-red-700">{error}</p>}
      {successMessage && <p className="text-sm text-green-700">{successMessage}</p>}

      <label className="flex flex-col gap-1 text-sm">
        Ad Soyad
        <input
          type="text"
          required
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className="rounded-md border border-border px-3 py-2"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        E-posta
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="rounded-md border border-border px-3 py-2"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        Geçici Şifre
        <input
          type="password"
          required
          minLength={10}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="rounded-md border border-border px-3 py-2"
        />
      </label>

      <label className="flex flex-col gap-1 text-sm">
        Rol
        <select value={role} onChange={(e) => setRole(e.target.value as Role)} className="rounded-md border border-border px-3 py-2">
          {_CREATABLE_ROLES.map((r) => (
            <option key={r} value={r}>
              {_ROLE_LABELS[r]}
            </option>
          ))}
        </select>
      </label>

      <button
        type="submit"
        disabled={submitting}
        className="mt-2 w-fit rounded-md border border-border px-4 py-2 text-sm disabled:opacity-50"
      >
        {submitting ? "Oluşturuluyor..." : "Oluştur"}
      </button>
    </form>
  );
}

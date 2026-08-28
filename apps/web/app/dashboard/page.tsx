"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/lib/auth-context";

export default function DashboardPage() {
  const { user, status, logout } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  if (status !== "authenticated" || !user) {
    return null;
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold">Merhaba, {user.display_name}</h1>
      <p className="text-sm text-muted">
        Rol: {user.role} — Faz 2 (Identity/Tenant/RBAC) placeholder&apos;ı. Gerçek öğrenci panosu Faz 9&apos;da geliyor.
      </p>
      <button
        onClick={() => logout().then(() => router.push("/login"))}
        className="w-fit rounded-md border border-border px-4 py-2 text-sm"
      >
        Çıkış yap
      </button>
    </main>
  );
}

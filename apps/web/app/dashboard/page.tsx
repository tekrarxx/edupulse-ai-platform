"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { fetchStudentDashboard, type StudentDashboard } from "@/lib/dashboard";
import { SkillProgressCard } from "@/components/skill-progress-card";

const _ADMIN_ROLES = new Set(["SCHOOL_ADMIN", "TENANT_ADMIN", "SUPER_ADMIN"]);

export default function DashboardPage() {
  const { user, accessToken, status, logout } = useAuth();
  const router = useRouter();
  const [dashboard, setDashboard] = useState<StudentDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    } else if (status === "authenticated" && user?.role === "TEACHER") {
      // This route renders the student view; a teacher has their own
      // aggregate page (§76) rather than a single-student one.
      router.replace("/dashboard/teacher");
    } else if (status === "authenticated" && user && _ADMIN_ROLES.has(user.role)) {
      // Tenant/school/super admins have their own aggregate page (§77).
      router.replace("/dashboard/admin");
    }
  }, [status, user, router]);

  useEffect(() => {
    if (status === "authenticated" && accessToken && user?.role !== "TEACHER" && user && !_ADMIN_ROLES.has(user.role)) {
      fetchStudentDashboard(accessToken)
        .then(setDashboard)
        .catch(() => setError("Panonuz yüklenirken bir sorun oluştu."));
    }
  }, [status, accessToken, user]);

  if (status !== "authenticated" || !user || user.role === "TEACHER" || _ADMIN_ROLES.has(user.role)) {
    return null;
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-2xl flex-col gap-6 p-8">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Merhaba, {user.display_name}</h1>
        <button
          onClick={() => logout().then(() => router.push("/login"))}
          className="w-fit rounded-md border border-border px-4 py-2 text-sm"
        >
          Çıkış yap
        </button>
      </div>

      {error && <p className="text-sm text-red-700">{error}</p>}

      {dashboard && (
        <>
          <div className="flex gap-4 text-sm text-muted">
            <span>{dashboard.strong_skill_count} güçlü konu</span>
            <span>{dashboard.weak_skill_count} çalışılması gereken konu</span>
            <span>{dashboard.upcoming_retention_count} yaklaşan hatırlama kontrolü</span>
          </div>

          {dashboard.skills.length === 0 ? (
            <p className="text-sm text-muted">
              Henüz bir konu üzerinde çalışmadın. Bir soru çözdüğünde burada ilerlemeni göreceksin.
            </p>
          ) : (
            <div className="flex flex-col gap-3">
              {accessToken &&
                dashboard.skills.map((skill) => (
                  <SkillProgressCard key={skill.skill_id} skill={skill} accessToken={accessToken} />
                ))}
            </div>
          )}
        </>
      )}
    </main>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { fetchAdminDashboard, type AdminDashboard } from "@/lib/dashboard";
import { AddUserForm } from "@/components/add-user-form";
import { DashboardShell } from "@/components/dashboard-shell";

const _ADMIN_ROLES = new Set(["SCHOOL_ADMIN", "TENANT_ADMIN", "SUPER_ADMIN"]);

export default function AdminDashboardPage() {
  const { user, accessToken, status, logout } = useAuth();
  const router = useRouter();
  const [dashboard, setDashboard] = useState<AdminDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    } else if (status === "authenticated" && user && !_ADMIN_ROLES.has(user.role)) {
      // Only tenant/school/super admins have this view (§77).
      router.replace("/dashboard");
    }
  }, [status, user, router]);

  const reloadDashboard = () => {
    if (accessToken) {
      fetchAdminDashboard(accessToken)
        .then(setDashboard)
        .catch(() => setError("Pano yüklenirken bir sorun oluştu."));
    }
  };

  useEffect(() => {
    if (status === "authenticated" && accessToken && user && _ADMIN_ROLES.has(user.role)) {
      reloadDashboard();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, accessToken, user]);

  if (status !== "authenticated" || !user || !_ADMIN_ROLES.has(user.role)) {
    return null;
  }

  return (
    <DashboardShell title="Kurum Panosu" onLogout={() => logout().then(() => router.push("/login"))}>
      {error && <p className="text-sm text-red-700">{error}</p>}

      {accessToken && <AddUserForm accessToken={accessToken} onCreated={reloadDashboard} />}

      {dashboard && (
        <div className="flex flex-col gap-6">
          <section>
            <h2 className="text-lg font-medium">Plan: {dashboard.plan_name}</h2>
            <p className="mt-1 text-sm text-muted">
              Bu ay {dashboard.ai_explanations_used_this_month} AI açıklaması kullanıldı
              {dashboard.ai_explanations_monthly_limit !== null && ` / ${dashboard.ai_explanations_monthly_limit} limit`}
              {dashboard.ai_explanations_monthly_limit === null && " (sınırsız)"}.
            </p>
            <p className="mt-1 text-sm text-muted">
              {dashboard.tenant_user_count} kullanıcı
              {dashboard.tenant_user_limit !== null && ` / ${dashboard.tenant_user_limit} kullanıcı limiti`}
              {dashboard.tenant_user_limit === null && " (sınırsız)"}.
            </p>
          </section>

          <section className="grid grid-cols-2 gap-4">
            <Stat label="Aktif öğrenci" value={dashboard.active_student_count} />
            <Stat label="Aktif öğretmen" value={dashboard.active_teacher_count} />
            <Stat label="İlgi gerektiren öğrenci" value={dashboard.students_needing_attention_count} />
            <Stat label="Zayıf becerisi olan öğrenci" value={dashboard.weak_skill_student_count} />
            <Stat label="Unutma tespiti olan öğrenci" value={dashboard.forgetting_student_count} />
            <Stat label="Yanlış kavrama tespiti olan öğrenci" value={dashboard.misconception_student_count} />
          </section>

          <section>
            <h2 className="text-lg font-medium">Hatırlama kontrolleri</h2>
            <div className="mt-2 grid grid-cols-2 gap-4">
              <Stat label="Bekleyen" value={dashboard.retention_pending_count} />
              <Stat label="Doğrulandı" value={dashboard.retention_supported_count} />
              <Stat label="Doğrulanmadı" value={dashboard.retention_not_supported_count} />
              <Stat label="Belirsiz" value={dashboard.retention_inconclusive_count} />
            </div>
          </section>

          <section>
            <h2 className="text-lg font-medium">Prometheus kararları</h2>
            <div className="mt-2 grid grid-cols-2 gap-4">
              <Stat label="Toplam karar" value={dashboard.decisions_total_count} />
              <Stat label="Öğretmene yönlendirilen" value={dashboard.decisions_escalated_count} />
            </div>
          </section>

          <section>
            <h2 className="text-lg font-medium">Yapay zeka sistem sağlığı</h2>
            <div className="mt-2 grid grid-cols-2 gap-4">
              <Stat label="Toplam istek" value={dashboard.ai_requests_total_count} />
              <Stat label="Başarısız istek" value={dashboard.ai_requests_failed_count} />
            </div>
          </section>
        </div>
      )}
    </DashboardShell>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-border p-4">
      <p className="text-2xl font-semibold">{value}</p>
      <p className="text-sm text-muted">{label}</p>
    </div>
  );
}

"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { fetchTeacherDashboard, type TeacherDashboard } from "@/lib/dashboard";
import { StudentSummaryCard } from "@/components/student-summary-card";
import { DashboardShell } from "@/components/dashboard-shell";

export default function TeacherDashboardPage() {
  const { user, accessToken, status, logout } = useAuth();
  const router = useRouter();
  const [dashboard, setDashboard] = useState<TeacherDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    } else if (status === "authenticated" && user && user.role !== "TEACHER") {
      // Only a TEACHER has this view (§76) — everyone else goes to the
      // student dashboard, which itself redirects TEACHER here.
      router.replace("/dashboard");
    }
  }, [status, user, router]);

  useEffect(() => {
    if (status === "authenticated" && accessToken && user?.role === "TEACHER") {
      fetchTeacherDashboard(accessToken)
        .then(setDashboard)
        .catch(() => setError("Pano yüklenirken bir sorun oluştu."));
    }
  }, [status, accessToken, user]);

  if (status !== "authenticated" || !user || user.role !== "TEACHER") {
    return null;
  }

  return (
    <DashboardShell title="Öğrencilerim" onLogout={() => logout().then(() => router.push("/login"))}>
      {error && <p className="text-sm text-red-700">{error}</p>}

      {dashboard && (
        <>
          <p className="text-sm text-muted">{dashboard.students_needing_attention_count} öğrenci ilgi gerektiriyor.</p>

          {dashboard.students.length === 0 ? (
            <p className="text-sm text-muted">Henüz size bağlı bir öğrenci yok.</p>
          ) : (
            <div className="flex flex-col gap-3">
              {dashboard.students.map((student) => (
                <StudentSummaryCard key={student.student_user_id} student={student} />
              ))}
            </div>
          )}
        </>
      )}
    </DashboardShell>
  );
}

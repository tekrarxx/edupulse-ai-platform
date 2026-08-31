"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { fetchMyChildren, fetchStudentDashboard, type ParentChild, type StudentDashboard } from "@/lib/dashboard";
import { SkillProgressCard } from "@/components/skill-progress-card";
import { DashboardShell } from "@/components/dashboard-shell";

export default function ParentDashboardPage() {
  const { user, accessToken, status, logout } = useAuth();
  const router = useRouter();
  const [children, setChildren] = useState<ParentChild[] | null>(null);
  const [selectedChildId, setSelectedChildId] = useState<string | null>(null);
  const [childDashboard, setChildDashboard] = useState<StudentDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    } else if (status === "authenticated" && user && user.role !== "PARENT") {
      router.replace("/dashboard");
    }
  }, [status, user, router]);

  useEffect(() => {
    if (status === "authenticated" && accessToken && user?.role === "PARENT") {
      fetchMyChildren(accessToken)
        .then((list) => {
          setChildren(list);
          // A single-child parent shouldn't need to pick — go straight to
          // that child's dashboard, the common case for an individual tenant.
          if (list.length === 1) {
            setSelectedChildId(list[0].student_user_id);
          }
        })
        .catch(() => setError("Çocuklarınız yüklenirken bir sorun oluştu."));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, accessToken, user]);

  useEffect(() => {
    if (accessToken && selectedChildId) {
      fetchStudentDashboard(accessToken, selectedChildId)
        .then(setChildDashboard)
        .catch(() => setError("Pano yüklenirken bir sorun oluştu."));
    }
  }, [accessToken, selectedChildId]);

  if (status !== "authenticated" || !user || user.role !== "PARENT") {
    return null;
  }

  const selectedChild = children?.find((c) => c.student_user_id === selectedChildId) ?? null;

  return (
    <DashboardShell title="Veli Panosu" onLogout={() => logout().then(() => router.push("/login"))}>
      {error && <p className="text-sm text-red-700">{error}</p>}

      {children && children.length === 0 && (
        <p className="text-sm text-muted">Hesabınıza bağlı bir öğrenci bulunmuyor.</p>
      )}

      {children && children.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {children.map((child) => (
            <button
              key={child.student_user_id}
              onClick={() => {
                setChildDashboard(null);
                setSelectedChildId(child.student_user_id);
              }}
              className={`rounded-md border px-3 py-1.5 text-sm ${
                child.student_user_id === selectedChildId ? "border-primary font-medium text-primary" : "border-border"
              }`}
            >
              {child.display_name}
            </button>
          ))}
        </div>
      )}

      {selectedChild && !selectedChild.consent_on_file && (
        <p className="text-sm text-amber-800">
          Bu öğrenci için okul kaydında rıza onayı bulunmuyor — bazı öneriler öğretmen incelemesine yönlendirilebilir.
        </p>
      )}

      {selectedChildId && accessToken && childDashboard && (
        <div className="flex flex-col gap-6">
          <h2 className="text-lg font-medium">{selectedChild?.display_name}</h2>
          <div className="flex gap-4 text-sm text-muted">
            <span>{childDashboard.strong_skill_count} güçlü konu</span>
            <span>{childDashboard.weak_skill_count} çalışılması gereken konu</span>
            <span>{childDashboard.upcoming_retention_count} yaklaşan hatırlama kontrolü</span>
          </div>

          {childDashboard.skills.length === 0 ? (
            <p className="text-sm text-muted">Henüz bir konu üzerinde çalışma kaydı yok.</p>
          ) : (
            <div className="flex flex-col gap-3">
              {childDashboard.skills.map((skill) => (
                <SkillProgressCard key={skill.skill_id} skill={skill} accessToken={accessToken} />
              ))}
            </div>
          )}
        </div>
      )}
    </DashboardShell>
  );
}

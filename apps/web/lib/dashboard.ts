// Student dashboard API client. Mirrors lib/auth.ts's pattern: typed fetch
// functions only, no authorization logic — the backend (§51) is what
// actually decides who can see whose dashboard.

export type SkillProgress = {
  skill_id: string;
  skill_name: string;
  mastery_label: string;
  is_weak: boolean;
  is_strong: boolean;
  next_action_label: string | null;
  next_action_decision_id: string | null;
  pending_retention_checkpoints: number;
};

export type StudentDashboard = {
  student_user_id: string;
  skills: SkillProgress[];
  weak_skill_count: number;
  strong_skill_count: number;
  upcoming_retention_count: number;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchStudentDashboard(accessToken: string, studentId?: string): Promise<StudentDashboard> {
  // studentId lets a PARENT (or staff) fetch a specific linked child's
  // dashboard instead of the caller's own — the backend (§51) still
  // decides whether the caller is actually allowed to see that student.
  const url = studentId
    ? `${API_URL}/dashboard/student?student_id=${encodeURIComponent(studentId)}`
    : `${API_URL}/dashboard/student`;
  const response = await fetch(url, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error(`dashboard request failed with status ${response.status}`);
  }
  return response.json();
}

export type ParentChild = {
  student_user_id: string;
  display_name: string;
  consent_on_file: boolean;
};

export async function fetchMyChildren(accessToken: string): Promise<ParentChild[]> {
  const response = await fetch(`${API_URL}/auth/parent/children`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error(`parent children request failed with status ${response.status}`);
  }
  return response.json();
}

export type StudentSummary = {
  student_user_id: string;
  student_name: string;
  needs_attention: boolean;
  attention_reasons: string[];
  weak_skill_names: string[];
  improving_skill_names: string[];
  forgetting_skill_names: string[];
  misconception_skill_names: string[];
  next_action_label: string | null;
};

export type TeacherDashboard = {
  students: StudentSummary[];
  students_needing_attention_count: number;
};

export async function fetchTeacherDashboard(accessToken: string): Promise<TeacherDashboard> {
  const response = await fetch(`${API_URL}/dashboard/teacher`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error(`teacher dashboard request failed with status ${response.status}`);
  }
  return response.json();
}

export type AdminDashboard = {
  tenant_id: string;
  active_student_count: number;
  active_teacher_count: number;
  students_needing_attention_count: number;
  weak_skill_student_count: number;
  forgetting_student_count: number;
  misconception_student_count: number;
  escalated_student_count: number;
  retention_pending_count: number;
  retention_supported_count: number;
  retention_not_supported_count: number;
  retention_inconclusive_count: number;
  decisions_total_count: number;
  decisions_allowed_count: number;
  decisions_escalated_count: number;
  decisions_rejected_count: number;
  ai_requests_total_count: number;
  ai_requests_success_count: number;
  ai_requests_failed_count: number;
  plan_name: string;
  ai_explanations_used_this_month: number;
  ai_explanations_monthly_limit: number | null;
  tenant_user_count: number;
  tenant_user_limit: number | null;
};

export async function fetchAdminDashboard(accessToken: string): Promise<AdminDashboard> {
  const response = await fetch(`${API_URL}/dashboard/admin`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error(`admin dashboard request failed with status ${response.status}`);
  }
  return response.json();
}

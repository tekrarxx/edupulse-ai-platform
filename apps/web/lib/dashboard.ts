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

export async function fetchStudentDashboard(accessToken: string): Promise<StudentDashboard> {
  const response = await fetch(`${API_URL}/dashboard/student`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error(`dashboard request failed with status ${response.status}`);
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

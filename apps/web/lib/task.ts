// Execution layer client (§113 P8+). Two calls: fetch the real Question
// behind a Decision's selected_action, then submit the student's answer
// through the existing, unchanged POST /assessment/attempts — this module
// never grades anything itself, the backend already does (§26).

export type DecisionTask = {
  decision_id: string;
  skill_id: string;
  skill_name: string;
  selected_action: string;
  assessment_type: string;
  question_id: string;
  prompt: string;
  difficulty: number;
};

export type AttemptResult = {
  id: string;
  question_id: string;
  assessment_type: string;
  is_correct: boolean | null;
  evaluation_method: string | null;
  evaluation_confidence: number | null;
  submitted_at: string;
  evaluated_at: string | null;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class TaskApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function fetchDecisionTask(accessToken: string, decisionId: string): Promise<DecisionTask> {
  const response = await fetch(`${API_URL}/decisions/${encodeURIComponent(decisionId)}/task`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new TaskApiError(response.status, detail.detail ?? "task_request_failed");
  }
  return response.json();
}

export async function submitAttempt(
  accessToken: string,
  input: { question_id: string; assessment_type: string; learner_response: string }
): Promise<AttemptResult> {
  const response = await fetch(`${API_URL}/assessment/attempts`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({
      ...input,
      // A fresh key per submission, not per question — a retry of the same
      // click must reuse this key (§130), but a *second* attempt at the
      // same question later is a genuinely new attempt.
      idempotency_key: crypto.randomUUID(),
    }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new TaskApiError(response.status, detail.detail ?? "attempt_submission_failed");
  }
  return response.json();
}

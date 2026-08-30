// AI Gateway client (ADR-015). Mirrors lib/dashboard.ts's pattern: a typed
// fetch function only, no retry/caching logic here — the backend already
// owns retries (app/ai/providers/ollama.py) and this call can genuinely
// fail (§43: the LLM is a supporting component, never assumed available).

export type SkillExplanation = {
  skill_id: string;
  explanation: string;
  key_points: string[];
  provider: string;
  model: string;
  prompt_name: string;
  prompt_version: string;
  generated_at: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class AIRequestError extends Error {
  constructor(public status: number) {
    super(`ai request failed with status ${status}`);
  }
}

export async function fetchSkillExplanation(accessToken: string, skillId: string): Promise<SkillExplanation> {
  const response = await fetch(`${API_URL}/ai/explanations`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ skill_id: skillId }),
  });
  if (!response.ok) {
    throw new AIRequestError(response.status);
  }
  return response.json();
}

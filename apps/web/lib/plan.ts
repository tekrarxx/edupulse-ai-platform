// Self-service plan switching client (ROADMAP.md P2, ADR-016's own
// trigger). Mirrors lib/dashboard.ts's pattern.

export type Plan = {
  id: string;
  slug: string;
  name: string;
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class PlanApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function fetchPlans(accessToken: string): Promise<Plan[]> {
  const response = await fetch(`${API_URL}/plans`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new PlanApiError(response.status, "plans_request_failed");
  }
  return response.json();
}

export async function switchTenantPlan(accessToken: string, planSlug: string): Promise<Plan> {
  const response = await fetch(`${API_URL}/plans/tenant`, {
    method: "PUT",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ plan_slug: planSlug }),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new PlanApiError(response.status, detail.detail ?? "plan_switch_failed");
  }
  return response.json();
}

export type HealthResponse = {
  status: "ok" | "degraded";
  dependencies: {
    database: "ok" | "unavailable";
    redis: "ok" | "unavailable";
  };
};

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function fetchHealth(): Promise<HealthResponse> {
  const response = await fetch(`${API_URL}/health`, { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`health check failed with status ${response.status}`);
  }
  return response.json();
}

import { fetchHealth, type HealthResponse } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

export default async function HomePage() {
  let health: HealthResponse | null = null;
  let error: string | null = null;

  try {
    health = await fetchHealth();
  } catch (err) {
    error = err instanceof Error ? err.message : "unknown error";
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center gap-6 p-8">
      <h1 className="text-2xl font-semibold">EduPulse AI</h1>
      <p className="text-sm text-muted">Yerel geliştirme iskeleti — Faz 1 (P0 Foundation)</p>

      <div className="flex flex-col gap-2">
        {error && (
          <StatusBadge label="API" status="unavailable" />
        )}
        {health && (
          <>
            <StatusBadge label="Veritabanı" status={health.dependencies.database} />
            <StatusBadge label="Redis" status={health.dependencies.redis} />
          </>
        )}
      </div>
    </main>
  );
}

"use client";

import { useEffect, useState } from "react";
import { fetchPlans, switchTenantPlan, type Plan } from "@/lib/plan";

// Self-service plan switching (ROADMAP.md P2, ADR-016's own trigger). No
// payment gate exists (§116) — this only removes the "needs an operator to
// run a script" friction the ADR flagged, honestly, not a checkout flow.
export function PlanSwitcher({
  accessToken,
  currentPlanName,
  onSwitched,
}: {
  accessToken: string;
  currentPlanName: string;
  onSwitched: () => void;
}) {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [selectedSlug, setSelectedSlug] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchPlans(accessToken)
      .then((fetched) => {
        setPlans(fetched);
        if (fetched.length > 0) setSelectedSlug(fetched[0].slug);
      })
      .catch(() => setError("Planlar yüklenemedi."));
  }, [accessToken]);

  const handleSwitch = () => {
    if (!selectedSlug) return;
    setError(null);
    setSuccessMessage(null);
    setSubmitting(true);
    switchTenantPlan(accessToken, selectedSlug)
      .then((plan) => {
        setSuccessMessage(`Plan değiştirildi: ${plan.name}`);
        onSwitched();
      })
      .catch(() => setError("Plan değiştirilemedi."))
      .finally(() => setSubmitting(false));
  };

  if (plans.length === 0) return null;

  return (
    <div className="mt-2 flex items-center gap-2 text-sm">
      <span className="text-muted">Şu anki plan: {currentPlanName}.</span>
      <label className="flex items-center gap-2">
        Plan değiştir:
        <select
          value={selectedSlug}
          onChange={(e) => setSelectedSlug(e.target.value)}
          className="rounded-md border border-border px-2 py-1"
        >
          {plans.map((p) => (
            <option key={p.id} value={p.slug}>
              {p.name}
            </option>
          ))}
        </select>
      </label>
      <button
        onClick={handleSwitch}
        disabled={submitting}
        className="rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
      >
        {submitting ? "Değiştiriliyor..." : "Değiştir"}
      </button>
      {error && <span className="text-red-700">{error}</span>}
      {successMessage && <span className="text-green-700">{successMessage}</span>}
    </div>
  );
}

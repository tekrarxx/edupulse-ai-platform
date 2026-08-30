"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { SkillProgress } from "@/lib/dashboard";
import { fetchSkillExplanation, type SkillExplanation } from "@/lib/ai";

export function SkillProgressCard({ skill, accessToken }: { skill: SkillProgress; accessToken: string }) {
  const [explanation, setExplanation] = useState<SkillExplanation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleExplain = () => {
    setError(null);
    setLoading(true);
    fetchSkillExplanation(accessToken, skill.skill_id)
      .then(setExplanation)
      // §43: the LLM is a supporting component that can genuinely be
      // unavailable or return output that fails validation — a real
      // possibility, not a hypothetical one (ADR-015's addendum measured
      // this against a real model), so this is a plain, honest failure
      // message, not silently retried or hidden.
      .catch(() => setError("Açıklama şu anda oluşturulamadı. Lütfen daha sonra tekrar deneyin."))
      .finally(() => setLoading(false));
  };

  return (
    <div className="flex flex-col gap-2 rounded-md border border-border p-4">
      <div className="flex items-center justify-between">
        <span className="font-medium text-foreground">{skill.skill_name}</span>
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-xs font-medium",
            skill.is_strong && "bg-green-100 text-green-800",
            skill.is_weak && "bg-amber-100 text-amber-800",
            !skill.is_strong && !skill.is_weak && "bg-blue-100 text-blue-800"
          )}
        >
          {skill.mastery_label}
        </span>
      </div>
      {skill.next_action_label && (
        <p className="text-sm text-muted">
          Önerilen sonraki adım: <span className="text-foreground">{skill.next_action_label}</span>
        </p>
      )}
      {skill.pending_retention_checkpoints > 0 && (
        <p className="text-sm text-muted">
          {skill.pending_retention_checkpoints} hatırlama kontrolü bekleniyor.
        </p>
      )}

      {!explanation && (
        <button
          onClick={handleExplain}
          disabled={loading}
          className="mt-1 w-fit rounded-md border border-border px-3 py-1.5 text-sm disabled:opacity-50"
        >
          {loading ? "Oluşturuluyor..." : "Bu konuyu açıkla"}
        </button>
      )}
      {error && <p className="text-sm text-red-700">{error}</p>}
      {explanation && (
        <div className="mt-1 flex flex-col gap-2 rounded-md border border-border p-3 text-sm">
          <p className="text-foreground">{explanation.explanation}</p>
          {explanation.key_points.length > 0 && (
            <ul className="list-inside list-disc text-muted">
              {explanation.key_points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import type { SkillProgress } from "@/lib/dashboard";
import { fetchSkillExplanation, type SkillExplanation } from "@/lib/ai";
import { fetchDecisionTask, submitAttempt, TaskApiError, type AttemptResult, type DecisionTask } from "@/lib/task";

// Execution layer (§113 P8+): GET /decisions/{id}/task's own error details
// map to a plain, honest message each — never a generic "something went
// wrong" that hides which of these three genuinely different situations
// occurred (§90).
const _TASK_ERROR_MESSAGES: Record<string, string> = {
  decision_not_executable: "Bu öneri şu anda uygulanabilir değil.",
  action_has_no_task: "Bu öneri bir soru çözerek yapılabilecek bir görev değil.",
  no_question_available: "Bu konu için henüz uygun bir soru yok.",
};

function TaskRunner({ decisionId, accessToken }: { decisionId: string; accessToken: string }) {
  const [task, setTask] = useState<DecisionTask | null>(null);
  const [taskError, setTaskError] = useState<string | null>(null);
  const [taskLoading, setTaskLoading] = useState(false);
  const [response, setResponse] = useState("");
  const [result, setResult] = useState<AttemptResult | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleStart = () => {
    setTaskError(null);
    setTaskLoading(true);
    fetchDecisionTask(accessToken, decisionId)
      .then(setTask)
      .catch((err) => {
        const detail = err instanceof TaskApiError ? _TASK_ERROR_MESSAGES[err.message] : undefined;
        setTaskError(detail ?? "Görev şu anda yüklenemedi. Lütfen daha sonra tekrar deneyin.");
      })
      .finally(() => setTaskLoading(false));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!task) return;
    setSubmitError(null);
    setSubmitting(true);
    submitAttempt(accessToken, { question_id: task.question_id, assessment_type: task.assessment_type, learner_response: response })
      .then(setResult)
      .catch(() => setSubmitError("Cevabın gönderilemedi. Lütfen tekrar dene."))
      .finally(() => setSubmitting(false));
  };

  if (result) {
    return (
      <p className={cn("text-sm font-medium", result.is_correct === true && "text-green-700", result.is_correct === false && "text-red-700")}>
        {result.is_correct === true && "Doğru! Panon güncellendi."}
        {result.is_correct === false && "Yanlış oldu, ama bu da bir kanıt — panon güncellendi."}
        {result.is_correct === null && "Cevabın kaydedildi, öğretmen değerlendirmesi bekleniyor."}
      </p>
    );
  }

  if (task) {
    return (
      <form onSubmit={handleSubmit} className="mt-1 flex flex-col gap-2 rounded-md border border-border p-3 text-sm">
        <p className="text-foreground">{task.prompt}</p>
        <input
          type="text"
          required
          value={response}
          onChange={(e) => setResponse(e.target.value)}
          placeholder="Cevabın"
          className="rounded-md border border-border px-3 py-2"
        />
        {submitError && <p className="text-red-700">{submitError}</p>}
        <button
          type="submit"
          disabled={submitting}
          className="w-fit rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? "Gönderiliyor..." : "Gönder"}
        </button>
      </form>
    );
  }

  return (
    <>
      <button
        onClick={handleStart}
        disabled={taskLoading}
        className="mt-1 w-fit rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
      >
        {taskLoading ? "Yükleniyor..." : "Başla"}
      </button>
      {taskError && <p className="text-sm text-red-700">{taskError}</p>}
    </>
  );
}

export function SkillProgressCard({
  skill,
  accessToken,
  canExecute = false,
}: {
  skill: SkillProgress;
  accessToken: string;
  // §51/§90: POST /assessment/attempts always attributes the attempt to
  // the caller, so only the skill's own student can meaningfully click
  // "Başla" — GET /decisions/{id}/task itself also enforces this
  // server-side (403), but a viewer who can never succeed (a parent
  // looking at their child's card) should not be shown a button that
  // always fails with a misleading "try again later" message. Defaults to
  // false so a new consumer of this shared component must opt in
  // explicitly, not silently inherit a button that doesn't work for it.
  canExecute?: boolean;
}) {
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
      {canExecute && skill.next_action_decision_id && <TaskRunner decisionId={skill.next_action_decision_id} accessToken={accessToken} />}
      {skill.pending_retention_checkpoints > 0 && (
        <p className="text-sm text-muted">
          {skill.pending_retention_checkpoints} hatırlama kontrolü bekleniyor.
        </p>
      )}

      {!explanation && (
        <button
          onClick={handleExplain}
          disabled={loading}
          className="mt-1 w-fit rounded-md bg-primary px-3 py-1.5 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
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

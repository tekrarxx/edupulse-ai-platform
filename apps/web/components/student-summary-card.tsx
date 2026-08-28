import { cn } from "@/lib/utils";
import type { StudentSummary } from "@/lib/dashboard";

export function StudentSummaryCard({ student }: { student: StudentSummary }) {
  return (
    <div
      className={cn(
        "flex flex-col gap-2 rounded-md border p-4",
        student.needs_attention ? "border-amber-400" : "border-border"
      )}
    >
      <div className="flex items-center justify-between">
        <span className="font-medium text-foreground">{student.student_name}</span>
        {student.needs_attention && (
          <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800">İlgi gerekiyor</span>
        )}
      </div>

      {student.attention_reasons.length > 0 && (
        <ul className="list-inside list-disc text-sm text-amber-800">
          {student.attention_reasons.map((reason) => (
            <li key={reason}>{reason}</li>
          ))}
        </ul>
      )}

      {student.weak_skill_names.length > 0 && (
        <p className="text-sm text-muted">
          Zayıf: <span className="text-foreground">{student.weak_skill_names.join(", ")}</span>
        </p>
      )}
      {student.improving_skill_names.length > 0 && (
        <p className="text-sm text-muted">
          Gelişiyor: <span className="text-foreground">{student.improving_skill_names.join(", ")}</span>
        </p>
      )}
      {student.forgetting_skill_names.length > 0 && (
        <p className="text-sm text-muted">
          Unutmuş olabilir: <span className="text-foreground">{student.forgetting_skill_names.join(", ")}</span>
        </p>
      )}
      {student.misconception_skill_names.length > 0 && (
        <p className="text-sm text-muted">
          Yanlış kavrama: <span className="text-foreground">{student.misconception_skill_names.join(", ")}</span>
        </p>
      )}
      {student.next_action_label && (
        <p className="text-sm text-muted">
          Önerilen sonraki adım: <span className="text-foreground">{student.next_action_label}</span>
        </p>
      )}
    </div>
  );
}

import { cn } from "@/lib/utils";
import type { SkillProgress } from "@/lib/dashboard";

export function SkillProgressCard({ skill }: { skill: SkillProgress }) {
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
    </div>
  );
}

import { cn } from "@/lib/utils";

type Status = "ok" | "unavailable" | "degraded";

export function StatusBadge({ label, status }: { label: string; status: Status }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border px-4 py-2">
      <span className="text-sm text-foreground">{label}</span>
      <span
        className={cn(
          "rounded-full px-2 py-0.5 text-xs font-medium",
          status === "ok" && "bg-green-100 text-green-800",
          status !== "ok" && "bg-red-100 text-red-800"
        )}
      >
        {status}
      </span>
    </div>
  );
}

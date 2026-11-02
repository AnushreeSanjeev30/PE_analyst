import type { AgentRunRecord, RunStatus } from "../lib/types";

const STATUS_COLOR: Record<RunStatus, string> = {
  completed: "var(--status-good)",
  running: "var(--series-1)",
  pending: "var(--text-muted)",
  failed: "var(--status-critical)",
  skipped: "var(--text-muted)",
};

const STATUS_LABEL: Record<RunStatus, string> = {
  completed: "Completed",
  running: "Running",
  pending: "Pending",
  failed: "Failed",
  skipped: "Skipped",
};

export function PipelineTrace({ stages }: { stages: AgentRunRecord[] }) {
  return (
    <div className="overflow-x-auto">
      <div className="flex items-stretch gap-2 min-w-max">
        {stages.map((stage, i) => (
          <div key={stage.stage} className="flex items-center">
            <div
              className="rounded-md border px-3 py-2 min-w-[140px]"
              style={{
                borderColor: STATUS_COLOR[stage.status],
                backgroundColor: stage.status === "failed" ? "#d03b3b0d" : "var(--surface-1)",
              }}
              title={stage.error ?? stage.response?.summary ?? undefined}
            >
              <div className="flex items-center gap-1.5">
                <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: STATUS_COLOR[stage.status] }} />
                <span className="text-xs font-medium text-[var(--text-primary)] capitalize">{stage.stage.replace(/_/g, " ")}</span>
              </div>
              <div className="mt-0.5 text-[11px] text-[var(--text-muted)]">{STATUS_LABEL[stage.status]}</div>
              {stage.error && <div className="mt-0.5 text-[11px] text-[var(--status-critical)]">{stage.error}</div>}
            </div>
            {i < stages.length - 1 && <span className="mx-1 text-[var(--text-muted)]">&rarr;</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

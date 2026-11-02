import { Bar, BarChart, CartesianGrid, Cell, LabelList, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ReactNode } from "react";
import type { ScenarioOutcome } from "../lib/types";

// Fixed categorical order (dataviz skill): slot 1 blue, slot 2 orange, slot 3 aqua.
// Scenario identity (Bear/Base/Bull) always maps to the same color, never cycled
// by sort order or position.
const SCENARIO_COLORS: Record<string, string> = {
  Bear: "var(--series-2)",
  Base: "var(--series-1)",
  Bull: "var(--series-3)",
};
const FALLBACK_COLORS = ["var(--series-1)", "var(--series-2)", "var(--series-3)"];

function colorFor(name: string, index: number): string {
  return SCENARIO_COLORS[name] ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length];
}

interface TooltipPayloadItem {
  payload: ScenarioOutcome;
}

function ChartTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayloadItem[] }) {
  if (!active || !payload?.length) return null;
  const outcome = payload[0].payload;
  return (
    <div className="rounded-md border border-[var(--border-hairline)] bg-[var(--surface-1)] px-3 py-2 text-xs shadow-sm">
      <p className="font-medium text-[var(--text-primary)]">{outcome.name}</p>
      <p className="text-[var(--text-secondary)] tabular-nums">IRR: {(outcome.irr * 100).toFixed(1)}%</p>
      <p className="text-[var(--text-secondary)] tabular-nums">MOIC: {outcome.moic.toFixed(2)}x</p>
      <p className="text-[var(--text-secondary)] tabular-nums">Exit multiple: {outcome.exit_multiple.toFixed(1)}x</p>
    </div>
  );
}

export function ScenarioIrrChart({ outcomes }: { outcomes: ScenarioOutcome[] }) {
  const data = outcomes.map((o) => ({ ...o, irr_pct: Number((o.irr * 100).toFixed(1)) }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--gridline)" vertical={false} />
        <XAxis dataKey="name" tick={{ fill: "var(--text-secondary)", fontSize: 12 }} axisLine={{ stroke: "var(--baseline)" }} tickLine={false} />
        <YAxis
          tick={{ fill: "var(--text-muted)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v}%`}
          width={44}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--page-plane)" }} />
        <Bar dataKey="irr_pct" radius={[4, 4, 0, 0]} maxBarSize={72}>
          {data.map((entry, index) => (
            <Cell key={entry.name} fill={colorFor(entry.name, index)} />
          ))}
          <LabelList dataKey="irr_pct" position="top" formatter={(v: ReactNode) => `${v}%`} style={{ fill: "var(--text-primary)", fontSize: 12 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

export function ScenarioMoicChart({ outcomes }: { outcomes: ScenarioOutcome[] }) {
  const data = outcomes.map((o) => ({ ...o, moic_x: Number(o.moic.toFixed(2)) }));
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={data} margin={{ top: 16, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--gridline)" vertical={false} />
        <XAxis dataKey="name" tick={{ fill: "var(--text-secondary)", fontSize: 12 }} axisLine={{ stroke: "var(--baseline)" }} tickLine={false} />
        <YAxis
          tick={{ fill: "var(--text-muted)", fontSize: 11 }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v) => `${v}x`}
          width={40}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "var(--page-plane)" }} />
        <Bar dataKey="moic_x" radius={[4, 4, 0, 0]} maxBarSize={72}>
          {data.map((entry, index) => (
            <Cell key={entry.name} fill={colorFor(entry.name, index)} />
          ))}
          <LabelList dataKey="moic_x" position="top" formatter={(v: ReactNode) => `${v}x`} style={{ fill: "var(--text-primary)", fontSize: 12 }} />
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

import type { SensitivityGrid } from "../lib/types";

// Sequential one-hue ramp (blue, light -> dark) for a continuous magnitude
// (IRR), per the dataviz skill. Direct value labels are kept in text ink, not
// hue, so the cell color alone never has to carry the exact number.
const SEQ_STEPS = ["var(--seq-100)", "var(--seq-200)", "var(--seq-300)", "var(--seq-400)", "var(--seq-500)", "var(--seq-600)", "var(--seq-700)"];

function stepFor(value: number, min: number, max: number): string {
  if (max === min) return SEQ_STEPS[3];
  const t = (value - min) / (max - min);
  const index = Math.min(SEQ_STEPS.length - 1, Math.max(0, Math.round(t * (SEQ_STEPS.length - 1))));
  return SEQ_STEPS[index];
}

// Dark steps (500-700) need light text; light steps need dark text.
function textColorFor(stepIndexHex: string): string {
  const darkSteps = new Set(["var(--seq-500)", "var(--seq-600)", "var(--seq-700)"]);
  return darkSteps.has(stepIndexHex) ? "#ffffff" : "var(--text-primary)";
}

export function SensitivityHeatmap({ grid }: { grid: SensitivityGrid }) {
  const irrValues = grid.cells.map((c) => c.irr);
  const min = Math.min(...irrValues);
  const max = Math.max(...irrValues);

  const cellByKey = new Map(grid.cells.map((c) => [`${c.exit_multiple}|${c.ebitda_multiplier}`, c]));

  return (
    <div className="overflow-x-auto">
      <table className="border-separate" style={{ borderSpacing: 2 }}>
        <thead>
          <tr>
            <th className="px-2 py-1 text-xs font-medium text-[var(--text-muted)] text-right">
              Exit &darr; / EBITDA &rarr;
            </th>
            {grid.ebitda_multipliers.map((m) => (
              <th key={m} className="px-2 py-1 text-xs font-medium text-[var(--text-muted)] tabular-nums">
                {m.toFixed(2)}x
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {grid.exit_multiples.map((exitMultiple) => (
            <tr key={exitMultiple}>
              <th className="px-2 py-1 text-xs font-medium text-[var(--text-muted)] text-right tabular-nums">
                {exitMultiple.toFixed(1)}x
              </th>
              {grid.ebitda_multipliers.map((ebitdaMultiplier) => {
                const cell = cellByKey.get(`${exitMultiple}|${ebitdaMultiplier}`);
                if (!cell) return <td key={ebitdaMultiplier} />;
                const bg = stepFor(cell.irr, min, max);
                return (
                  <td
                    key={ebitdaMultiplier}
                    className="rounded px-3 py-2 text-center tabular-nums text-xs"
                    style={{ backgroundColor: bg, color: textColorFor(bg) }}
                    title={`Exit ${cell.exit_multiple}x, EBITDA x${cell.ebitda_multiplier} -> IRR ${(cell.irr * 100).toFixed(1)}%, MOIC ${cell.moic.toFixed(2)}x`}
                  >
                    <div className="font-semibold">{(cell.irr * 100).toFixed(1)}%</div>
                    <div className="opacity-80">{cell.moic.toFixed(2)}x</div>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <div className="mt-3 flex items-center gap-2 text-xs text-[var(--text-muted)]">
        <span>Lower IRR</span>
        <div className="flex h-3 w-40 overflow-hidden rounded">
          {SEQ_STEPS.map((step) => (
            <div key={step} className="flex-1" style={{ backgroundColor: step }} />
          ))}
        </div>
        <span>Higher IRR</span>
      </div>
    </div>
  );
}

import { useState } from "react";
import type { FormEvent } from "react";
import { Layout } from "../components/Layout";
import { SensitivityHeatmap } from "../components/SensitivityHeatmap";
import { extractErrorMessage, sensitivityGrid } from "../lib/api";
import type { SensitivityGrid } from "../lib/types";

const DEFAULT_LBO_ASSUMPTIONS = { purchase_price: 1600.0, holding_period: 5, exit_multiple: 8.0 };

const DEFAULT_OPERATING_PROJECTION = [1, 2, 3, 4, 5].map((year) => ({
  year,
  revenue: 1000.0 + year * 60,
  ebitda: 220.0 + year * 15,
  taxes: 30.0 + year,
  capex: 30.0 + year,
  change_in_nwc: 10.0 + year,
}));

export function SensitivityPage() {
  const [lboAssumptionsText, setLboAssumptionsText] = useState(JSON.stringify(DEFAULT_LBO_ASSUMPTIONS, null, 2));
  const [operatingProjectionText, setOperatingProjectionText] = useState(JSON.stringify(DEFAULT_OPERATING_PROJECTION, null, 2));
  const [exitMultiplesText, setExitMultiplesText] = useState("6, 7, 8, 9, 10");
  const [ebitdaMultipliersText, setEbitdaMultipliersText] = useState("0.9, 1.0, 1.1");

  const [grid, setGrid] = useState<SensitivityGrid | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function parseNumberList(text: string): number[] {
    return text
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean)
      .map(Number);
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setGrid(null);

    let lboAssumptions: Record<string, unknown>;
    let operatingProjection: Record<string, unknown>[];
    try {
      lboAssumptions = JSON.parse(lboAssumptionsText);
    } catch {
      setError("LBO assumptions is not valid JSON.");
      return;
    }
    try {
      operatingProjection = JSON.parse(operatingProjectionText);
    } catch {
      setError("Operating projection is not valid JSON (expected an array).");
      return;
    }

    const exitMultiples = parseNumberList(exitMultiplesText);
    const ebitdaMultipliers = parseNumberList(ebitdaMultipliersText);
    if (exitMultiples.some(Number.isNaN) || exitMultiples.length === 0) {
      setError("Exit multiples must be a comma-separated list of numbers.");
      return;
    }
    if (ebitdaMultipliers.some(Number.isNaN) || ebitdaMultipliers.length === 0) {
      setError("EBITDA multipliers must be a comma-separated list of numbers.");
      return;
    }

    setSubmitting(true);
    try {
      const result = await sensitivityGrid({
        lbo_assumptions: lboAssumptions,
        operating_projection: operatingProjection,
        exit_multiples: exitMultiples,
        ebitda_multipliers: ebitdaMultipliers,
      });
      setGrid(result);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Layout>
      <div className="max-w-4xl pb-16">
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Sensitivity Explorer</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Standalone IRR/MOIC grid across exit multiple and EBITDA multiplier, independent of a full deal analysis
          run.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-5">
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]">LBO assumptions (JSON)</label>
            <textarea
              value={lboAssumptionsText}
              onChange={(e) => setLboAssumptionsText(e.target.value)}
              rows={6}
              className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-3 py-2 font-mono text-xs outline-none focus:ring-2 focus:ring-[var(--series-1)]"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--text-primary)]">Operating projection (JSON array)</label>
            <textarea
              value={operatingProjectionText}
              onChange={(e) => setOperatingProjectionText(e.target.value)}
              rows={10}
              className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-3 py-2 font-mono text-xs outline-none focus:ring-2 focus:ring-[var(--series-1)]"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)]">Exit multiples</label>
              <input
                type="text"
                value={exitMultiplesText}
                onChange={(e) => setExitMultiplesText(e.target.value)}
                className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
              />
              <p className="mt-1 text-xs text-[var(--text-muted)]">Comma-separated, e.g. 6, 7, 8, 9, 10</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--text-primary)]">EBITDA multipliers</label>
              <input
                type="text"
                value={ebitdaMultipliersText}
                onChange={(e) => setEbitdaMultipliersText(e.target.value)}
                className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
              />
              <p className="mt-1 text-xs text-[var(--text-muted)]">Comma-separated multipliers applied to base EBITDA, e.g. 0.9, 1.0, 1.1</p>
            </div>
          </div>

          {error && <p className="text-sm text-[var(--status-critical)]">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-[var(--series-1)] px-5 py-2.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? "Computing..." : "Compute grid"}
          </button>
        </form>

        {grid && (
          <div className="mt-8 rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)] p-5">
            <h2 className="text-base font-semibold text-[var(--text-primary)]">IRR / MOIC grid</h2>
            <p className="mt-1 text-xs text-[var(--text-muted)]">Each cell shows IRR (bold) and MOIC.</p>
            <div className="mt-4">
              <SensitivityHeatmap grid={grid} />
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

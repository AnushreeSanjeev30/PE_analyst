import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Layout } from "../components/Layout";
import { SeverityBadge } from "../components/SeverityBadge";
import { compareAnalyses, extractErrorMessage } from "../lib/api";
import type { AnalysisComparison, ComparisonRun, MetricChange } from "../lib/types";

function formatValue(value: number | string | null, unit: MetricChange["unit"]): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "string") return value;
  switch (unit) {
    case "percent":
      return `${(value * 100).toFixed(1)}%`;
    case "multiple":
      return `${value.toFixed(2)}x`;
    case "money":
      return value.toLocaleString(undefined, { maximumFractionDigits: 2 });
    default:
      return value.toLocaleString(undefined, { maximumFractionDigits: 1 });
  }
}

function formatDelta(metric: MetricChange): string {
  if (metric.delta === null || !metric.changed) return metric.changed ? "changed" : "—";
  const sign = metric.delta > 0 ? "+" : "−";
  const size = Math.abs(metric.delta);
  switch (metric.unit) {
    case "percent":
      // A change in a percentage is stated in percentage points, not percent of a percent.
      return `${sign}${(size * 100).toFixed(1)} pts`;
    case "multiple":
      return `${sign}${size.toFixed(2)}x`;
    default:
      return `${sign}${size.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
  }
}

function formatInput(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "number") return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  return String(value);
}

function RunHeader({ label, run }: { label: string; run: ComparisonRun }) {
  return (
    <div className="rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)] p-4">
      <div className="text-xs font-medium text-[var(--text-muted)] uppercase">{label}</div>
      <div className="mt-1 flex items-center justify-between gap-3">
        <Link to={`/analyses/${run.id}`} className="font-medium text-[var(--series-1)] hover:underline">
          {run.company_name}
        </Link>
        {run.recommendation && <SeverityBadge level={run.recommendation} />}
      </div>
      <div className="mt-1 text-xs text-[var(--text-muted)] tabular-nums">
        {new Date(run.created_at).toLocaleString()}
      </div>
    </div>
  );
}

const TH = "px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase";

export function ComparePage() {
  const [params] = useSearchParams();
  const base = params.get("base");
  const other = params.get("other");
  const [comparison, setComparison] = useState<AnalysisComparison | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showUnchanged, setShowUnchanged] = useState(false);

  useEffect(() => {
    if (!base || !other) return;
    let cancelled = false;
    compareAnalyses(base, other)
      .then((result) => {
        if (!cancelled) setComparison(result);
      })
      .catch((err) => {
        if (!cancelled) setError(extractErrorMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [base, other]);

  if (!base || !other) {
    return (
      <Layout>
        <p className="text-sm text-[var(--text-secondary)]">
          Pick two analyses to compare from <Link to="/analyses" className="text-[var(--series-1)]">Analyses</Link>.
        </p>
      </Layout>
    );
  }
  if (error) {
    return (
      <Layout>
        <p className="text-sm text-[var(--status-critical)]">{error}</p>
      </Layout>
    );
  }
  if (!comparison) {
    return (
      <Layout>
        <p className="text-sm text-[var(--text-muted)]">Comparing...</p>
      </Layout>
    );
  }

  const metrics = showUnchanged ? comparison.metrics : comparison.metrics.filter((metric) => metric.changed);
  const drivers = showUnchanged ? comparison.drivers : comparison.drivers.filter((driver) => driver.changed);

  return (
    <Layout>
      <div className="max-w-5xl space-y-6 pb-16">
        <div>
          <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Compare runs</h1>
          <p className="mt-2 text-sm text-[var(--text-primary)]">{comparison.summary}</p>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <RunHeader label="Baseline" run={comparison.base} />
          <RunHeader label="Compared with" run={comparison.other} />
        </div>

        <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
          <input type="checkbox" checked={showUnchanged} onChange={(e) => setShowUnchanged(e.target.checked)} />
          Also show results that did not change
        </label>

        <section className="rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)] p-5">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">What changed in the inputs</h2>
          {comparison.input_changes.length === 0 ? (
            <p className="mt-3 text-sm text-[var(--text-muted)]">
              The two runs used identical inputs. Any difference in results comes from the documents themselves.
            </p>
          ) : (
            <div className="mt-3 overflow-x-auto rounded-md border border-[var(--border-hairline)]">
              <table className="min-w-full divide-y divide-[var(--gridline)] text-sm">
                <thead className="bg-[var(--page-plane)]">
                  <tr>
                    <th className={TH}>Input</th>
                    <th className={TH}>Baseline</th>
                    <th className={TH}>Compared with</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--gridline)]">
                  {comparison.input_changes.map((change) => (
                    <tr key={change.path}>
                      <td className="px-3 py-2 font-mono text-xs text-[var(--text-primary)]">{change.path}</td>
                      <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{formatInput(change.base)}</td>
                      <td className="px-3 py-2 tabular-nums text-[var(--text-primary)]">{formatInput(change.other)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {comparison.input_changes_truncated && (
            <p className="mt-2 text-xs text-[var(--text-muted)]">More inputs differ than are listed here.</p>
          )}
        </section>

        <section className="rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)] p-5">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">What changed in the results</h2>
          {metrics.length === 0 ? (
            <p className="mt-3 text-sm text-[var(--text-muted)]">No headline result changed.</p>
          ) : (
            <div className="mt-3 overflow-x-auto rounded-md border border-[var(--border-hairline)]">
              <table className="min-w-full divide-y divide-[var(--gridline)] text-sm">
                <thead className="bg-[var(--page-plane)]">
                  <tr>
                    <th className={TH}>Result</th>
                    <th className={TH}>Baseline</th>
                    <th className={TH}>Compared with</th>
                    <th className={TH}>Change</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--gridline)]">
                  {metrics.map((metric) => (
                    <tr key={metric.key}>
                      <td className="px-3 py-2 font-medium text-[var(--text-primary)]">{metric.label}</td>
                      <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">
                        {formatValue(metric.base, metric.unit)}
                      </td>
                      <td className="px-3 py-2 tabular-nums text-[var(--text-primary)]">
                        {formatValue(metric.other, metric.unit)}
                      </td>
                      <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{formatDelta(metric)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        <section className="rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)] p-5">
          <h2 className="text-base font-semibold text-[var(--text-primary)]">Scorecard votes</h2>
          {drivers.length === 0 ? (
            <p className="mt-3 text-sm text-[var(--text-muted)]">No scorecard area changed its vote.</p>
          ) : (
            <ul className="mt-3 space-y-3">
              {drivers.map((driver) => (
                <li key={driver.area} className="rounded-md border border-[var(--border-hairline)] p-4">
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <span className="text-sm font-semibold text-[var(--text-primary)]">{driver.area}</span>
                    <span className="text-xs text-[var(--text-secondary)]">
                      {driver.base_direction ?? "—"}
                      {driver.changed && <> &rarr; {driver.other_direction ?? "—"}</>}
                    </span>
                  </div>
                  <div className="mt-2 grid grid-cols-1 gap-3 text-sm text-[var(--text-secondary)] sm:grid-cols-2">
                    <p>
                      <span className="block text-xs text-[var(--text-muted)]">Baseline</span>
                      {driver.base_statement ?? "—"}
                    </p>
                    <p>
                      <span className="block text-xs text-[var(--text-muted)]">Compared with</span>
                      {driver.other_statement ?? "—"}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </Layout>
  );
}

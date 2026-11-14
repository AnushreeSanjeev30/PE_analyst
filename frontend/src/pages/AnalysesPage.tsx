import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";
import { SeverityBadge } from "../components/SeverityBadge";
import { deleteAnalysis, extractErrorMessage, listAnalyses } from "../lib/api";
import type { DealAnalysisSummary } from "../lib/types";

const STATUS_LABEL: Record<string, string> = {
  pending: "Queued",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
};

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

export function AnalysesPage() {
  const [analyses, setAnalyses] = useState<DealAnalysisSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    async function load() {
      try {
        const items = await listAnalyses();
        if (cancelled) return;
        setAnalyses(items);
        setError(null);
        // Keep the list fresh while anything is still running.
        if (items.some((item) => item.status === "pending" || item.status === "running")) {
          timer = window.setTimeout(load, 3000);
        }
      } catch (err) {
        if (!cancelled) setError(extractErrorMessage(err));
      }
    }

    load();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, []);

  async function handleDelete(analysis: DealAnalysisSummary) {
    if (!window.confirm(`Delete the saved analysis of ${analysis.company_name}? This cannot be undone.`)) return;
    try {
      await deleteAnalysis(analysis.id);
      setAnalyses((current) => current?.filter((item) => item.id !== analysis.id) ?? null);
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  return (
    <Layout>
      <div className="max-w-5xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--text-primary)]">Analyses</h1>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Every analysis you run is saved here with its full report, so you can reopen it without re-running it.
            </p>
          </div>
          <Link
            to="/analysis/new"
            className="shrink-0 rounded-md bg-[var(--series-1)] px-4 py-2 text-sm font-medium text-white hover:opacity-90"
          >
            New analysis
          </Link>
        </div>

        <div className="mt-8">
          {error && <p className="text-sm text-[var(--status-critical)]">{error}</p>}
          {analyses === null && !error && <p className="text-sm text-[var(--text-muted)]">Loading analyses...</p>}
          {analyses && analyses.length === 0 && (
            <p className="text-sm text-[var(--text-muted)]">No analyses yet. Run one to see it here.</p>
          )}
          {analyses && analyses.length > 0 && (
            <div className="overflow-hidden rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)]">
              <table className="min-w-full divide-y divide-[var(--gridline)]">
                <thead className="bg-[var(--page-plane)]">
                  <tr>
                    {["Company", "Recommendation", "Status", "Started", ""].map((heading) => (
                      <th
                        key={heading}
                        className="px-4 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase"
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--gridline)]">
                  {analyses.map((analysis) => (
                    <tr key={analysis.id} className="hover:bg-[var(--page-plane)]">
                      <td className="px-4 py-3 text-sm">
                        <Link
                          to={`/analyses/${analysis.id}`}
                          className="font-medium text-[var(--series-1)] hover:underline"
                        >
                          {analysis.company_name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-sm">
                        {analysis.recommendation ? (
                          <SeverityBadge level={analysis.recommendation} />
                        ) : (
                          <span className="text-[var(--text-muted)]">&mdash;</span>
                        )}
                      </td>
                      <td
                        className={`px-4 py-3 text-sm ${
                          analysis.status === "failed" ? "text-[var(--status-critical)]" : "text-[var(--text-secondary)]"
                        }`}
                        title={analysis.error ?? undefined}
                      >
                        {STATUS_LABEL[analysis.status] ?? analysis.status}
                      </td>
                      <td className="px-4 py-3 text-sm text-[var(--text-secondary)] tabular-nums">
                        {formatDate(analysis.created_at)}
                      </td>
                      <td className="px-4 py-3 text-right text-sm">
                        <button
                          type="button"
                          onClick={() => handleDelete(analysis)}
                          className="text-[var(--text-muted)] hover:text-[var(--status-critical)]"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

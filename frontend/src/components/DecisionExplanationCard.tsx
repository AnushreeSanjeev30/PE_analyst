import { PdfPageLink } from "./PdfPageLink";
import { SeverityBadge } from "./SeverityBadge";
import type { DecisionDriver, DecisionExplanation } from "../lib/types";

// The answer to "why?" behind a BUY / HOLD / REJECT: each factor, how much it weighed, what it
// rests on, and the document passages that back it. Built by the backend from fixed rules, so
// it can never disagree with the ruling it explains.

const BASIS_HELP: Record<string, string> = {
  "Document evidence": "Quoted from the uploaded document, with page numbers.",
  Calculated: "Computed by the financial engines from the inputs.",
  "Analyst input": "Supplied by the person who ran this analysis.",
};

function DriverRow({ driver }: { driver: DecisionDriver }) {
  const against = driver.direction === "Against";
  return (
    <li
      className="rounded-md border border-[var(--border-hairline)] p-4"
      style={{ borderLeft: `4px solid ${against ? "var(--status-critical)" : "var(--status-good, #0ca30c)"}` }}
    >
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-sm font-semibold text-[var(--text-primary)]">{driver.area}</span>
        <span
          className="text-xs font-medium"
          style={{ color: against ? "var(--status-critical)" : "#0ca30c" }}
        >
          {against ? "Counts against the deal" : "Supports the deal"}
        </span>
        {driver.weight !== null && (
          <span className="text-xs text-[var(--text-muted)] tabular-nums">
            {(driver.weight * 100).toFixed(0)}% of the scorecard
          </span>
        )}
        <span
          className="rounded border border-[var(--border-hairline)] px-2 py-0.5 text-xs text-[var(--text-secondary)]"
          title={BASIS_HELP[driver.basis]}
        >
          {driver.basis}
        </span>
      </div>
      <p className="mt-2 text-sm text-[var(--text-secondary)]">{driver.statement}</p>
      {driver.basis_detail && <p className="mt-1 text-xs text-[var(--text-muted)]">{driver.basis_detail}</p>}

      {driver.evidence.length > 0 && (
        <div className="mt-3 space-y-2">
          <p className="text-xs font-medium text-[var(--text-muted)]">From the document</p>
          {driver.evidence.map((citation, index) => (
            <blockquote
              key={index}
              className="border-l-2 border-[var(--baseline)] bg-[var(--page-plane)] px-3 py-2 text-sm text-[var(--text-secondary)]"
            >
              <p>&ldquo;{citation.excerpt}&rdquo;</p>
              <footer className="mt-1 text-xs text-[var(--text-muted)] tabular-nums">
                <PdfPageLink documentId={citation.document_id} page={citation.page_number} title={citation.source}>
                  {citation.source}, page {citation.page_number}
                </PdfPageLink>{" "}
                &middot; extraction confidence{" "}
                {(citation.confidence * 100).toFixed(0)}%
              </footer>
            </blockquote>
          ))}
        </div>
      )}
    </li>
  );
}

function BulletList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div>
      <h3 className="text-sm font-semibold text-[var(--text-primary)]">{title}</h3>
      <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-[var(--text-secondary)]">
        {items.map((item, index) => (
          <li key={index}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

export function DecisionExplanationCard({ explanation }: { explanation: DecisionExplanation }) {
  return (
    <section className="rounded-lg border-2 border-[var(--series-1)] bg-[var(--surface-1)] p-5">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-base font-semibold text-[var(--text-primary)]">Why this decision</h2>
        <SeverityBadge level={explanation.recommendation} />
      </div>
      <p className="mt-3 text-sm text-[var(--text-primary)]">{explanation.headline}</p>

      <ul className="mt-5 space-y-3">
        {explanation.drivers.map((driver) => (
          <DriverRow key={driver.area} driver={driver} />
        ))}
      </ul>

      <div className="mt-6 grid grid-cols-1 gap-6 lg:grid-cols-2">
        <BulletList title="What would change the ruling" items={explanation.what_would_change} />
        <div className="space-y-6">
          <BulletList title="Conditions before signing" items={explanation.conditions} />
          <BulletList title="Check before relying on this" items={explanation.evidence_gaps} />
        </div>
      </div>
    </section>
  );
}

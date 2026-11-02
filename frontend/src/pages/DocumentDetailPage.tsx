import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { Layout } from "../components/Layout";
import { ProvenanceTag } from "../components/ProvenanceTag";
import { extractErrorMessage, getDocument, queryRag } from "../lib/api";
import type { DocumentIntelligenceReport, RAGAnswer } from "../lib/types";

export function DocumentDetailPage() {
  const { documentId } = useParams<{ documentId: string }>();
  const [report, setReport] = useState<DocumentIntelligenceReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<RAGAnswer | null>(null);
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState<string | null>(null);

  useEffect(() => {
    if (!documentId) return;
    setReport(null);
    setError(null);
    getDocument(documentId)
      .then(setReport)
      .catch((err) => setError(extractErrorMessage(err)));
  }, [documentId]);

  async function handleAsk(event: FormEvent) {
    event.preventDefault();
    if (!question.trim() || !documentId) return;
    setAsking(true);
    setAskError(null);
    try {
      const result = await queryRag({ question, document_id: documentId });
      setAnswer(result);
    } catch (err) {
      setAskError(extractErrorMessage(err));
    } finally {
      setAsking(false);
    }
  }

  return (
    <Layout>
      <div className="max-w-4xl">
        <Link to="/documents" className="text-sm text-[var(--series-1)] hover:underline">
          &larr; Document library
        </Link>

        {error && <p className="mt-4 text-sm text-[var(--status-critical)]">{error}</p>}
        {!report && !error && <p className="mt-4 text-sm text-[var(--text-muted)]">Loading...</p>}

        {report && (
          <>
            <h1 className="mt-2 text-2xl font-semibold text-[var(--text-primary)]">{report.file_name}</h1>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              {report.page_count} pages &middot; {report.risk_factors.length} risk factors &middot;{" "}
              {report.notes.length} notes &middot; {report.industry_evidence.length} industry evidence items
            </p>

            {report.warnings.length > 0 && (
              <div className="mt-4 rounded-md border border-[var(--status-warning)] bg-[#fab21914] px-4 py-3">
                <p className="text-sm font-medium text-[var(--text-primary)]">Extraction warnings</p>
                <ul className="mt-1 list-disc pl-5 text-sm text-[var(--text-secondary)]">
                  {report.warnings.map((warning, i) => (
                    <li key={i}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Ask a question */}
            <section className="mt-8 rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)] p-5">
              <h2 className="text-base font-semibold text-[var(--text-primary)]">Ask a question about this document</h2>
              <form onSubmit={handleAsk} className="mt-3 flex gap-2">
                <input
                  type="text"
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="e.g. What were the key risk factors mentioned?"
                  className="flex-1 rounded-md border border-[var(--border-hairline)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
                />
                <button
                  type="submit"
                  disabled={asking}
                  className="rounded-md bg-[var(--series-1)] px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
                >
                  {asking ? "Asking..." : "Ask"}
                </button>
              </form>
              {askError && <p className="mt-2 text-sm text-[var(--status-critical)]">{askError}</p>}
              {answer && (
                <div className="mt-4 rounded-md bg-[var(--page-plane)] p-4">
                  <p className="text-sm text-[var(--text-primary)]">{answer.answer}</p>
                  <p className="mt-2 text-xs text-[var(--text-muted)] tabular-nums">
                    Confidence: {(answer.confidence * 100).toFixed(0)}%
                  </p>
                  {answer.citations.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {answer.citations.map((c, i) => (
                        <ProvenanceTag key={i} page={c.page_number} confidence={c.score} excerpt={c.excerpt} />
                      ))}
                    </div>
                  )}
                  {answer.warnings.length > 0 && (
                    <ul className="mt-2 list-disc pl-5 text-xs text-[var(--status-serious)]">
                      {answer.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </section>

            {/* Sections */}
            {report.sections.length > 0 && (
              <section className="mt-8">
                <h2 className="text-base font-semibold text-[var(--text-primary)]">Sections</h2>
                <div className="mt-3 space-y-2">
                  {report.sections.map((section, i) => (
                    <div key={i} className="rounded-md border border-[var(--border-hairline)] bg-[var(--surface-1)] p-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-[var(--text-primary)]">{section.title}</span>
                        <span className="text-xs text-[var(--text-muted)]">{section.kind}</span>
                      </div>
                      <p className="mt-1 text-xs text-[var(--text-muted)]">Pages: {section.pages.join(", ")}</p>
                      {section.references.length > 0 && (
                        <div className="mt-2 flex flex-wrap gap-2">
                          {section.references.map((ref, j) => (
                            <ProvenanceTag key={j} page={ref.page_number} confidence={ref.confidence} excerpt={ref.excerpt} />
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Risk factors */}
            {report.risk_factors.length > 0 && (
              <section className="mt-8">
                <h2 className="text-base font-semibold text-[var(--text-primary)]">Risk factors</h2>
                <div className="mt-3 space-y-2">
                  {report.risk_factors.map((rf, i) => (
                    <div key={i} className="rounded-md border border-[var(--border-hairline)] bg-[var(--surface-1)] p-4">
                      <p className="text-sm font-medium text-[var(--text-primary)]">{rf.title}</p>
                      <p className="mt-1 text-sm text-[var(--text-secondary)]">{rf.text}</p>
                      <div className="mt-2">
                        <ProvenanceTag page={rf.source.page_number} confidence={rf.source.confidence} excerpt={rf.source.excerpt} />
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Notes */}
            {report.notes.length > 0 && (
              <section className="mt-8">
                <h2 className="text-base font-semibold text-[var(--text-primary)]">Notes</h2>
                <div className="mt-3 space-y-2">
                  {report.notes.map((note, i) => (
                    <div key={i} className="rounded-md border border-[var(--border-hairline)] bg-[var(--surface-1)] p-4">
                      <p className="text-sm font-medium text-[var(--text-primary)]">{note.title}</p>
                      <p className="mt-1 text-sm text-[var(--text-secondary)]">{note.text}</p>
                      <div className="mt-2">
                        <ProvenanceTag page={note.source.page_number} confidence={note.source.confidence} excerpt={note.source.excerpt} />
                      </div>
                    </div>
                  ))}
                </div>
              </section>
            )}

            {/* Industry evidence */}
            {report.industry_evidence.length > 0 && (
              <section className="mt-8 mb-12">
                <h2 className="text-base font-semibold text-[var(--text-primary)]">Industry evidence</h2>
                <div className="mt-3 space-y-2">
                  {report.industry_evidence.map((ev, i) => (
                    <div key={i} className="rounded-md border border-[var(--border-hairline)] bg-[var(--surface-1)] p-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-[var(--text-primary)] capitalize">{ev.topic}</span>
                        <ProvenanceTag page={ev.page_number} confidence={ev.confidence} excerpt={ev.excerpt} />
                      </div>
                      <p className="mt-1 text-sm text-[var(--text-secondary)]">{ev.claim}</p>
                      <p className="mt-1 text-xs italic text-[var(--text-muted)]">&ldquo;{ev.excerpt}&rdquo;</p>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}

import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { DEFAULT_FINANCIALS, FinancialStatementFields } from "../components/FinancialStatementFields";
import { analyzeDeal, extractErrorMessage, listDocuments } from "../lib/api";
import type { DealAnalysisRequest, DocumentSummary, FinancialStatementInput } from "../lib/types";

const DEFAULT_VALUATION_INPUTS = {
  current_price_per_share: 85.0,
  dcf: {
    revenue: 1000.0,
    assumptions: {
      revenue_growth: 0.08,
      ebit_margin: 0.2,
      cash: 100.0,
      debt: 200.0,
      shares_outstanding: 10.0,
    },
  },
  comparables: {
    target: {
      revenue: 1000.0,
      ebitda: 220.0,
      cash: 100.0,
      debt: 200.0,
      shares_outstanding: 10.0,
    },
    peers: [
      { name: "Peer A", enterprise_value: 1800.0, market_cap: 1600.0, revenue: 200.0, ebitda: 40.0, net_income: 20.0, book_value: 200.0 },
      { name: "Peer B", enterprise_value: 2000.0, market_cap: 1750.0, revenue: 250.0, ebitda: 50.0, net_income: 25.0, book_value: 225.0 },
      { name: "Peer C", enterprise_value: 1650.0, market_cap: 1400.0, revenue: 220.0, ebitda: 44.0, net_income: 22.0, book_value: 180.0 },
    ],
  },
  lbo: {
    assumptions: { purchase_price: 1600.0, holding_period: 5, exit_multiple: 8.0 },
    operating_projection: [1, 2, 3, 4, 5].map((year) => ({
      year,
      revenue: 1000.0 + year * 60,
      ebitda: 220.0 + year * 15,
      taxes: 30.0 + year,
      capex: 30.0 + year,
      change_in_nwc: 10.0 + year,
    })),
  },
};

const DEFAULT_INDUSTRY_INPUTS = {
  industry_name: "Vertical Software",
  evidence: [
    {
      topic: "market",
      source: "2025 Annual Report",
      page_number: 12,
      excerpt: "Market demand remains strong.",
      claim: "Management expects durable demand.",
      confidence: 0.9,
    },
  ],
};

export function NewAnalysisPage() {
  const navigate = useNavigate();

  const [companyName, setCompanyName] = useState("ExampleCo");
  const [currentFinancials, setCurrentFinancials] = useState<FinancialStatementInput>(DEFAULT_FINANCIALS);
  const [previousFinancials, setPreviousFinancials] = useState<FinancialStatementInput>(DEFAULT_FINANCIALS);

  const [valuationInputsText, setValuationInputsText] = useState(JSON.stringify(DEFAULT_VALUATION_INPUTS, null, 2));

  const [useRiskInputs, setUseRiskInputs] = useState(true);
  const [altmanZ, setAltmanZ] = useState(3.2);
  const [piotroskiScore, setPiotroskiScore] = useState(7);
  const [industryRiskScore, setIndustryRiskScore] = useState(30);

  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [documentId, setDocumentId] = useState<string>("");
  const [industryName, setIndustryName] = useState("Vertical Software");
  const [industryInputsText, setIndustryInputsText] = useState(JSON.stringify(DEFAULT_INDUSTRY_INPUTS, null, 2));
  const [dueDiligenceInputsText, setDueDiligenceInputsText] = useState("[]");

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listDocuments()
      .then(setDocuments)
      .catch(() => setDocuments([]));
  }, []);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    let valuationInputs: Record<string, unknown>;
    try {
      valuationInputs = JSON.parse(valuationInputsText);
    } catch {
      setError("Valuation inputs is not valid JSON.");
      return;
    }

    const request: DealAnalysisRequest = {
      company_name: companyName,
      current_financials: currentFinancials,
      previous_financials: previousFinancials,
      valuation_inputs: valuationInputs,
    };

    if (useRiskInputs) {
      request.risk_inputs = {
        altman_z: altmanZ,
        piotroski_score: piotroskiScore,
        industry_risk_score: industryRiskScore,
      };
    }

    if (documentId) {
      request.document_id = documentId;
      request.industry_name = industryName;
      if (!industryName.trim()) {
        setError("Industry name is required when deriving evidence from a document.");
        return;
      }
    } else {
      try {
        request.industry_inputs = JSON.parse(industryInputsText);
      } catch {
        setError("Industry inputs is not valid JSON.");
        return;
      }
      try {
        const parsed = JSON.parse(dueDiligenceInputsText);
        request.due_diligence_inputs = Array.isArray(parsed) ? parsed : [];
      } catch {
        setError("Due diligence inputs is not valid JSON (expected an array).");
        return;
      }
    }

    setSubmitting(true);
    try {
      const report = await analyzeDeal(request);
      navigate("/analysis/result", { state: { report } });
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Layout>
      <div className="max-w-4xl pb-16">
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">New Deal Analysis</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Runs the full underwriting workflow: financial &rarr; valuation &rarr; risk &rarr; due diligence &rarr;
          industry &rarr; investment committee debate.
        </p>

        <form onSubmit={handleSubmit} className="mt-6 space-y-8">
          <section>
            <label className="block text-sm font-medium text-[var(--text-primary)]">Company name</label>
            <input
              type="text"
              required
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              className="mt-1 w-full max-w-sm rounded-md border border-[var(--border-hairline)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
            />
          </section>

          <section>
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Current period financials</h2>
            <div className="mt-3">
              <FinancialStatementFields value={currentFinancials} onChange={setCurrentFinancials} />
            </div>
          </section>

          <section>
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Previous period financials</h2>
            <div className="mt-3">
              <FinancialStatementFields value={previousFinancials} onChange={setPreviousFinancials} />
            </div>
          </section>

          <section>
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Risk inputs (optional)</h2>
            <label className="mt-2 flex items-center gap-2 text-sm text-[var(--text-secondary)]">
              <input type="checkbox" checked={useRiskInputs} onChange={(e) => setUseRiskInputs(e.target.checked)} />
              Supply risk inputs
            </label>
            {useRiskInputs && (
              <div className="mt-3 grid grid-cols-3 gap-3 max-w-md">
                <label className="block">
                  <span className="block text-xs font-medium text-[var(--text-secondary)]">Altman Z-score</span>
                  <input
                    type="number"
                    step="any"
                    value={altmanZ}
                    onChange={(e) => setAltmanZ(Number(e.target.value))}
                    className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
                  />
                </label>
                <label className="block">
                  <span className="block text-xs font-medium text-[var(--text-secondary)]">Piotroski score</span>
                  <input
                    type="number"
                    step="1"
                    value={piotroskiScore}
                    onChange={(e) => setPiotroskiScore(Number(e.target.value))}
                    className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
                  />
                </label>
                <label className="block">
                  <span className="block text-xs font-medium text-[var(--text-secondary)]">Industry risk score</span>
                  <input
                    type="number"
                    step="any"
                    value={industryRiskScore}
                    onChange={(e) => setIndustryRiskScore(Number(e.target.value))}
                    className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
                  />
                </label>
              </div>
            )}
          </section>

          <section>
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Industry &amp; due diligence evidence</h2>
            <label className="mt-2 block text-sm font-medium text-[var(--text-secondary)]">
              Derive from a previously uploaded document (optional)
            </label>
            <select
              value={documentId}
              onChange={(e) => setDocumentId(e.target.value)}
              className="mt-1 w-full max-w-md rounded-md border border-[var(--border-hairline)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
            >
              <option value="">None - enter evidence manually below</option>
              {documents.map((doc) => (
                <option key={doc.document_id} value={doc.document_id}>
                  {doc.file_name}
                </option>
              ))}
            </select>

            {documentId ? (
              <div className="mt-3">
                <label className="block text-sm font-medium text-[var(--text-secondary)]">Industry name (required)</label>
                <input
                  type="text"
                  required
                  value={industryName}
                  onChange={(e) => setIndustryName(e.target.value)}
                  className="mt-1 w-full max-w-sm rounded-md border border-[var(--border-hairline)] px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
                />
                <p className="mt-1 text-xs text-[var(--text-muted)]">
                  Industry evidence and due-diligence red-flag candidates will be derived automatically from this
                  document's extracted content.
                </p>
              </div>
            ) : (
              <div className="mt-3 space-y-4">
                <div>
                  <label className="block text-sm font-medium text-[var(--text-secondary)]">Industry inputs (JSON)</label>
                  <textarea
                    value={industryInputsText}
                    onChange={(e) => setIndustryInputsText(e.target.value)}
                    rows={10}
                    className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-3 py-2 font-mono text-xs outline-none focus:ring-2 focus:ring-[var(--series-1)]"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-[var(--text-secondary)]">
                    Due diligence inputs (JSON array, optional)
                  </label>
                  <textarea
                    value={dueDiligenceInputsText}
                    onChange={(e) => setDueDiligenceInputsText(e.target.value)}
                    rows={3}
                    className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-3 py-2 font-mono text-xs outline-none focus:ring-2 focus:ring-[var(--series-1)]"
                  />
                </div>
              </div>
            )}
          </section>

          <section>
            <h2 className="text-base font-semibold text-[var(--text-primary)]">Valuation inputs (JSON)</h2>
            <p className="mt-1 text-xs text-[var(--text-muted)]">
              Nested DCF, comparables, and LBO assumptions. Pre-filled with working sample values &mdash; edit as needed.
            </p>
            <textarea
              value={valuationInputsText}
              onChange={(e) => setValuationInputsText(e.target.value)}
              rows={26}
              className="mt-2 w-full rounded-md border border-[var(--border-hairline)] px-3 py-2 font-mono text-xs outline-none focus:ring-2 focus:ring-[var(--series-1)]"
            />
          </section>

          {error && <p className="text-sm text-[var(--status-critical)]">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-[var(--series-1)] px-5 py-2.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? "Running analysis... this can take a moment" : "Run deal analysis"}
          </button>
        </form>
      </div>
    </Layout>
  );
}

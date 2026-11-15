import { useEffect, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { DEFAULT_FINANCIALS, FinancialStatementFields } from "../components/FinancialStatementFields";
import { Layout } from "../components/Layout";
import { PdfPageLink } from "../components/PdfPageLink";
import { extractErrorMessage, getDealRoom, listDocuments, startAnalysis, suggestInputs } from "../lib/api";
import type {
  DealAnalysisRequest,
  DocumentSummary,
  FinancialStatementInput,
  PeerInput,
  SuggestedInputs,
  Suggestion,
  ValuationAssumptionInputs,
} from "../lib/types";

// ---------------------------------------------------------------------------
// Assumption fields
// ---------------------------------------------------------------------------

type FieldKind = "percent" | "money" | "multiple" | "number" | "years";

interface AssumptionField {
  key: keyof ValuationAssumptionInputs;
  label: string;
  kind: FieldKind;
  optional?: boolean;
}

const OPERATING_FIELDS: AssumptionField[] = [
  { key: "revenue_growth", label: "Revenue growth", kind: "percent" },
  { key: "ebitda_margin", label: "EBITDA margin", kind: "percent" },
  { key: "ebit_margin", label: "EBIT margin", kind: "percent" },
  { key: "capex_pct_revenue", label: "Capex (% of revenue)", kind: "percent" },
  { key: "nwc_pct_revenue", label: "Working capital (% of revenue growth)", kind: "percent" },
  { key: "tax_rate", label: "Tax rate", kind: "percent" },
];

const CAPITAL_FIELDS: AssumptionField[] = [
  { key: "debt", label: "Debt", kind: "money" },
  { key: "cash", label: "Cash", kind: "money" },
  { key: "shares_outstanding", label: "Shares outstanding", kind: "number" },
  { key: "current_price_per_share", label: "Current price per share", kind: "money", optional: true },
];

const DEAL_FIELDS: AssumptionField[] = [
  { key: "entry_multiple", label: "Entry multiple (EV / EBITDA)", kind: "multiple" },
  { key: "exit_multiple", label: "Exit multiple (EV / EBITDA)", kind: "multiple" },
  { key: "holding_period", label: "Holding period", kind: "years" },
];

const ALL_FIELDS = [...OPERATING_FIELDS, ...CAPITAL_FIELDS, ...DEAL_FIELDS];

const UNIT_SUFFIX: Record<FieldKind, string> = { percent: "%", money: "", multiple: "x", number: "", years: "yrs" };

// Form values are kept as the text the analyst sees: percentages as "8", not 0.08.
type AssumptionText = Record<string, string>;

const STARTING_ASSUMPTIONS: AssumptionText = {
  revenue_growth: "8",
  ebitda_margin: "22",
  ebit_margin: "15",
  capex_pct_revenue: "4",
  nwc_pct_revenue: "2",
  tax_rate: "25",
  debt: "200",
  cash: "100",
  shares_outstanding: "10",
  current_price_per_share: "85",
  entry_multiple: "8",
  exit_multiple: "8",
  holding_period: "5",
};

const EXAMPLE_PEERS: PeerInput[] = [
  { name: "Peer A", enterprise_value: 1800, market_cap: 1600, revenue: 200, ebitda: 40, net_income: 20, book_value: 200 },
  { name: "Peer B", enterprise_value: 2000, market_cap: 1750, revenue: 250, ebitda: 50, net_income: 25, book_value: 225 },
  { name: "Peer C", enterprise_value: 1650, market_cap: 1400, revenue: 220, ebitda: 44, net_income: 22, book_value: 180 },
];

const PEER_COLUMNS: Array<[keyof PeerInput, string]> = [
  ["enterprise_value", "Enterprise value"],
  ["market_cap", "Market cap"],
  ["revenue", "Revenue"],
  ["ebitda", "EBITDA"],
  ["net_income", "Net income"],
  ["book_value", "Book value"],
];

const DEFAULT_INDUSTRY_EVIDENCE = [
  {
    topic: "market",
    source: "2025 Annual Report",
    page_number: 12,
    excerpt: "Market demand remains strong.",
    claim: "Management expects durable demand.",
    confidence: 0.9,
  },
];

function toText(value: number | string | null, kind: FieldKind): string {
  if (value === null || value === undefined || value === "") return "";
  const number = Number(value);
  if (Number.isNaN(number)) return "";
  const shown = kind === "percent" ? number * 100 : number;
  // Trim float noise (11.111111 -> 11.11) without forcing trailing zeros.
  return String(Math.round(shown * 100) / 100);
}

function fromText(text: string, kind: FieldKind): number {
  const number = Number(text);
  return kind === "percent" ? number / 100 : number;
}

// ---------------------------------------------------------------------------
// Provenance
// ---------------------------------------------------------------------------

const BASIS_STYLE: Record<string, { bg: string; fg: string; label: string }> = {
  Document: { bg: "#0ca30c1a", fg: "#0a7a0a", label: "From document" },
  Calculated: { bg: "#3987e51a", fg: "#184f95", label: "Calculated from document" },
  Default: { bg: "#fab2191a", fg: "#9a6700", label: "Default - confirm" },
  "Needs input": { bg: "#d03b3b1a", fg: "#d03b3b", label: "Needs your input" },
};

function Provenance({ suggestion }: { suggestion: Suggestion | undefined }) {
  if (!suggestion) return null;
  const style = BASIS_STYLE[suggestion.basis] ?? BASIS_STYLE.Default;
  return (
    <div className="mt-1 text-xs text-[var(--text-muted)]">
      <span className="inline-block rounded px-1.5 py-0.5 font-medium" style={{ backgroundColor: style.bg, color: style.fg }}>
        {style.label}
      </span>{" "}
      {suggestion.citation && (
        <PdfPageLink
          documentId={suggestion.citation.document_id}
          page={suggestion.citation.page_number}
          title={suggestion.citation.source}
        >
          {suggestion.citation.source}, p.{suggestion.citation.page_number}
        </PdfPageLink>
      )}
      <div className="mt-0.5">{suggestion.note}</div>
    </div>
  );
}

const INPUT_CLASS =
  "w-full rounded-md border border-[var(--border-hairline)] px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]";

function AssumptionGrid({
  fields,
  values,
  onChange,
  suggestions,
}: {
  fields: AssumptionField[];
  values: AssumptionText;
  onChange: (key: string, value: string) => void;
  suggestions: Record<string, Suggestion>;
}) {
  return (
    <div className="grid grid-cols-1 gap-x-4 gap-y-4 sm:grid-cols-2 lg:grid-cols-3">
      {fields.map((field) => (
        <div key={field.key}>
          <label className="block">
            <span className="block text-xs font-medium text-[var(--text-secondary)]">
              {field.label}
              {field.optional && <span className="font-normal text-[var(--text-muted)]"> (optional)</span>}
            </span>
            <span className="mt-1 flex items-center gap-1.5">
              <input
                type="number"
                step="any"
                required={!field.optional}
                value={values[field.key] ?? ""}
                onChange={(e) => onChange(field.key, e.target.value)}
                className={INPUT_CLASS}
              />
              {UNIT_SUFFIX[field.kind] && (
                <span className="w-6 shrink-0 text-xs text-[var(--text-muted)]">{UNIT_SUFFIX[field.kind]}</span>
              )}
            </span>
          </label>
          <Provenance suggestion={suggestions[field.key]} />
        </div>
      ))}
    </div>
  );
}

function Section({ title, hint, children }: { title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)] p-5">
      <h2 className="text-base font-semibold text-[var(--text-primary)]">{title}</h2>
      {hint && <p className="mt-1 text-xs text-[var(--text-muted)]">{hint}</p>}
      <div className="mt-4">{children}</div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export function NewAnalysisPage() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const dealId = params.get("deal") ?? "";

  const [dealName, setDealName] = useState<string | null>(null);
  const [companyName, setCompanyName] = useState("");
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  // Order matters: financial figures are taken from the first document that reports each one.
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  const [suggested, setSuggested] = useState<SuggestedInputs | null>(null);
  const [suggesting, setSuggesting] = useState(false);

  const [currentFinancials, setCurrentFinancials] = useState<FinancialStatementInput>(DEFAULT_FINANCIALS);
  const [previousFinancials, setPreviousFinancials] = useState<FinancialStatementInput>(DEFAULT_FINANCIALS);

  const [assumptions, setAssumptions] = useState<AssumptionText>(STARTING_ASSUMPTIONS);
  const [peers, setPeers] = useState<PeerInput[]>(EXAMPLE_PEERS);
  const [peersAreExamples, setPeersAreExamples] = useState(true);
  const [peerTickers, setPeerTickers] = useState("");

  const [industryName, setIndustryName] = useState("");
  const [competitivePosition, setCompetitivePosition] = useState("Neutral");
  const [marketGrowth, setMarketGrowth] = useState("");
  const [industryEvidenceText, setIndustryEvidenceText] = useState(JSON.stringify(DEFAULT_INDUSTRY_EVIDENCE, null, 2));
  const [dueDiligenceText, setDueDiligenceText] = useState("[]");

  const [useRiskInputs, setUseRiskInputs] = useState(true);
  const [altmanZ, setAltmanZ] = useState(3.2);
  const [piotroskiScore, setPiotroskiScore] = useState(7);
  const [industryRiskScore, setIndustryRiskScore] = useState(30);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    listDocuments(dealId || undefined)
      .then((items) => {
        if (cancelled) return;
        setDocuments(items);
        // Inside a deal the natural starting point is "everything we have on the company".
        if (dealId) setSelectedIds(items.map((item) => item.document_id).reverse());
      })
      .catch(() => {
        if (!cancelled) setDocuments([]);
      });
    if (dealId) {
      getDealRoom(dealId)
        .then((room) => {
          if (!cancelled) setDealName(room.name);
        })
        .catch(() => undefined);
    }
    return () => {
      cancelled = true;
    };
  }, [dealId]);

  const usingDocuments = selectedIds.length > 0;
  const suggestionByField: Record<string, Suggestion> = {};
  for (const item of suggested?.assumptions ?? []) suggestionByField[item.field] = item;

  function toggleDocument(id: string) {
    setSelectedIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
    // The proposals describe a specific set of documents; a different set invalidates them.
    setSuggested(null);
  }

  async function handleSuggest() {
    setError(null);
    setSuggesting(true);
    try {
      const result = await suggestInputs(selectedIds);
      setSuggested(result);
      setCurrentFinancials({ ...zeroFinancials(), ...result.current_financials } as FinancialStatementInput);
      setPreviousFinancials({ ...zeroFinancials(), ...result.previous_financials } as FinancialStatementInput);
      const next: AssumptionText = { ...assumptions };
      for (const item of result.assumptions) {
        const field = ALL_FIELDS.find((candidate) => candidate.key === item.field);
        if (field) next[item.field] = toText(item.value, field.kind);
      }
      setAssumptions(next);
      if (typeof result.competitive_position.value === "string") {
        setCompetitivePosition(result.competitive_position.value);
      }
      setMarketGrowth(toText(result.market_growth_pct.value, "percent"));
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSuggesting(false);
    }
  }

  function updatePeer(index: number, key: keyof PeerInput, value: string) {
    setPeersAreExamples(false);
    setPeers((current) =>
      current.map((peer, position) =>
        position === index ? { ...peer, [key]: key === "name" ? value : Number(value) } : peer,
      ),
    );
  }

  /** Figures the analyst changed, or typed in because the documents lacked them. */
  function financialOverrides(): Record<string, Record<string, number>> | null {
    if (!suggested) return null;
    const overrides: Record<string, Record<string, number>> = { current: {}, previous: {} };
    const periods = [
      ["current", currentFinancials, suggested.current_financials],
      ["previous", previousFinancials, suggested.previous_financials],
    ] as const;
    for (const [period, form, read] of periods) {
      for (const key of Object.keys(form) as Array<keyof FinancialStatementInput>) {
        // A figure the documents lacked stays missing until the analyst types a real value, so
        // the server can still refuse the run and name it rather than accept a silent zero.
        const missingAndBlank = read[key] === undefined && form[key] === 0;
        if (!missingAndBlank && read[key] !== form[key]) overrides[period][key] = form[key];
      }
    }
    const changed = Object.keys(overrides.current).length + Object.keys(overrides.previous).length;
    return changed > 0 ? overrides : null;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);

    const tickers = peerTickers
      .split(",")
      .map((ticker) => ticker.trim().toUpperCase())
      .filter(Boolean);
    const namedPeers = peers.filter((peer) => peer.name.trim());
    if (namedPeers.length < 2 && tickers.length === 0) {
      setError("Add at least two comparable companies, or enter peer tickers to look up.");
      return;
    }

    const valuation: Record<string, unknown> = {
      peers: tickers.length > 0 && namedPeers.length < 2 ? [] : namedPeers,
      peer_tickers: tickers.length > 0 && namedPeers.length < 2 ? tickers : [],
    };
    for (const field of ALL_FIELDS) {
      const text = assumptions[field.key] ?? "";
      if (text === "") {
        if (field.optional) continue;
        setError(`${field.label} is required.`);
        return;
      }
      valuation[field.key] = fromText(text, field.kind);
    }

    const request: DealAnalysisRequest = {
      company_name: companyName,
      valuation_assumptions: valuation as unknown as ValuationAssumptionInputs,
    };
    if (dealId) request.deal_room_id = dealId;
    if (useRiskInputs) {
      request.risk_inputs = {
        altman_z: altmanZ,
        piotroski_score: piotroskiScore,
        industry_risk_score: industryRiskScore,
      };
    }

    if (usingDocuments) {
      if (!industryName.trim()) {
        setError("Industry name is required.");
        return;
      }
      request.document_ids = selectedIds;
      request.industry_name = industryName.trim();
      request.competitive_position = competitivePosition;
      request.market_growth_pct = marketGrowth === "" ? null : Number(marketGrowth) / 100;
      request.financial_overrides = financialOverrides();
    } else {
      request.current_financials = currentFinancials;
      request.previous_financials = previousFinancials;
      try {
        request.industry_inputs = {
          industry_name: industryName.trim() || "Unspecified",
          evidence: JSON.parse(industryEvidenceText),
          competitive_position: competitivePosition,
          market_growth_pct: marketGrowth === "" ? null : Number(marketGrowth) / 100,
        };
      } catch {
        setError("Industry evidence is not valid JSON.");
        return;
      }
      try {
        const parsed = JSON.parse(dueDiligenceText);
        request.due_diligence_inputs = Array.isArray(parsed) ? parsed : [];
      } catch {
        setError("Due diligence items is not valid JSON (expected an array).");
        return;
      }
    }

    setSubmitting(true);
    try {
      const analysis = await startAnalysis(request);
      navigate(`/analyses/${analysis.id}`);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  const missing = suggested?.missing_financials ?? [];
  // Many figures share a page; list each document page once.
  const financialSources = (suggested?.financial_sources ?? []).filter(
    (source, index, all) =>
      all.findIndex(
        (other) => other.document_id === source.document_id && other.page_number === source.page_number,
      ) === index,
  );

  return (
    <Layout>
      <div className="max-w-4xl pb-16">
        <h1 className="text-2xl font-semibold text-[var(--text-primary)]">New Deal Analysis</h1>
        <p className="mt-1 text-sm text-[var(--text-secondary)]">
          Pick the documents, let the app read what it can from them, then confirm or correct each input. Every
          proposed value shows where it came from.
        </p>
        {dealId && (
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            Filed in deal{" "}
            <Link to={`/deals/${dealId}`} className="font-medium text-[var(--series-1)] hover:underline">
              {dealName ?? "..."}
            </Link>
            ; the whole deal team will see it.
          </p>
        )}

        <form onSubmit={handleSubmit} className="mt-6 space-y-6">
          <Section title="1. Company and documents">
            <label className="block max-w-sm">
              <span className="block text-xs font-medium text-[var(--text-secondary)]">Company name</span>
              <input
                type="text"
                required
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className={`mt-1 ${INPUT_CLASS}`}
              />
            </label>

            <div className="mt-4">
              <span className="block text-xs font-medium text-[var(--text-secondary)]">
                Documents to analyse {usingDocuments && `(${selectedIds.length} selected)`}
              </span>
              {documents.length === 0 ? (
                <p className="mt-1 text-sm text-[var(--text-muted)]">
                  No documents available.{" "}
                  <Link to={dealId ? `/deals/${dealId}` : "/documents"} className="text-[var(--series-1)]">
                    Upload one
                  </Link>{" "}
                  or enter everything by hand below.
                </p>
              ) : (
                <ul className="mt-2 divide-y divide-[var(--gridline)] rounded-md border border-[var(--border-hairline)]">
                  {documents.map((doc) => {
                    const position = selectedIds.indexOf(doc.document_id);
                    return (
                      <li key={doc.document_id}>
                        <label className="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm">
                          <input type="checkbox" checked={position >= 0} onChange={() => toggleDocument(doc.document_id)} />
                          <span className="min-w-0 flex-1 truncate text-[var(--text-primary)]">{doc.display_name}</span>
                          <span className="shrink-0 text-xs text-[var(--text-muted)] tabular-nums">
                            {position >= 0 && selectedIds.length > 1 && <>priority {position + 1} &middot; </>}
                            {doc.page_count} pages
                          </span>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              )}
              {selectedIds.length > 1 && (
                <p className="mt-1 text-xs text-[var(--text-muted)]">
                  When two documents report the same figure, the higher-priority one wins. Tick the audited
                  accounts first.
                </p>
              )}
            </div>

            {usingDocuments && (
              <div className="mt-4 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  onClick={handleSuggest}
                  disabled={suggesting}
                  className="rounded-md border border-[var(--series-1)] px-4 py-2 text-sm font-medium text-[var(--series-1)] hover:bg-[var(--page-plane)] disabled:opacity-50"
                >
                  {suggesting ? "Reading documents..." : suggested ? "Read the documents again" : "Read inputs from these documents"}
                </button>
                {suggested && (
                  <span className="text-sm text-[var(--text-secondary)]">
                    Inputs filled in below. Check anything marked "Default" or "Needs your input".
                  </span>
                )}
              </div>
            )}
          </Section>

          {(!usingDocuments || suggested) && (
            <Section
              title="2. Financial statements"
              hint={
                usingDocuments
                  ? "Read from the documents, in the documents' own units. Correct any figure that is wrong; your corrections are used in place of the extracted value."
                  : "Enter the two most recent periods."
              }
            >
              {missing.length > 0 && (
                <p className="mb-3 rounded-md border border-[var(--status-warning)] bg-[#fab21914] px-3 py-2 text-sm text-[var(--text-primary)]">
                  Not found in the documents, so shown as 0 - enter them for both periods:{" "}
                  <span className="font-medium">{missing.map((name) => name.replace(/_/g, " ")).join(", ")}</span>.
                </p>
              )}
              {suggested?.warnings.map((warning) => (
                <p key={warning} className="mb-2 text-xs text-[var(--text-muted)]">
                  Note: {warning.replace(/_/g, " ")}
                </p>
              ))}
              <details open={!usingDocuments || missing.length > 0}>
                <summary className="cursor-pointer text-sm font-medium text-[var(--series-1)]">
                  {usingDocuments
                    ? `Review the figures (${Object.keys(suggested?.current_financials ?? {}).length} of 14 read from the documents)`
                    : "Figures"}
                </summary>
                <h3 className="mt-4 text-sm font-semibold text-[var(--text-primary)]">Current period</h3>
                <div className="mt-2">
                  <FinancialStatementFields value={currentFinancials} onChange={setCurrentFinancials} />
                </div>
                <h3 className="mt-5 text-sm font-semibold text-[var(--text-primary)]">Previous period</h3>
                <div className="mt-2">
                  <FinancialStatementFields value={previousFinancials} onChange={setPreviousFinancials} />
                </div>
              </details>
              {financialSources.length > 0 && (
                <p className="mt-3 text-xs text-[var(--text-muted)]">
                  Sources:{" "}
                  {financialSources.map((source, index) => (
                    <span key={index}>
                      {index > 0 && ", "}
                      <PdfPageLink documentId={source.document_id} page={source.page_number} title={source.source}>
                        {source.source} p.{source.page_number}
                      </PdfPageLink>
                    </span>
                  ))}
                </p>
              )}
            </Section>
          )}

          <Section
            title="3. Operating assumptions"
            hint="How the business is expected to perform over the holding period. Revenue and EBITDA start from the current-period statement."
          >
            <AssumptionGrid
              fields={OPERATING_FIELDS}
              values={assumptions}
              onChange={(key, value) => setAssumptions((current) => ({ ...current, [key]: value }))}
              suggestions={suggestionByField}
            />
          </Section>

          <Section title="4. Capital structure" hint="Same units as the financial statements.">
            <AssumptionGrid
              fields={CAPITAL_FIELDS}
              values={assumptions}
              onChange={(key, value) => setAssumptions((current) => ({ ...current, [key]: value }))}
              suggestions={suggestionByField}
            />
          </Section>

          <Section
            title="5. The deal"
            hint="The purchase price is the entry multiple times current EBITDA. These are your call; nothing in the documents sets them."
          >
            <AssumptionGrid
              fields={DEAL_FIELDS}
              values={assumptions}
              onChange={(key, value) => setAssumptions((current) => ({ ...current, [key]: value }))}
              suggestions={suggestionByField}
            />
          </Section>

          <Section
            title="6. Comparable companies"
            hint="At least two. Used to value the company on market multiples."
          >
            {peersAreExamples && (
              <p className="mb-3 rounded-md border border-[var(--status-warning)] bg-[#fab21914] px-3 py-2 text-sm text-[var(--text-primary)]">
                These are made-up example peers so the form runs as it stands. Replace them with real comparables
                before relying on the valuation.
              </p>
            )}
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr>
                    <th className="pb-1 pr-2 text-left text-xs font-medium text-[var(--text-secondary)]">Name</th>
                    {PEER_COLUMNS.map(([, label]) => (
                      <th key={label} className="pb-1 pr-2 text-left text-xs font-medium text-[var(--text-secondary)]">
                        {label}
                      </th>
                    ))}
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {peers.map((peer, index) => (
                    <tr key={index}>
                      <td className="py-1 pr-2">
                        <input
                          type="text"
                          aria-label={`Peer ${index + 1} name`}
                          value={peer.name}
                          onChange={(e) => updatePeer(index, "name", e.target.value)}
                          className={INPUT_CLASS}
                        />
                      </td>
                      {PEER_COLUMNS.map(([key, label]) => (
                        <td key={key} className="py-1 pr-2">
                          <input
                            type="number"
                            step="any"
                            aria-label={`Peer ${index + 1} ${label}`}
                            value={peer[key]}
                            onChange={(e) => updatePeer(index, key, e.target.value)}
                            className={`min-w-20 ${INPUT_CLASS}`}
                          />
                        </td>
                      ))}
                      <td className="py-1">
                        <button
                          type="button"
                          onClick={() => {
                            setPeersAreExamples(false);
                            setPeers((current) => current.filter((_, position) => position !== index));
                          }}
                          className="text-xs text-[var(--text-muted)] hover:text-[var(--status-critical)]"
                        >
                          Remove
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <button
              type="button"
              onClick={() => {
                setPeersAreExamples(false);
                setPeers((current) => [
                  ...current,
                  { name: "", enterprise_value: 0, market_cap: 0, revenue: 0, ebitda: 0, net_income: 0, book_value: 0 },
                ]);
              }}
              className="mt-2 text-sm font-medium text-[var(--series-1)]"
            >
              + Add a peer
            </button>
            <label className="mt-4 block max-w-md">
              <span className="block text-xs font-medium text-[var(--text-secondary)]">
                Or look peers up by ticker (comma separated)
              </span>
              <input
                type="text"
                value={peerTickers}
                onChange={(e) => setPeerTickers(e.target.value)}
                placeholder="ORCL, SAP, ADBE"
                className={`mt-1 ${INPUT_CLASS}`}
              />
              <span className="mt-1 block text-xs text-[var(--text-muted)]">
                Used only when fewer than two peers are entered above. Needs a market-data key on the server.
              </span>
            </label>
          </Section>

          <Section title="7. Industry view">
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <label className="block">
                <span className="block text-xs font-medium text-[var(--text-secondary)]">Industry name</span>
                <input
                  type="text"
                  required={usingDocuments}
                  value={industryName}
                  onChange={(e) => setIndustryName(e.target.value)}
                  placeholder="Vertical software"
                  className={`mt-1 ${INPUT_CLASS}`}
                />
              </label>
              <div>
                <label className="block">
                  <span className="block text-xs font-medium text-[var(--text-secondary)]">Competitive position</span>
                  <select
                    value={competitivePosition}
                    onChange={(e) => setCompetitivePosition(e.target.value)}
                    className={`mt-1 ${INPUT_CLASS}`}
                  >
                    {["Leader", "Strong", "Neutral", "Weak"].map((position) => (
                      <option key={position}>{position}</option>
                    ))}
                  </select>
                </label>
                <Provenance suggestion={suggested?.competitive_position} />
                {suggested?.competitive_position.citation && (
                  <p className="mt-1 text-xs italic text-[var(--text-muted)]">
                    &ldquo;{suggested.competitive_position.citation.excerpt}&rdquo;
                  </p>
                )}
              </div>
              <div>
                <label className="block">
                  <span className="block text-xs font-medium text-[var(--text-secondary)]">
                    Market growth <span className="font-normal text-[var(--text-muted)]">(optional)</span>
                  </span>
                  <span className="mt-1 flex items-center gap-1.5">
                    <input
                      type="number"
                      step="any"
                      value={marketGrowth}
                      onChange={(e) => setMarketGrowth(e.target.value)}
                      className={INPUT_CLASS}
                    />
                    <span className="w-6 shrink-0 text-xs text-[var(--text-muted)]">%</span>
                  </span>
                </label>
                <Provenance suggestion={suggested?.market_growth_pct} />
              </div>
            </div>

            {usingDocuments ? (
              <p className="mt-4 text-xs text-[var(--text-muted)]">
                Market, competition and management commentary, and the risk factors and notes screened for red
                flags, are taken from the selected documents.
              </p>
            ) : (
              <div className="mt-4 space-y-4">
                <label className="block">
                  <span className="block text-xs font-medium text-[var(--text-secondary)]">
                    Industry evidence (JSON list of cited excerpts)
                  </span>
                  <textarea
                    value={industryEvidenceText}
                    onChange={(e) => setIndustryEvidenceText(e.target.value)}
                    rows={9}
                    className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-3 py-2 font-mono text-xs outline-none focus:ring-2 focus:ring-[var(--series-1)]"
                  />
                </label>
                <label className="block">
                  <span className="block text-xs font-medium text-[var(--text-secondary)]">
                    Due diligence items (JSON array, optional)
                  </span>
                  <textarea
                    value={dueDiligenceText}
                    onChange={(e) => setDueDiligenceText(e.target.value)}
                    rows={3}
                    className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-3 py-2 font-mono text-xs outline-none focus:ring-2 focus:ring-[var(--series-1)]"
                  />
                </label>
              </div>
            )}
          </Section>

          <Section title="8. Risk scores (optional)">
            <label className="flex items-center gap-2 text-sm text-[var(--text-secondary)]">
              <input type="checkbox" checked={useRiskInputs} onChange={(e) => setUseRiskInputs(e.target.checked)} />
              Supply risk scores
            </label>
            {useRiskInputs && (
              <div className="mt-3 grid max-w-md grid-cols-3 gap-3">
                {(
                  [
                    ["Altman Z-score", altmanZ, setAltmanZ, "any"],
                    ["Piotroski score", piotroskiScore, setPiotroskiScore, "1"],
                    ["Industry risk score", industryRiskScore, setIndustryRiskScore, "any"],
                  ] as const
                ).map(([label, value, setter, step]) => (
                  <label key={label} className="block">
                    <span className="block text-xs font-medium text-[var(--text-secondary)]">{label}</span>
                    <input
                      type="number"
                      step={step}
                      value={value}
                      onChange={(e) => setter(Number(e.target.value))}
                      className={`mt-1 ${INPUT_CLASS}`}
                    />
                  </label>
                ))}
              </div>
            )}
          </Section>

          {error && <p className="text-sm text-[var(--status-critical)]">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="rounded-md bg-[var(--series-1)] px-5 py-2.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? "Starting analysis..." : "Run deal analysis"}
          </button>
        </form>
      </div>
    </Layout>
  );
}

function zeroFinancials(): FinancialStatementInput {
  const zeros = { ...DEFAULT_FINANCIALS };
  for (const key of Object.keys(zeros) as Array<keyof FinancialStatementInput>) zeros[key] = 0;
  return zeros;
}

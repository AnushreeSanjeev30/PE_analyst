import { useCallback, useEffect, useRef, useState } from "react";
import type { FormEvent } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  DEFAULT_FINANCIALS,
  FinancialStatementFields,
  financialLabel,
} from "../components/FinancialStatementFields";
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

// What each input means and where to get it. Shown wherever the documents could not supply
// the value, so nobody has to guess what belongs in an empty box.
const FIELD_HELP: Record<string, string> = {
  revenue_growth: "Your forecast of yearly revenue growth over the holding period.",
  ebitda_margin: "EBITDA divided by revenue.",
  ebit_margin: "Operating income divided by revenue.",
  capex_pct_revenue: "Capital expenditure divided by revenue.",
  nwc_pct_revenue: "Extra working capital needed per unit of new revenue. 2% is typical for software; higher for stock-heavy businesses.",
  tax_rate: "The company's effective tax rate (income tax / pre-tax profit).",
  debt: "All borrowings on the balance sheet, short and long term.",
  cash: "Cash and cash equivalents on the balance sheet.",
  shares_outstanding: "Share count from the cover page or the equity note, in the same units as the statements (e.g. millions).",
  current_price_per_share: "Today's share price or the offer price. Leave blank for a private company.",
  entry_multiple: "The price you expect to pay, as a multiple of current EBITDA. Purchase price = this x EBITDA.",
  exit_multiple: "The multiple you expect to sell at. Follows the entry multiple until you change it.",
  holding_period: "Years you plan to hold the investment before selling.",
};

/** The assumptions that are plain arithmetic on the financial statements. */
function deriveFromStatements(
  current: FinancialStatementInput,
  previous: FinancialStatementInput,
): Record<string, string> {
  const derived: Record<string, string> = {};
  const ratio = (top: number, bottom: number) => String(Math.round((top / bottom) * 10000) / 100);
  if (current.revenue > 0) {
    derived.ebitda_margin = ratio(current.ebitda, current.revenue);
    derived.ebit_margin = ratio(current.ebit, current.revenue);
    derived.capex_pct_revenue = ratio(current.capital_expenditure, current.revenue);
    if (previous.revenue > 0) derived.revenue_growth = ratio(current.revenue - previous.revenue, previous.revenue);
  }
  derived.debt = String(current.total_debt);
  return derived;
}

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

function Provenance({
  suggestion,
  status,
  help,
}: {
  suggestion: Suggestion | undefined;
  /** Overrides the document's label once the analyst or the form has changed the value. */
  status?: "yours" | "recalculated" | "linked";
  help?: string;
}) {
  if (status) {
    const text = {
      yours: ["#89878133", "#52514e", "Your value", ""],
      recalculated: ["#3987e51a", "#184f95", "Recalculated", "Updated from the financial figures above."],
      linked: ["#3987e51a", "#184f95", "Follows entry multiple", "Change it if you expect to sell at a different multiple."],
    }[status];
    return (
      <div className="mt-1 text-xs text-[var(--text-muted)]">
        <span className="inline-block rounded px-1.5 py-0.5 font-medium" style={{ backgroundColor: text[0], color: text[1] }}>
          {text[2]}
        </span>
        {text[3] && <div className="mt-0.5">{text[3]}</div>}
      </div>
    );
  }
  if (!suggestion) return help ? <div className="mt-1 text-xs text-[var(--text-muted)]">{help}</div> : null;
  const style = BASIS_STYLE[suggestion.basis] ?? BASIS_STYLE.Default;
  const showHelp = help && (suggestion.basis === "Needs input" || suggestion.basis === "Default");
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
      {showHelp && <div className="mt-0.5">{help}</div>}
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
  statuses,
}: {
  fields: AssumptionField[];
  values: AssumptionText;
  onChange: (key: string, value: string) => void;
  suggestions: Record<string, Suggestion>;
  statuses: Record<string, "yours" | "recalculated" | "linked">;
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
                id={`field-${field.key}`}
                type="number"
                step="any"
                value={values[field.key] ?? ""}
                onChange={(e) => onChange(field.key, e.target.value)}
                className={`${INPUT_CLASS} ${
                  !field.optional && (values[field.key] ?? "") === "" ? "border-[var(--status-critical)] bg-[#d03b3b0d]" : ""
                }`}
              />
              {UNIT_SUFFIX[field.kind] && (
                <span className="w-6 shrink-0 text-xs text-[var(--text-muted)]">{UNIT_SUFFIX[field.kind]}</span>
              )}
            </span>
          </label>
          <Provenance
            suggestion={suggestions[field.key]}
            status={statuses[field.key]}
            help={FIELD_HELP[field.key]}
          />
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
  const companyTouched = useRef(false);
  // How each assumption last got its value, when that was not straight from the documents.
  const [statuses, setStatuses] = useState<Record<string, "yours" | "recalculated" | "linked">>({});
  const statusesRef = useRef(statuses);
  statusesRef.current = statuses;
  // Figures the analyst has typed, as "current:revenue". A missing figure counts as supplied
  // once it has been typed, even when the value typed is a genuine zero.
  const [typedFigures, setTypedFigures] = useState<Set<string>>(new Set());
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
  }

  /** The analyst typed a value: keep it, and stop overwriting that field automatically. */
  function setAssumption(key: string, value: string) {
    const linkExit = key === "entry_multiple" && statusesRef.current.exit_multiple !== "yours";
    setAssumptions((current) => ({ ...current, [key]: value, ...(linkExit ? { exit_multiple: value } : {}) }));
    setStatuses((current) => ({ ...current, [key]: "yours", ...(linkExit ? { exit_multiple: "linked" } : {}) }));
  }

  /** A financial figure changed: refresh every assumption that is arithmetic on the statements,
   *  except the ones the analyst has set by hand. */
  function setFinancials(
    period: "current" | "previous",
    next: FinancialStatementInput,
    changed: keyof FinancialStatementInput,
  ) {
    setTypedFigures((existing) => new Set(existing).add(`${period}:${changed}`));
    const current = period === "current" ? next : currentFinancials;
    const previous = period === "previous" ? next : previousFinancials;
    if (period === "current") setCurrentFinancials(next);
    else setPreviousFinancials(next);
    const derived = deriveFromStatements(current, previous);
    const updates: Record<string, string> = {};
    for (const [key, value] of Object.entries(derived)) {
      if (statusesRef.current[key] !== "yours" && assumptions[key] !== value) updates[key] = value;
    }
    if (Object.keys(updates).length === 0) return;
    setAssumptions((existing) => ({ ...existing, ...updates }));
    setStatuses((existing) => {
      const merged = { ...existing };
      for (const key of Object.keys(updates)) merged[key] = "recalculated";
      return merged;
    });
  }

  const readDocuments = useCallback(async (ids: string[]) => {
    setError(null);
    setSuggesting(true);
    try {
      const result = await suggestInputs(ids);
      setSuggested(result);
      setTypedFigures(new Set());
      setCurrentFinancials({ ...zeroFinancials(), ...result.current_financials } as FinancialStatementInput);
      setPreviousFinancials({ ...zeroFinancials(), ...result.previous_financials } as FinancialStatementInput);
      // Values the analyst typed survive a re-read; everything else takes the documents' value.
      const mine = statusesRef.current;
      setAssumptions((existing) => {
        const next: AssumptionText = { ...existing };
        for (const item of result.assumptions) {
          const field = ALL_FIELDS.find((candidate) => candidate.key === item.field);
          if (field && mine[item.field] !== "yours") next[item.field] = toText(item.value, field.kind);
        }
        return next;
      });
      setStatuses((existing) =>
        Object.fromEntries(Object.entries(existing).filter(([, status]) => status === "yours")),
      );
      if (typeof result.competitive_position.value === "string") {
        setCompetitivePosition(result.competitive_position.value);
      }
      setMarketGrowth(toText(result.market_growth_pct.value, "percent"));
      if (!companyTouched.current && typeof result.company_name.value === "string") {
        setCompanyName(result.company_name.value);
      }
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSuggesting(false);
    }
  }, []);

  // Read the documents as soon as the selection settles: no button to remember to press.
  const selectionKey = selectedIds.join(",");
  useEffect(() => {
    if (!selectionKey) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- selection cleared
      setSuggested(null);
      return;
    }
    const timer = window.setTimeout(() => readDocuments(selectionKey.split(",")), 350);
    return () => window.clearTimeout(timer);
  }, [selectionKey, readDocuments]);

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
        const missingAndBlank = read[key] === undefined && !typedFigures.has(`${period}:${key}`);
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

  // What still stands between the analyst and a run, and what merely deserves a second look.
  const blockers: Array<{ text: string; target: string }> = [];
  const checks: Array<{ text: string; target: string }> = [];
  if (!companyName.trim()) blockers.push({ text: "Enter the company name.", target: "field-company" });
  for (const name of missing) {
    if (!typedFigures.has(`current:${name}`) || !typedFigures.has(`previous:${name}`)) {
      blockers.push({
        text: `Enter ${financialLabel(name).toLowerCase()} for both periods (not found in the documents).`,
        target: typedFigures.has(`current:${name}`) ? `fin-previous-${name}` : `fin-current-${name}`,
      });
    }
  }
  for (const field of ALL_FIELDS) {
    const text = assumptions[field.key] ?? "";
    const suggestion = suggestionByField[field.key];
    if (text === "" && !field.optional) {
      blockers.push({ text: `Enter ${field.label.toLowerCase()}.`, target: `field-${field.key}` });
    } else if (suggestion?.basis === "Default" && !statuses[field.key]) {
      checks.push({
        text: `${field.label} is a default (${text}${UNIT_SUFFIX[field.kind]}), not from the documents.`,
        target: `field-${field.key}`,
      });
    }
  }
  const namedPeerCount = peers.filter((peer) => peer.name.trim()).length;
  if (namedPeerCount < 2 && !peerTickers.trim()) {
    blockers.push({ text: "Add at least two comparable companies, or peer tickers.", target: "section-peers" });
  } else if (peersAreExamples) {
    checks.push({ text: "The comparable companies are made-up examples. Replace them.", target: "section-peers" });
  }
  if (usingDocuments && !industryName.trim()) {
    blockers.push({ text: "Enter the industry name.", target: "field-industry" });
  }
  if (suggested && suggested.competitive_position.basis !== "Document") {
    checks.push({ text: "Competitive position was not stated in the documents; set it yourself.", target: "field-position" });
  }

  function jumpTo(target: string) {
    const element = document.getElementById(target);
    if (!element) return;
    // A figure inside the collapsed statements panel must be revealed before it can be focused.
    element.closest("details")?.setAttribute("open", "");
    element.scrollIntoView({ behavior: "smooth", block: "center" });
    if (element instanceof HTMLInputElement || element instanceof HTMLSelectElement) element.focus();
  }
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
          Most of this form fills itself in. Your job is to check it and supply the few things only you know.
        </p>
        <ol className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-4">
          {[
            ["Pick the documents", "Tick everything you have on the company. They are read automatically."],
            ["Check what was read", "Figures and assumptions appear with the page they came from."],
            ["Add what's missing", "The checklist at the bottom names every box that still needs you."],
            ["Run it", "The analysis runs in the background and is saved to the deal."],
          ].map(([title, text], index) => (
            <li key={title} className="rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)] p-3">
              <div className="text-xs font-semibold text-[var(--series-1)]">Step {index + 1}</div>
              <div className="mt-0.5 text-sm font-medium text-[var(--text-primary)]">{title}</div>
              <div className="mt-1 text-xs text-[var(--text-muted)]">{text}</div>
            </li>
          ))}
        </ol>
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
                id="field-company"
                type="text"
                value={companyName}
                onChange={(e) => {
                  companyTouched.current = true;
                  setCompanyName(e.target.value);
                }}
                placeholder="Filled in from the document when you pick one"
                className={`mt-1 ${INPUT_CLASS}`}
              />
              {suggested && !companyTouched.current && typeof suggested.company_name.value === "string" && (
                <span className="mt-1 block text-xs text-[var(--text-muted)]">{suggested.company_name.note}</span>
              )}
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
                <span className="text-sm text-[var(--text-secondary)]">
                  {suggesting
                    ? "Reading the documents..."
                    : suggested
                      ? "Read. The form below is filled in from these documents; values you type yourself are kept."
                      : "The documents will be read automatically."}
                </span>
                {suggested && !suggesting && (
                  <button
                    type="button"
                    onClick={() => readDocuments(selectedIds)}
                    className="text-sm font-medium text-[var(--series-1)] hover:underline"
                  >
                    Read again
                  </button>
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
                  Not found in the documents: <span className="font-medium">{missing.map(financialLabel).join(", ")}</span>.
                  They are outlined in red below with a note on where to find each one. Margins and growth update
                  on their own as you type.
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
                  <FinancialStatementFields
                    value={currentFinancials}
                    onChange={(next, changed) => setFinancials("current", next, changed)}
                    needsInput={missing.filter((name) => !typedFigures.has(`current:${name}`))}
                    idPrefix="fin-current"
                  />
                </div>
                <h3 className="mt-5 text-sm font-semibold text-[var(--text-primary)]">Previous period</h3>
                <div className="mt-2">
                  <FinancialStatementFields
                    value={previousFinancials}
                    onChange={(next, changed) => setFinancials("previous", next, changed)}
                    needsInput={missing.filter((name) => !typedFigures.has(`previous:${name}`))}
                    idPrefix="fin-previous"
                  />
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
              onChange={setAssumption}
              suggestions={suggestionByField}
              statuses={statuses}
            />
          </Section>

          <Section title="4. Capital structure" hint="Same units as the financial statements.">
            <AssumptionGrid
              fields={CAPITAL_FIELDS}
              values={assumptions}
              onChange={setAssumption}
              suggestions={suggestionByField}
              statuses={statuses}
            />
          </Section>

          <Section
            title="5. The deal"
            hint="The purchase price is the entry multiple times current EBITDA. These are your call; nothing in the documents sets them."
          >
            <AssumptionGrid
              fields={DEAL_FIELDS}
              values={assumptions}
              onChange={setAssumption}
              suggestions={suggestionByField}
              statuses={statuses}
            />
          </Section>

          <div id="section-peers" />
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
                  id="field-industry"
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
                    id="field-position"
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

          <section
            className="rounded-lg border-2 bg-[var(--surface-1)] p-5"
            style={{ borderColor: blockers.length > 0 ? "var(--status-critical)" : "var(--status-good)" }}
          >
            <h2 className="text-base font-semibold text-[var(--text-primary)]">
              {blockers.length > 0
                ? `Before you run: ${blockers.length} thing${blockers.length === 1 ? "" : "s"} still needed`
                : "Ready to run"}
            </h2>
            {blockers.length > 0 && (
              <ul className="mt-3 space-y-1.5">
                {blockers.map((item) => (
                  <li key={item.text} className="flex items-start gap-2 text-sm">
                    <span className="mt-0.5 font-semibold text-[var(--status-critical)]">Needed</span>
                    <button type="button" onClick={() => jumpTo(item.target)} className="text-left text-[var(--series-1)] hover:underline">
                      {item.text}
                    </button>
                  </li>
                ))}
              </ul>
            )}
            {checks.length > 0 && (
              <>
                <p className="mt-4 text-xs font-medium text-[var(--text-muted)]">
                  Worth a look (these will not stop the run)
                </p>
                <ul className="mt-1.5 space-y-1.5">
                  {checks.map((item) => (
                    <li key={item.text} className="flex items-start gap-2 text-sm">
                      <span className="mt-0.5 font-semibold" style={{ color: "#9a6700" }}>Check</span>
                      <button type="button" onClick={() => jumpTo(item.target)} className="text-left text-[var(--series-1)] hover:underline">
                        {item.text}
                      </button>
                    </li>
                  ))}
                </ul>
              </>
            )}
            {blockers.length === 0 && checks.length === 0 && (
              <p className="mt-2 text-sm text-[var(--text-secondary)]">Every input is filled in.</p>
            )}

            {error && <p className="mt-4 text-sm text-[var(--status-critical)]">{error}</p>}

            <button
              type="submit"
              disabled={submitting || suggesting || blockers.length > 0}
              className="mt-4 rounded-md bg-[var(--series-1)] px-5 py-2.5 text-sm font-medium text-white hover:opacity-90 disabled:opacity-40"
            >
              {submitting ? "Starting analysis..." : "Run deal analysis"}
            </button>
            {blockers.length > 0 && (
              <span className="ml-3 text-xs text-[var(--text-muted)]">Click an item above to jump to it.</span>
            )}
          </section>
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

// Mirrors the FastAPI backend's JSON contract field-for-field (snake_case kept
// intentionally so shapes can be compared directly against the Python source).
// See: src/pe_analyst/{auth,document_intelligence,rag,deals}/* and src/agents/*, src/lbo/*.

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface UserPublic {
  id: string;
  email: string;
  role: string;
}

export interface Token {
  access_token: string;
  token_type: string;
}

// ---------------------------------------------------------------------------
// Document intelligence
// ---------------------------------------------------------------------------

export interface SourceReference {
  page_number: number;
  excerpt: string;
  confidence: number;
}

export type SectionKind =
  | "income_statement"
  | "balance_sheet"
  | "cash_flow_statement"
  | "risk_factors"
  | "notes"
  | "management_discussion"
  | "other"
  | string;

export interface DocumentSection {
  kind: SectionKind;
  title: string;
  pages: number[];
  references: SourceReference[];
}

export interface StatementLineItem {
  statement: SectionKind;
  label: string;
  raw_values: string[];
  parsed_values: (number | null)[];
  source: SourceReference;
}

export interface ExtractedRiskFactor {
  title: string;
  text: string;
  source: SourceReference;
}

export interface ExtractedNote {
  title: string;
  text: string;
  source: SourceReference;
}

export interface IndustryEvidence {
  topic: string;
  source: string;
  page_number: number;
  excerpt: string;
  claim: string;
  confidence: number;
}

export interface DocumentIntelligenceReport {
  document_id: string;
  file_name: string;
  page_count: number;
  sections: DocumentSection[];
  statement_line_items: StatementLineItem[];
  risk_factors: ExtractedRiskFactor[];
  notes: ExtractedNote[];
  management_discussion: SourceReference[];
  industry_evidence: IndustryEvidence[];
  warnings: string[];
}

export interface DocumentSummary {
  document_id: string;
  file_name: string;
  page_count: number;
  risk_factor_count: number;
  warning_count: number;
}

// ---------------------------------------------------------------------------
// RAG
// ---------------------------------------------------------------------------

export interface Citation {
  document_id: string;
  page_number: number;
  excerpt: string;
  score: number;
}

export interface RAGAnswer {
  answer: string;
  citations: Citation[];
  confidence: number;
  warnings: string[];
}

export interface RAGQueryRequest {
  question: string;
  document_id?: string | null;
}

// ---------------------------------------------------------------------------
// Deal analysis - request
// ---------------------------------------------------------------------------

export interface FinancialStatementInput {
  revenue: number;
  cost_of_goods_sold: number;
  ebitda: number;
  ebit: number;
  net_income: number;
  operating_cash_flow: number;
  capital_expenditure: number;
  total_assets: number;
  shareholders_equity: number;
  total_debt: number;
  interest_expense: number;
  current_assets: number;
  inventory: number;
  current_liabilities: number;
}

export interface DealAnalysisRequest {
  company_name: string;
  // Omit both to have the backend read them from the document named by document_id.
  current_financials?: FinancialStatementInput | null;
  previous_financials?: FinancialStatementInput | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  valuation_inputs: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  risk_inputs?: Record<string, any> | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  industry_inputs?: Record<string, any> | null;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  due_diligence_inputs?: Record<string, any>[] | null;
  document_id?: string | null;
  industry_name?: string;
}

export interface SensitivityRequest {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  lbo_assumptions: Record<string, any>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  operating_projection: Record<string, any>[];
  exit_multiples: number[];
  ebitda_multipliers: number[];
}

// ---------------------------------------------------------------------------
// Deal analysis - response (UnifiedDealReport and everything it nests)
// ---------------------------------------------------------------------------

export type RunStatus = "pending" | "running" | "completed" | "failed" | "skipped";

export interface AgentResponse {
  agent_name: string;
  summary: string;
  confidence: number;
  findings: string[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  metadata: Record<string, any>;
}

export interface AgentRunRecord {
  stage: string;
  agent_name: string;
  status: RunStatus;
  started_at: string | null;
  completed_at: string | null;
  response: AgentResponse | null;
  error: string | null;
}

// Financial
export type FinancialHealth = "Excellent" | "Good" | "Average" | "Weak" | "Distressed";
export type Trend = "Improving" | "Stable" | "Declining";

export interface FinancialFinding {
  title: string;
  description: string;
  severity: string;
}

export interface MetricScore {
  name: string;
  value: number;
  benchmark: number | null;
  unit: string;
}

export interface FinancialSummary {
  company_name: string;
  health: FinancialHealth;
  trend: Trend;
  confidence: number;
  executive_summary: string;
}

export interface FinancialStrength {
  title: string;
  explanation: string;
}

export interface FinancialWeakness {
  title: string;
  explanation: string;
}

export interface FinancialRecommendation {
  recommendation: string;
  reasoning: string;
}

export interface FinancialReport {
  summary: FinancialSummary;
  findings: FinancialFinding[];
  metrics: MetricScore[];
  strengths: FinancialStrength[];
  weaknesses: FinancialWeakness[];
  recommendation: FinancialRecommendation | null;
}

// Valuation
export type ValuationRecommendation = "Accept" | "Watch" | "Reject" | "Insufficient Data";

export interface ValuationMethod {
  name: string;
  enterprise_value: number | null;
  equity_value: number | null;
  value_per_share: number | null;
  weight: number;
  confidence: number;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  assumptions: Record<string, any>;
}

export interface LBOReturnProfile {
  entry_enterprise_value: number;
  exit_enterprise_value: number;
  exit_equity_value: number;
  irr: number;
  moic: number;
  debt_remaining: number;
  holding_period_years: number;
}

export interface ValuationSummary {
  company_name: string;
  intrinsic_value_per_share: number | null;
  fair_value_per_share: number | null;
  current_price_per_share: number | null;
  upside_downside_pct: number | null;
  margin_of_safety_pct: number | null;
  confidence: number;
  recommendation: ValuationRecommendation;
  executive_summary: string;
}

export interface ValuationFinding {
  title: string;
  description: string;
  severity: string;
}

export interface ScenarioOutcome {
  name: string;
  exit_multiple: number;
  irr: number;
  moic: number;
  exit_equity_value: number;
}

export interface ScenarioAnalysis {
  target_irr: number;
  outcomes: ScenarioOutcome[];
  breakeven_exit_multiple: number | null;
}

export interface ValuationReport {
  summary: ValuationSummary;
  methods: ValuationMethod[];
  lbo_returns: LBOReturnProfile | null;
  scenario_analysis: ScenarioAnalysis | null;
  findings: ValuationFinding[];
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  key_assumptions: Record<string, any>;
}

// Risk
export type RiskLevel = "Low" | "Moderate" | "High" | "Critical";

export interface RiskFactor {
  category: string;
  score: number;
  level: RiskLevel;
  rationale: string;
  metric: number | null;
  benchmark: number | null;
}

export interface RiskItem {
  title: string;
  description: string;
  severity: RiskLevel;
  mitigation: string;
}

export interface RiskSummary {
  company_name: string;
  score: number;
  level: RiskLevel;
  confidence: number;
  executive_summary: string;
}

export interface RiskReport {
  summary: RiskSummary;
  factors: RiskFactor[];
  major_risks: RiskItem[];
  mitigations: string[];
  missing_data: string[];
}

// Industry
export type CompetitivePosition = "Leader" | "Strong" | "Neutral" | "Weak";

export interface SourceCitation {
  source: string;
  page_number: number;
  excerpt: string;
  confidence: number;
}

export interface IndustryFinding {
  title: string;
  analysis: string;
  citations: SourceCitation[];
}

export interface CompetitorProfile {
  name: string;
  market_share_pct: number | null;
  positioning: string;
}

export interface IndustrySummary {
  industry_name: string;
  market_growth_pct: number | null;
  competitive_position: CompetitivePosition;
  confidence: number;
  executive_summary: string;
}

export interface IndustryReport {
  summary: IndustrySummary;
  competitors: CompetitorProfile[];
  findings: IndustryFinding[];
  porter_forces: Record<string, number>;
  management_themes: string[];
  evidence_count: number;
}

// Due diligence
export type RedFlagSeverity = "Low" | "Moderate" | "High" | "Critical";
export type DueDiligenceAssessment = "Clear" | "Caution" | "Critical";

export interface RedFlag {
  title: string;
  category: string;
  severity: RedFlagSeverity;
  rationale: string;
  citation: SourceCitation;
}

export interface DueDiligenceSummary {
  company_name: string;
  assessment: DueDiligenceAssessment;
  red_flag_count: number;
  confidence: number;
  executive_summary: string;
}

export interface DueDiligenceReport {
  summary: DueDiligenceSummary;
  red_flags: RedFlag[];
  items_reviewed: number;
}

// Investment committee (scorecard)
export type CommitteeRecommendation = "BUY" | "HOLD" | "REJECT";

export interface CommitteeVote {
  area: string;
  outcome: string;
  rationale: string;
  weight: number;
}

export interface InvestmentCommitteeSummary {
  company_name: string;
  recommendation: CommitteeRecommendation;
  confidence: number;
  target_price: number | null;
  expected_irr: number | null;
  executive_summary: string;
}

export interface InvestmentCommitteeReport {
  summary: InvestmentCommitteeSummary;
  votes: CommitteeVote[];
  investment_thesis: string[];
  top_risks: string[];
  conditions_precedent: string[];
}

// IC simulation (the debate)
export type PartnerPosition = "Advocate" | "Neutral" | "Oppose";

export interface DealPartnerOpinion {
  position: PartnerPosition;
  thesis: string[];
  rationale: string;
}

export type RiskOfficerVerdict = "Clear" | "Conditional" | "Veto";

export interface RiskOfficerOpinion {
  verdict: RiskOfficerVerdict;
  objections: string[];
  required_conditions: string[];
  rationale: string;
}

export type ValueCreationPotential = "Strong" | "Moderate" | "Limited";

export interface OperatingPartnerOpinion {
  potential: ValueCreationPotential;
  value_levers: string[];
  rationale: string;
}

export interface DissentingView {
  member: string;
  position: string;
  rationale: string;
}

export type DriverDirection = "Supports" | "Against";

/** One factor behind the ruling, what it rests on, and the document passages that back it. */
export interface DecisionDriver {
  area: string;
  direction: DriverDirection;
  weight: number | null;
  statement: string;
  basis: string;
  basis_detail: string;
  evidence: SourceCitation[];
}

export interface DecisionExplanation {
  recommendation: string;
  headline: string;
  deciding_rule: string;
  support_weight: number;
  drivers: DecisionDriver[];
  conditions: string[];
  what_would_change: string[];
  evidence_gaps: string[];
}

export interface ICDecision {
  company_name: string;
  final_recommendation: string;
  unanimous: boolean;
  chair_rationale: string;
  committee_vote: InvestmentCommitteeReport;
  deal_partner: DealPartnerOpinion;
  risk_officer: RiskOfficerOpinion;
  operating_partner: OperatingPartnerOpinion;
  dissent: DissentingView[];
  explanation: DecisionExplanation | null;
}

export interface ScenarioCase {
  name: string;
  probability: number;
  revenue_multiplier: number;
  ebitda_multiplier: number;
  exit_multiple: number;
  irr: number;
  moic: number;
  exit_equity_value: number;
  meets_target: boolean;
}

export interface ScenarioReport {
  summary: {
    company_name: string;
    resilience: "Resilient" | "Balanced" | "Fragile";
    target_irr: number;
    probability_weighted_irr: number;
    probability_weighted_moic: number;
    confidence: number;
    executive_summary: string;
  };
  cases: ScenarioCase[];
  breakeven_exit_multiple: number | null;
  capital_preservation_exit_multiple: number | null;
  probability_of_meeting_target: number;
  downside_capital_loss: boolean;
  sensitivity: SensitivityGrid | null;
  findings: string[];
}

export interface InvestmentMemo {
  company_name: string;
  recommendation: string;
  sections: { heading: string; body: string; bullets: string[] }[];
  llm_draft: string | null;
  llm_warnings: string[];
  markdown: string;
}

/** LLM commentary over an agent's deterministic output (absent when no LLM key is set). */
export interface Narrative {
  agent: string;
  commentary: string;
  key_points: string[];
  provider: string | null;
  model: string | null;
  ungrounded_numbers: string[];
  warnings: string[];
}

export interface UnifiedDealReport {
  run_id: string;
  company_name: string;
  status: RunStatus;
  started_at: string | null;
  completed_at: string | null;
  stages: AgentRunRecord[];
  financial_report: FinancialReport | null;
  valuation_report: ValuationReport | null;
  scenario_report: ScenarioReport | null;
  risk_report: RiskReport | null;
  industry_report: IndustryReport | null;
  due_diligence_report: DueDiligenceReport | null;
  investment_committee_report: InvestmentCommitteeReport | null;
  ic_decision: ICDecision | null;
  investment_memo: InvestmentMemo | null;
  narratives: Record<string, Narrative>;
  final_recommendation: string | null;
  failed_stage: string | null;
  error: string | null;
}

// ---------------------------------------------------------------------------
// Sensitivity grid
// ---------------------------------------------------------------------------

export type AnalysisStatus = "pending" | "running" | "completed" | "failed";

/** A saved analysis as shown in the history list. */
export interface DealAnalysisSummary {
  id: string;
  company_name: string;
  status: AnalysisStatus;
  recommendation: string | null;
  document_id: string | null;
  error: string | null;
  created_at: string;
  completed_at: string | null;
}

/** A saved analysis with its report, which is null until the run finishes. */
export interface DealAnalysisRecord extends DealAnalysisSummary {
  report: UnifiedDealReport | null;
}

export interface SensitivityCell {
  exit_multiple: number;
  ebitda_multiplier: number;
  irr: number;
  moic: number;
}

export interface SensitivityGrid {
  exit_multiples: number[];
  ebitda_multipliers: number[];
  cells: SensitivityCell[];
}

import { Link, useLocation } from "react-router-dom";
import { Layout } from "../components/Layout";
import { PipelineTrace } from "../components/PipelineTrace";
import { ScenarioIrrChart, ScenarioMoicChart } from "../components/ScenarioChart";
import { SeverityBadge } from "../components/SeverityBadge";
import { useState } from "react";
import type { InvestmentMemo, Narrative, ScenarioReport, UnifiedDealReport } from "../lib/types";

function Card({ title, children, className = "" }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={`rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)] p-5 ${className}`}>
      <h2 className="text-base font-semibold text-[var(--text-primary)]">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-[var(--text-muted)]">{label}</div>
      <div className="mt-0.5 text-lg font-semibold text-[var(--text-primary)] tabular-nums">{value}</div>
    </div>
  );
}

function pct(v: number | null | undefined): string {
  return v === null || v === undefined ? "—" : `${(v * 100).toFixed(1)}%`;
}

function num(v: number | null | undefined, digits = 2): string {
  return v === null || v === undefined ? "—" : v.toFixed(digits);
}

function AnalystNote({ narrative }: { narrative: Narrative | undefined }) {
  if (!narrative || !narrative.commentary) return null;
  return (
    <div className="mt-4 rounded-md bg-[var(--page-plane)] p-4">
      <p className="text-xs font-medium text-[var(--text-muted)]">
        Analyst commentary ({narrative.model}) &middot; written by an LLM from the figures above
      </p>
      <p className="mt-1 text-sm text-[var(--text-secondary)]">{narrative.commentary}</p>
      {narrative.ungrounded_numbers.length > 0 && (
        <p className="mt-2 text-xs text-[var(--status-warning)]">
          Check before relying on: {narrative.ungrounded_numbers.join(", ")} not found in the agent's output.
        </p>
      )}
    </div>
  );
}

function ScenarioCard({ scenario, narrative }: { scenario: ScenarioReport; narrative?: Narrative }) {
  const { summary } = scenario;
  return (
    <Card title="Scenario stress test">
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Stat label="Resilience" value={summary.resilience} />
        <Stat label="Probability-weighted IRR" value={pct(summary.probability_weighted_irr)} />
        <Stat label="Chance of hitting target" value={pct(scenario.probability_of_meeting_target)} />
        <Stat
          label="Capital-preservation exit"
          value={scenario.capital_preservation_exit_multiple !== null ? `${num(scenario.capital_preservation_exit_multiple, 1)}x` : "—"}
        />
      </div>
      <p className="mt-4 text-sm text-[var(--text-secondary)]">{summary.executive_summary}</p>
      {scenario.downside_capital_loss && (
        <p className="mt-2 text-sm font-medium text-[var(--status-critical)]">The downside case loses equity capital.</p>
      )}
      <div className="mt-5 overflow-hidden rounded-md border border-[var(--border-hairline)]">
        <table className="min-w-full divide-y divide-[var(--gridline)] text-sm">
          <thead className="bg-[var(--page-plane)]">
            <tr>
              {["Scenario", "Probability", "EBITDA", "Exit multiple", "IRR", "MOIC"].map((h) => (
                <th key={h} className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--gridline)]">
            {scenario.cases.map((c) => (
              <tr key={c.name}>
                <td className="px-3 py-2 font-medium text-[var(--text-primary)]">{c.name}</td>
                <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{pct(c.probability)}</td>
                <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{num(c.ebitda_multiplier)}x</td>
                <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{num(c.exit_multiple, 1)}x</td>
                <td className={`px-3 py-2 tabular-nums ${c.meets_target ? "text-[var(--text-primary)]" : "text-[var(--status-warning)]"}`}>{pct(c.irr)}</td>
                <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{num(c.moic)}x</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <AnalystNote narrative={narrative} />
    </Card>
  );
}

function MemoCard({ memo }: { memo: InvestmentMemo }) {
  const [showDraft, setShowDraft] = useState(false);
  const text = showDraft && memo.llm_draft ? memo.llm_draft : memo.markdown;
  const download = () => {
    const url = URL.createObjectURL(new Blob([text], { type: "text/markdown" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `${memo.company_name.replace(/\W+/g, "_")}_investment_memo.md`;
    link.click();
    URL.revokeObjectURL(url);
  };
  return (
    <Card title="Investment memo">
      <div className="flex flex-wrap items-center gap-3">
        {memo.llm_draft && (
          <div className="inline-flex rounded-md border border-[var(--border-hairline)] text-xs">
            <button type="button" onClick={() => setShowDraft(false)} className={`px-3 py-1 ${!showDraft ? "bg-[var(--page-plane)] font-semibold" : ""}`}>
              Structured
            </button>
            <button type="button" onClick={() => setShowDraft(true)} className={`px-3 py-1 ${showDraft ? "bg-[var(--page-plane)] font-semibold" : ""}`}>
              LLM draft
            </button>
          </div>
        )}
        <button type="button" onClick={download} className="text-sm font-medium text-[var(--series-1)]">
          Download .md
        </button>
      </div>
      {showDraft && memo.llm_warnings.length > 0 && (
        <p className="mt-3 text-xs text-[var(--status-warning)]">{memo.llm_warnings.join(" ")}</p>
      )}
      <pre className="mt-4 max-h-[32rem] overflow-auto whitespace-pre-wrap rounded-md bg-[var(--page-plane)] p-4 font-sans text-sm text-[var(--text-secondary)]">
        {text}
      </pre>
    </Card>
  );
}

export function DealReportPage() {
  const location = useLocation();
  const report = (location.state as { report?: UnifiedDealReport } | null)?.report;

  if (!report) {
    return (
      <Layout>
        <div className="max-w-2xl rounded-lg border border-[var(--border-hairline)] bg-[var(--surface-1)] p-6">
          <h1 className="text-lg font-semibold text-[var(--text-primary)]">No report loaded</h1>
          <p className="mt-2 text-sm text-[var(--text-secondary)]">
            Deal reports are held in memory for this session only (the backend doesn't persist runs). Run a new
            analysis to see a report here.
          </p>
          <Link to="/analysis/new" className="mt-4 inline-block text-sm font-medium text-[var(--series-1)]">
            Start a new analysis &rarr;
          </Link>
        </div>
      </Layout>
    );
  }

  const {
    company_name,
    status,
    stages,
    failed_stage,
    error,
    final_recommendation,
    valuation_report,
    risk_report,
    due_diligence_report,
    industry_report,
    ic_decision,
    scenario_report,
    investment_memo,
  } = report;
  const narratives = report.narratives ?? {};

  return (
    <Layout>
      <div className="max-w-5xl pb-16 space-y-6">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--text-primary)]">{company_name}</h1>
            <p className="mt-1 text-sm text-[var(--text-secondary)]">
              Run status: <span className="font-medium capitalize">{status}</span>
              {failed_stage && (
                <span className="text-[var(--status-critical)]"> &mdash; failed at stage "{failed_stage}"</span>
              )}
            </p>
          </div>
          {final_recommendation && (
            <div className="shrink-0">
              <SeverityBadge level={final_recommendation} />
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-md border border-[var(--status-critical)] bg-[#d03b3b0d] px-4 py-3 text-sm text-[var(--text-primary)]">
            {error}
          </div>
        )}

        <Card title="Pipeline trace">
          <PipelineTrace stages={stages} />
        </Card>

        {valuation_report && (
          <Card title="Valuation">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Recommendation" value={<SeverityBadge level={valuation_report.summary.recommendation} />} />
              <Stat label="Fair value / share" value={valuation_report.summary.fair_value_per_share !== null ? `$${num(valuation_report.summary.fair_value_per_share)}` : "—"} />
              <Stat label="Upside / downside" value={pct(valuation_report.summary.upside_downside_pct)} />
              <Stat label="Confidence" value={pct(valuation_report.summary.confidence)} />
            </div>
            <p className="mt-4 text-sm text-[var(--text-secondary)]">{valuation_report.summary.executive_summary}</p>
            <AnalystNote narrative={narratives["Valuation Agent"]} />

            {valuation_report.lbo_returns && (
              <div className="mt-5 grid grid-cols-2 gap-4 sm:grid-cols-4 rounded-md bg-[var(--page-plane)] p-4">
                <Stat label="Entry EV" value={`$${num(valuation_report.lbo_returns.entry_enterprise_value, 0)}`} />
                <Stat label="Exit EV" value={`$${num(valuation_report.lbo_returns.exit_enterprise_value, 0)}`} />
                <Stat label="Base IRR" value={pct(valuation_report.lbo_returns.irr)} />
                <Stat label="Base MOIC" value={`${num(valuation_report.lbo_returns.moic)}x`} />
              </div>
            )}

            {valuation_report.scenario_analysis && valuation_report.scenario_analysis.outcomes.length > 0 && (
              <div className="mt-6">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-[var(--text-primary)]">Scenario analysis</h3>
                  <div className="text-xs text-[var(--text-muted)] tabular-nums">
                    Target IRR: {pct(valuation_report.scenario_analysis.target_irr)}
                    {valuation_report.scenario_analysis.breakeven_exit_multiple !== null && (
                      <> &middot; Breakeven exit multiple: {num(valuation_report.scenario_analysis.breakeven_exit_multiple, 1)}x</>
                    )}
                  </div>
                </div>
                <div className="mt-3 grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div>
                    <p className="text-xs font-medium text-[var(--text-muted)]">IRR by scenario</p>
                    <ScenarioIrrChart outcomes={valuation_report.scenario_analysis.outcomes} />
                  </div>
                  <div>
                    <p className="text-xs font-medium text-[var(--text-muted)]">MOIC by scenario</p>
                    <ScenarioMoicChart outcomes={valuation_report.scenario_analysis.outcomes} />
                  </div>
                </div>
              </div>
            )}

            {valuation_report.methods.length > 0 && (
              <div className="mt-6 overflow-hidden rounded-md border border-[var(--border-hairline)]">
                <table className="min-w-full divide-y divide-[var(--gridline)] text-sm">
                  <thead className="bg-[var(--page-plane)]">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Method</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Enterprise value</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Value / share</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Weight</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Confidence</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--gridline)]">
                    {valuation_report.methods.map((m, i) => (
                      <tr key={i}>
                        <td className="px-3 py-2 font-medium text-[var(--text-primary)]">{m.name}</td>
                        <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{m.enterprise_value !== null ? `$${num(m.enterprise_value, 0)}` : "—"}</td>
                        <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{m.value_per_share !== null ? `$${num(m.value_per_share)}` : "—"}</td>
                        <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{pct(m.weight)}</td>
                        <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{pct(m.confidence)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )}

        {scenario_report && (
          <ScenarioCard scenario={scenario_report} narrative={narratives["Scenario Analysis Agent"]} />
        )}

        {risk_report && (
          <Card title="Risk">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Risk level" value={<SeverityBadge level={risk_report.summary.level} />} />
              <Stat label="Risk score" value={num(risk_report.summary.score, 1)} />
              <Stat label="Confidence" value={pct(risk_report.summary.confidence)} />
            </div>
            <p className="mt-4 text-sm text-[var(--text-secondary)]">{risk_report.summary.executive_summary}</p>
            <AnalystNote narrative={narratives["Risk Agent"]} />

            {risk_report.major_risks.length > 0 && (
              <div className="mt-5 overflow-hidden rounded-md border border-[var(--border-hairline)]">
                <table className="min-w-full divide-y divide-[var(--gridline)] text-sm">
                  <thead className="bg-[var(--page-plane)]">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Risk</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Severity</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Mitigation</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--gridline)]">
                    {risk_report.major_risks.map((r, i) => (
                      <tr key={i}>
                        <td className="px-3 py-2 align-top">
                          <div className="font-medium text-[var(--text-primary)]">{r.title}</div>
                          <div className="text-xs text-[var(--text-secondary)]">{r.description}</div>
                        </td>
                        <td className="px-3 py-2 align-top"><SeverityBadge level={r.severity} /></td>
                        <td className="px-3 py-2 align-top text-[var(--text-secondary)]">{r.mitigation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        )}

        {due_diligence_report && (
          <Card title="Due diligence red flags">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Assessment" value={<SeverityBadge level={due_diligence_report.summary.assessment} />} />
              <Stat label="Red flags" value={due_diligence_report.summary.red_flag_count} />
              <Stat label="Items reviewed" value={due_diligence_report.items_reviewed} />
              <Stat label="Confidence" value={pct(due_diligence_report.summary.confidence)} />
            </div>
            <p className="mt-4 text-sm text-[var(--text-secondary)]">{due_diligence_report.summary.executive_summary}</p>

            {due_diligence_report.red_flags.length > 0 ? (
              <div className="mt-5 overflow-hidden rounded-md border border-[var(--border-hairline)]">
                <table className="min-w-full divide-y divide-[var(--gridline)] text-sm">
                  <thead className="bg-[var(--page-plane)]">
                    <tr>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Flag</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Category</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Severity</th>
                      <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Source</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[var(--gridline)]">
                    {due_diligence_report.red_flags.map((f, i) => (
                      <tr key={i}>
                        <td className="px-3 py-2 align-top">
                          <div className="font-medium text-[var(--text-primary)]">{f.title}</div>
                          <div className="text-xs text-[var(--text-secondary)]">{f.rationale}</div>
                        </td>
                        <td className="px-3 py-2 align-top text-[var(--text-secondary)]">{f.category}</td>
                        <td className="px-3 py-2 align-top"><SeverityBadge level={f.severity} /></td>
                        <td className="px-3 py-2 align-top text-xs text-[var(--text-muted)]">
                          p.{f.citation.page_number} &middot; {(f.citation.confidence * 100).toFixed(0)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="mt-3 text-sm text-[var(--text-muted)]">No red flags identified.</p>
            )}
          </Card>
        )}

        {industry_report && (
          <Card title="Industry">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Industry" value={industry_report.summary.industry_name} />
              <Stat label="Competitive position" value={industry_report.summary.competitive_position} />
              <Stat label="Market growth" value={pct(industry_report.summary.market_growth_pct)} />
              <Stat label="Confidence" value={pct(industry_report.summary.confidence)} />
            </div>
            <p className="mt-4 text-sm text-[var(--text-secondary)]">{industry_report.summary.executive_summary}</p>
            <AnalystNote narrative={narratives["Industry Agent"]} />
          </Card>
        )}

        {ic_decision && (
          <Card title="Investment Committee debate" className="border-2 border-[var(--series-1)]">
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <div className="text-xs text-[var(--text-muted)]">Chairperson's final ruling</div>
                <div className="mt-0.5 flex items-center gap-2">
                  <SeverityBadge level={ic_decision.final_recommendation} />
                  <span className="text-sm text-[var(--text-secondary)]">
                    {ic_decision.unanimous ? "Unanimous" : "Not unanimous"}
                  </span>
                </div>
              </div>
            </div>
            <p className="mt-3 text-sm text-[var(--text-secondary)]">{ic_decision.chair_rationale}</p>

            {ic_decision.dissent.length > 0 && (
              <div className="mt-4 rounded-md border border-[var(--status-warning)] bg-[#fab21914] p-4">
                <p className="text-sm font-semibold text-[var(--text-primary)]">Dissent on record</p>
                <ul className="mt-2 space-y-2">
                  {ic_decision.dissent.map((d, i) => (
                    <li key={i} className="text-sm text-[var(--text-secondary)]">
                      <span className="font-medium text-[var(--text-primary)]">{d.member}</span> &mdash; {d.position}: {d.rationale}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Committee scorecard */}
            {ic_decision.committee_vote.votes.length > 0 && (
              <div className="mt-6">
                <h3 className="text-sm font-semibold text-[var(--text-primary)]">Committee scorecard</h3>
                <div className="mt-2 overflow-hidden rounded-md border border-[var(--border-hairline)]">
                  <table className="min-w-full divide-y divide-[var(--gridline)] text-sm">
                    <thead className="bg-[var(--page-plane)]">
                      <tr>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Area</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Outcome</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Weight</th>
                        <th className="px-3 py-2 text-left text-xs font-semibold text-[var(--text-muted)] uppercase">Rationale</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[var(--gridline)]">
                      {ic_decision.committee_vote.votes.map((v, i) => (
                        <tr key={i}>
                          <td className="px-3 py-2 font-medium text-[var(--text-primary)]">{v.area}</td>
                          <td className="px-3 py-2 text-[var(--text-secondary)]">{v.outcome}</td>
                          <td className="px-3 py-2 tabular-nums text-[var(--text-secondary)]">{pct(v.weight)}</td>
                          <td className="px-3 py-2 text-[var(--text-secondary)]">{v.rationale}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Personas */}
            <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="rounded-md border border-[var(--border-hairline)] p-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-[var(--text-primary)]">Deal Partner</h4>
                  <SeverityBadge level={ic_decision.deal_partner.position === "Advocate" ? "BUY" : ic_decision.deal_partner.position === "Oppose" ? "REJECT" : "HOLD"} />
                </div>
                <p className="mt-2 text-xs text-[var(--text-muted)]">{ic_decision.deal_partner.position}</p>
                <p className="mt-2 text-sm text-[var(--text-secondary)]">{ic_decision.deal_partner.rationale}</p>
                {ic_decision.deal_partner.thesis.length > 0 && (
                  <ul className="mt-2 list-disc pl-4 space-y-1 text-sm text-[var(--text-secondary)]">
                    {ic_decision.deal_partner.thesis.map((t, i) => (
                      <li key={i}>{t}</li>
                    ))}
                  </ul>
                )}
              </div>

              <div className="rounded-md border border-[var(--border-hairline)] p-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-[var(--text-primary)]">Risk Officer</h4>
                  <SeverityBadge level={ic_decision.risk_officer.verdict} />
                </div>
                <p className="mt-2 text-sm text-[var(--text-secondary)]">{ic_decision.risk_officer.rationale}</p>
                {ic_decision.risk_officer.objections.length > 0 && (
                  <>
                    <p className="mt-2 text-xs font-medium text-[var(--text-muted)]">Objections</p>
                    <ul className="mt-1 list-disc pl-4 space-y-1 text-sm text-[var(--text-secondary)]">
                      {ic_decision.risk_officer.objections.map((o, i) => (
                        <li key={i}>{o}</li>
                      ))}
                    </ul>
                  </>
                )}
                {ic_decision.risk_officer.required_conditions.length > 0 && (
                  <>
                    <p className="mt-2 text-xs font-medium text-[var(--text-muted)]">Required conditions</p>
                    <ul className="mt-1 list-disc pl-4 space-y-1 text-sm text-[var(--text-secondary)]">
                      {ic_decision.risk_officer.required_conditions.map((c, i) => (
                        <li key={i}>{c}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>

              <div className="rounded-md border border-[var(--border-hairline)] p-4">
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-semibold text-[var(--text-primary)]">Operating Partner</h4>
                  <span className="text-xs font-medium text-[var(--text-secondary)]">{ic_decision.operating_partner.potential}</span>
                </div>
                <p className="mt-2 text-sm text-[var(--text-secondary)]">{ic_decision.operating_partner.rationale}</p>
                {ic_decision.operating_partner.value_levers.length > 0 && (
                  <>
                    <p className="mt-2 text-xs font-medium text-[var(--text-muted)]">Value creation levers</p>
                    <ul className="mt-1 list-disc pl-4 space-y-1 text-sm text-[var(--text-secondary)]">
                      {ic_decision.operating_partner.value_levers.map((l, i) => (
                        <li key={i}>{l}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </div>
          </Card>
        )}

        {investment_memo && <MemoCard memo={investment_memo} />}
      </div>
    </Layout>
  );
}

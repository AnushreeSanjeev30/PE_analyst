import type { FinancialStatementInput } from "../lib/types";

const FIELD_LABELS: Array<[keyof FinancialStatementInput, string]> = [
  ["revenue", "Revenue"],
  ["cost_of_goods_sold", "Cost of goods sold"],
  ["ebitda", "EBITDA"],
  ["ebit", "EBIT"],
  ["net_income", "Net income"],
  ["operating_cash_flow", "Operating cash flow"],
  ["capital_expenditure", "Capital expenditure"],
  ["total_assets", "Total assets"],
  ["shareholders_equity", "Shareholders' equity"],
  ["total_debt", "Total debt"],
  ["interest_expense", "Interest expense"],
  ["current_assets", "Current assets"],
  ["inventory", "Inventory"],
  ["current_liabilities", "Current liabilities"],
];

export function FinancialStatementFields({
  value,
  onChange,
}: {
  value: FinancialStatementInput;
  onChange: (next: FinancialStatementInput) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {FIELD_LABELS.map(([key, label]) => (
        <label key={key} className="block">
          <span className="block text-xs font-medium text-[var(--text-secondary)]">{label}</span>
          <input
            type="number"
            step="any"
            value={value[key]}
            onChange={(e) => onChange({ ...value, [key]: Number(e.target.value) })}
            className="mt-1 w-full rounded-md border border-[var(--border-hairline)] px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)]"
          />
        </label>
      ))}
    </div>
  );
}

export const DEFAULT_FINANCIALS: FinancialStatementInput = {
  revenue: 1000.0,
  cost_of_goods_sold: 600.0,
  ebitda: 220.0,
  ebit: 150.0,
  net_income: 100.0,
  operating_cash_flow: 140.0,
  capital_expenditure: 40.0,
  total_assets: 1000.0,
  shareholders_equity: 400.0,
  total_debt: 200.0,
  interest_expense: 20.0,
  current_assets: 200.0,
  inventory: 50.0,
  current_liabilities: 180.0,
};

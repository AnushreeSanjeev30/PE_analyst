import type { FinancialStatementInput } from "../lib/types";

// Label, and where an analyst finds the figure in a set of accounts.
export const FINANCIAL_FIELDS: Array<[keyof FinancialStatementInput, string, string]> = [
  ["revenue", "Revenue", "Income statement, top line (total revenues or net sales)."],
  ["cost_of_goods_sold", "Cost of goods sold", "Income statement: cost of revenue or cost of sales."],
  ["ebitda", "EBITDA", "Operating income plus depreciation and amortization."],
  ["ebit", "EBIT", "Income statement: operating income (income from operations)."],
  ["net_income", "Net income", "Income statement, bottom line."],
  ["operating_cash_flow", "Operating cash flow", "Cash flow statement: net cash from operating activities."],
  ["capital_expenditure", "Capital expenditure", "Cash flow statement: purchases of property and equipment."],
  ["total_assets", "Total assets", "Balance sheet."],
  ["shareholders_equity", "Shareholders' equity", "Balance sheet: total stockholders' equity."],
  ["total_debt", "Total debt", "Balance sheet: short-term plus long-term borrowings."],
  ["interest_expense", "Interest expense", "Income statement: interest or finance costs."],
  ["current_assets", "Current assets", "Balance sheet: total current assets."],
  ["inventory", "Inventory", "Balance sheet. Enter 0 for a business that holds none."],
  ["current_liabilities", "Current liabilities", "Balance sheet: total current liabilities."],
];

export function financialLabel(key: string): string {
  return FINANCIAL_FIELDS.find(([name]) => name === key)?.[1] ?? key.replace(/_/g, " ");
}

export function FinancialStatementFields({
  value,
  onChange,
  needsInput = [],
  idPrefix = "",
}: {
  value: FinancialStatementInput;
  /** Called with the new statement and the field that was typed into. */
  onChange: (next: FinancialStatementInput, changed: keyof FinancialStatementInput) => void;
  /** Fields the documents did not supply: outlined, with a note on where to find them. */
  needsInput?: string[];
  /** Prefix for input ids, so a checklist can jump to a field. */
  idPrefix?: string;
}) {
  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {FINANCIAL_FIELDS.map(([key, label, hint]) => {
        const flagged = needsInput.includes(key);
        return (
          <label key={key} className="block" title={hint}>
            <span className="block text-xs font-medium text-[var(--text-secondary)]">{label}</span>
            <input
              id={idPrefix ? `${idPrefix}-${key}` : undefined}
              type="number"
              step="any"
              value={value[key]}
              onChange={(e) => onChange({ ...value, [key]: Number(e.target.value) }, key)}
              className={`mt-1 w-full rounded-md border px-2 py-1.5 text-sm outline-none focus:ring-2 focus:ring-[var(--series-1)] ${
                flagged ? "border-[var(--status-critical)] bg-[#d03b3b0d]" : "border-[var(--border-hairline)]"
              }`}
            />
            {flagged && (
              <span className="mt-1 block text-xs text-[var(--status-critical)]">
                Not found. {hint} Type 0 if it really is zero.
              </span>
            )}
          </label>
        );
      })}
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

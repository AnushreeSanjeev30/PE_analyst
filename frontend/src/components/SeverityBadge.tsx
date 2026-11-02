// Status colors are fixed/reserved (never reused for categorical series) and
// always paired with a text label, per the dataviz skill's status-palette rule.
const LEVEL_STYLES: Record<string, { bg: string; fg: string; label: string }> = {
  Low: { bg: "#0ca30c1a", fg: "#0ca30c", label: "Low" },
  Moderate: { bg: "#fab2191a", fg: "#9a6700", label: "Moderate" },
  High: { bg: "#ec835a1a", fg: "#b24a26", label: "High" },
  Critical: { bg: "#d03b3b1a", fg: "#d03b3b", label: "Critical" },
  Clear: { bg: "#0ca30c1a", fg: "#0ca30c", label: "Clear" },
  Caution: { bg: "#fab2191a", fg: "#9a6700", label: "Caution" },
  Veto: { bg: "#d03b3b1a", fg: "#d03b3b", label: "Veto" },
  Conditional: { bg: "#fab2191a", fg: "#9a6700", label: "Conditional" },
  BUY: { bg: "#0ca30c1a", fg: "#0ca30c", label: "BUY" },
  HOLD: { bg: "#fab2191a", fg: "#9a6700", label: "HOLD" },
  REJECT: { bg: "#d03b3b1a", fg: "#d03b3b", label: "REJECT" },
};

export function SeverityBadge({ level }: { level: string }) {
  const style = LEVEL_STYLES[level] ?? { bg: "#89878133", fg: "#52514e", label: level };
  return (
    <span
      className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium"
      style={{ backgroundColor: style.bg, color: style.fg }}
    >
      {style.label}
    </span>
  );
}

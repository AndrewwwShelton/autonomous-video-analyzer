// Monetization badge — YT Studio's $ icon language:
// green $ = Monetizable, yellow $ = Restricted (limited ads), gray = not analyzed.
export function MonetizationBadge({ verdict, compact = false }) {
  const mode =
    verdict === "Monetizable" ? "on" : verdict === "Restricted" ? "limited" : "none";
  const label =
    verdict === "Monetizable" ? "On" : verdict === "Restricted" ? "Limited" : "—";
  return (
    <span className={`mon mon--${mode}`} title={verdict ?? "Not analyzed yet"}>
      <span className="mon__icon">
        <span className="material-symbols-outlined">attach_money</span>
      </span>
      {!compact && <span className="mon__label">{label}</span>}
    </span>
  );
}

// Status palette — fixed across light/dark (validated: >=3:1 on both surfaces,
// worst adjacent CVD ΔE 16.4). Always paired with a text label, so the color
// never carries the meaning on its own.
export const SEVERITY_COLORS = {
  High: "#d03b3b",
  Medium: "#ec835a",
  Low: "#fab219",
  "Ad spot": "#0ca30c",
};

export function SeverityChip({ value }) {
  const color = SEVERITY_COLORS[value] ?? "#717171";
  return (
    <span className="chip" style={{ "--chip-c": color }}>
      <span className="chip__dot" style={{ background: color }} />
      {value}
    </span>
  );
}

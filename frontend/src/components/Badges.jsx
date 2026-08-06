// Monetization badge — YT Studio's $ icon language:
//   green  $  Monetizable  — nothing blocking found
//   yellow $  Review       — risks found, but context suggests they may be rendered
//   red    $  Restricted   — treated as real
//   gray   $  not analyzed
// "Review" exists because a binary verdict was the flaw this tool set out to fix:
// restricting a video for a weapon drawn inside a game is the same context-blind
// call the project criticises. See src/pipeline/orchestrator.assess_compliance.
const MONETIZATION = {
  Monetizable: { mode: "on", label: "On" },
  Review: { mode: "review", label: "Review" },
  Restricted: { mode: "restricted", label: "Limited" },
};

export function MonetizationBadge({ verdict, compact = false, reason }) {
  const { mode, label } = MONETIZATION[verdict] ?? { mode: "none", label: "—" };
  return (
    <span className={`mon mon--${mode}`} title={reason ?? verdict ?? "Not analyzed yet"}>
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

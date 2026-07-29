/* Chart primitives.
 *
 * Deliberately CSS-driven rather than SVG: they stay readable at every breakpoint,
 * and the value is always rendered as text beside the bar — so the chart doubles as
 * its own table view and never encodes meaning in color alone.
 *
 * Color rules followed here:
 * - A count-by-category chart is ONE series, so it gets ONE hue (no rainbow).
 * - Severity is a status, so it keeps the fixed status palette used everywhere else.
 */
import { SEVERITY_COLORS } from "./Badges";

export function BarList({ rows, color = "var(--blue)", unit = "", emptyText = "No data yet" }) {
  if (!rows?.length) return <p className="chart-empty">{emptyText}</p>;
  const max = Math.max(...rows.map((r) => r.value), 1);
  return (
    <ul className="barlist">
      {rows.map((r) => (
        <li key={r.label}>
          <span className="barlist__label" title={r.label}>{r.label}</span>
          <span className="barlist__track">
            <span
              className="barlist__fill"
              style={{
                width: `${(r.value / max) * 100}%`,
                background: r.color ?? color,
              }}
            />
          </span>
          <span className="barlist__value">
            {r.value}{unit}
          </span>
        </li>
      ))}
    </ul>
  );
}

/** Severity uses the fixed status palette so it matches the timeline and chips. */
export function SeverityBars({ rows }) {
  const order = ["High", "Medium", "Low"];
  const sorted = [...(rows ?? [])].sort(
    (a, b) => order.indexOf(a.label) - order.indexOf(b.label)
  );
  return (
    <BarList
      rows={sorted.map((r) => ({ ...r, color: SEVERITY_COLORS[r.label] }))}
      emptyText="No audio flags recorded yet"
    />
  );
}

/** Two-segment stacked bar for the Monetizable / Restricted split. */
export function VerdictSplit({ monetizable, restricted }) {
  const total = monetizable + restricted;
  if (!total) return <p className="chart-empty">Nothing analysed yet</p>;
  const pct = (n) => (n / total) * 100;
  return (
    <div className="verdict">
      <div className="verdict__bar" role="img"
           aria-label={`${monetizable} monetizable, ${restricted} restricted`}>
        {monetizable > 0 && (
          <span className="verdict__seg" style={{ width: `${pct(monetizable)}%`, background: "var(--good)" }} />
        )}
        {restricted > 0 && (
          <span className="verdict__seg" style={{ width: `${pct(restricted)}%`, background: "var(--mon-yellow)" }} />
        )}
      </div>
      <div className="verdict__legend">
        <span><i style={{ background: "var(--good)" }} />Monetizable <b>{monetizable}</b></span>
        <span><i style={{ background: "var(--mon-yellow)" }} />Restricted <b>{restricted}</b></span>
      </div>
    </div>
  );
}

export function StatCard({ value, label, hint, tone }) {
  return (
    <div className="card stat">
      <div className="stat__value" style={tone ? { color: tone } : undefined}>{value}</div>
      <div className="stat__label">{label}</div>
      {hint && <div className="stat__hint">{hint}</div>}
    </div>
  );
}

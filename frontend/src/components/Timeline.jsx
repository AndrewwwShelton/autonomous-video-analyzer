import { useLayoutEffect, useRef, useState } from "react";
import { fmtTime } from "../api";
import { SEVERITY_COLORS } from "./Badges";

const LANES = ["Audio", "Visual", "Ad spots"];
const LANE_H = 44;
const BAR_H = 18;
const AXIS_H = 24;
const HEIGHT = LANES.length * LANE_H + AXIS_H;

function tickStep(duration) {
  for (const s of [1, 2, 5, 10, 15, 30, 60, 120, 300, 600])
    if (duration / s <= 9) return s;
  return 900;
}

// Map flags into renderable events. Visual flags are instants — give them a
// minimum visible width. Category → severity buckets share one color key.
function buildEvents(audio, visual, adSpots, duration) {
  const minW = Math.max(0.6, duration * 0.01);
  const ev = [];
  for (const f of audio)
    ev.push({
      lane: 0, start: f.timestamp_start,
      end: Math.max(f.timestamp_end, f.timestamp_start + minW),
      key: f.severity, label: `“${f.word_flagged}”`, detail: f.transcript_context,
    });
  for (const f of visual)
    ev.push({
      lane: 1, start: Math.max(0, f.frame_timestamp - minW / 2),
      end: f.frame_timestamp + minW / 2,
      key: f.risk_category === "Substance" ? "Medium" : "High",
      label: f.object_detected,
      detail: `${f.risk_category} · confidence ${f.confidence_score.toFixed(2)}`,
    });
  for (const s of adSpots)
    ev.push({
      lane: 2, start: s.timestamp_start, end: s.timestamp_end,
      key: "Ad spot", label: (s.spot_type ?? "spot").replace("_", " "),
      detail: `suitability ${s.suitability_score?.toFixed(2)}`,
    });
  return ev;
}

export default function Timeline({ duration, audio, visual, adSpots, currentTime, onSeek }) {
  const wrapRef = useRef(null);
  const [width, setWidth] = useState(800);
  const [tip, setTip] = useState(null);

  useLayoutEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setWidth(el.clientWidth - 76));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const events = buildEvents(audio, visual, adSpots, duration);
  const x = (t) => (t / Math.max(duration, 1)) * width;
  const step = tickStep(duration);
  const ticks = [];
  for (let t = 0; t <= duration; t += step) ticks.push(t);

  return (
    <div ref={wrapRef} style={{ position: "relative" }}>
      <div className="timeline">
        <div className="timeline__labels">
          {LANES.map((l) => <div key={l}>{l}</div>)}
        </div>
        <svg width={width} height={HEIGHT}>
          {ticks.map((t) => (
            <g key={t}>
              <line className="timeline__grid"
                    x1={x(t)} y1={0} x2={x(t)} y2={HEIGHT - AXIS_H} />
              <text className="timeline__tick"
                    x={x(t)} y={HEIGHT - 8} textAnchor="middle">
                {fmtTime(t)}
              </text>
            </g>
          ))}
          <line className="timeline__axis"
                x1={0} y1={HEIGHT - AXIS_H} x2={width} y2={HEIGHT - AXIS_H} />

          {events.map((ev, i) => (
            <rect
              key={i}
              className="timeline__bar"
              x={x(ev.start)}
              y={ev.lane * LANE_H + (LANE_H - BAR_H) / 2}
              width={Math.max(4, x(ev.end) - x(ev.start))}
              height={BAR_H}
              rx={4}
              fill={SEVERITY_COLORS[ev.key] ?? "#717171"}
              tabIndex={0}
              role="button"
              aria-label={`${LANES[ev.lane]} event at ${fmtTime(ev.start)}: ${ev.label}, ${ev.key}. Jump to this moment.`}
              onClick={() => onSeek?.(ev.start)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onSeek?.(ev.start);
                }
              }}
              onFocus={(e) => {
                const r = wrapRef.current.getBoundingClientRect();
                const b = e.target.getBoundingClientRect();
                setTip({ x: b.left - r.left + b.width / 2, y: b.top - r.top, ev });
              }}
              onBlur={() => setTip(null)}
              onMouseMove={(e) => {
                const r = wrapRef.current.getBoundingClientRect();
                setTip({ x: e.clientX - r.left, y: e.clientY - r.top, ev });
              }}
              onMouseLeave={() => setTip(null)}
            />
          ))}

          {currentTime > 0 && currentTime <= duration && (
            <g>
              <line className="timeline__playhead"
                    x1={x(currentTime)} y1={0} x2={x(currentTime)} y2={HEIGHT - AXIS_H} />
              <path className="timeline__playhead-cap"
                    d={`M ${x(currentTime) - 5} 0 L ${x(currentTime) + 5} 0 L ${x(currentTime)} 7 Z`} />
            </g>
          )}
        </svg>
      </div>

      <div className="timeline-legend">
        {Object.entries(SEVERITY_COLORS).map(([k, c]) => (
          <span key={k}>
            <span className="chip__dot" style={{ background: c }} /> {k}
          </span>
        ))}
      </div>

      {tip && (
        <div className="tooltip" style={{ left: tip.x, top: tip.y }}>
          <b>{fmtTime(tip.ev.start)} — {tip.ev.label}</b>
          <span className="muted">{tip.ev.key}{tip.ev.detail ? ` · ${tip.ev.detail}` : ""}</span>
        </div>
      )}
    </div>
  );
}

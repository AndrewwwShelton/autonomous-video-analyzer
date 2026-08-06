import { useEffect, useState } from "react";
import { api } from "../api";
import { BarList, SeverityBars, StatCard, VerdictSplit } from "../components/Charts";

export default function AnalyticsPage({ toast }) {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.stats().then(setStats).catch((e) => toast(e.message));
  }, [toast]);

  if (!stats) return <div className="skeleton-page" aria-busy="true" />;

  const {
    totals, verdicts, severity_breakdown, risk_category_breakdown,
    top_words, top_objects, spot_types,
  } = stats;

  if (totals.audio_flags + totals.visual_flags + totals.ad_spots === 0) {
    return (
      <>
        <h1 className="page-title">Analytics</h1>
        <div className="card empty">
          <span className="material-symbols-outlined">bar_chart</span>
          <h3>No analysis data yet</h3>
          <p>Run checks on a video and its results will be aggregated here.</p>
        </div>
      </>
    );
  }

  return (
    <>
      <h1 className="page-title">Analytics</h1>
      <p className="muted-note" style={{ marginTop: -12, marginBottom: 20 }}>
        Aggregated across every analysed video in the library.
      </p>

      <div className="stats stats--3">
        <StatCard value={totals.audio_flags} label="Audio flags" />
        <StatCard value={totals.visual_flags} label="Visual risks" />
        <StatCard value={`${Math.round(totals.ad_inventory_sec)}s`} label="Ad inventory" />
      </div>

      <div className="dash-grid">
        <section className="card form-card">
          <h3>Monetization outcome</h3>
          <VerdictSplit monetizable={verdicts.Monetizable} review={verdicts.Review}
                        restricted={verdicts.Restricted} />
        </section>

        <section className="card form-card">
          <h3>Audio flags by severity</h3>
          <SeverityBars rows={severity_breakdown} />
        </section>

        <section className="card form-card">
          <h3>Visual risks by category</h3>
          <BarList rows={risk_category_breakdown}
                   emptyText="No visual risks recorded yet" />
        </section>

        <section className="card form-card">
          <h3>Most frequent flagged words</h3>
          <BarList rows={top_words} emptyText="No flagged words yet" />
        </section>

        <section className="card form-card">
          <h3>Most detected objects</h3>
          <BarList rows={top_objects} emptyText="No detections yet" />
        </section>

        <section className="card form-card">
          <h3>Ad inventory by surface</h3>
          <BarList
            rows={spot_types.map((s) => ({
              label: (s.label ?? "unknown").replace("_", " "),
              value: s.seconds,
            }))}
            color="var(--good)"
            unit="s"
            emptyText="No ad spots found yet"
          />
        </section>
      </div>
    </>
  );
}

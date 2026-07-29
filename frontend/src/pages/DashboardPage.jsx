import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, fmtDate, fmtTime } from "../api";
import { MonetizationBadge } from "../components/Badges";
import { StatCard, VerdictSplit } from "../components/Charts";

const STATUS_ICON = {
  completed: { icon: "check_circle", color: "var(--good)", text: "Checks complete" },
  processing: { icon: "progress_activity", color: "var(--blue)", text: "Running checks" },
  failed: { icon: "error", color: "var(--sev-high)", text: "Checks failed" },
  pending: { icon: "pending", color: "var(--ink-3)", text: "Not analysed" },
};

export default function DashboardPage({ toast }) {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);

  useEffect(() => {
    api.stats().then(setStats).catch((e) => toast(e.message));
  }, [toast]);

  if (!stats) return <div className="skeleton-page" aria-busy="true" />;

  const { totals, verdicts, recent_videos: recent } = stats;
  const flags = totals.audio_flags + totals.visual_flags;
  const analysed = verdicts.Monetizable + verdicts.Restricted;

  if (totals.videos === 0) {
    return (
      <>
        <h1 className="page-title">Dashboard</h1>
        <div className="card empty">
          <span className="material-symbols-outlined">movie</span>
          <h3>Let's audit your first video</h3>
          <p>Upload a video and AdSafe Studio will check it for brand-safety risks
             and find ad placement opportunities — all on this machine.</p>
          <Link className="btn btn--primary" to="/content">Go to content</Link>
        </div>
      </>
    );
  }

  return (
    <>
      <h1 className="page-title">Dashboard</h1>

      <div className="stats stats--4">
        <StatCard value={totals.videos} label="Videos in library"
                  hint={`${fmtTime(totals.duration_sec)} total runtime`} />
        <StatCard value={verdicts.Monetizable} label="Fully monetizable"
                  tone="var(--good)"
                  hint={analysed ? `of ${analysed} analysed` : "none analysed yet"} />
        <StatCard value={flags} label="Risk flags found"
                  tone={flags ? "var(--sev-med)" : undefined}
                  hint={`${totals.audio_flags} audio · ${totals.visual_flags} visual`} />
        <StatCard value={`${Math.round(totals.ad_inventory_sec)}s`} label="Ad inventory"
                  hint={`across ${totals.ad_spots} premium spots`} />
      </div>

      <div className="dash-grid">
        <section className="card form-card">
          <h3>Library health</h3>
          <p className="muted-note">
            How your analysed videos would fare against advertiser-friendly guidelines.
          </p>
          <VerdictSplit monetizable={verdicts.Monetizable} restricted={verdicts.Restricted} />
          <Link className="btn btn--text" to="/analytics" style={{ marginTop: 12 }}>
            <span className="material-symbols-outlined" aria-hidden="true">bar_chart</span>
            See full analytics
          </Link>
        </section>

        <section className="card form-card">
          <h3>Recent uploads</h3>
          {recent.length === 0 ? (
            <p className="chart-empty">Nothing uploaded yet</p>
          ) : (
            <ul className="activity">
              {recent.map((v) => {
                const s = STATUS_ICON[v.processed_status] ?? STATUS_ICON.pending;
                return (
                  <li key={v.video_id}>
                    <button className="activity__row"
                            onClick={() => navigate(`/video/${v.video_id}`)}>
                      <span className="material-symbols-outlined"
                            style={{ color: s.color }} aria-hidden="true">{s.icon}</span>
                      <span className="activity__body">
                        <span className="activity__title">{v.filename}</span>
                        <span className="activity__meta">
                          {s.text} · {fmtTime(v.duration_sec)} · {fmtDate(v.upload_timestamp)}
                        </span>
                      </span>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
          <Link className="btn btn--text" to="/content">View all content</Link>
        </section>
      </div>
    </>
  );
}

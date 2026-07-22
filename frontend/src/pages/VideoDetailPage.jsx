import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, fmtTime } from "../api";
import { MonetizationBadge, SeverityChip } from "../components/Badges";
import Timeline from "../components/Timeline";

const TABS = ["Audio flags", "Visual risks", "Ad spots"];

export default function VideoDetailPage({ toast }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const videoRef = useRef(null);
  const [video, setVideo] = useState(null);
  const [flags, setFlags] = useState(null);
  const [tab, setTab] = useState(TABS[0]);
  const [currentTime, setCurrentTime] = useState(0);

  const load = useCallback(async () => {
    try {
      setVideo(await api.getVideo(id));
      setFlags(await api.flags(id));
    } catch (e) {
      toast(e.message);
      navigate("/");
    }
  }, [id, toast, navigate]);

  useEffect(() => { load(); }, [load]);

  function seek(t) {
    const el = videoRef.current;
    if (!el) return;
    el.currentTime = t;
    el.play().catch(() => {});
  }

  async function exportReport(fmt) {
    try {
      const report = await api.createReport(Number(id), fmt);
      toast(`${fmt} report generated`);
      window.open(`/api/reports/${report.report_id}/download`, "_blank");
    } catch (e) {
      toast(e.message);
    }
  }

  if (!video || !flags) return <p style={{ color: "var(--ink-2)" }}>Loading…</p>;

  const inventory = flags.ad_spots.reduce(
    (acc, s) => acc + (s.timestamp_end - s.timestamp_start), 0);

  return (
    <>
      <div className="detail-header">
        <button className="icon-btn" onClick={() => navigate("/")} title="Back to content">
          <span className="material-symbols-outlined">arrow_back</span>
        </button>
        <h1>{video.filename}</h1>
        <MonetizationBadge verdict={flags.verdict} />
        <button className="btn btn--outline" onClick={() => exportReport("CSV")}>
          <span className="material-symbols-outlined" style={{ fontSize: 20 }}>download</span>
          Export CSV
        </button>
        <button className="btn btn--outline" onClick={() => exportReport("JSON")}>JSON</button>
      </div>

      {video.processed_status !== "completed" ? (
        <div className="card empty">
          <span className="material-symbols-outlined">pending</span>
          <h3>This video hasn’t been analyzed yet</h3>
          <p>Run checks from the Content page to populate this view.</p>
        </div>
      ) : (
        <div className="detail-grid">
          <div>
            <div className="stats">
              <div className="card stat">
                <div className="stat__value">{flags.audio.length}</div>
                <div className="stat__label">Audio flags</div>
              </div>
              <div className="card stat">
                <div className="stat__value">{flags.visual.length}</div>
                <div className="stat__label">Visual risks</div>
              </div>
              <div className="card stat">
                <div className="stat__value">{flags.ad_spots.length}</div>
                <div className="stat__label">Premium ad spots</div>
              </div>
              <div className="card stat">
                <div className="stat__value">{Math.round(inventory)}s</div>
                <div className="stat__label">Ad inventory</div>
              </div>
            </div>

            <div className="card timeline-card">
              <h3>Audit timeline — click an event to jump the player</h3>
              <Timeline
                duration={video.duration_sec}
                audio={flags.audio}
                visual={flags.visual}
                adSpots={flags.ad_spots}
                currentTime={currentTime}
                onSeek={seek}
              />
            </div>

            <div className="card flags-card">
              <div className="tabs">
                {TABS.map((t) => (
                  <button key={t} className={`tab${tab === t ? " active" : ""}`}
                          onClick={() => setTab(t)}>
                    {t}
                  </button>
                ))}
              </div>
              {tab === "Audio flags" && <AudioTable rows={flags.audio} onSeek={seek} />}
              {tab === "Visual risks" && <VisualTable rows={flags.visual} onSeek={seek} />}
              {tab === "Ad spots" && <SpotsTable rows={flags.ad_spots} onSeek={seek} />}
            </div>
          </div>

          <div className="card playercard">
            <video ref={videoRef} src={video.video_url} controls
                   onTimeUpdate={(e) => setCurrentTime(e.target.currentTime)} />
            <div className="playercard__meta">
              <span className="k">Filename</span>
              <span className="v">{video.filename}</span>
              <span className="k">Details</span>
              <span className="v">
                {fmtTime(video.duration_sec)} · {video.resolution_width}×{video.resolution_height} · {Math.round(video.fps)} fps
              </span>
              <span className="k">Video link</span>
              <a className="v" href={video.video_url} target="_blank" rel="noreferrer">
                {video.video_url}
              </a>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

const JumpBtn = ({ t, onSeek }) => (
  <button className="btn btn--text" style={{ height: 28, padding: "0 10px" }}
          onClick={() => onSeek(t)}>
    {fmtTime(t)}
  </button>
);

function AudioTable({ rows, onSeek }) {
  if (!rows.length) return <div className="empty"><p>No audio flags.</p></div>;
  return (
    <table className="vtable">
      <thead><tr><th>At</th><th>Word</th><th>Severity</th><th>Context</th><th>Model</th></tr></thead>
      <tbody>
        {rows.map((f) => (
          <tr key={f.audio_flag_id}>
            <td><JumpBtn t={f.timestamp_start} onSeek={onSeek} /></td>
            <td><b>“{f.word_flagged}”</b></td>
            <td><SeverityChip value={f.severity} /></td>
            <td style={{ color: "var(--ink-2)", maxWidth: 420 }}>…{f.transcript_context}…</td>
            <td style={{ color: "var(--ink-2)" }}>{f.detection_model}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function VisualTable({ rows, onSeek }) {
  if (!rows.length) return <div className="empty"><p>No visual risks.</p></div>;
  return (
    <table className="vtable">
      <thead><tr><th>At</th><th>Object</th><th>Category</th><th>Confidence</th><th>Bounding box</th></tr></thead>
      <tbody>
        {rows.map((f) => (
          <tr key={f.visual_flag_id}>
            <td><JumpBtn t={f.frame_timestamp} onSeek={onSeek} /></td>
            <td><b>{f.object_detected}</b></td>
            <td><SeverityChip value={f.risk_category} /></td>
            <td>
              <span className="confbar">
                <span className="confbar__track">
                  <span className="confbar__fill" style={{ width: `${f.confidence_score * 100}%`, display: "block" }} />
                </span>
                {f.confidence_score.toFixed(2)}
              </span>
            </td>
            <td style={{ color: "var(--ink-2)", fontFamily: "monospace", fontSize: 12 }}>
              {f.bounding_box_json}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SpotsTable({ rows, onSeek }) {
  if (!rows.length) return <div className="empty"><p>No ad spots found.</p></div>;
  return (
    <table className="vtable">
      <thead><tr><th>From</th><th>To</th><th>Duration</th><th>Surface</th><th>Area (px)</th><th>Suitability</th></tr></thead>
      <tbody>
        {rows.map((s) => (
          <tr key={s.spot_id}>
            <td><JumpBtn t={s.timestamp_start} onSeek={onSeek} /></td>
            <td>{fmtTime(s.timestamp_end)}</td>
            <td>{(s.timestamp_end - s.timestamp_start).toFixed(1)}s</td>
            <td><b>{(s.spot_type ?? "").replace("_", " ")}</b></td>
            <td>{Math.round(s.area_pixels).toLocaleString()}</td>
            <td>
              <span className="confbar">
                <span className="confbar__track">
                  <span className="confbar__fill" style={{ width: `${(s.suitability_score ?? 0) * 100}%`, display: "block", background: "var(--good)" }} />
                </span>
                {s.suitability_score?.toFixed(2)}
              </span>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

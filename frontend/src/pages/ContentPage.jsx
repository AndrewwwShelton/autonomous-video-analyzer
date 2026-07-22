import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, fmtDate, fmtTime } from "../api";
import { MonetizationBadge } from "../components/Badges";

function StatusCell({ video, progress }) {
  const s = video.processed_status;
  if (s === "processing") {
    const pct = Math.round((progress?.progress ?? 0) * 100);
    return (
      <div className="progress">
        <div className="progress__label">
          <span>{progress?.stage ?? "Running checks…"}</span><span>{pct}%</span>
        </div>
        <div className="progress__track">
          <div className="progress__fill" style={{ width: `${pct}%` }} />
        </div>
      </div>
    );
  }
  if (s === "completed")
    return (
      <span className="statuscell">
        <span className="material-symbols-outlined" style={{ color: "var(--good)" }}>check_circle</span>
        Checks complete
      </span>
    );
  if (s === "failed")
    return (
      <span className="statuscell">
        <span className="material-symbols-outlined" style={{ color: "var(--sev-high)" }}>error</span>
        Checks failed
      </span>
    );
  return (
    <span className="statuscell">
      <span className="material-symbols-outlined">pending</span>
      Not analyzed
    </span>
  );
}

export default function ContentPage({ search, toast, refreshKey }) {
  const navigate = useNavigate();
  const [videos, setVideos] = useState(null);
  const [progressMap, setProgressMap] = useState({});

  const load = useCallback(async () => {
    try {
      setVideos(await api.listVideos());
    } catch (e) {
      toast(`Failed to load videos: ${e.message}`);
    }
  }, [toast]);

  useEffect(() => { load(); }, [load, refreshKey]);

  // Poll while anything is processing — YT-style live "checks" progress.
  const anyProcessing = videos?.some((v) => v.processed_status === "processing");
  useEffect(() => {
    if (!anyProcessing) return;
    const id = setInterval(async () => {
      const processing = videos.filter((v) => v.processed_status === "processing");
      const entries = await Promise.all(
        processing.map(async (v) => [v.video_id, await api.status(v.video_id).catch(() => null)])
      );
      setProgressMap(Object.fromEntries(entries.filter(([, s]) => s)));
      if (entries.some(([, s]) => s && s.status !== "processing")) load();
    }, 800);
    return () => clearInterval(id);
  }, [anyProcessing, videos, load]);

  async function analyze(v) {
    try {
      await api.analyze(v.video_id);
      toast(`Running checks on ${v.filename}`);
      load();
    } catch (e) {
      toast(e.message);
    }
  }

  async function remove(v) {
    if (!window.confirm(`Delete "${v.filename}" and all its audit data?`)) return;
    await api.deleteVideo(v.video_id);
    toast("Video deleted");
    load();
  }

  async function makeDemo() {
    toast("Rendering demo footage…");
    try {
      await api.createDemo();
      load();
    } catch (e) {
      toast(e.message);
    }
  }

  if (videos === null) return <p style={{ color: "var(--ink-2)" }}>Loading…</p>;

  const filtered = videos.filter((v) =>
    v.filename.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <>
      <h1 className="page-title">Library content</h1>
      <div className="card">
        <div className="tabs">
          <button className="tab active">Videos</button>
        </div>
        <div className="filterbar">
          <span className="material-symbols-outlined">filter_list</span>
          <span style={{ fontSize: 13 }}>Filter</span>
          {search && <span style={{ fontSize: 13 }}>— matching “{search}”</span>}
        </div>

        {filtered.length === 0 ? (
          <div className="empty">
            <span className="material-symbols-outlined">video_library</span>
            <h3>{videos.length === 0 ? "No content available" : "No videos match your search"}</h3>
            {videos.length === 0 && (
              <>
                <p>Upload a video to audit it for brand safety and ad inventory.</p>
                <button className="btn btn--text" onClick={makeDemo}>
                  Generate a demo video instead
                </button>
              </>
            )}
          </div>
        ) : (
          <table className="vtable">
            <thead>
              <tr>
                <th>Video</th><th>Monetization</th><th>Status</th><th>Date</th>
                <th>Duration</th><th>Flags</th><th>Ad spots</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((v) => (
                <tr key={v.video_id}>
                  <td>
                    <div className="vcell">
                      {v.thumbnail_url ? (
                        <img className="vcell__thumb" src={v.thumbnail_url} alt=""
                             onClick={() => navigate(`/video/${v.video_id}`)} />
                      ) : (
                        <div className="vcell__thumb vcell__thumb--empty">
                          <span className="material-symbols-outlined">smart_display</span>
                        </div>
                      )}
                      <div>
                        <div className="vcell__title" onClick={() => navigate(`/video/${v.video_id}`)}>
                          {v.filename}
                        </div>
                        <div className="vcell__sub">
                          {v.resolution_width}×{v.resolution_height} · {Math.round(v.fps)} fps · {v.file_size_mb} MB
                        </div>
                        <div className="vcell__actions">
                          <button className="icon-btn" title="Open" onClick={() => navigate(`/video/${v.video_id}`)}>
                            <span className="material-symbols-outlined">open_in_new</span>
                          </button>
                          <button className="icon-btn" title={v.processed_status === "completed" ? "Re-run checks" : "Run checks"}
                                  onClick={() => analyze(v)}
                                  disabled={v.processed_status === "processing"}>
                            <span className="material-symbols-outlined">refresh</span>
                          </button>
                          <button className="icon-btn" title="Delete" onClick={() => remove(v)}>
                            <span className="material-symbols-outlined">delete</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </td>
                  <td><MonetizationBadge verdict={v.verdict} /></td>
                  <td><StatusCell video={v} progress={progressMap[v.video_id]} /></td>
                  <td>
                    {fmtDate(v.upload_timestamp)}
                    <div className="vcell__sub">Uploaded</div>
                  </td>
                  <td>{fmtTime(v.duration_sec)}</td>
                  <td>{v.counts ? v.counts.audio + v.counts.visual : "—"}</td>
                  <td>{v.counts ? v.counts.ad_spots : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </>
  );
}

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
      // Do NOT refetch here. The endpoint returns 202 as soon as the job is
      // queued, before the background task writes processed_status; a refetch
      // races that write and usually wins, so the row comes back "pending",
      // anyProcessing stays false, the poll below never starts and no progress
      // bar is ever drawn. Nothing refetches again, so the row sits stale for
      // the whole run. Mark it processing from what the POST already told us
      // and let the poll reconcile with the server from here.
      setVideos((prev) => (prev ?? []).map((x) =>
        x.video_id === v.video_id ? { ...x, processed_status: "processing" } : x));
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

  if (videos === null) return <div className="skeleton-page" aria-busy="true" />;

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
            <span className="material-symbols-outlined" aria-hidden="true">video_library</span>
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
          // .table-scroll keeps the seven-column table inside its card at
          // laptop and tablet widths. Without it the table widened the page
          // itself and the whole layout scrolled sideways.
          <div className="table-scroll">
          <table className="vtable vtable--cards">
            <thead>
              <tr>
                <th>Video</th><th>Monetization</th><th>Status</th><th>Date</th>
                <th>Duration</th><th>Flags</th><th>Ad spots</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((v) => (
                <tr key={v.video_id}>
                  <td data-label="Video">
                    <div className="vcell">
                      {v.thumbnail_url ? (
                        <img className="vcell__thumb" src={v.thumbnail_url} alt=""
                             onClick={() => navigate(`/video/${v.video_id}`)} />
                      ) : (
                        <div className="vcell__thumb vcell__thumb--empty">
                          <span className="material-symbols-outlined" aria-hidden="true">smart_display</span>
                        </div>
                      )}
                      <div>
                        <button className="vcell__title"
                                onClick={() => navigate(`/video/${v.video_id}`)}>
                          {v.filename}
                        </button>
                        <div className="vcell__sub">
                          {v.resolution_width}×{v.resolution_height} · {Math.round(v.fps)} fps · {v.file_size_mb} MB
                        </div>
                        <div className="vcell__actions">
                          <button className="icon-btn" aria-label={`Open ${v.filename}`}
                                  onClick={() => navigate(`/video/${v.video_id}`)}>
                            <span className="material-symbols-outlined" aria-hidden="true">open_in_new</span>
                          </button>
                          <button className="icon-btn"
                                  aria-label={`${v.processed_status === "completed" ? "Re-run" : "Run"} checks on ${v.filename}`}
                                  onClick={() => analyze(v)}
                                  disabled={v.processed_status === "processing"}>
                            <span className="material-symbols-outlined" aria-hidden="true">refresh</span>
                          </button>
                          <button className="icon-btn" aria-label={`Delete ${v.filename}`}
                                  onClick={() => remove(v)}>
                            <span className="material-symbols-outlined" aria-hidden="true">delete</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  </td>
                  <td data-label="Monetization"><MonetizationBadge verdict={v.verdict} /></td>
                  <td data-label="Status"><StatusCell video={v} progress={progressMap[v.video_id]} /></td>
                  <td data-label="Uploaded">{fmtDate(v.upload_timestamp)}</td>
                  <td data-label="Duration">{fmtTime(v.duration_sec)}</td>
                  <td data-label="Flags">{v.counts ? v.counts.audio + v.counts.visual : "—"}</td>
                  <td data-label="Ad spots">{v.counts ? v.counts.ad_spots : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>
        )}
      </div>
    </>
  );
}

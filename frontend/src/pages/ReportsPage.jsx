import { useCallback, useEffect, useState } from "react";
import { api, fmtDate } from "../api";

export default function ReportsPage({ toast }) {
  const [videos, setVideos] = useState([]);
  const [reports, setReports] = useState([]);
  const [videoId, setVideoId] = useState("");
  const [format, setFormat] = useState("CSV");

  const load = useCallback(async () => {
    const [v, r] = await Promise.all([api.listVideos(), api.listReports()]);
    setVideos(v);
    setReports(r);
    if (!videoId && v.length) {
      const done = v.find((x) => x.processed_status === "completed");
      if (done) setVideoId(String(done.video_id));
    }
  }, [videoId]);

  useEffect(() => { load(); }, [load]);

  const videoName = (id) =>
    videos.find((v) => v.video_id === id)?.filename ?? `#${id}`;

  async function generate() {
    try {
      await api.createReport(Number(videoId), format);
      toast(`${format} report generated`);
      load();
    } catch (e) {
      toast(e.message);
    }
  }

  const completed = videos.filter((v) => v.processed_status === "completed");

  return (
    <>
      <h1 className="page-title">Reports</h1>

      <div className="card form-card">
        <h3>Create a compliance report</h3>
        <div className="form-row">
          <label>Video</label>
          <select className="input" value={videoId} onChange={(e) => setVideoId(e.target.value)}>
            <option value="" disabled>Select an analyzed video…</option>
            {completed.map((v) => (
              <option key={v.video_id} value={v.video_id}>
                #{v.video_id} · {v.filename}
              </option>
            ))}
          </select>
        </div>
        <div className="form-row">
          <label>Format</label>
          <select className="input" value={format} onChange={(e) => setFormat(e.target.value)}>
            <option>CSV</option>
            <option>JSON</option>
            <option disabled>PDF (available in M5)</option>
          </select>
        </div>
        <div className="page-actions">
          <button className="btn btn--primary" onClick={generate} disabled={!videoId}>
            Generate report
          </button>
        </div>
      </div>

      <div className="card">
        {reports.length === 0 ? (
          <div className="empty">
            <span className="material-symbols-outlined" aria-hidden="true">description</span>
            <h3>No reports yet</h3>
          </div>
        ) : (
          <div className="table-scroll">
          <table className="vtable">
            <thead>
              <tr>
                <th>Generated</th><th>Video</th><th>Type</th><th>Audio</th>
                <th>Visual</th><th>Ad spots</th><th>Verdict</th><th></th>
              </tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.report_id}>
                  <td>{fmtDate(r.generation_timestamp)}</td>
                  <td>{videoName(r.video_id)}</td>
                  <td>{r.report_type}</td>
                  <td>{r.total_audio_risks}</td>
                  <td>{r.total_visual_risks}</td>
                  <td>{r.total_ad_spots}</td>
                  <td>{r.compliance_status}</td>
                  <td>
                    <a className="icon-btn" style={{ display: "inline-flex" }}
                       href={`/api/reports/${r.report_id}/download`}
                       aria-label={`Download ${r.report_type} report`}>
                      <span className="material-symbols-outlined" aria-hidden="true">download</span>
                    </a>
                  </td>
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

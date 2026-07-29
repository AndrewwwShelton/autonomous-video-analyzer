// Thin API client. Vite proxies /api and /media to the FastAPI server (:8000).

async function request(method, url, body) {
  const opts = { method, headers: {} };
  if (body !== undefined) {
    opts.headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }
  const res = await fetch(url, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch { /* non-JSON error body */ }
    throw new Error(detail);
  }
  return res.status === 204 ? null : res.json();
}

export const api = {
  listVideos: () => request("GET", "/api/videos"),
  getVideo: (id) => request("GET", `/api/videos/${id}`),
  deleteVideo: (id) => request("DELETE", `/api/videos/${id}`),
  createDemo: () => request("POST", "/api/videos/demo"),
  analyze: (id) => request("POST", `/api/videos/${id}/analyze`),
  status: (id) => request("GET", `/api/videos/${id}/status`),
  flags: (id) => request("GET", `/api/videos/${id}/flags`),
  stats: () => request("GET", "/api/stats"),
  getConfig: () => request("GET", "/api/config"),
  putConfig: (cfg) => request("PUT", "/api/config", cfg),
  listReports: (videoId) =>
    request("GET", videoId ? `/api/reports?video_id=${videoId}` : "/api/reports"),
  createReport: (videoId, format) =>
    request("POST", "/api/reports", { video_id: videoId, format }),
};

// Upload with progress needs XHR — fetch has no upload progress events.
export function uploadVideo(file, onProgress) {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/videos");
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total);
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          reject(new Error(JSON.parse(xhr.responseText).detail));
        } catch {
          reject(new Error(`Upload failed (${xhr.status})`));
        }
      }
    };
    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(form);
  });
}

export const fmtTime = (sec) => {
  const s = Math.max(0, Math.round(sec));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
};

export const fmtDate = (iso) => {
  if (!iso) return "—";
  const d = new Date(iso.includes("T") ? iso : iso.replace(" ", "T") + "Z");
  return d.toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" });
};

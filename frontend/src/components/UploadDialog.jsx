import { useRef, useState } from "react";
import { uploadVideo } from "../api";

const ACCEPTED = [".mp4", ".mov", ".avi"];
const MAX_MB = 2048;

/** Client-side gate so obvious mistakes never cost an upload round-trip. */
function validateFile(file) {
  const ext = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
  if (!ACCEPTED.includes(ext))
    return `“${ext || file.name}” isn’t a supported format. Use MP4, MOV or AVI.`;
  if (file.size === 0) return "That file is empty.";
  if (file.size > MAX_MB * 1_048_576)
    return `That file is ${Math.round(file.size / 1_048_576)} MB — the limit is ${MAX_MB} MB.`;
  return null;
}

export default function UploadDialog({ onClose, onUploaded, toast }) {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);
  const [progress, setProgress] = useState(null); // null = idle, 0..1 uploading
  const [error, setError] = useState(null);

  async function handleFiles(files) {
    const file = files?.[0];
    if (!file) return;

    const problem = validateFile(file);
    if (problem) {
      setError(problem);
      return;
    }

    setError(null);
    setProgress(0);
    try {
      const video = await uploadVideo(file, setProgress);
      toast(`Uploaded ${video.filename}`);
      onUploaded(video);
      onClose();
    } catch (e) {
      setError(e.message);
      setProgress(null);
    }
  }

  return (
    <div className="overlay" onClick={progress === null ? onClose : undefined}
         role="dialog" aria-modal="true" aria-label="Upload videos">
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog__header">
          <h2>Upload videos</h2>
          <button className="icon-btn" onClick={onClose} disabled={progress !== null}
                  aria-label="Close upload dialog">
            <span className="material-symbols-outlined" aria-hidden="true">close</span>
          </button>
        </div>

        <div
          className={`dropzone${drag ? " drag" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); handleFiles(e.dataTransfer.files); }}
        >
          <div className="dropzone__icon">
            <span className="material-symbols-outlined" aria-hidden="true">upload</span>
          </div>
          {progress === null ? (
            <>
              <h3>Drag and drop a video file to upload</h3>
              <p>Your videos stay on this machine — nothing is sent to the cloud.</p>
              <p>MP4, MOV or AVI · up to {MAX_MB} MB</p>

              {error && (
                <p className="field-error" role="alert">
                  <span className="material-symbols-outlined" aria-hidden="true">error</span>
                  {error}
                </p>
              )}

              <button className="btn btn--primary" onClick={() => inputRef.current?.click()}>
                Select file
              </button>
              <input
                ref={inputRef}
                type="file"
                accept={ACCEPTED.join(",")}
                hidden
                onChange={(e) => handleFiles(e.target.files)}
              />
            </>
          ) : (
            <>
              <h3>Uploading… {Math.round(progress * 100)}%</h3>
              <div className="progress" style={{ width: 280 }}>
                <div className="progress__track">
                  <div className="progress__fill" style={{ width: `${progress * 100}%` }} />
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

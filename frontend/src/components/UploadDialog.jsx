import { useRef, useState } from "react";
import { uploadVideo } from "../api";

export default function UploadDialog({ onClose, onUploaded, toast }) {
  const inputRef = useRef(null);
  const [drag, setDrag] = useState(false);
  const [progress, setProgress] = useState(null); // null = idle, 0..1 uploading

  async function handleFiles(files) {
    const file = files?.[0];
    if (!file) return;
    setProgress(0);
    try {
      const video = await uploadVideo(file, setProgress);
      toast(`Uploaded ${video.filename}`);
      onUploaded(video);
      onClose();
    } catch (e) {
      toast(e.message);
      setProgress(null);
    }
  }

  return (
    <div className="overlay" onClick={progress === null ? onClose : undefined}>
      <div className="dialog" onClick={(e) => e.stopPropagation()}>
        <div className="dialog__header">
          <h2>Upload videos</h2>
          <button className="icon-btn" onClick={onClose} disabled={progress !== null}>
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>

        <div
          className={`dropzone${drag ? " drag" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => { e.preventDefault(); setDrag(false); handleFiles(e.dataTransfer.files); }}
        >
          <div className="dropzone__icon">
            <span className="material-symbols-outlined">upload</span>
          </div>
          {progress === null ? (
            <>
              <h3>Drag and drop a video file to upload</h3>
              <p>Your videos stay on this machine — nothing is sent to the cloud.</p>
              <p>MP4, MOV or AVI</p>
              <button className="btn btn--primary" onClick={() => inputRef.current?.click()}>
                Select file
              </button>
              <input
                ref={inputRef}
                type="file"
                accept=".mp4,.mov,.avi"
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

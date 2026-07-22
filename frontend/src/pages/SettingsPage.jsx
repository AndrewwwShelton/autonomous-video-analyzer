import { useEffect, useState } from "react";
import { api } from "../api";

export default function SettingsPage({ toast }) {
  const [cfg, setCfg] = useState(null);

  useEffect(() => {
    api.getConfig().then(setCfg).catch((e) => toast(e.message));
  }, [toast]);

  if (!cfg) return <p style={{ color: "var(--ink-2)" }}>Loading…</p>;

  const set = (key, value) => setCfg({ ...cfg, [key]: value });
  const setRule = (i, patch) => {
    const rules = cfg.profanity_dictionary.slice();
    rules[i] = { ...rules[i], ...patch };
    set("profanity_dictionary", rules);
  };

  async function save() {
    try {
      setCfg(await api.putConfig(cfg));
      toast("Settings saved");
    } catch (e) {
      toast(e.message);
    }
  }

  return (
    <>
      <h1 className="page-title">Settings</h1>

      <div className="card form-card">
        <h3>Restricted keyword dictionary</h3>
        <p style={{ fontSize: 13, color: "var(--ink-2)", marginBottom: 16 }}>
          Words and phrases matched against the transcript. Changes apply to the next run.
        </p>
        {cfg.profanity_dictionary.map((rule, i) => (
          <div className="dict-row" key={i}>
            <input className="input" value={rule.word} placeholder="word or phrase"
                   onChange={(e) => setRule(i, { word: e.target.value })} />
            <select className="input" value={rule.severity}
                    onChange={(e) => setRule(i, { severity: e.target.value })}>
              <option>Low</option><option>Medium</option><option>High</option>
            </select>
            <button className="icon-btn" title="Remove"
                    onClick={() => set("profanity_dictionary",
                      cfg.profanity_dictionary.filter((_, j) => j !== i))}>
              <span className="material-symbols-outlined">delete</span>
            </button>
          </div>
        ))}
        <button className="btn btn--text"
                onClick={() => set("profanity_dictionary",
                  [...cfg.profanity_dictionary, { word: "", severity: "Medium" }])}>
          <span className="material-symbols-outlined" style={{ fontSize: 20 }}>add</span>
          Add rule
        </button>
      </div>

      <div className="card form-card">
        <h3>Pipeline</h3>
        <div className="form-row">
          <label>Frame sample rate (FPS) — SRS FR3 specifies 1</label>
          <input className="input" type="number" min="0.25" max="4" step="0.25"
                 value={cfg.frame_sample_fps}
                 onChange={(e) => set("frame_sample_fps", Number(e.target.value))} />
        </div>
        <div className="form-row">
          <label>Minimum ad-spot persistence (seconds)</label>
          <input className="input" type="number" min="2" max="15" step="0.5"
                 value={cfg.min_ad_spot_duration_sec}
                 onChange={(e) => set("min_ad_spot_duration_sec", Number(e.target.value))} />
        </div>
        <div className="form-row">
          <label>Detection confidence threshold</label>
          <input className="input" type="number" min="0" max="1" step="0.05"
                 value={cfg.detection_confidence_threshold}
                 onChange={(e) => set("detection_confidence_threshold", Number(e.target.value))} />
        </div>
        <div className="form-row">
          <label>Whisper model (from M1)</label>
          <select className="input" value={cfg.whisper_model}
                  onChange={(e) => set("whisper_model", e.target.value)}>
            <option>tiny.en</option><option>base.en</option>
            <option>small.en</option><option>medium.en</option>
          </select>
        </div>
      </div>

      <div className="page-actions">
        <button className="btn btn--primary" onClick={save}>Save</button>
      </div>
    </>
  );
}

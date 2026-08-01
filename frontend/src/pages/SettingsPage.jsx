import { useEffect, useMemo, useState } from "react";
import { api } from "../api";

const NUMERIC_FIELDS = {
  frame_sample_fps: { min: 0.25, max: 4, step: 0.25, label: "Frame sample rate" },
  min_ad_spot_duration_sec: { min: 2, max: 15, step: 0.5, label: "Minimum ad-spot persistence" },
  detection_confidence_threshold: { min: 0, max: 1, step: 0.05, label: "Detection confidence threshold" },
};

/** Returns { dictionary: {index: msg}, numeric: {key: msg} } — empty when valid. */
function validate(cfg) {
  const dictionary = {};
  const seen = new Map();
  cfg.profanity_dictionary.forEach((rule, i) => {
    const word = (rule.word ?? "").trim().toLowerCase();
    if (!word) {
      dictionary[i] = "Enter a word or phrase, or remove this row.";
    } else if (seen.has(word)) {
      dictionary[i] = `Already listed on row ${seen.get(word) + 1}.`;
    } else {
      seen.set(word, i);
    }
  });

  const numeric = {};
  for (const [key, f] of Object.entries(NUMERIC_FIELDS)) {
    const v = cfg[key];
    if (v === "" || v === null || Number.isNaN(Number(v))) {
      numeric[key] = "Enter a number.";
    } else if (Number(v) < f.min || Number(v) > f.max) {
      numeric[key] = `Must be between ${f.min} and ${f.max}.`;
    }
  }
  return { dictionary, numeric };
}

function FieldError({ msg }) {
  if (!msg) return null;
  return (
    <span className="field-error" role="alert">
      <span className="material-symbols-outlined" aria-hidden="true">error</span>
      {msg}
    </span>
  );
}

export default function SettingsPage({ toast }) {
  const [cfg, setCfg] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getConfig().then(setCfg).catch((e) => toast(e.message));
  }, [toast]);

  const errors = useMemo(() => (cfg ? validate(cfg) : null), [cfg]);
  const hasErrors =
    errors && (Object.keys(errors.dictionary).length > 0 || Object.keys(errors.numeric).length > 0);

  if (!cfg) return <div className="skeleton-page" aria-busy="true" />;

  const set = (key, value) => setCfg({ ...cfg, [key]: value });
  const setRule = (i, patch) => {
    const rules = cfg.profanity_dictionary.slice();
    rules[i] = { ...rules[i], ...patch };
    set("profanity_dictionary", rules);
  };

  async function save() {
    if (hasErrors) return;
    setSaving(true);
    try {
      const payload = {
        ...cfg,
        ...Object.fromEntries(
          Object.keys(NUMERIC_FIELDS).map((k) => [k, Number(cfg[k])])
        ),
      };
      setCfg(await api.putConfig(payload));
      toast("Settings saved");
    } catch (e) {
      toast(e.message);
    } finally {
      setSaving(false);
    }
  }

  const numberField = (key) => {
    const f = NUMERIC_FIELDS[key];
    const err = errors.numeric[key];
    return (
      <div className="form-row">
        <label htmlFor={key}>{f.label}</label>
        <div style={{ flex: 1 }}>
          <input
            id={key}
            className={`input${err ? " input--invalid" : ""}`}
            type="number"
            min={f.min} max={f.max} step={f.step}
            value={cfg[key]}
            aria-invalid={Boolean(err)}
            onChange={(e) => set(key, e.target.value)}
          />
          <FieldError msg={err} />
        </div>
      </div>
    );
  };

  return (
    <>
      <h1 className="page-title">Settings</h1>

      <div className="card form-card">
        <h3>Analysis engines</h3>
        <p className="muted-note">
          Real mode runs the implemented AI engines. Demo mode substitutes deterministic
          stand-ins, needs no model weights, and is instant — useful for demonstrations.
        </p>
        <div className="form-row">
          <label htmlFor="analysis_mode">Mode</label>
          <select id="analysis_mode" className="input" value={cfg.analysis_mode}
                  onChange={(e) => set("analysis_mode", e.target.value)}>
            <option value="demo">Demo — stand-in engines</option>
            <option value="real">Real — run the AI models</option>
          </select>
        </div>
        <p className="form-hint">
          {cfg.analysis_mode === "real"
            ? "Audio transcription is real (faster-whisper). Visual detection and ad-spot "
              + "detection remain stand-ins until those milestones land."
            : "All engines are stand-ins. Switch to Real to transcribe actual speech."}
        </p>
      </div>

      <div className="card form-card">
        <h3>Restricted keyword dictionary</h3>
        <p className="muted-note">
          Words and phrases matched against the transcript. Changes apply to the next run.
        </p>
        {cfg.profanity_dictionary.map((rule, i) => (
          <div key={i} style={{ marginBottom: 8 }}>
            <div className="dict-row">
              <input
                className={`input${errors.dictionary[i] ? " input--invalid" : ""}`}
                value={rule.word}
                placeholder="word or phrase"
                aria-label={`Restricted word ${i + 1}`}
                aria-invalid={Boolean(errors.dictionary[i])}
                onChange={(e) => setRule(i, { word: e.target.value })}
              />
              <select className="input" value={rule.severity}
                      aria-label={`Severity for ${rule.word || `row ${i + 1}`}`}
                      onChange={(e) => setRule(i, { severity: e.target.value })}>
                <option>Low</option><option>Medium</option><option>High</option>
              </select>
              <button className="icon-btn" aria-label={`Remove ${rule.word || `row ${i + 1}`}`}
                      onClick={() => set("profanity_dictionary",
                        cfg.profanity_dictionary.filter((_, j) => j !== i))}>
                <span className="material-symbols-outlined" aria-hidden="true">delete</span>
              </button>
            </div>
            <FieldError msg={errors.dictionary[i]} />
          </div>
        ))}
        <button className="btn btn--text"
                onClick={() => set("profanity_dictionary",
                  [...cfg.profanity_dictionary, { word: "", severity: "Medium" }])}>
          <span className="material-symbols-outlined" style={{ fontSize: 20 }} aria-hidden="true">add</span>
          Add rule
        </button>
      </div>

      <div className="card form-card">
        <h3>Pipeline</h3>
        {numberField("frame_sample_fps")}
        <p className="form-hint">SRS FR3 specifies 1 FPS. Raise only on GPU hardware.</p>
        {numberField("min_ad_spot_duration_sec")}
        <p className="form-hint">A Premium Ad Spot is a surface that stays clear this long.</p>
        {numberField("detection_confidence_threshold")}
        <div className="form-row">
          <label htmlFor="whisper_model">Transcription model</label>
          <select id="whisper_model" className="input" value={cfg.whisper_model}
                  onChange={(e) => set("whisper_model", e.target.value)}>
            <option>tiny.en</option><option>base.en</option>
            <option>small.en</option><option>medium.en</option>
          </select>
        </div>
        <p className="form-hint">
          Larger models are more accurate and slower. Weights download once into
          <code> models/</code> and are reused offline afterwards.
        </p>
      </div>

      <div className="page-actions">
        {hasErrors && (
          <span className="field-error" role="alert">
            <span className="material-symbols-outlined" aria-hidden="true">error</span>
            Fix the highlighted fields before saving.
          </span>
        )}
        <button className="btn btn--primary" onClick={save} disabled={hasErrors || saving}>
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </>
  );
}

-- Schema per DDD_Final.pdf §8, with performance indexes.
-- PRAGMAs (foreign_keys, WAL) are set per-connection in connection.py.

CREATE TABLE IF NOT EXISTS VideoMetadata (
    video_id            INTEGER PRIMARY KEY AUTOINCREMENT,
    filename            TEXT NOT NULL,
    filepath            TEXT NOT NULL,
    file_size_mb        REAL NOT NULL,
    duration_sec        REAL NOT NULL,
    fps                 REAL NOT NULL,
    resolution_width    INTEGER,
    resolution_height   INTEGER,
    upload_timestamp    TEXT DEFAULT CURRENT_TIMESTAMP,
    processed_status    TEXT DEFAULT 'pending'
                        CHECK (processed_status IN ('pending','processing','completed','failed')),
    -- Persistent-overlay evidence as JSON (src/vision/overlay.py). Extends the
    -- DDD schema: a weapon detection alone cannot distinguish gameplay from real
    -- footage, and the verdict needs that context to avoid restricting a video
    -- for an object rendered inside a game.
    overlay_context     TEXT
);

CREATE TABLE IF NOT EXISTS AudioFlags (
    audio_flag_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id            INTEGER NOT NULL REFERENCES VideoMetadata(video_id) ON DELETE CASCADE,
    timestamp_start     REAL NOT NULL,
    timestamp_end       REAL NOT NULL,
    word_flagged        TEXT NOT NULL,
    transcript_context  TEXT,
    severity            TEXT CHECK (severity IN ('Low','Medium','High')),
    -- Default reflects decision D3 (PLAN.md): faster-whisper, not stock Whisper.
    detection_model     TEXT DEFAULT 'faster-whisper-base.en'
);

CREATE TABLE IF NOT EXISTS VisualFlags (
    visual_flag_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id            INTEGER NOT NULL REFERENCES VideoMetadata(video_id) ON DELETE CASCADE,
    frame_timestamp     REAL NOT NULL,
    object_detected     TEXT NOT NULL,
    bounding_box_json   TEXT NOT NULL,
    confidence_score    REAL NOT NULL,
    risk_category       TEXT CHECK (risk_category IN ('Weapon','Substance','Graphic')),
    -- Which engine produced this, mirroring AudioFlags. Its absence was a real
    -- failure: demo detections are invented at fixed fractions of the duration
    -- and looked identical to measured ones in the interface, so a demo run on a
    -- real news clip read as a genuine misclassification.
    detection_model     TEXT
);

CREATE TABLE IF NOT EXISTS AdSpots (
    spot_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id            INTEGER NOT NULL REFERENCES VideoMetadata(video_id) ON DELETE CASCADE,
    timestamp_start     REAL NOT NULL,
    timestamp_end       REAL NOT NULL,
    spot_type           TEXT,
    bounding_box_json   TEXT NOT NULL,
    area_pixels         REAL,
    suitability_score   REAL
);

CREATE TABLE IF NOT EXISTS AuditReports (
    report_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id              INTEGER NOT NULL REFERENCES VideoMetadata(video_id) ON DELETE CASCADE,
    generation_timestamp  TEXT DEFAULT CURRENT_TIMESTAMP,
    report_type           TEXT CHECK (report_type IN ('PDF','CSV','JSON')),
    file_path             TEXT,
    total_audio_risks     INTEGER,
    total_visual_risks    INTEGER,
    total_ad_spots        INTEGER,
    compliance_status     TEXT
);

CREATE TABLE IF NOT EXISTS SystemConfig (
    config_key      TEXT PRIMARY KEY,
    config_value    TEXT NOT NULL,
    config_type     TEXT CHECK (config_type IN ('string','int','float','json')),
    description     TEXT,
    last_updated    TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audioflags_video   ON AudioFlags(video_id, timestamp_start);
CREATE INDEX IF NOT EXISTS idx_visualflags_video  ON VisualFlags(video_id, frame_timestamp);
CREATE INDEX IF NOT EXISTS idx_adspots_video      ON AdSpots(video_id, timestamp_start);
CREATE INDEX IF NOT EXISTS idx_reports_video      ON AuditReports(video_id);

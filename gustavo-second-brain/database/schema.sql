-- gustavo-second-brain -- SQLite schema
-- Generic "sources" model so the same pipeline can later cover non-YouTube material (FASE 25).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS sources (
    source_id           TEXT PRIMARY KEY,          -- e.g. YT_GUS_<video_id>
    source_type         TEXT NOT NULL,              -- youtube | document | call | ...
    visibility          TEXT NOT NULL DEFAULT 'PUBLIC',  -- PUBLIC | PRIVATE_INTERNAL | SENSITIVE_INTERNAL
    original_title       TEXT,
    original_url         TEXT,
    channel             TEXT,
    published_at         TEXT,
    transcript_source    TEXT,                       -- youtube_official | yt_dlp_manual | yt_dlp_auto | whisper_local
    processing_version   TEXT,
    processing_status    TEXT NOT NULL DEFAULT 'DISCOVERED',
    -- DISCOVERED -> METADATA_READY -> TRANSCRIPT_PENDING -> TRANSCRIPT_READY
    -- -> PROCESSED -> CHUNKED -> INDEXED -> DRIVE_SYNCED -> FAILED
    raw_path             TEXT,
    processed_path        TEXT,
    drive_raw_url        TEXT,
    drive_processed_url  TEXT,
    content_hash         TEXT,
    error                TEXT,
    last_processed        TEXT,
    created_at           TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at           TEXT NOT NULL DEFAULT (datetime('now')),

    -- Classification & governance layer (FASE pre-piloto). See
    -- scripts/classify_videos.py and CLASSIFICATION_REPORT.md.
    content_format           TEXT NOT NULL DEFAULT 'UNKNOWN',
    -- LONG_FORM | SHORT | LIVE | CLIP | UNKNOWN

    youtube_privacy_status   TEXT,
    -- PUBLIC | UNLISTED | PRIVATE -- raw value from the YouTube API
    -- (status.privacyStatus), never reinterpreted/inferred by an LLM.

    include_in_knowledge_base INTEGER NOT NULL DEFAULT 1,
    -- 0/1. SHORT defaults to 0 (excluded from transcription/embeddings/search
    -- until explicitly opted back in); metadata is never deleted either way.

    primary_content_type     TEXT,
    -- STRATEGY_EDUCATION | CRT_CONCEPT | MARKET_ANALYSIS | RISK_MANAGEMENT |
    -- PSYCHOLOGY | CASE_STUDY | TESTIMONIAL | LIVE_CLASS | VIP_CLASS |
    -- MENTORSHIP | PERSONAL | ANNOUNCEMENT | SALES_MARKETING | OTHER
    -- NULL = not yet classified (pending transcript-based review).

    distribution_policy      TEXT NOT NULL DEFAULT 'ASK_BEFORE_SHARING',
    -- SHAREABLE | INTERNAL_ONLY | ASK_BEFORE_SHARING

    internal_classification  TEXT,
    -- e.g. PRIVATE_UNCLASSIFIED. NULL = not applicable / not yet reviewed.

    published_year           INTEGER,

    temporal_status          TEXT NOT NULL DEFAULT 'UNKNOWN',
    -- CURRENT | LEGACY | SUPERSEDED | DEPRECATED | UNKNOWN
    -- SUPERSEDED/DEPRECATED require explicit evidence; never auto-assigned.

    potential_conflict        INTEGER NOT NULL DEFAULT 0,
    -- 0/1. See source_relations for conflicts_with/supersedes links.

    source_authority_type     TEXT,
    -- CANONICAL_EDUCATION | VIP_CLASS | MENTORSHIP_CLASS | LONG_FORM_YOUTUBE |
    -- LIVE_STREAM | MARKET_ANALYSIS | OTHER
    -- Deliberately NEVER set for content_format='SHORT' -- a SHORT gets no
    -- semantic classification of any kind (see classify_videos.py: Shorts
    -- are inventory-only, not knowledge-base sources).

    -- Optional, NEVER auto-populated now (see classify_videos.py docstring).
    -- Many Shorts are clips of a long-form video; these let a FUTURE phase
    -- record that relationship without spending any processing today.
    derived_from_source_id     TEXT REFERENCES sources(source_id),
    possible_parent_video_id   TEXT,
    parent_match_confidence    REAL
);

-- Multi-valued classification fields: join tables, not comma-separated TEXT,
-- so they stay queryable with plain SQL (WHERE audience = 'VIP_STUDENT' etc).

CREATE TABLE IF NOT EXISTS source_secondary_topics (
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    topic     TEXT NOT NULL,
    PRIMARY KEY (source_id, topic)
);

CREATE TABLE IF NOT EXISTS source_allowed_audience (
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    audience  TEXT NOT NULL,  -- PUBLIC | STUDENT | VIP_STUDENT | TEAM
    PRIMARY KEY (source_id, audience)
);

-- Tracks both conflicts_with_source_ids[] and supersedes_source_ids[] from
-- the spec: relation_type distinguishes the two. Never auto-populated --
-- requires explicit evidence (see scripts/classify_videos.py docstring).
CREATE TABLE IF NOT EXISTS source_relations (
    source_id         TEXT NOT NULL REFERENCES sources(source_id),
    related_source_id TEXT NOT NULL REFERENCES sources(source_id),
    relation_type      TEXT NOT NULL CHECK (relation_type IN ('conflicts_with', 'supersedes')),
    noted_at           TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (source_id, related_source_id, relation_type)
);

-- Ground-truth evidence from yt-dlp flat-extracting the channel's own
-- /shorts and /streams tabs (metadata-only, no video/audio download). A
-- video_id present here is what YouTube ITSELF presents in that section --
-- this takes priority over the duration/hashtag heuristic in
-- classify_videos.py. See scripts/discover_shorts_live_tabs.py.
CREATE TABLE IF NOT EXISTS video_tab_membership (
    video_id      TEXT NOT NULL,
    tab_type      TEXT NOT NULL CHECK (tab_type IN ('shorts', 'streams')),
    channel_id    TEXT NOT NULL,
    discovered_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (video_id, tab_type)
);

CREATE TABLE IF NOT EXISTS youtube_channels (
    channel_id    TEXT PRIMARY KEY,
    channel_name  TEXT,
    channel_url   TEXT,
    uploads_playlist_id TEXT,
    last_synced_at TEXT
);

CREATE TABLE IF NOT EXISTS youtube_videos (
    video_id      TEXT PRIMARY KEY,
    source_id     TEXT NOT NULL REFERENCES sources(source_id),
    channel_id    TEXT NOT NULL REFERENCES youtube_channels(channel_id),
    title         TEXT,
    url           TEXT,
    published_at  TEXT,
    duration_sec  INTEGER,
    description   TEXT,
    thumbnail_url TEXT,
    availability  TEXT DEFAULT 'available'   -- available | private | unavailable
);

CREATE TABLE IF NOT EXISTS transcripts (
    source_id          TEXT PRIMARY KEY REFERENCES sources(source_id),
    method             TEXT NOT NULL,   -- youtube_official | yt_dlp_manual | yt_dlp_auto | whisper_local
    raw_file_path       TEXT,
    language           TEXT,
    segment_count       INTEGER,
    created_at         TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chunks (
    chunk_id     TEXT PRIMARY KEY,
    source_id    TEXT NOT NULL REFERENCES sources(source_id),
    start_sec    INTEGER,
    end_sec      INTEGER,
    topic        TEXT,
    text         TEXT NOT NULL,
    source_url   TEXT,
    deep_link    TEXT,
    embedding_indexed INTEGER NOT NULL DEFAULT 0
);

-- Standalone (not external-content) FTS5 table: its `text` holds a
-- search-corrected copy (known ASR jargon mistranscriptions fixed, see
-- config/term_corrections.json), which can differ from chunks.text (the
-- verbatim transcript kept for citation/display). Rebuilt in full by
-- build_search_index.py; chunk_id is stored as a plain (indexed) column
-- so we can map a match back to its chunk without relying on rowid
-- alignment with the `chunks` table.
--
-- Named chunks_search (not chunks_fts) because an earlier schema
-- revision used chunks_fts as an external-content table bound to
-- `chunks`; this is a different, incompatible structure and the old
-- chunks_fts/_data/_idx/_docsize/_config shadow tables are left
-- orphaned (harmless) rather than dropped on existing databases.
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_search USING fts5(
    chunk_id,
    text
);

CREATE TABLE IF NOT EXISTS processing_runs (
    run_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    phase       TEXT NOT NULL,     -- discovery | pilot | full_import | retry
    started_at  TEXT NOT NULL DEFAULT (datetime('now')),
    finished_at TEXT,
    videos_total INTEGER,
    videos_done  INTEGER,
    status      TEXT DEFAULT 'running'  -- running | completed | interrupted | failed
);

CREATE TABLE IF NOT EXISTS errors (
    error_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id   TEXT,
    stage       TEXT,              -- discovery | metadata | transcript | normalize | chunk | index | drive_sync
    message     TEXT,
    occurred_at TEXT NOT NULL DEFAULT (datetime('now')),
    resolved    INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS drive_sync (
    source_id           TEXT PRIMARY KEY REFERENCES sources(source_id),
    drive_raw_file_id        TEXT,
    drive_processed_file_id  TEXT,
    drive_metadata_file_id   TEXT,
    synced_at           TEXT
);

CREATE INDEX IF NOT EXISTS idx_sources_status ON sources(processing_status);
CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_sources_content_format ON sources(content_format);
CREATE INDEX IF NOT EXISTS idx_sources_include_in_kb ON sources(include_in_knowledge_base);
CREATE INDEX IF NOT EXISTS idx_tab_membership_video ON video_tab_membership(video_id);

-- AI Content OS SQLite Schema (WAL Mode + FTS5)

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS content_items (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    format_type TEXT NOT NULL, -- 'reels', 'carousel', 'stories', 'multi_format'
    research_summary TEXT,
    ai_raw_output TEXT,
    reels_script TEXT,
    carousel_json TEXT,
    stories_json TEXT,
    caption_text TEXT,
    hashtags TEXT,
    image_prompts TEXT,
    state TEXT NOT NULL DEFAULT 'INITIATED', -- 'INITIATED', 'RESEARCHING', 'AI_GENERATED', 'PENDING_APPROVAL', 'APPROVED', 'PUBLISHING', 'PUBLISHED', 'FAILED'
    is_human_approved INTEGER NOT NULL DEFAULT 0, -- Hardened Human Approval Gate
    rejection_reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS preference_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id TEXT NOT NULL,
    original_text TEXT NOT NULL,
    edited_text TEXT NOT NULL,
    diff_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (content_id) REFERENCES content_items(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS knowledge_base (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source_type TEXT NOT NULL, -- 'web', 'reddit', 'github', 'youtube', 'document'
    url TEXT,
    content_body TEXT NOT NULL,
    tags TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Full-Text Search index for Knowledge Base
CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
    id UNINDEXED,
    title,
    content_body,
    tags,
    tokenize='porter unicode61'
);

CREATE TABLE IF NOT EXISTS execution_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT,
    step_name TEXT NOT NULL,
    status TEXT NOT NULL, -- 'INFO', 'WARNING', 'ERROR', 'SUCCESS'
    message TEXT NOT NULL,
    screenshot_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

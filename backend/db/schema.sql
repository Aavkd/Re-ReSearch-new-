-- =============================================================================
-- Re:Search — Universal Node / Edge schema
-- All CREATE statements use IF NOT EXISTS so this file is safe to re-run.
-- The literal placeholder  {embedding_dim}  is replaced at runtime by
-- backend/db/migrations.py before the SQL is executed.
-- =============================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------------
-- Core tables
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS nodes (
    id           TEXT    PRIMARY KEY,
    node_type    TEXT    NOT NULL,
    title        TEXT    NOT NULL,
    content_path TEXT,                          -- nullable; relative path to file
    metadata     TEXT    DEFAULT '{}',          -- JSON blob
    created_at   INTEGER DEFAULT (unixepoch()),
    updated_at   INTEGER DEFAULT (unixepoch())
);

CREATE TABLE IF NOT EXISTS edges (
    source_id     TEXT NOT NULL,
    target_id     TEXT NOT NULL,
    relation_type TEXT DEFAULT 'related',
    created_at    INTEGER DEFAULT (unixepoch()),
    PRIMARY KEY (source_id, target_id, relation_type),
    FOREIGN KEY (source_id) REFERENCES nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES nodes(id) ON DELETE CASCADE
);

-- Graph traversal indexes
CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target_id);

-- ---------------------------------------------------------------------------
-- Full-text search (FTS5 + porter stemmer)
-- ---------------------------------------------------------------------------

CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(
    id           UNINDEXED,
    title,
    content_body,         -- extracted text inserted by the RAG pipeline
    tokenize = 'porter unicode61'
);

-- Keep FTS in sync with the nodes table on INSERT.
-- content_body starts empty; the RAG ingestor fills it later.
CREATE TRIGGER IF NOT EXISTS nodes_ai
AFTER INSERT ON nodes
BEGIN
    INSERT INTO nodes_fts(id, title, content_body)
    VALUES (new.id, new.title, '');
END;

-- Keep FTS title in sync on UPDATE.
CREATE TRIGGER IF NOT EXISTS nodes_au
AFTER UPDATE OF title ON nodes
BEGIN
    UPDATE nodes_fts SET title = new.title WHERE id = new.id;
END;

-- Remove FTS row when a node is deleted (CASCADE handles the edges table).
CREATE TRIGGER IF NOT EXISTS nodes_ad
AFTER DELETE ON nodes
BEGIN
    DELETE FROM nodes_fts WHERE id = old.id;
END;

-- ---------------------------------------------------------------------------
-- Vector search (sqlite-vec)
-- Dimension is injected at runtime: {embedding_dim}
-- ---------------------------------------------------------------------------

CREATE VIRTUAL TABLE IF NOT EXISTS nodes_vec USING vec0(
    id        TEXT PRIMARY KEY,
    embedding float[{embedding_dim}]
);

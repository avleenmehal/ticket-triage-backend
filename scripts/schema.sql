-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Orders table
CREATE TABLE IF NOT EXISTS orders (
    order_id       TEXT PRIMARY KEY,
    customer_name  TEXT NOT NULL,
    email          TEXT NOT NULL,
    items          JSONB NOT NULL,
    order_date     DATE NOT NULL,
    status         TEXT NOT NULL,
    delivery_date  DATE,
    total_amount   NUMERIC(10, 2) NOT NULL,
    currency       TEXT NOT NULL DEFAULT 'USD'
);

-- Issues table (keyword → issue_type mapping)
CREATE TABLE IF NOT EXISTS issues (
    id         SERIAL PRIMARY KEY,
    keyword    TEXT NOT NULL,
    issue_type TEXT NOT NULL
);

-- Replies table (issue_type → reply template)
CREATE TABLE IF NOT EXISTS replies (
    issue_type TEXT PRIMARY KEY,
    template   TEXT NOT NULL
);

-- Policy chunks table with vector embeddings
CREATE TABLE IF NOT EXISTS policy_chunks (
    doc_id    TEXT PRIMARY KEY,
    file      TEXT NOT NULL,
    text      TEXT NOT NULL,
    embedding vector(384)
);

-- Triage log table (written on every commit_action)
CREATE TABLE IF NOT EXISTS triage_log (
    id               SERIAL PRIMARY KEY,
    order_id         TEXT NOT NULL,
    issue_type       TEXT,
    policy_citations TEXT[],
    final_status     TEXT,
    created_at       TIMESTAMP DEFAULT NOW()
);

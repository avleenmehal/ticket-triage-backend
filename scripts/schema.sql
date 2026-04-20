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

-- Customer profiles (one row per unique email)
CREATE TABLE IF NOT EXISTS customers (
    email        TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    created_at   TIMESTAMP DEFAULT NOW(),
    risk_tier    TEXT NOT NULL DEFAULT 'normal'  -- 'normal' | 'watch' | 'flagged'
);

-- Unified support ticket history — covers refund and replacement claims
-- ticket_type: 'refund' | 'replacement'
-- issue_type: mirrors triage classifier values (e.g. missing_item, duplicate_charge, damaged_item, wrong_item)
-- resolution: JSONB — for refunds: {"amount": 49.99}, for replacements: {"item": "Webcam Pro", "sku": "SKU-230-P"}
-- abuse_label is ground truth for evaluator testing: 'legitimate' | 'suspicious' | 'abusive'
CREATE TABLE IF NOT EXISTS support_tickets (
    id              SERIAL PRIMARY KEY,
    customer_email  TEXT NOT NULL REFERENCES customers(email),
    order_id        TEXT NOT NULL,
    ticket_text     TEXT NOT NULL,
    ticket_type     TEXT NOT NULL,
    issue_type      TEXT NOT NULL,
    requested_at    TIMESTAMP NOT NULL,
    outcome         TEXT NOT NULL DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected'
    resolution      JSONB,
    abuse_label     TEXT NOT NULL DEFAULT 'legitimate'
);

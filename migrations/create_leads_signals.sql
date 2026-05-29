-- Migration: Create leads_signals table
-- Records each score change event for a lead, enabling audit trail and sparkline charts.
-- Run BEFORE enable_rls_all_tables.sql (which enables RLS on this table).

CREATE TABLE IF NOT EXISTS leads_signals (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lead_id         UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    score_before    INTEGER NOT NULL DEFAULT 0,
    score_after     INTEGER NOT NULL DEFAULT 0,
    delta           INTEGER NOT NULL DEFAULT 0,
    signal_type     TEXT,
    signal_keywords TEXT[],
    message_excerpt TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_leads_signals_lead_id     ON leads_signals(lead_id);
CREATE INDEX IF NOT EXISTS idx_leads_signals_created_at  ON leads_signals(created_at DESC);

-- Migration 005: Lead scoring system with signal-based scoring and history tracking
-- Aligns leads schema and adds lead_score_history table for audit trail

-- Phase 1: Add missing columns to leads table (if not present)
-- These columns are queried by CalificacionModule but missing from the original schema
ALTER TABLE leads ADD COLUMN IF NOT EXISTS user_id VARCHAR(255);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS state VARCHAR(50) DEFAULT 'curioso';
ALTER TABLE leads ADD COLUMN IF NOT EXISTS score_reason TEXT;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS score_updated_at TIMESTAMPTZ;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS interaction_count INT DEFAULT 0;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS last_interaction TIMESTAMPTZ;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS urgency NUMERIC(3,1) DEFAULT 0;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS decision_power NUMERIC(3,1) DEFAULT 0;
ALTER TABLE leads ADD COLUMN IF NOT EXISTS budget NUMERIC(12,2);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS tags TEXT[];
ALTER TABLE leads ADD COLUMN IF NOT EXISTS name VARCHAR(255);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS phone VARCHAR(20);
ALTER TABLE leads ADD COLUMN IF NOT EXISTS company VARCHAR(255);

-- Phase 2: Backfill new columns from legacy Spanish names (one-time migration)
UPDATE leads
SET
  name = COALESCE(name, nombre),
  phone = COALESCE(phone, telefono),
  state = COALESCE(state, estado),
  updated_at = COALESCE(updated_at, NOW())
WHERE name IS NULL OR phone IS NULL OR state IS NULL;

-- Phase 3: Extend state enum to include all five states (if constraint exists, loosen it)
-- Note: if a CHECK constraint exists, drop it and recreate
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE contype = 'c' AND conname LIKE '%estado%' AND conrelid = 'leads'::regclass
  ) THEN
    ALTER TABLE leads DROP CONSTRAINT IF EXISTS check_estado;
  END IF;
END $$;

-- Phase 4: Create lead_score_history table (audit trail for scoring decisions)
CREATE TABLE IF NOT EXISTS lead_score_history (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  cliente_id UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
  lead_id UUID NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
  user_id VARCHAR(255),
  score_before NUMERIC(3,1) NOT NULL DEFAULT 0,
  score_after NUMERIC(3,1) NOT NULL DEFAULT 0,
  delta NUMERIC(3,1) NOT NULL,
  signal_type VARCHAR(500), -- comma-separated signal names: "urgency,budget,decision_power"
  signal_keywords TEXT[], -- matched keywords for this message
  message_excerpt VARCHAR(500), -- first 500 chars of user message
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Phase 5: Add indexes for lead_score_history
CREATE INDEX IF NOT EXISTS idx_lead_score_history_lead ON lead_score_history(lead_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_lead_score_history_cliente ON lead_score_history(cliente_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_leads_state_score ON leads(cliente_id, state, score DESC);
CREATE INDEX IF NOT EXISTS idx_leads_user_id ON leads(cliente_id, user_id);

-- Phase 6: Enable RLS on lead_score_history (same policies as leads table)
ALTER TABLE lead_score_history ENABLE ROW LEVEL SECURITY;

-- Allow admins to read all score history for their client
CREATE POLICY IF NOT EXISTS lead_score_history_select_admin ON lead_score_history
  FOR SELECT
  USING (
    cliente_id = (SELECT cliente_id FROM auth.jwt() WHERE role = 'admin')
    OR auth.jwt() ->> 'role' = 'super_admin'
  );

-- Allow superadmins to read everything
CREATE POLICY IF NOT EXISTS lead_score_history_select_superadmin ON lead_score_history
  FOR SELECT
  USING (auth.jwt() ->> 'role' = 'super_admin');

-- Allow service role (backend) to insert
CREATE POLICY IF NOT EXISTS lead_score_history_insert_backend ON lead_score_history
  FOR INSERT
  WITH CHECK (TRUE); -- service role bypasses RLS anyway

-- Phase 7: Update triggers for leads table to maintain updated_at
CREATE OR REPLACE FUNCTION update_leads_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_leads_updated_at ON leads;
CREATE TRIGGER trigger_leads_updated_at
  BEFORE UPDATE ON leads
  FOR EACH ROW
  EXECUTE FUNCTION update_leads_timestamp();

-- Phase 8: Similar trigger for lead_score_history
DROP TRIGGER IF EXISTS trigger_lead_score_history_updated_at ON lead_score_history;
CREATE TRIGGER trigger_lead_score_history_updated_at
  BEFORE UPDATE ON lead_score_history
  FOR EACH ROW
  EXECUTE FUNCTION update_leads_timestamp();

-- Add support for bank transfer and cash payment methods on subscriptions
-- Run this migration in Supabase SQL editor

-- 1. Add payment_method column to subscription
ALTER TABLE subscription ADD COLUMN IF NOT EXISTS payment_method TEXT NOT NULL DEFAULT 'payphone';
ALTER TABLE subscription ADD CONSTRAINT subscription_payment_method_check
  CHECK (payment_method IN ('payphone', 'transferencia', 'efectivo'));

-- 2. Add proof fields for transfer verification
ALTER TABLE subscription ADD COLUMN IF NOT EXISTS pending_proof_url TEXT;
ALTER TABLE subscription ADD COLUMN IF NOT EXISTS pending_proof_submitted_at TIMESTAMPTZ;

-- 3. Make payphone-specific columns nullable (not relevant for manual methods)
ALTER TABLE subscription ALTER COLUMN payphone_client_transaction_id DROP NOT NULL;
ALTER TABLE subscription ALTER COLUMN payphone_transaction_id DROP NOT NULL;

-- 4. Extend status CHECK to include proof_submitted
ALTER TABLE subscription DROP CONSTRAINT IF EXISTS subscription_status_check;
ALTER TABLE subscription ADD CONSTRAINT subscription_status_check
  CHECK (status IN ('active', 'past_due', 'cancelled', 'trialing', 'pending_payment', 'proof_submitted'));

-- 5. Create subscription_payments ledger (one row per monthly billing cycle)
CREATE TABLE IF NOT EXISTS subscription_payments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  subscription_id UUID REFERENCES subscription(id) ON DELETE CASCADE,
  cliente_id UUID REFERENCES clientes(id) ON DELETE CASCADE,
  payment_method TEXT NOT NULL CHECK (payment_method IN ('payphone', 'transferencia', 'efectivo')),
  amount DECIMAL(10, 2) NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'proof_submitted', 'paid', 'rejected')),
  proof_url TEXT,
  period_start TIMESTAMPTZ,
  period_end TIMESTAMPTZ,
  verified_by TEXT,
  verified_at TIMESTAMPTZ,
  notes TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_subscription_payments_cliente_id ON subscription_payments(cliente_id);
CREATE INDEX IF NOT EXISTS idx_subscription_payments_subscription_id ON subscription_payments(subscription_id);
CREATE INDEX IF NOT EXISTS idx_subscription_payments_status ON subscription_payments(status);

-- 6. Enable RLS (service_role bypasses it; same pattern as all other tables)
ALTER TABLE subscription_payments ENABLE ROW LEVEL SECURITY;

-- Allow service_role full access (backend uses service_role)
CREATE POLICY "service_role_all" ON subscription_payments
  FOR ALL TO service_role USING (true) WITH CHECK (true);

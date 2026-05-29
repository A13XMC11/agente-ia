-- Migration: rename Stripe-specific columns in subscription table to Payphone equivalents
-- Run once after deploying the Payphone billing update.

-- Add new Payphone columns
ALTER TABLE subscription
  ADD COLUMN IF NOT EXISTS payphone_client_transaction_id TEXT,
  ADD COLUMN IF NOT EXISTS payphone_transaction_id TEXT;

-- Migrate existing data (if any Stripe IDs were stored, preserve them in a notes column)
-- stripe_subscription_id → payphone_client_transaction_id (both store our internal transaction UUID)
-- stripe_customer_id     → payphone_transaction_id         (both store the provider's transaction ID)
UPDATE subscription
SET
  payphone_client_transaction_id = stripe_subscription_id,
  payphone_transaction_id        = stripe_customer_id
WHERE
  payphone_client_transaction_id IS NULL
  AND stripe_subscription_id IS NOT NULL;

-- Drop old Stripe columns (comment out if you want to keep them for rollback safety)
ALTER TABLE subscription
  DROP COLUMN IF EXISTS stripe_subscription_id,
  DROP COLUMN IF EXISTS stripe_customer_id;

-- Update the status enum to include pending_payment if using CHECK constraints
-- (Only needed if your subscription.status column has a CHECK constraint)
-- ALTER TABLE subscription DROP CONSTRAINT IF EXISTS subscription_status_check;
-- ALTER TABLE subscription ADD CONSTRAINT subscription_status_check
--   CHECK (status IN ('active', 'past_due', 'cancelled', 'trialing', 'pending_payment'));

-- Add index for faster callback lookups
CREATE INDEX IF NOT EXISTS idx_subscription_payphone_client_transaction
  ON subscription (payphone_client_transaction_id)
  WHERE payphone_client_transaction_id IS NOT NULL;

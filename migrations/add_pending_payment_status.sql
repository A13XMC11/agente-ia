-- Add pending_payment to subscription status CHECK constraint
ALTER TABLE subscription DROP CONSTRAINT IF EXISTS subscription_status_check;
ALTER TABLE subscription ADD CONSTRAINT subscription_status_check
  CHECK (status IN ('active', 'past_due', 'cancelled', 'trialing', 'pending_payment'));

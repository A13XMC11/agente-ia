-- Backfill trialing subscription for existing clients that have no subscription row.
-- This prevents the bot gate (router.py subscription check) from blocking clients
-- who were created before the subscription gate was introduced.
--
-- Run once after deploying the subscription gate to production.

INSERT INTO subscription (cliente_id, status, monthly_amount)
SELECT
  c.id AS cliente_id,
  'trialing' AS status,
  CASE c.plan
    WHEN 'basico'       THEN 149
    WHEN 'profesional'  THEN 249
    WHEN 'empresarial'  THEN 399
    ELSE 0
  END AS monthly_amount
FROM clientes c
LEFT JOIN subscription s ON s.cliente_id = c.id
WHERE s.id IS NULL;

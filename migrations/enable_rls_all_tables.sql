-- Migration: Enable Row Level Security on all unrestricted tables
-- Reason: Defense-in-depth — service_role bypasses RLS, but anon/user keys should
--         never access cross-tenant data even if a bug or misconfiguration exposes them.
-- Date: 2026-05-29
--
-- Tables in production currently showing UNRESTRICTED (RLS disabled):
--   agentes, canales_config, citas, clientes, comprobantes_procesados,
--   conversaciones, datos_bancarios, leads_signals, mensajes, modulos_activos, pagos
--
-- NOTE: Policies for most tables already exist from schema.sql.
--       This migration only re-enables the RLS enforcement flag.
--       service_role key continues to bypass RLS automatically — no backend changes needed.

-- ============================================================================
-- 1. Re-enable RLS (policies already defined in schema.sql)
-- ============================================================================
ALTER TABLE agentes               ENABLE ROW LEVEL SECURITY;
ALTER TABLE canales_config        ENABLE ROW LEVEL SECURITY;
ALTER TABLE citas                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE clientes              ENABLE ROW LEVEL SECURITY;
ALTER TABLE comprobantes_procesados ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversaciones        ENABLE ROW LEVEL SECURITY;
ALTER TABLE datos_bancarios       ENABLE ROW LEVEL SECURITY;
ALTER TABLE mensajes              ENABLE ROW LEVEL SECURITY;
ALTER TABLE modulos_activos       ENABLE ROW LEVEL SECURITY;
ALTER TABLE pagos                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE usuarios              ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 1b. subscription — not in original schema.sql, needs policies
-- ============================================================================
ALTER TABLE subscription ENABLE ROW LEVEL SECURITY;

CREATE POLICY "clients_can_see_own_subscription" ON subscription
    FOR SELECT USING (
        cliente_id = (
            SELECT cliente_id FROM usuarios
            WHERE email = auth.email()
            LIMIT 1
        )
    );

-- INSERT/UPDATE only by service_role (Stripe webhooks)
CREATE POLICY "system_can_insert_subscription" ON subscription
    FOR INSERT WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "system_can_update_subscription" ON subscription
    FOR UPDATE USING (auth.role() = 'service_role');

-- ============================================================================
-- 2. leads_signals — policies not yet defined, add them now
-- ============================================================================
ALTER TABLE leads_signals ENABLE ROW LEVEL SECURITY;

-- leads_signals joins through leads which has cliente_id
CREATE POLICY "clients_can_see_own_lead_signals" ON leads_signals
    FOR SELECT USING (
        lead_id IN (
            SELECT id FROM leads
            WHERE cliente_id = (
                SELECT cliente_id FROM usuarios
                WHERE email = auth.email()
                LIMIT 1
            )
        )
    );

CREATE POLICY "system_can_insert_lead_signals" ON leads_signals
    FOR INSERT WITH CHECK (
        lead_id IN (
            SELECT id FROM leads
            WHERE cliente_id = (
                SELECT cliente_id FROM usuarios
                WHERE email = auth.email()
                LIMIT 1
            )
        )
    );

-- ============================================================================
-- Verify
-- ============================================================================
-- SELECT tablename, rowsecurity
-- FROM pg_tables
-- WHERE schemaname = 'public'
-- ORDER BY tablename;

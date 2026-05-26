-- Migration: Create campanas and campaign_recipients tables
-- Reason: UI de campañas masivas requiere estas tablas para crear, lanzar y cancelar campañas
-- Date: 2026-05-24

-- ============================================================================
-- Table: campanas
-- ============================================================================
CREATE TABLE IF NOT EXISTS campanas (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id      UUID NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    message         TEXT NOT NULL,
    target_segment  TEXT NOT NULL DEFAULT 'all'
                        CHECK (target_segment IN ('all', 'hot_leads', 'inactive', 'customers', 'custom')),
    channel         TEXT NOT NULL DEFAULT 'whatsapp'
                        CHECK (channel IN ('whatsapp', 'email')),
    status          TEXT NOT NULL DEFAULT 'draft'
                        CHECK (status IN ('draft', 'scheduled', 'sent', 'cancelled')),
    scheduled_for   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recipients_count INTEGER,
    launched_at     TIMESTAMPTZ,
    sent_at         TIMESTAMPTZ,
    cancelled_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- Table: campaign_recipients
-- ============================================================================
CREATE TABLE IF NOT EXISTS campaign_recipients (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id  UUID NOT NULL REFERENCES campanas(id) ON DELETE CASCADE,
    user_id      UUID,
    phone        TEXT,
    status       TEXT NOT NULL DEFAULT 'pending'
                     CHECK (status IN ('pending', 'sent', 'delivered', 'failed')),
    sent_at      TIMESTAMPTZ,
    error        TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ============================================================================
-- Indexes
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_campanas_cliente_id    ON campanas(cliente_id);
CREATE INDEX IF NOT EXISTS idx_campanas_status        ON campanas(status);
CREATE INDEX IF NOT EXISTS idx_campanas_scheduled_for ON campanas(scheduled_for) WHERE status = 'scheduled';

CREATE INDEX IF NOT EXISTS idx_campaign_recipients_campaign_id ON campaign_recipients(campaign_id);
CREATE INDEX IF NOT EXISTS idx_campaign_recipients_status      ON campaign_recipients(campaign_id, status);

-- ============================================================================
-- Row Level Security
-- ============================================================================
ALTER TABLE campanas ENABLE ROW LEVEL SECURITY;
ALTER TABLE campaign_recipients ENABLE ROW LEVEL SECURITY;

-- Clientes solo ven sus propias campañas
CREATE POLICY campanas_cliente_select ON campanas
    FOR SELECT USING (
        cliente_id = (
            SELECT cliente_id FROM usuarios
            WHERE email = auth.email()
            LIMIT 1
        )
    );

CREATE POLICY campanas_cliente_insert ON campanas
    FOR INSERT WITH CHECK (
        cliente_id = (
            SELECT cliente_id FROM usuarios
            WHERE email = auth.email()
            LIMIT 1
        )
    );

CREATE POLICY campanas_cliente_update ON campanas
    FOR UPDATE USING (
        cliente_id = (
            SELECT cliente_id FROM usuarios
            WHERE email = auth.email()
            LIMIT 1
        )
    );

-- Recipients: acceso a través de la campaña del cliente
CREATE POLICY campaign_recipients_select ON campaign_recipients
    FOR SELECT USING (
        campaign_id IN (
            SELECT id FROM campanas WHERE cliente_id = (
                SELECT cliente_id FROM usuarios WHERE email = auth.email() LIMIT 1
            )
        )
    );

-- Verificar que las tablas se crearon correctamente:
-- SELECT table_name FROM information_schema.tables
-- WHERE table_schema = 'public' AND table_name IN ('campanas', 'campaign_recipients');

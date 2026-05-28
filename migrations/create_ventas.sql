-- Migration: create product_catalog, quotes, and catalog_sync_config tables

-- ── product_catalog ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS product_catalog (
    id          UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id  UUID           NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    sku         TEXT,                          -- optional; used as upsert key on sync
    nombre      TEXT           NOT NULL,
    descripcion TEXT,
    precio      NUMERIC(10, 2) NOT NULL DEFAULT 0,
    moneda      TEXT           NOT NULL DEFAULT 'USD',
    categoria   TEXT,
    stock       INTEGER,                       -- NULL = unlimited / not tracked
    imagen_url  TEXT,
    activo      BOOLEAN        NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    UNIQUE (cliente_id, sku)                   -- sku unique per client (nullable ok)
);

CREATE INDEX IF NOT EXISTS idx_product_catalog_cliente
    ON product_catalog(cliente_id);
CREATE INDEX IF NOT EXISTS idx_product_catalog_activo
    ON product_catalog(cliente_id, activo);

ALTER TABLE product_catalog ENABLE ROW LEVEL SECURITY;

-- ── quotes ────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quotes (
    id                  UUID           PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id          UUID           NOT NULL REFERENCES clientes(id) ON DELETE CASCADE,
    user_id             UUID,
    items               JSONB          NOT NULL DEFAULT '[]',
    subtotal            NUMERIC(10, 2) NOT NULL DEFAULT 0,
    discount_percentage NUMERIC(5, 2)  NOT NULL DEFAULT 0,
    discount_amount     NUMERIC(10, 2) NOT NULL DEFAULT 0,
    total               NUMERIC(10, 2) NOT NULL DEFAULT 0,
    moneda              TEXT           NOT NULL DEFAULT 'USD',
    notas               TEXT,
    discount_reason     TEXT,
    status              TEXT           NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending', 'sent', 'accepted', 'rejected', 'expired')),
    payment_link_id     UUID,
    sent_at             TIMESTAMPTZ,
    accepted_at         TIMESTAMPTZ,
    rejected_at         TIMESTAMPTZ,
    expires_at          TIMESTAMPTZ    NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
    created_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_quotes_cliente
    ON quotes(cliente_id);
CREATE INDEX IF NOT EXISTS idx_quotes_user
    ON quotes(user_id);
CREATE INDEX IF NOT EXISTS idx_quotes_status
    ON quotes(cliente_id, status);

ALTER TABLE quotes ENABLE ROW LEVEL SECURITY;

-- ── catalog_sync_config ───────────────────────────────────────────────────────
-- One row per client that wants automatic catalog sync.
-- tipo = 'manual'  → no auto-sync; client manages products from the dashboard
-- tipo = 'sheets'  → pull from a public Google Sheets URL every sync_interval_minutes
-- tipo = 'webhook' → pull from client's own API endpoint every sync_interval_minutes
CREATE TABLE IF NOT EXISTS catalog_sync_config (
    id                     UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    cliente_id             UUID        NOT NULL UNIQUE REFERENCES clientes(id) ON DELETE CASCADE,
    tipo                   TEXT        NOT NULL DEFAULT 'manual'
        CHECK (tipo IN ('manual', 'sheets', 'webhook')),
    sheets_url             TEXT,       -- Google Sheets edit or pub URL
    webhook_url            TEXT,       -- External API that returns JSON product list
    sync_interval_minutes  INTEGER     NOT NULL DEFAULT 60,
    ultimo_sync            TIMESTAMPTZ,
    activo                 BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE catalog_sync_config ENABLE ROW LEVEL SECURITY;

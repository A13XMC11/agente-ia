-- Migration: Add follow-up tracking columns for automatic follow-up system
-- Reason: SeguimientoModule needs to track sent reminders for citas and store alert references
-- Date: 2026-05-15

-- Add reminder tracking columns to citas table
ALTER TABLE citas
ADD COLUMN IF NOT EXISTS recordatorio_24h_enviado BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS recordatorio_1h_enviado BOOLEAN DEFAULT FALSE;

-- Add reference ID to alertas table for lead/cita identification
ALTER TABLE alertas
ADD COLUMN IF NOT EXISTS referencia_id TEXT;

-- Create index for faster lookups when checking for duplicate alerts
CREATE INDEX IF NOT EXISTS idx_alertas_cliente_tipo_referencia
ON alertas(cliente_id, tipo, referencia_id);

-- Verify columns were added
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'citas' AND column_name LIKE 'recordatorio%';
-- SELECT column_name, data_type FROM information_schema.columns
-- WHERE table_name = 'alertas' AND column_name = 'referencia_id';

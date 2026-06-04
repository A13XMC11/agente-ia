-- Migration: Add WhatsApp template support to campanas
-- Reason: Meta requires pre-approved templates for outbound messages outside 24h window
-- Date: 2026-06-04

ALTER TABLE campanas
  ADD COLUMN IF NOT EXISTS template_name       TEXT,
  ADD COLUMN IF NOT EXISTS template_language   TEXT NOT NULL DEFAULT 'es',
  ADD COLUMN IF NOT EXISTS template_variables  JSONB NOT NULL DEFAULT '[]';

-- template_name: name of the approved Meta template (e.g. 'oferta_especial')
--   NULL means use free-form text (only valid within 24h conversation window)
-- template_language: BCP-47 language code (es, en_US, etc.)
-- template_variables: ordered list of text values for {{1}}, {{2}}, ... placeholders
--   Example: ["Juan", "30%", "junio"] fills {{1}}=Juan, {{2}}=30%, {{3}}=junio

COMMENT ON COLUMN campanas.template_name IS 'Meta-approved HSM template name. Required for outbound campaigns outside 24h window.';
COMMENT ON COLUMN campanas.template_variables IS 'Ordered array of text substitutions for template body parameters {{1}}, {{2}}, ...';

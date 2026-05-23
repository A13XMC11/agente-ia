-- Migration: Re-enable Row Level Security on leads table
-- Reason: RLS was disabled as workaround; CalificacionModule uses service_role key
--         which bypasses RLS automatically — no need to disable it globally.
-- Date: 2026-05-22

ALTER TABLE leads ENABLE ROW LEVEL SECURITY;

-- Policies already defined in schema.sql:
--   clients_can_see_own_leads    (SELECT)
--   clients_can_insert_own_leads (INSERT)
--   clients_can_update_own_leads (UPDATE)
--
-- service_role key bypasses RLS by default in Supabase — CalificacionModule
-- continues to work without any policy change.

-- Verify RLS status:
-- SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'leads';

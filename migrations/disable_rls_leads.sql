-- Migration: Disable Row Level Security on leads table
-- Reason: CalificacionModule needs to insert/update leads without RLS restrictions
-- Date: 2026-05-14

ALTER TABLE leads DISABLE ROW LEVEL SECURITY;

-- Verify RLS status
-- SELECT tablename, rowsecurity FROM pg_tables WHERE tablename = 'leads';

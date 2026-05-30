-- Migration: Enable calificacion module for all existing clients
-- Clients who have a modulos_activos row with calificacion = false or NULL
-- will not trigger automatic lead scoring. This migration enables it globally.
--
-- Safe to re-run (UPDATE is idempotent).

UPDATE modulos_activos
SET calificacion = true
WHERE calificacion IS FALSE OR calificacion IS NULL;

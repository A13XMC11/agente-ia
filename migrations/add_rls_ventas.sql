-- RLS policies for product_catalog, quotes, and catalog_sync_config
-- The dashboard and backend always use the service_role key, which bypasses RLS.
-- These policies block direct access via the anon/authenticated Supabase keys.

-- ── product_catalog ───────────────────────────────────────────────────────────

-- Block anon reads (e.g. direct Supabase JS calls with anon key)
CREATE POLICY "anon_no_access_product_catalog"
ON product_catalog FOR ALL TO anon
USING (false);

-- Authenticated Supabase users (future-proofing): read only their client's products
-- Currently unused — the dashboard uses custom JWTs, not Supabase Auth sessions.
CREATE POLICY "authenticated_read_own_products"
ON product_catalog FOR SELECT TO authenticated
USING (
  cliente_id::text = (auth.jwt() ->> 'cliente_id')
);

-- ── quotes ────────────────────────────────────────────────────────────────────

CREATE POLICY "anon_no_access_quotes"
ON quotes FOR ALL TO anon
USING (false);

CREATE POLICY "authenticated_read_own_quotes"
ON quotes FOR SELECT TO authenticated
USING (
  cliente_id::text = (auth.jwt() ->> 'cliente_id')
);

-- ── catalog_sync_config ───────────────────────────────────────────────────────

CREATE POLICY "anon_no_access_catalog_sync_config"
ON catalog_sync_config FOR ALL TO anon
USING (false);

CREATE POLICY "authenticated_read_own_sync_config"
ON catalog_sync_config FOR SELECT TO authenticated
USING (
  cliente_id::text = (auth.jwt() ->> 'cliente_id')
);

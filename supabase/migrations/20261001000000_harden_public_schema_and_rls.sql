-- Migration: 20261001000000_harden_public_schema_and_rls.sql
-- Description: Enable Row Level Security (RLS) on unhardened tables (shops, menu_items),
--              establish explicit least-privilege table and column grants, and configure
--              strict access policies across all public-schema tables.

-- ============================================================================
-- 1. Enable Row Level Security across public schema tables
-- ============================================================================

ALTER TABLE IF EXISTS shops ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS menu_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS shop_curation ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS shop_curation_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE IF EXISTS favorites ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 2. Explicit Least-Privilege Table Grants & Revocations
-- ============================================================================

-- 2.1 menu_items: Intentionally unused in public Data API; restricted to service_role
REVOKE ALL ON menu_items FROM anon, authenticated, public;
GRANT ALL ON menu_items TO service_role;

-- 2.2 shops: Public & authenticated may SELECT; mutations restricted to authenticated curators/admins & service_role
REVOKE ALL ON shops FROM anon, authenticated, public;
GRANT SELECT ON shops TO anon, authenticated;
GRANT INSERT, UPDATE, DELETE ON shops TO authenticated;
GRANT ALL ON shops TO service_role;

-- 2.3 shop_curation: Expose only non-sensitive columns (shop_id, status) to anon and authenticated
REVOKE ALL ON shop_curation FROM anon, authenticated, public;
GRANT SELECT (shop_id, status) ON shop_curation TO anon, authenticated;
GRANT ALL ON shop_curation TO service_role;

-- 2.4 shop_curation_audit: Curator read-only; mutations restricted to service_role
REVOKE ALL ON shop_curation_audit FROM anon, authenticated, public;
GRANT SELECT ON shop_curation_audit TO authenticated;
GRANT ALL ON shop_curation_audit TO service_role;

-- 2.5 reviews: No anon access; authenticated read and self-delete; writes via security-definer RPCs
REVOKE ALL ON reviews FROM anon, public;
REVOKE INSERT, UPDATE ON reviews FROM authenticated;
GRANT SELECT, DELETE ON reviews TO authenticated;
GRANT ALL ON reviews TO service_role;

-- 2.6 favorites: No anon access; authenticated read and self-delete; writes via security-definer RPC
REVOKE ALL ON favorites FROM anon, public;
REVOKE INSERT, UPDATE ON favorites FROM authenticated;
GRANT SELECT, DELETE ON favorites TO authenticated;
GRANT ALL ON favorites TO service_role;

-- ============================================================================
-- 3. Row Level Security Policies
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 3.1 menu_items policies
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Allow service role full access on menu_items" ON menu_items;
CREATE POLICY "Allow service role full access on menu_items" ON menu_items
    TO service_role USING (true) WITH CHECK (true);

-- ----------------------------------------------------------------------------
-- 3.2 shops policies
-- ----------------------------------------------------------------------------
-- Public/Authenticated: SELECT allowed for APPROVED shops or curator/admin callers
DROP POLICY IF EXISTS "Allow public read access on approved shops" ON shops;
CREATE POLICY "Allow public read access on approved shops" ON shops
    FOR SELECT TO anon, authenticated
    USING (
        EXISTS (
            SELECT 1 FROM shop_curation sc
            WHERE sc.shop_id = shops.id
              AND sc.status = 'APPROVED'
        )
        OR (auth.jwt() -> 'app_metadata' ->> 'role') IN ('curator', 'admin')
    );

-- Authenticated Curators/Admins: INSERT allowed
DROP POLICY IF EXISTS "Allow curator and admin to insert shops" ON shops;
CREATE POLICY "Allow curator and admin to insert shops" ON shops
    FOR INSERT TO authenticated
    WITH CHECK (
        (auth.jwt() -> 'app_metadata' ->> 'role') IN ('curator', 'admin')
    );

-- Authenticated Curators/Admins: UPDATE allowed
DROP POLICY IF EXISTS "Allow curator and admin to update shops" ON shops;
CREATE POLICY "Allow curator and admin to update shops" ON shops
    FOR UPDATE TO authenticated
    USING ((auth.jwt() -> 'app_metadata' ->> 'role') IN ('curator', 'admin'))
    WITH CHECK ((auth.jwt() -> 'app_metadata' ->> 'role') IN ('curator', 'admin'));

-- Authenticated Curators/Admins: DELETE allowed
DROP POLICY IF EXISTS "Allow curator and admin to delete shops" ON shops;
CREATE POLICY "Allow curator and admin to delete shops" ON shops
    FOR DELETE TO authenticated
    USING ((auth.jwt() -> 'app_metadata' ->> 'role') IN ('curator', 'admin'));

-- Service Role: full access
DROP POLICY IF EXISTS "Allow service role full access on shops" ON shops;
CREATE POLICY "Allow service role full access on shops" ON shops
    TO service_role USING (true) WITH CHECK (true);

-- ----------------------------------------------------------------------------
-- 3.3 shop_curation policies
-- ----------------------------------------------------------------------------
-- Drop legacy overly permissive public read policy
DROP POLICY IF EXISTS "Allow public read access on shop_curation" ON shop_curation;

-- Scoped SELECT policy: APPROVED shops readable, or all shops if curator/admin
DROP POLICY IF EXISTS "Allow read access on approved shop curation status" ON shop_curation;
CREATE POLICY "Allow read access on approved shop curation status" ON shop_curation
    FOR SELECT TO anon, authenticated
    USING (
        status = 'APPROVED'
        OR (auth.jwt() -> 'app_metadata' ->> 'role') IN ('curator', 'admin')
    );

-- Service Role: full access
DROP POLICY IF EXISTS "Allow service role full access on shop_curation" ON shop_curation;
CREATE POLICY "Allow service role full access on shop_curation" ON shop_curation
    TO service_role USING (true) WITH CHECK (true);

-- ----------------------------------------------------------------------------
-- 3.4 shop_curation_audit policies
-- ----------------------------------------------------------------------------
DROP POLICY IF EXISTS "Allow curator read access on shop_curation_audit" ON shop_curation_audit;
CREATE POLICY "Allow curator read access on shop_curation_audit" ON shop_curation_audit
    FOR SELECT TO authenticated
    USING (
        (auth.jwt() -> 'app_metadata' ->> 'role') IN ('curator', 'admin')
    );

DROP POLICY IF EXISTS "Allow service role full access on shop_curation_audit" ON shop_curation_audit;
CREATE POLICY "Allow service role full access on shop_curation_audit" ON shop_curation_audit
    TO service_role USING (true) WITH CHECK (true);

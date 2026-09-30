-- Migration: 20260930000000_favorite_coffee_shops.sql
-- Description: Table access privileges, Row Level Security (RLS), and secure RPCs for favorite coffee shops

-- 1. Table Access Privileges
-- Prevent direct client insertion and updates via PostgREST.
-- Controlled writes must pass through security-definer RPC functions.
REVOKE INSERT, UPDATE ON favorites FROM authenticated;
REVOKE INSERT, UPDATE ON favorites FROM anon;
REVOKE INSERT, UPDATE ON favorites FROM public;
GRANT SELECT, DELETE ON favorites TO authenticated;

-- 2. Row Level Security (RLS)
ALTER TABLE favorites ENABLE ROW LEVEL SECURITY;

-- Authenticated SELECT: allowed only for caller's own favorites (cross-user isolation)
DROP POLICY IF EXISTS "Allow authenticated read access on favorites" ON favorites;
CREATE POLICY "Allow authenticated read access on favorites" ON favorites
    FOR SELECT TO authenticated
    USING (auth.uid() = user_id);

-- Authenticated DELETE: allowed only for caller's own favorites
DROP POLICY IF EXISTS "Allow users to delete own favorite" ON favorites;
CREATE POLICY "Allow users to delete own favorite" ON favorites
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- Service role full access for internal backend maintenance tasks
DROP POLICY IF EXISTS "Allow service role full access on favorites" ON favorites;
CREATE POLICY "Allow service role full access on favorites" ON favorites
    TO service_role USING (true) WITH CHECK (true);

-- 3. Controlled Secure Write RPC
-- Derives caller identity from JWT auth.uid(), verifies shop existence and APPROVED curation status,
-- and prevents client-forged user_id or timestamps.
CREATE OR REPLACE FUNCTION create_user_favorite(
    p_shop_id UUID
)
RETURNS favorites
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth, pg_temp
AS $$
DECLARE
    v_user_id UUID;
    v_favorite favorites;
BEGIN
    -- Derive caller identity from authenticated database context
    v_user_id := auth.uid();
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Authentication required to favorite a coffee shop.'
            USING ERRCODE = '28000';
    END IF;

    -- Verify coffee shop existence
    IF NOT EXISTS (SELECT 1 FROM shops WHERE id = p_shop_id) THEN
        RAISE EXCEPTION 'Coffee shop not found.'
            USING ERRCODE = 'P0002';
    END IF;

    -- Enforce APPROVED shop curation status
    IF NOT EXISTS (
        SELECT 1 FROM shop_curation
        WHERE shop_id = p_shop_id AND status = 'APPROVED'
    ) THEN
        RAISE EXCEPTION 'Cannot favorite a coffee shop that is not approved for public discovery.'
            USING ERRCODE = 'P0001';
    END IF;

    -- Enforce 1 favorite per user per shop uniqueness constraint
    IF EXISTS (
        SELECT 1 FROM favorites
        WHERE user_id = v_user_id AND shop_id = p_shop_id
    ) THEN
        RAISE EXCEPTION 'You have already favorited this coffee shop.'
            USING ERRCODE = '23505';
    END IF;

    -- Insert favorite record with strictly server-managed fields
    INSERT INTO favorites (
        shop_id,
        user_id,
        created_at
    ) VALUES (
        p_shop_id,
        v_user_id,
        NOW()
    )
    RETURNING * INTO v_favorite;

    RETURN v_favorite;
END;
$$;

-- Restrict execution privileges on secure favorite RPC to authenticated role only
REVOKE EXECUTE ON FUNCTION create_user_favorite(UUID) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION create_user_favorite(UUID) TO authenticated;

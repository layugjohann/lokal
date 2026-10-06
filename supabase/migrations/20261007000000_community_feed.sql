-- Migration: 20261007000000_community_feed.sql
-- Description: Community feed index, secure RPC with bounded (limit + 1) pagination,
--              privacy projection, and least-privilege execution grants.

-- ============================================================================
-- 1. Chronological Feed Index on First-Party LOKAL Reviews
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_reviews_community_feed
    ON public.reviews (created_at DESC, id DESC)
    WHERE source = 'lokal';

-- ============================================================================
-- 2. Community Feed Retrieval Stored Procedure
-- ============================================================================
-- Returns recent first-party LOKAL reviews for APPROVED coffee shops.
-- Excludes user_id, email, curator notes, claim metadata, and internal fields.
-- Fetches up to (limit + 1) rows so the backend service layer can deterministically
-- derive `has_more` without unbounded scans or inaccurate length guesses.
CREATE OR REPLACE FUNCTION get_community_feed(
    p_limit INTEGER DEFAULT 20,
    p_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    shop_id UUID,
    shop_name TEXT,
    shop_address TEXT,
    author_name TEXT,
    rating INTEGER,
    content TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_limit INTEGER;
    v_offset INTEGER;
BEGIN
    -- Clamp pagination limits to safe bounded windows (max 50, default 20)
    v_limit := COALESCE(p_limit, 20);
    IF v_limit < 1 THEN
        v_limit := 20;
    ELSIF v_limit > 50 THEN
        v_limit := 50;
    END IF;

    -- Clamp offset to non-negative integer
    v_offset := GREATEST(COALESCE(p_offset, 0), 0);

    RETURN QUERY
    SELECT
        r.id,
        r.shop_id,
        s.name AS shop_name,
        s.address AS shop_address,
        r.author_name,
        r.rating,
        r.content,
        r.created_at,
        r.updated_at
    FROM public.reviews r
    INNER JOIN public.shops s ON s.id = r.shop_id
    INNER JOIN public.shop_curation sc ON sc.shop_id = r.shop_id
    WHERE r.source = 'lokal'
      AND sc.status = 'APPROVED'
    ORDER BY r.created_at DESC, r.id DESC
    LIMIT (v_limit + 1)
    OFFSET v_offset;
END;
$$;

-- ============================================================================
-- 3. Execution Privileges & Least-Privilege Grants
-- ============================================================================
REVOKE ALL ON FUNCTION get_community_feed(INTEGER, INTEGER) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION get_community_feed(INTEGER, INTEGER) FROM anon;
GRANT EXECUTE ON FUNCTION get_community_feed(INTEGER, INTEGER) TO authenticated, service_role;

-- Migration: 20260919000000_user_reviews.sql
-- Description: LOKAL first-party user reviews schema, constraints, indexes, RLS, and secure RPCs

-- 1. Table Schema Enhancements
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS author_name TEXT NOT NULL DEFAULT 'LOKAL User';
ALTER TABLE reviews ALTER COLUMN source SET DEFAULT 'lokal';

-- 2. Single review per user per shop constraint (automatically creates unique index)
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_reviews_user_shop') THEN
        ALTER TABLE reviews ADD CONSTRAINT uq_reviews_user_shop UNIQUE (user_id, shop_id);
    END IF;
END $$;

-- 3. Performance & lookup indexes
CREATE INDEX IF NOT EXISTS idx_reviews_shop_id ON reviews (shop_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews (user_id);

-- 4. Table Privileges
-- Prevent direct client insertion and updates via PostgREST.
-- Controlled writes must pass through security-definer RPC functions.
REVOKE INSERT, UPDATE ON reviews FROM authenticated;
REVOKE INSERT, UPDATE ON reviews FROM anon;
REVOKE INSERT, UPDATE ON reviews FROM public;
GRANT SELECT, DELETE ON reviews TO authenticated;

-- 5. Row Level Security (RLS)
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;

-- Drop legacy insert/update policies if previously created
DROP POLICY IF EXISTS "Allow users to insert own review" ON reviews;
DROP POLICY IF EXISTS "Allow users to update own review" ON reviews;

-- Authenticated SELECT: allowed for APPROVED shops OR the user's own review
DROP POLICY IF EXISTS "Allow authenticated read access on reviews" ON reviews;
CREATE POLICY "Allow authenticated read access on reviews" ON reviews
    FOR SELECT TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM shop_curation sc
            WHERE sc.shop_id = reviews.shop_id
              AND sc.status = 'APPROVED'
        )
        OR auth.uid() = user_id
    );

-- Authenticated DELETE: allowed only for caller's own review (even if shop is excluded/pending_review)
DROP POLICY IF EXISTS "Allow users to delete own review" ON reviews;
CREATE POLICY "Allow users to delete own review" ON reviews
    FOR DELETE TO authenticated
    USING (auth.uid() = user_id);

-- Service role full access for internal backend maintenance tasks
DROP POLICY IF EXISTS "Allow service role full access on reviews" ON reviews;
CREATE POLICY "Allow service role full access on reviews" ON reviews
    TO service_role USING (true) WITH CHECK (true);

-- 6. Controlled Secure Write RPCs

-- Secure RPC: create_user_review
-- Derives caller identity from JWT auth.uid(), snapshots server-side author name,
-- enforces APPROVED shop curation status, and prevents client-forged metadata.
CREATE OR REPLACE FUNCTION create_user_review(
    p_shop_id UUID,
    p_rating INTEGER,
    p_content TEXT DEFAULT NULL
)
RETURNS reviews
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth, pg_temp
AS $$
DECLARE
    v_user_id UUID;
    v_author_name TEXT;
    v_review reviews;
BEGIN
    -- Derive caller identity from authenticated database context
    v_user_id := auth.uid();
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Authentication required to submit a review.'
            USING ERRCODE = '28000';
    END IF;

    -- Validate rating range
    IF p_rating IS NULL OR p_rating < 1 OR p_rating > 5 THEN
        RAISE EXCEPTION 'Rating must be between 1 and 5.'
            USING ERRCODE = '22003';
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
        RAISE EXCEPTION 'Cannot review a coffee shop that is not approved for public discovery.'
            USING ERRCODE = 'P0001';
    END IF;

    -- Enforce 1 review per user per shop uniqueness constraint
    IF EXISTS (
        SELECT 1 FROM reviews
        WHERE user_id = v_user_id AND shop_id = p_shop_id
    ) THEN
        RAISE EXCEPTION 'You have already reviewed this coffee shop. You can edit your existing review.'
            USING ERRCODE = '23505';
    END IF;

    -- Resolve author display name snapshot from server-side profile metadata
    SELECT COALESCE(
        NULLIF(TRIM(raw_user_meta_data->>'full_name'), ''),
        NULLIF(TRIM(raw_user_meta_data->>'display_name'), ''),
        NULLIF(TRIM((auth.jwt() -> 'user_metadata' ->> 'full_name')), ''),
        NULLIF(TRIM((auth.jwt() -> 'user_metadata' ->> 'display_name')), ''),
        'LOKAL User'
    )
    INTO v_author_name
    FROM auth.users
    WHERE id = v_user_id;

    IF v_author_name IS NULL THEN
        v_author_name := COALESCE(
            NULLIF(TRIM((auth.jwt() -> 'user_metadata' ->> 'full_name')), ''),
            NULLIF(TRIM((auth.jwt() -> 'user_metadata' ->> 'display_name')), ''),
            'LOKAL User'
        );
    END IF;

    -- Insert review record with strictly server-managed fields
    INSERT INTO reviews (
        shop_id,
        user_id,
        author_name,
        rating,
        content,
        source,
        created_at,
        updated_at
    ) VALUES (
        p_shop_id,
        v_user_id,
        v_author_name,
        p_rating,
        NULLIF(TRIM(p_content), ''),
        'lokal',
        NOW(),
        NOW()
    )
    RETURNING * INTO v_review;

    RETURN v_review;
END;
$$;

-- Secure RPC: update_user_review
-- Derives caller identity from JWT auth.uid(), enforces APPROVED shop curation status,
-- preserves server-managed fields (author_name, source, user_id, shop_id, created_at),
-- and performs atomic partial update on rating and/or content.
CREATE OR REPLACE FUNCTION update_user_review(
    p_shop_id UUID,
    p_rating INTEGER DEFAULT NULL,
    p_content TEXT DEFAULT NULL,
    p_update_content BOOLEAN DEFAULT FALSE
)
RETURNS reviews
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, auth, pg_temp
AS $$
DECLARE
    v_user_id UUID;
    v_review reviews;
BEGIN
    -- Derive caller identity from authenticated database context
    v_user_id := auth.uid();
    IF v_user_id IS NULL THEN
        RAISE EXCEPTION 'Authentication required to update a review.'
            USING ERRCODE = '28000';
    END IF;

    -- Validate field presence
    IF p_rating IS NULL AND NOT p_update_content THEN
        RAISE EXCEPTION 'At least one field (rating or content) must be provided for update.'
            USING ERRCODE = '22023';
    END IF;

    -- Validate rating range if provided
    IF p_rating IS NOT NULL AND (p_rating < 1 OR p_rating > 5) THEN
        RAISE EXCEPTION 'Rating must be between 1 and 5.'
            USING ERRCODE = '22003';
    END IF;

    -- Verify coffee shop existence
    IF NOT EXISTS (SELECT 1 FROM shops WHERE id = p_shop_id) THEN
        RAISE EXCEPTION 'Coffee shop not found.'
            USING ERRCODE = 'P0002';
    END IF;

    -- Enforce APPROVED shop curation status (editing is blocked if shop is excluded/pending)
    IF NOT EXISTS (
        SELECT 1 FROM shop_curation
        WHERE shop_id = p_shop_id AND status = 'APPROVED'
    ) THEN
        RAISE EXCEPTION 'Cannot edit reviews for a coffee shop that is not approved for public discovery.'
            USING ERRCODE = 'P0001';
    END IF;

    -- Verify that the caller has an existing review for this shop
    IF NOT EXISTS (
        SELECT 1 FROM reviews
        WHERE user_id = v_user_id AND shop_id = p_shop_id
    ) THEN
        RAISE EXCEPTION 'You have not reviewed this coffee shop.'
            USING ERRCODE = 'P0002';
    END IF;

    -- Perform partial update on mutable fields only
    UPDATE reviews
    SET
        rating = COALESCE(p_rating, rating),
        content = CASE WHEN p_update_content THEN NULLIF(TRIM(p_content), '') ELSE content END,
        updated_at = NOW()
    WHERE user_id = v_user_id AND shop_id = p_shop_id
    RETURNING * INTO v_review;

    RETURN v_review;
END;
$$;

-- Grant execution privileges on secure review RPCs to authenticated role
GRANT EXECUTE ON FUNCTION create_user_review(UUID, INTEGER, TEXT) TO authenticated;
GRANT EXECUTE ON FUNCTION update_user_review(UUID, INTEGER, TEXT, BOOLEAN) TO authenticated;

-- Migration: 20261006000000_shop_claims.sql
-- Description: Coffee shop owner claims table, claim status enum, partial unique indexes,
--              Row Level Security policies, and least-privilege table grants.

-- ============================================================================
-- 1. Create Enum for Claim Status
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'shop_claim_status') THEN
        CREATE TYPE shop_claim_status AS ENUM ('PENDING', 'APPROVED', 'REJECTED', 'REVOKED');
    END IF;
END $$;

-- ============================================================================
-- 2. Dedicated Shop Claims Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS shop_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    status shop_claim_status NOT NULL DEFAULT 'PENDING',
    claimant_name TEXT NOT NULL,
    claimant_phone TEXT,
    claimant_role TEXT NOT NULL,
    business_proof TEXT,
    curator_id UUID,
    review_notes TEXT,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())
);

-- Trigger for shop_claims.updated_at
DROP TRIGGER IF EXISTS set_shop_claims_updated_at ON shop_claims;
CREATE TRIGGER set_shop_claims_updated_at
    BEFORE UPDATE ON shop_claims
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- 3. Indexes & Uniqueness Constraints
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_shop_claims_shop_id ON shop_claims (shop_id);
CREATE INDEX IF NOT EXISTS idx_shop_claims_user_id ON shop_claims (user_id);
CREATE INDEX IF NOT EXISTS idx_shop_claims_status ON shop_claims (status);

-- Authoritative single-ownership constraint: at most ONE active approved owner per shop
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_approved_claim_per_shop
    ON shop_claims (shop_id)
    WHERE status = 'APPROVED';

-- Single pending claim constraint: at most ONE pending claim per user per shop
CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_pending_claim_per_user_shop
    ON shop_claims (user_id, shop_id)
    WHERE status = 'PENDING';

-- ============================================================================
-- 4. Row Level Security & Least-Privilege Grants
-- ============================================================================
ALTER TABLE shop_claims ENABLE ROW LEVEL SECURITY;

-- Revoke all privileges from client roles by default
REVOKE ALL ON shop_claims FROM anon, authenticated, public;

-- Authenticated users may read their own claims or all claims if curator/admin
GRANT SELECT ON shop_claims TO authenticated;

-- Service role has full access via backend gateway
GRANT ALL ON shop_claims TO service_role;

-- RLS Policies
DROP POLICY IF EXISTS "Allow users to read own claims and curators to read all" ON shop_claims;
CREATE POLICY "Allow users to read own claims and curators to read all" ON shop_claims
    FOR SELECT TO authenticated
    USING (
        auth.uid() = user_id
        OR (auth.jwt() -> 'app_metadata' ->> 'role') IN ('curator', 'admin')
    );

DROP POLICY IF EXISTS "Allow service role full access on shop_claims" ON shop_claims;
CREATE POLICY "Allow service role full access on shop_claims" ON shop_claims
    TO service_role USING (true) WITH CHECK (true);

-- ============================================================================
-- 5. Atomic Curation Demotion Trigger
-- ============================================================================
-- Ensures that transitioning a shop away from APPROVED (to EXCLUDED or PENDING_REVIEW)
-- atomically revokes any active approved claims in the exact same database transaction.
-- If revocation fails, the entire transaction rolls back and curation status does not commit.
-- Restoration back to APPROVED does not resurrect revoked claims.
CREATE OR REPLACE FUNCTION revoke_approved_claims_on_curation_demotion()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    IF OLD.status = 'APPROVED' AND NEW.status != 'APPROVED' THEN
        UPDATE public.shop_claims
        SET status = 'REVOKED',
            review_notes = COALESCE(
                'Automatically revoked due to coffee shop curation status change to ' || NEW.status || '.',
                review_notes
            ),
            updated_at = timezone('utc'::text, now())
        WHERE shop_id = NEW.shop_id
          AND status = 'APPROVED';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_revoke_claims_on_curation_demotion ON shop_curation;
CREATE TRIGGER trg_revoke_claims_on_curation_demotion
    AFTER UPDATE OF status ON shop_curation
    FOR EACH ROW
    WHEN (OLD.status = 'APPROVED' AND NEW.status != 'APPROVED')
    EXECUTE FUNCTION revoke_approved_claims_on_curation_demotion();

-- ============================================================================
-- 6. Claim Approval Serialization & Curation Coordination
-- ============================================================================
-- Ensures that approving a claim strictly coordinates with the shop's curation status
-- at the database boundary. Prevents approving claims for unapproved shops and prevents
-- race conditions between approval and concurrent curation demotions.

CREATE OR REPLACE FUNCTION check_claim_approval_shop_curation()
RETURNS TRIGGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_curation_status public.shop_eligibility_status;
BEGIN
    IF NEW.status = 'APPROVED' AND (OLD IS NULL OR OLD.status != 'APPROVED') THEN
        -- Coordinate with curation at the database boundary:
        -- Lock the shop_curation row FOR SHARE to serialize against concurrent curation transitions.
        SELECT status INTO v_curation_status
        FROM public.shop_curation
        WHERE shop_id = NEW.shop_id
        FOR SHARE;

        IF NOT FOUND OR v_curation_status != 'APPROVED' THEN
            RAISE EXCEPTION 'Cannot approve claim: coffee shop is not currently approved for public discovery.'
                USING ERRCODE = 'P0001';
        END IF;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_check_claim_approval_curation ON shop_claims;
CREATE TRIGGER trg_check_claim_approval_curation
    BEFORE UPDATE OF status ON shop_claims
    FOR EACH ROW
    WHEN (NEW.status = 'APPROVED' AND OLD.status != 'APPROVED')
    EXECUTE FUNCTION check_claim_approval_shop_curation();

-- Dedicated atomic approval RPC establishing a curation-first serialization boundary.
-- Privileged operation executable strictly by service_role via backend curator endpoint.
CREATE OR REPLACE FUNCTION approve_shop_claim(
    p_claim_id UUID,
    p_curator_id UUID,
    p_review_notes TEXT DEFAULT NULL
)
RETURNS shop_claims
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
    v_claim public.shop_claims;
    v_curation_status public.shop_eligibility_status;
BEGIN
    -- 1. Fetch claim and ensure it exists and is currently PENDING
    SELECT * INTO v_claim
    FROM public.shop_claims
    WHERE id = p_claim_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Ownership claim not found.'
            USING ERRCODE = 'P0002';
    END IF;

    IF v_claim.status != 'PENDING' THEN
        RAISE EXCEPTION 'Claim status changed during review. Reload and try again.'
            USING ERRCODE = 'P0005';
    END IF;

    -- 2. Lock the target shop_curation row FOR UPDATE to establish serialization boundary
    -- against concurrent curation demotions.
    SELECT status INTO v_curation_status
    FROM public.shop_curation
    WHERE shop_id = v_claim.shop_id
    FOR UPDATE;

    IF NOT FOUND OR v_curation_status != 'APPROVED' THEN
        RAISE EXCEPTION 'Cannot approve claim: coffee shop is not currently approved for public discovery.'
            USING ERRCODE = 'P0001';
    END IF;

    -- 3. Atomically transition claim from PENDING to APPROVED
    -- If another claim was concurrently approved for this shop, idx_unique_approved_claim_per_shop
    -- will throw 23505 (unique_violation), preserving the partial unique index authority.
    UPDATE public.shop_claims
    SET status = 'APPROVED',
        curator_id = p_curator_id,
        review_notes = p_review_notes,
        reviewed_at = timezone('utc'::text, now()),
        updated_at = timezone('utc'::text, now())
    WHERE id = p_claim_id
      AND status = 'PENDING'
    RETURNING * INTO v_claim;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Claim status changed during review. Reload and try again.'
            USING ERRCODE = 'P0005';
    END IF;

    RETURN v_claim;
END;
$$;

-- Explicitly revoke execution from PUBLIC, anon, and authenticated roles
REVOKE ALL ON FUNCTION approve_shop_claim(UUID, UUID, TEXT) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION approve_shop_claim(UUID, UUID, TEXT) FROM anon;
REVOKE EXECUTE ON FUNCTION approve_shop_claim(UUID, UUID, TEXT) FROM authenticated;
GRANT EXECUTE ON FUNCTION approve_shop_claim(UUID, UUID, TEXT) TO service_role;

-- ============================================================================
-- 7. Owner Dashboard Review Aggregates RPC
-- ============================================================================
-- Computes first-party review count and average rating entirely within PostgreSQL,
-- avoiding pulling large sets of review ratings into application memory.
CREATE OR REPLACE FUNCTION get_shop_review_aggregates(p_shop_id UUID)
RETURNS TABLE (
    reviews_count BIGINT,
    average_rating NUMERIC
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*)::BIGINT AS reviews_count,
        ROUND(AVG(rating)::numeric, 2) AS average_rating
    FROM public.reviews
    WHERE shop_id = p_shop_id
      AND source = 'lokal'
      AND rating IS NOT NULL
      AND rating >= 1.0
      AND rating <= 5.0;
END;
$$;

GRANT EXECUTE ON FUNCTION get_shop_review_aggregates(UUID) TO authenticated, service_role;


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

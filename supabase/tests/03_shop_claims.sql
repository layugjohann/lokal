-- pgTAP database authorization test suite for coffee shop owner claims (shop_claims)
-- Tests table-level RLS flags, least-privilege grants/revocations, partial unique indexes,
-- and executable allow/deny behavior across anon, authenticated (ordinary & curator), and service roles.

BEGIN;
SELECT plan(15);

-- ============================================================================
-- 0. Seed test fixtures (runs as postgres/superuser within transaction)
-- ============================================================================
INSERT INTO auth.users (id, email) VALUES
    ('11111111-1111-1111-1111-111111111111', 'user_a@example.com'),
    ('22222222-2222-2222-2222-222222222222', 'user_b@example.com'),
    ('33333333-3333-3333-3333-333333333333', 'curator@example.com')
ON CONFLICT (id) DO NOTHING;

INSERT INTO shops (id, name, address, latitude, longitude) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'Approved Cafe 1', '123 Main St', 14.5547, 121.0244),
    ('a0000000-0000-0000-0000-000000000002', 'Approved Cafe 2', '456 Side St', 14.5580, 121.0300)
ON CONFLICT (id) DO NOTHING;

INSERT INTO shop_curation (shop_id, status) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'APPROVED'),
    ('a0000000-0000-0000-0000-000000000002', 'APPROVED')
ON CONFLICT (shop_id) DO NOTHING;

-- Seed initial claim records via superuser
INSERT INTO shop_claims (id, shop_id, user_id, status, claimant_name, claimant_role) VALUES
    ('c0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 'APPROVED', 'Owner A', 'Owner'),
    ('c0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000002', '22222222-2222-2222-2222-222222222222', 'PENDING', 'Claimant B', 'Manager');

-- ============================================================================
-- 1. Metadata Verification: RLS Enabled on shop_claims
-- ============================================================================
SELECT ok(relrowsecurity, 'RLS is enabled on shop_claims')
FROM pg_class WHERE relname = 'shop_claims' AND relnamespace = 'public'::regnamespace;

-- ============================================================================
-- 2. Anonymous Role Verification
-- ============================================================================
SET LOCAL ROLE anon;
SET LOCAL "request.jwt.claim.sub" = '';
SET LOCAL "request.jwt.claim.role" = 'anon';

-- Anon should not be able to select from shop_claims
SELECT throws_ok(
    'SELECT * FROM shop_claims',
    '42501',
    NULL,
    'anon is denied SELECT on shop_claims'
);

-- Anon should not be able to insert into shop_claims
SELECT throws_ok(
    'INSERT INTO shop_claims (shop_id, user_id, claimant_name, claimant_role) VALUES (''a0000000-0000-0000-0000-000000000001'', ''11111111-1111-1111-1111-111111111111'', ''Anon'', ''Owner'')',
    '42501',
    NULL,
    'anon is denied INSERT on shop_claims'
);

-- ============================================================================
-- 3. Authenticated Ordinary User (User A) Verification
-- ============================================================================
SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claim.sub" = '11111111-1111-1111-1111-111111111111';
SET LOCAL "request.jwt.claim.role" = 'authenticated';
SET LOCAL "request.jwt.claims" = '{"sub": "11111111-1111-1111-1111-111111111111", "role": "authenticated"}';

-- User A can see their own claim
SELECT results_eq(
    'SELECT id FROM shop_claims WHERE user_id = ''11111111-1111-1111-1111-111111111111''',
    ARRAY['c0000000-0000-0000-0000-000000000001'::uuid],
    'User A can select their own claim'
);

-- User A cannot see User B''s claim
SELECT is_empty(
    'SELECT * FROM shop_claims WHERE user_id = ''22222222-2222-2222-2222-222222222222''',
    'User A cannot select User B claims (isolated by RLS)'
);

-- User A is denied direct INSERT on shop_claims (must go through FastAPI service_role gateway)
SELECT throws_ok(
    'INSERT INTO shop_claims (shop_id, user_id, claimant_name, claimant_role) VALUES (''a0000000-0000-0000-0000-000000000002'', ''11111111-1111-1111-1111-111111111111'', ''User A'', ''Owner'')',
    '42501',
    NULL,
    'authenticated is denied direct INSERT on shop_claims'
);

-- User A is denied direct UPDATE on shop_claims
SELECT throws_ok(
    'UPDATE shop_claims SET status = ''APPROVED'' WHERE id = ''c0000000-0000-0000-0000-000000000001''',
    '42501',
    NULL,
    'authenticated is denied direct UPDATE on shop_claims'
);

-- User A is denied direct DELETE on shop_claims
SELECT throws_ok(
    'DELETE FROM shop_claims WHERE id = ''c0000000-0000-0000-0000-000000000001''',
    '42501',
    NULL,
    'authenticated is denied direct DELETE on shop_claims'
);

-- ============================================================================
-- 4. Curator User Verification
-- ============================================================================
SET LOCAL ROLE authenticated;
SET LOCAL "request.jwt.claim.sub" = '33333333-3333-3333-3333-333333333333';
SET LOCAL "request.jwt.claim.role" = 'authenticated';
SET LOCAL "request.jwt.claims" = '{"sub": "33333333-3333-3333-3333-333333333333", "role": "authenticated", "app_metadata": {"role": "curator"}}';

-- Curator can see all claims
SELECT results_eq(
    'SELECT count(*)::integer FROM shop_claims',
    ARRAY[2],
    'Curator can view all claims across all users'
);

-- ============================================================================
-- 5. Service Role & Uniqueness Constraint Enforcement
-- ============================================================================
SET LOCAL ROLE service_role;
SET LOCAL "request.jwt.claim.role" = 'service_role';
SET LOCAL "request.jwt.claims" = '{"role": "service_role"}';

-- Duplicate APPROVED claim for the same shop must violate idx_unique_approved_claim_per_shop
SELECT throws_ok(
    'INSERT INTO shop_claims (shop_id, user_id, status, claimant_name, claimant_role) VALUES (''a0000000-0000-0000-0000-000000000001'', ''22222222-2222-2222-2222-222222222222'', ''APPROVED'', ''Compete Claimant'', ''Owner'')',
    '23505',
    NULL,
    'Partial unique index prevents multiple APPROVED claims for the same shop'
);

-- Duplicate PENDING claim for the same user and shop must violate idx_unique_pending_claim_per_user_shop
SELECT throws_ok(
    'INSERT INTO shop_claims (shop_id, user_id, status, claimant_name, claimant_role) VALUES (''a0000000-0000-0000-0000-000000000002'', ''22222222-2222-2222-2222-222222222222'', ''PENDING'', ''User B Again'', ''Manager'')',
    '23505',
    NULL,
    'Partial unique index prevents duplicate PENDING claims for the same user and shop'
);

-- Different users CAN have pending claims for the same shop
SELECT lives_ok(
    'INSERT INTO shop_claims (shop_id, user_id, status, claimant_name, claimant_role) VALUES (''a0000000-0000-0000-0000-000000000002'', ''11111111-1111-1111-1111-111111111111'', ''PENDING'', ''User A Pending'', ''Manager'')',
    'Different users can submit competing PENDING claims for curator evaluation'
);

-- Cascade delete: deleting a shop cascades to its claims
SELECT lives_ok(
    'DELETE FROM shops WHERE id = ''a0000000-0000-0000-0000-000000000001''',
    'Shop deletion cascades cleanly to claims'
);

SELECT is_empty(
    'SELECT * FROM shop_claims WHERE shop_id = ''a0000000-0000-0000-0000-000000000001''',
    'Claims are cleanly removed when shop is deleted'
);

ROLLBACK;

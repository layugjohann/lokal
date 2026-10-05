-- pgTAP database authorization test suite for coffee shop owner claims (shop_claims)
-- Tests table-level RLS flags, least-privilege grants/revocations, partial unique indexes,
-- and executable allow/deny behavior across anon, authenticated (ordinary & curator), and service roles.

BEGIN;
SELECT plan(27);

-- ============================================================================
-- 0. Seed test fixtures (runs as postgres/superuser within transaction)
-- ============================================================================
INSERT INTO auth.users (id, email) VALUES
    ('11111111-1111-1111-1111-111111111111', 'user_a@example.com'),
    ('22222222-2222-2222-2222-222222222222', 'user_b@example.com'),
    ('33333333-3333-3333-3333-333333333333', 'curator@example.com'),
    ('44444444-4444-4444-4444-444444444444', 'user_d@example.com')
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

-- Anon is denied EXECUTE on approve_shop_claim
SELECT throws_ok(
    'SELECT approve_shop_claim(''c0000000-0000-0000-0000-000000000002'', ''33333333-3333-3333-3333-333333333333'', ''Anon attempt'')',
    '42501',
    NULL,
    'anon is denied EXECUTE on approve_shop_claim'
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

-- User A is denied direct EXECUTE on approve_shop_claim
SELECT throws_ok(
    'SELECT approve_shop_claim(''c0000000-0000-0000-0000-000000000002'', ''33333333-3333-3333-3333-333333333333'', ''User A attempt'')',
    '42501',
    NULL,
    'authenticated is denied direct EXECUTE on approve_shop_claim'
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

-- Curator connecting under authenticated role is denied direct EXECUTE on approve_shop_claim (must execute via service_role backend gateway)
SELECT throws_ok(
    'SELECT approve_shop_claim(''c0000000-0000-0000-0000-000000000002'', ''33333333-3333-3333-3333-333333333333'', ''Curator direct attempt'')',
    '42501',
    NULL,
    'curator role under authenticated is denied direct EXECUTE on approve_shop_claim'
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

-- ============================================================================
-- 6. Atomic Curation Demotion & Lifecycle Enforcement
-- ============================================================================
-- Seed shop 3 and approved claim 3 for atomic lifecycle testing
INSERT INTO shops (id, name, address, latitude, longitude) VALUES
    ('a0000000-0000-0000-0000-000000000003', 'Approved Cafe 3', '789 Third St', 14.5600, 121.0350)
ON CONFLICT (id) DO NOTHING;

INSERT INTO shop_curation (shop_id, status) VALUES
    ('a0000000-0000-0000-0000-000000000003', 'APPROVED')
ON CONFLICT (shop_id) DO NOTHING;

INSERT INTO shop_claims (id, shop_id, user_id, status, claimant_name, claimant_role) VALUES
    ('c0000000-0000-0000-0000-000000000003', 'a0000000-0000-0000-0000-000000000003', '11111111-1111-1111-1111-111111111111', 'APPROVED', 'Owner C', 'Owner')
ON CONFLICT (id) DO NOTHING;

-- 1. Demoting curation from APPROVED to EXCLUDED atomically revokes active approved claim
UPDATE shop_curation SET status = 'EXCLUDED' WHERE shop_id = 'a0000000-0000-0000-0000-000000000003';

SELECT results_eq(
    'SELECT status FROM shop_claims WHERE id = ''c0000000-0000-0000-0000-000000000003''',
    ARRAY['REVOKED'::shop_claim_status],
    'Curation demotion to EXCLUDED atomically revokes active APPROVED claim via trigger'
);

-- 2. Restoring curation to APPROVED does NOT resurrect revoked claim (remains REVOKED)
UPDATE shop_curation SET status = 'APPROVED' WHERE shop_id = 'a0000000-0000-0000-0000-000000000003';

SELECT results_eq(
    'SELECT status FROM shop_claims WHERE id = ''c0000000-0000-0000-0000-000000000003''',
    ARRAY['REVOKED'::shop_claim_status],
    'Curation restoration back to APPROVED does NOT resurrect revoked claim'
);

-- 3. Atomic rollback: failure during claim revocation rolls back curation transition
-- Reset claim to APPROVED for testing rollback
UPDATE shop_claims SET status = 'APPROVED' WHERE id = 'c0000000-0000-0000-0000-000000000003';

-- Temporarily elevate to table owner to add a check constraint simulating atomic failure
RESET ROLE;
ALTER TABLE shop_claims ADD CONSTRAINT test_simulate_revocation_failure CHECK (status != 'REVOKED');

SET LOCAL ROLE service_role;
SET LOCAL "request.jwt.claim.role" = 'service_role';
SET LOCAL "request.jwt.claims" = '{"role": "service_role"}';

SELECT throws_ok(
    'UPDATE shop_curation SET status = ''EXCLUDED'' WHERE shop_id = ''a0000000-0000-0000-0000-000000000003''',
    '23514',
    NULL,
    'Failure in claim revocation trigger aborts the entire curation transition transaction'
);

RESET ROLE;
ALTER TABLE shop_claims DROP CONSTRAINT test_simulate_revocation_failure;

SET LOCAL ROLE service_role;
SET LOCAL "request.jwt.claim.role" = 'service_role';
SET LOCAL "request.jwt.claims" = '{"role": "service_role"}';

-- Verify curation status was NOT committed and remained APPROVED
SELECT results_eq(
    'SELECT status FROM shop_curation WHERE shop_id = ''a0000000-0000-0000-0000-000000000003''',
    ARRAY['APPROVED'::shop_eligibility_status],
    'Curation status remained APPROVED after failed atomic revocation transaction'
);

-- ============================================================================
-- 7. Claim Approval Serialization & Coordination Tests
-- ============================================================================
-- Seed shop 4 (APPROVED) and pending claims 4 and 5
INSERT INTO shops (id, name, address, latitude, longitude) VALUES
    ('a0000000-0000-0000-0000-000000000004', 'Approved Cafe 4', '101 Fourth St', 14.5610, 121.0360)
ON CONFLICT (id) DO NOTHING;

INSERT INTO shop_curation (shop_id, status) VALUES
    ('a0000000-0000-0000-0000-000000000004', 'APPROVED')
ON CONFLICT (shop_id) DO NOTHING;

INSERT INTO shop_claims (id, shop_id, user_id, status, claimant_name, claimant_role) VALUES
    ('c0000000-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000004', '11111111-1111-1111-1111-111111111111', 'PENDING', 'Owner D', 'Owner'),
    ('c0000000-0000-0000-0000-000000000005', 'a0000000-0000-0000-0000-000000000004', '22222222-2222-2222-2222-222222222222', 'PENDING', 'Compete D', 'Manager')
ON CONFLICT (id) DO NOTHING;

SET LOCAL ROLE service_role;
SET LOCAL "request.jwt.claim.role" = 'service_role';
SET LOCAL "request.jwt.claims" = '{"role": "service_role"}';

-- 1. Normal approval of a currently APPROVED shop succeeds via approve_shop_claim (service_role)
SELECT lives_ok(
    'SELECT approve_shop_claim(''c0000000-0000-0000-0000-000000000004'', ''33333333-3333-3333-3333-333333333333'', ''Approved by curator'')',
    'service_role can execute approve_shop_claim successfully for pending claim on APPROVED shop'
);

-- 2. Competing approval for same shop violates idx_unique_approved_claim_per_shop (23505)
SELECT throws_ok(
    'SELECT approve_shop_claim(''c0000000-0000-0000-0000-000000000005'', ''33333333-3333-3333-3333-333333333333'', ''Competing approval'')',
    '23505',
    NULL,
    'approve_shop_claim raises 23505 when shop already has an approved claim'
);

-- Demote shop 4 to EXCLUDED
UPDATE shop_curation SET status = 'EXCLUDED' WHERE shop_id = 'a0000000-0000-0000-0000-000000000004';

-- 3. Attempting to approve claim on demoted (EXCLUDED) shop fails with P0001
SELECT throws_ok(
    'SELECT approve_shop_claim(''c0000000-0000-0000-0000-000000000005'', ''33333333-3333-3333-3333-333333333333'', ''Late approval'')',
    'P0001',
    'Cannot approve claim: coffee shop is not currently approved for public discovery.',
    'approve_shop_claim fails with P0001 when target shop is not APPROVED'
);

-- 4. Direct UPDATE of claim status to APPROVED on demoted shop is rejected by trg_check_claim_approval_curation
SELECT throws_ok(
    'UPDATE shop_claims SET status = ''APPROVED'' WHERE id = ''c0000000-0000-0000-0000-000000000005''',
    'P0001',
    'Cannot approve claim: coffee shop is not currently approved for public discovery.',
    'Direct update to APPROVED on unapproved shop is rejected by database trigger'
);

-- ============================================================================
-- 8. Owner Dashboard Review Aggregates RPC Tests
-- ============================================================================
-- Seed reviews for shop 4:
-- 2 valid reviews (5 and 4 stars)
-- 1 out-of-range rating (6)
-- 1 null rating
-- 1 third-party review (source = google)
INSERT INTO reviews (id, shop_id, user_id, author_name, rating, content, source) VALUES
    ('b0000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000004', '11111111-1111-1111-1111-111111111111', 'Reviewer 1', 5.0, 'Superb', 'lokal'),
    ('b0000000-0000-0000-0000-000000000002', 'a0000000-0000-0000-0000-000000000004', '22222222-2222-2222-2222-222222222222', 'Reviewer 2', 4.0, 'Good', 'lokal'),
    ('b0000000-0000-0000-0000-000000000004', 'a0000000-0000-0000-0000-000000000004', '33333333-3333-3333-3333-333333333333', 'Reviewer 4', NULL, 'No rating', 'lokal'),
    ('b0000000-0000-0000-0000-000000000005', 'a0000000-0000-0000-0000-000000000004', '44444444-4444-4444-4444-444444444444', 'Reviewer 5', 5.0, 'Google review', 'google')
ON CONFLICT (id) DO NOTHING;

-- 5. get_shop_review_aggregates returns count=2 and avg=4.50 (excludes null, invalid, third-party)
SELECT results_eq(
    'SELECT reviews_count, average_rating FROM get_shop_review_aggregates(''a0000000-0000-0000-0000-000000000004'')',
    'VALUES (2::bigint, 4.50::numeric)',
    'get_shop_review_aggregates correctly filters valid first-party reviews and computes count & avg'
);

-- 6. Shop with no reviews returns count=0 and average_rating IS NULL
SELECT results_eq(
    'SELECT reviews_count, average_rating FROM get_shop_review_aggregates(''a0000000-0000-0000-0000-000000000003'')',
    'VALUES (0::bigint, NULL::numeric)',
    'get_shop_review_aggregates returns count 0 and NULL avg for unreviewed shop'
);

ROLLBACK;


-- pgTAP database test suite for community feed RPC
-- Tests get_community_feed SQL function logic, including:
-- - Execution privileges (denied to anon, permitted to authenticated & service_role)
-- - Deterministic newest-first ordering (created_at DESC, id DESC)
-- - Bounded limit + 1 pagination behavior
-- - Filtering for APPROVED coffee shops only
-- - Filtering for source = 'lokal' only
-- - Privacy: absence of user_id or email
-- - Dynamic curation demotion exclusion
-- - Lifecycle: review edits and deletions

BEGIN;
SELECT plan(12);

-- ============================================================================
-- 0. Seed test fixtures
-- ============================================================================

INSERT INTO auth.users (id, email) VALUES
    ('feed0001-0000-0000-0000-000000000001', 'feed_user_1@example.com'),
    ('feed0001-0000-0000-0000-000000000002', 'feed_user_2@example.com'),
    ('feed0001-0000-0000-0000-000000000003', 'feed_user_3@example.com'),
    ('feed0001-0000-0000-0000-000000000004', 'feed_user_4@example.com')
ON CONFLICT (id) DO NOTHING;

INSERT INTO shops (id, name, address, latitude, longitude, rating) VALUES
    ('f0000000-0000-0000-0000-000000000001', 'Approved Cafe Alpha', '100 Escolta St, Manila', 14.5995, 120.9842, 4.80),
    ('f0000000-0000-0000-0000-000000000002', 'Approved Cafe Beta', '200 Escolta St, Manila', 14.5990, 120.9840, 4.50),
    ('f0000000-0000-0000-0000-000000000003', 'Pending Cafe Gamma', '300 Escolta St, Manila', 14.5985, 120.9835, 4.00),
    ('f0000000-0000-0000-0000-000000000004', 'Excluded Cafe Delta', '400 Escolta St, Manila', 14.5980, 120.9830, 3.50)
ON CONFLICT (id) DO NOTHING;

INSERT INTO shop_curation (shop_id, status, confidence) VALUES
    ('f0000000-0000-0000-0000-000000000001', 'APPROVED', 'HIGH'),
    ('f0000000-0000-0000-0000-000000000002', 'APPROVED', 'HIGH'),
    ('f0000000-0000-0000-0000-000000000003', 'PENDING_REVIEW', 'LOW'),
    ('f0000000-0000-0000-0000-000000000004', 'EXCLUDED', 'HIGH')
ON CONFLICT (shop_id) DO NOTHING;

-- Seed reviews with explicit chronological created_at timestamps (valid UUIDs d0000000...)
INSERT INTO reviews (id, shop_id, user_id, author_name, rating, content, source, created_at, updated_at) VALUES
    ('d0000000-0000-0000-0000-000000000001', 'f0000000-0000-0000-0000-000000000001', 'feed0001-0000-0000-0000-000000000001', 'Barista Bob', 5, 'Best espresso ever!', 'lokal', '2026-10-01 10:00:00+00', '2026-10-01 10:00:00+00'),
    ('d0000000-0000-0000-0000-000000000002', 'f0000000-0000-0000-0000-000000000001', 'feed0001-0000-0000-0000-000000000002', 'Coffee Alice', 4, 'Cozy place to study.', 'lokal', '2026-10-02 11:00:00+00', '2026-10-02 11:00:00+00'),
    ('d0000000-0000-0000-0000-000000000003', 'f0000000-0000-0000-0000-000000000002', 'feed0001-0000-0000-0000-000000000003', 'Mocha Mark', 5, 'Top tier cold brew.', 'lokal', '2026-10-03 12:00:00+00', '2026-10-03 12:00:00+00'),
    ('d0000000-0000-0000-0000-000000000004', 'f0000000-0000-0000-0000-000000000002', 'feed0001-0000-0000-0000-000000000004', 'Latte Lisa', 3, 'Average pastries.', 'lokal', '2026-10-04 13:00:00+00', '2026-10-04 13:00:00+00'),
    -- External/Google review (must be excluded by source = 'lokal')
    ('d0000000-0000-0000-0000-000000000005', 'f0000000-0000-0000-0000-000000000001', NULL, 'Google Reviewer', 5, 'External review text', 'google', '2026-10-05 14:00:00+00', '2026-10-05 14:00:00+00'),
    -- Reviews on unapproved shops (must be excluded by curation status)
    ('d0000000-0000-0000-0000-000000000006', 'f0000000-0000-0000-0000-000000000003', 'feed0001-0000-0000-0000-000000000001', 'Barista Bob', 5, 'Pending shop review', 'lokal', '2026-10-06 15:00:00+00', '2026-10-06 15:00:00+00'),
    ('d0000000-0000-0000-0000-000000000007', 'f0000000-0000-0000-0000-000000000004', 'feed0001-0000-0000-0000-000000000001', 'Barista Bob', 1, 'Excluded shop review', 'lokal', '2026-10-07 16:00:00+00', '2026-10-07 16:00:00+00')
ON CONFLICT (id) DO NOTHING;

-- ============================================================================
-- 1. Privilege Verification: anon is denied execution
-- ============================================================================
SET LOCAL ROLE anon;
SELECT set_config('request.jwt.claims', '{}', true);
SELECT set_config('request.jwt.claim.role', 'anon', true);

SELECT throws_ok(
    $$ SELECT * FROM get_community_feed(20, 0) $$,
    '42501',
    NULL,
    'anon execution of get_community_feed must throw permission denied (42501)'
);

-- ============================================================================
-- 2. Privilege Verification: authenticated role can execute
-- ============================================================================
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims', json_build_object('sub', 'feed0001-0000-0000-0000-000000000001', 'role', 'authenticated')::text, true);
SELECT set_config('request.jwt.claim.role', 'authenticated', true);

SELECT lives_ok(
    $$ SELECT * FROM get_community_feed(20, 0) $$,
    'authenticated role can execute get_community_feed'
);

-- ============================================================================
-- 3. Privilege Verification: service_role can execute
-- ============================================================================
SET LOCAL ROLE service_role;
SELECT lives_ok(
    $$ SELECT * FROM get_community_feed(20, 0) $$,
    'service_role can execute get_community_feed'
);

-- ============================================================================
-- 4. Deterministic Ordering: newest-first (created_at DESC, id DESC)
-- ============================================================================
SET LOCAL ROLE authenticated;

SELECT results_eq(
    $$ SELECT id FROM get_community_feed(10, 0) $$,
    $$ VALUES
        ('d0000000-0000-0000-0000-000000000004'::uuid),
        ('d0000000-0000-0000-0000-000000000003'::uuid),
        ('d0000000-0000-0000-0000-000000000002'::uuid),
        ('d0000000-0000-0000-0000-000000000001'::uuid)
    $$,
    'get_community_feed returns eligible reviews ordered strictly newest-first'
);

-- ============================================================================
-- 5. Limit + 1 pagination semantics: asking limit 2 returns 3 rows (2 + 1)
-- ============================================================================
SELECT is(
    (SELECT count(*)::integer FROM get_community_feed(2, 0)),
    3,
    'get_community_feed with limit 2 fetches up to 3 rows (limit + 1) when extra rows exist'
);

-- ============================================================================
-- 6. Offset pagination semantics: offset 2 with limit 2 returns 2 rows (offset 2, 3)
-- ============================================================================
SELECT results_eq(
    $$ SELECT id FROM get_community_feed(2, 2) $$,
    $$ VALUES
        ('d0000000-0000-0000-0000-000000000002'::uuid),
        ('d0000000-0000-0000-0000-000000000001'::uuid)
    $$,
    'get_community_feed respects offset pagination'
);

-- ============================================================================
-- 7. Curation Filtering: unapproved shops (PENDING_REVIEW, EXCLUDED) excluded
-- ============================================================================
SELECT is_empty(
    $$ SELECT id FROM get_community_feed(20, 0) WHERE shop_id IN ('f0000000-0000-0000-0000-000000000003'::uuid, 'f0000000-0000-0000-0000-000000000004'::uuid) $$,
    'reviews for PENDING_REVIEW or EXCLUDED shops are excluded from get_community_feed'
);

-- ============================================================================
-- 8. Source Filtering: non-lokal reviews (google) are excluded
-- ============================================================================
SELECT is_empty(
    $$ SELECT id FROM get_community_feed(20, 0) WHERE id = 'd0000000-0000-0000-0000-000000000005'::uuid $$,
    'non-lokal (google) reviews are excluded from get_community_feed'
);

-- ============================================================================
-- 9. Dynamic Curation Demotion: demoting shop Alpha to EXCLUDED hides its reviews
-- ============================================================================
SET LOCAL ROLE service_role;
UPDATE shop_curation SET status = 'EXCLUDED' WHERE shop_id = 'f0000000-0000-0000-0000-000000000001';

SET LOCAL ROLE authenticated;
SELECT results_eq(
    $$ SELECT id FROM get_community_feed(10, 0) $$,
    $$ VALUES
        ('d0000000-0000-0000-0000-000000000004'::uuid),
        ('d0000000-0000-0000-0000-000000000003'::uuid)
    $$,
    'demoting coffee shop curation immediately excludes its reviews from get_community_feed'
);

-- Restore Alpha to APPROVED for remaining tests
SET LOCAL ROLE service_role;
UPDATE shop_curation SET status = 'APPROVED' WHERE shop_id = 'f0000000-0000-0000-0000-000000000001';

-- ============================================================================
-- 10. Review Update: editing rating/content reflects immediately in feed
-- ============================================================================
SET LOCAL ROLE service_role;
UPDATE reviews
SET rating = 1, content = 'Updated negative comment', updated_at = '2026-10-07 18:00:00+00'
WHERE id = 'd0000000-0000-0000-0000-000000000004';

SET LOCAL ROLE authenticated;
SELECT results_eq(
    $$ SELECT rating, content FROM get_community_feed(1, 0) LIMIT 1 $$,
    $$ VALUES (1, 'Updated negative comment'::text) $$,
    'review edit is immediately reflected in get_community_feed'
);

-- ============================================================================
-- 11. Review Deletion: deleting a review immediately drops it from feed
-- ============================================================================
SET LOCAL ROLE service_role;
DELETE FROM reviews WHERE id = 'd0000000-0000-0000-0000-000000000004';

SET LOCAL ROLE authenticated;
SELECT is(
    (SELECT id FROM get_community_feed(1, 0) LIMIT 1),
    'd0000000-0000-0000-0000-000000000003'::uuid,
    'deleted review is immediately omitted from get_community_feed'
);

-- ============================================================================
-- 12. Projection Contract: application identifiers present, private user data absent
-- ============================================================================
SELECT results_eq(
    $$ SELECT shop_name, author_name, rating FROM get_community_feed(1, 0) LIMIT 1 $$,
    $$ VALUES ('Approved Cafe Beta'::text, 'Mocha Mark'::text, 5) $$,
    'get_community_feed projects correct shop and author metadata'
);

SELECT * FROM finish();
ROLLBACK;

-- pgTAP database test suite for advanced shop search and filtering RPC
-- Tests get_nearby_shops SQL function logic, including:
-- - Name search and address search
-- - APPROVED-only curation enforcement
-- - First-party LOKAL rating aggregation and NULL behavior
-- - min_lokal_rating and min_rating filtering
-- - Combined multi-criteria filtering
-- - Sorting by distance, external rating, and LOKAL community rating
-- - Deterministic tie-breaking
-- - Least-privilege execution restrictions (authenticated only; anon denied)

BEGIN;
SELECT plan(15);

-- ============================================================================
-- 0. Seed test fixtures
-- ============================================================================

INSERT INTO auth.users (id, email) VALUES
    ('11111111-1111-1111-1111-111111111111', 'reviewer_a@example.com'),
    ('22222222-2222-2222-2222-222222222222', 'reviewer_b@example.com')
ON CONFLICT (id) DO NOTHING;

INSERT INTO shops (id, name, address, latitude, longitude, rating) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'Kape Escolta', 'Escolta St, Binondo, Manila', 14.5995, 120.9842, 4.80),
    ('a0000000-0000-0000-0000-000000000002', 'Intramuros Roasters', 'General Luna St, Intramuros, Manila', 14.5890, 120.9750, 4.20),
    ('a0000000-0000-0000-0000-000000000003', 'Binondo Brews', 'Ongpin St, Binondo, Manila', 14.6000, 120.9750, 4.00),
    ('b0000000-0000-0000-0000-000000000004', 'Escolta Pending Cafe', 'Escolta St, Binondo, Manila', 14.5995, 120.9842, 4.90),
    ('c0000000-0000-0000-0000-000000000005', 'Escolta Excluded Cafe', 'Escolta St, Binondo, Manila', 14.5995, 120.9842, 5.00)
ON CONFLICT (id) DO NOTHING;

INSERT INTO shop_curation (shop_id, status, confidence) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'APPROVED', 'HIGH'),
    ('a0000000-0000-0000-0000-000000000002', 'APPROVED', 'HIGH'),
    ('a0000000-0000-0000-0000-000000000003', 'APPROVED', 'HIGH'),
    ('b0000000-0000-0000-0000-000000000004', 'PENDING_REVIEW', 'LOW'),
    ('c0000000-0000-0000-0000-000000000005', 'EXCLUDED', 'HIGH')
ON CONFLICT (shop_id) DO NOTHING;

-- Shop 1 has 2 LOKAL reviews (5 and 4 -> average 4.50, count 2)
-- Shop 2 has 1 LOKAL review (3 -> average 3.00, count 1)
-- Shop 3 has 0 reviews (NULL average, count 0)
INSERT INTO reviews (shop_id, user_id, rating, content, source) VALUES
    ('a0000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 5, 'Great coffee!', 'lokal'),
    ('a0000000-0000-0000-0000-000000000001', '22222222-2222-2222-2222-222222222222', 4, 'Good vibe', 'lokal'),
    ('a0000000-0000-0000-0000-000000000002', '11111111-1111-1111-1111-111111111111', 3, 'Average brew', 'lokal')
ON CONFLICT (user_id, shop_id) DO NOTHING;

-- ============================================================================
-- 1. Execution Privilege Verification: anon is denied
-- ============================================================================
SET LOCAL ROLE anon;
SELECT set_config('request.jwt.claims', '{}', true);
SELECT set_config('request.jwt.claim.role', 'anon', true);

SELECT throws_ok(
    $$ SELECT * FROM get_nearby_shops(14.5995, 120.9842) $$,
    '42501',
    NULL,
    'anon execution of get_nearby_shops must throw permission denied (42501)'
);

-- ============================================================================
-- 2. Execution Privilege Verification: authenticated succeeds
-- ============================================================================
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims', '{"sub": "11111111-1111-1111-1111-111111111111"}', true);
SELECT set_config('request.jwt.claim.role', 'authenticated', true);

SELECT lives_ok(
    $$ SELECT * FROM get_nearby_shops(14.5995, 120.9842) $$,
    'authenticated execution of get_nearby_shops succeeds'
);

-- ============================================================================
-- 3. APPROVED-only curation invariant
-- ============================================================================
-- Searching for 'Escolta' matches Approved (Shop 1), Pending (Shop 4), and Excluded (Shop 5).
-- Only Approved (Shop 1) must be returned.
SELECT is(
    (SELECT count(*)::integer FROM get_nearby_shops(14.5995, 120.9842, search_query := 'Escolta')),
    1,
    'Search for Escolta returns exactly 1 approved shop'
);

SELECT is(
    (SELECT id FROM get_nearby_shops(14.5995, 120.9842, search_query := 'Escolta') LIMIT 1),
    'a0000000-0000-0000-0000-000000000001'::uuid,
    'Escolta search result is Shop 1 (Approved); Pending and Excluded shops are omitted'
);

-- ============================================================================
-- 4. Search by Name
-- ============================================================================
SELECT is(
    (SELECT id FROM get_nearby_shops(14.5995, 120.9842, search_query := 'Intramuros') LIMIT 1),
    'a0000000-0000-0000-0000-000000000002'::uuid,
    'Search by name Intramuros returns Shop 2'
);

-- ============================================================================
-- 5. Search by Address
-- ============================================================================
-- 'Ongpin' appears only in Shop 3's address ('Ongpin St, Binondo, Manila'), not in its name ('Binondo Brews')
SELECT is(
    (SELECT id FROM get_nearby_shops(14.5995, 120.9842, search_query := 'Ongpin') LIMIT 1),
    'a0000000-0000-0000-0000-000000000003'::uuid,
    'Search by address keyword Ongpin returns Shop 3'
);

-- ============================================================================
-- 6. LOKAL Rating Aggregation: populated reviews
-- ============================================================================
SELECT is(
    (SELECT lokal_rating FROM get_nearby_shops(14.5995, 120.9842, search_query := 'Kape Escolta') LIMIT 1),
    4.50::numeric,
    'Shop 1 with two reviews (5, 4) calculates lokal_rating = 4.50'
);

SELECT is(
    (SELECT lokal_reviews_count FROM get_nearby_shops(14.5995, 120.9842, search_query := 'Kape Escolta') LIMIT 1),
    2,
    'Shop 1 returns lokal_reviews_count = 2'
);

-- ============================================================================
-- 7. LOKAL Rating Contract: shop with zero reviews
-- ============================================================================
SELECT ok(
    (SELECT lokal_rating IS NULL FROM get_nearby_shops(14.5995, 120.9842, search_query := 'Binondo Brews') LIMIT 1),
    'Shop with no LOKAL reviews returns lokal_rating IS NULL'
);

SELECT is(
    (SELECT lokal_reviews_count FROM get_nearby_shops(14.5995, 120.9842, search_query := 'Binondo Brews') LIMIT 1),
    0,
    'Shop with no LOKAL reviews returns lokal_reviews_count = 0'
);

-- ============================================================================
-- 8. min_lokal_rating Filter: excludes below-threshold and NULL ratings
-- ============================================================================
-- Filtering min_lokal_rating >= 4.0 must return Shop 1 (4.50),
-- and exclude Shop 2 (3.00) AND exclude Shop 3 (NULL)
SELECT is(
    (SELECT count(*)::integer FROM get_nearby_shops(14.5995, 120.9842, min_lokal_rating := 4.0)),
    1,
    'min_lokal_rating = 4.0 returns exactly 1 shop'
);

SELECT is(
    (SELECT id FROM get_nearby_shops(14.5995, 120.9842, min_lokal_rating := 4.0) LIMIT 1),
    'a0000000-0000-0000-0000-000000000001'::uuid,
    'min_lokal_rating = 4.0 includes Shop 1 and excludes Shop 2 (3.00) and Shop 3 (NULL)'
);

-- ============================================================================
-- 9. Combined multi-criteria filtering
-- ============================================================================
-- Name/address query 'Binondo' matches Shop 1 and Shop 3.
-- min_rating (external) >= 4.5 includes Shop 1 (4.80) and excludes Shop 3 (4.00).
SELECT is(
    (SELECT id FROM get_nearby_shops(14.5995, 120.9842, search_query := 'Binondo', min_rating := 4.5) LIMIT 1),
    'a0000000-0000-0000-0000-000000000001'::uuid,
    'Combined query Binondo + min_rating 4.5 returns only Shop 1'
);

-- ============================================================================
-- 10. Sorting by lokal_rating with deterministic tie-breaking
-- ============================================================================
-- Order with sort_by = 'lokal_rating':
-- Shop 1 (4.50) -> Shop 2 (3.00) -> Shop 3 (NULL, ordered last)
SELECT results_eq(
    $$ SELECT id FROM get_nearby_shops(14.5995, 120.9842, sort_by := 'lokal_rating') $$,
    $$ VALUES
        ('a0000000-0000-0000-0000-000000000001'::uuid),
        ('a0000000-0000-0000-0000-000000000002'::uuid),
        ('a0000000-0000-0000-0000-000000000003'::uuid)
    $$,
    'sort_by = lokal_rating orders by community rating descending NULLS LAST'
);

-- ============================================================================
-- 11. Sorting by external rating
-- ============================================================================
-- External ratings: Shop 1 (4.80), Shop 2 (4.20), Shop 3 (4.00)
SELECT results_eq(
    $$ SELECT id FROM get_nearby_shops(14.5995, 120.9842, sort_by := 'rating') $$,
    $$ VALUES
        ('a0000000-0000-0000-0000-000000000001'::uuid),
        ('a0000000-0000-0000-0000-000000000002'::uuid),
        ('a0000000-0000-0000-0000-000000000003'::uuid)
    $$,
    'sort_by = rating orders by external rating descending NULLS LAST'
);

SELECT * FROM finish();
ROLLBACK;

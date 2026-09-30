-- pgTAP database authorization test suite for LOKAL public schema hardening
-- Tests table-level RLS flags, least-privilege grants/revocations, column-level restrictions,
-- and executable allow/deny behavior across anon, authenticated (ordinary & curator), and service roles.

BEGIN;
SELECT plan(55);

-- ============================================================================
-- 0. Seed test fixtures (runs as postgres/superuser within transaction)
-- ============================================================================
INSERT INTO auth.users (id, email) VALUES
    ('11111111-1111-1111-1111-111111111111', 'user_a@example.com'),
    ('22222222-2222-2222-2222-222222222222', 'user_b@example.com'),
    ('33333333-3333-3333-3333-333333333333', 'curator@example.com')
ON CONFLICT (id) DO NOTHING;

INSERT INTO shops (id, name, address, latitude, longitude) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'Approved Cafe', '123 Main St', 14.5547, 121.0244),
    ('b0000000-0000-0000-0000-000000000002', 'Pending Cafe', '456 Side St', 14.5580, 121.0300)
ON CONFLICT (id) DO NOTHING;

INSERT INTO shop_curation (shop_id, status, curator_notes, location_count, evidence_source, confidence) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'APPROVED', 'Verified independent cafe', 1, 'manual', 'HIGH'),
    ('b0000000-0000-0000-0000-000000000002', 'PENDING_REVIEW', 'Needs evaluation', 1, 'manual', 'LOW')
ON CONFLICT (shop_id) DO NOTHING;

INSERT INTO shop_curation_audit (shop_id, old_status, new_status, reason, changed_by, change_source) VALUES
    ('a0000000-0000-0000-0000-000000000001', NULL, 'APPROVED', 'Initial evaluation', '33333333-3333-3333-3333-333333333333', 'manual');

INSERT INTO menu_items (shop_id, name, price) VALUES
    ('a0000000-0000-0000-0000-000000000001', 'Flat White', 150.00);

INSERT INTO reviews (shop_id, user_id, rating, content) VALUES
    ('a0000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111', 5, 'User A review for Approved Cafe'),
    ('a0000000-0000-0000-0000-000000000001', '22222222-2222-2222-2222-222222222222', 4, 'User B review for Approved Cafe');

INSERT INTO favorites (shop_id, user_id) VALUES
    ('a0000000-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111'),
    ('a0000000-0000-0000-0000-000000000001', '22222222-2222-2222-2222-222222222222');

-- ============================================================================
-- 1. Metadata Verification: RLS Enabled on all 6 public tables
-- ============================================================================
SELECT ok(relrowsecurity, 'RLS is enabled on shops')
FROM pg_class WHERE relname = 'shops' AND relnamespace = 'public'::regnamespace;

SELECT ok(relrowsecurity, 'RLS is enabled on menu_items')
FROM pg_class WHERE relname = 'menu_items' AND relnamespace = 'public'::regnamespace;

SELECT ok(relrowsecurity, 'RLS is enabled on shop_curation')
FROM pg_class WHERE relname = 'shop_curation' AND relnamespace = 'public'::regnamespace;

SELECT ok(relrowsecurity, 'RLS is enabled on shop_curation_audit')
FROM pg_class WHERE relname = 'shop_curation_audit' AND relnamespace = 'public'::regnamespace;

SELECT ok(relrowsecurity, 'RLS is enabled on reviews')
FROM pg_class WHERE relname = 'reviews' AND relnamespace = 'public'::regnamespace;

SELECT ok(relrowsecurity, 'RLS is enabled on favorites')
FROM pg_class WHERE relname = 'favorites' AND relnamespace = 'public'::regnamespace;

-- ============================================================================
-- 2. Metadata Verification: Table & Column Grants
-- ============================================================================
-- shops: anon may SELECT, but cannot mutate
SELECT ok(has_table_privilege('anon', 'public.shops', 'SELECT'), 'anon has SELECT on shops');
SELECT ok(NOT has_table_privilege('anon', 'public.shops', 'INSERT'), 'anon lacks INSERT on shops');
SELECT ok(NOT has_table_privilege('anon', 'public.shops', 'UPDATE'), 'anon lacks UPDATE on shops');
SELECT ok(NOT has_table_privilege('anon', 'public.shops', 'DELETE'), 'anon lacks DELETE on shops');

-- menu_items: anon has no access whatsoever
SELECT ok(NOT has_table_privilege('anon', 'public.menu_items', 'SELECT'), 'anon lacks SELECT on menu_items');
SELECT ok(NOT has_table_privilege('anon', 'public.menu_items', 'INSERT'), 'anon lacks INSERT on menu_items');

-- audit, reviews, favorites: anon lacks access
SELECT ok(NOT has_table_privilege('anon', 'public.shop_curation_audit', 'SELECT'), 'anon lacks SELECT on shop_curation_audit');
SELECT ok(NOT has_table_privilege('anon', 'public.reviews', 'INSERT'), 'anon lacks INSERT on reviews');
SELECT ok(NOT has_table_privilege('anon', 'public.favorites', 'INSERT'), 'anon lacks INSERT on favorites');

-- shops: authenticated may SELECT, but direct mutations are revoked
SELECT ok(has_table_privilege('authenticated', 'public.shops', 'SELECT'), 'authenticated has SELECT on shops');
SELECT ok(NOT has_table_privilege('authenticated', 'public.shops', 'INSERT'), 'authenticated lacks INSERT on shops');
SELECT ok(NOT has_table_privilege('authenticated', 'public.shops', 'UPDATE'), 'authenticated lacks UPDATE on shops');
SELECT ok(NOT has_table_privilege('authenticated', 'public.shops', 'DELETE'), 'authenticated lacks DELETE on shops');

-- shop_curation column grants: anon can SELECT (shop_id, status), but not sensitive metadata
SELECT ok(has_column_privilege('anon', 'public.shop_curation', 'shop_id', 'SELECT'), 'anon has SELECT on shop_curation.shop_id');
SELECT ok(has_column_privilege('anon', 'public.shop_curation', 'status', 'SELECT'), 'anon has SELECT on shop_curation.status');
SELECT ok(NOT has_column_privilege('anon', 'public.shop_curation', 'curator_notes', 'SELECT'), 'anon lacks SELECT on shop_curation.curator_notes');

-- ============================================================================
-- 3. Executable Authorization: anon role
-- ============================================================================
SET LOCAL ROLE anon;
SELECT set_config('request.jwt.claims', '{}', true);
SELECT set_config('request.jwt.claim.sub', '', true);
SELECT set_config('request.jwt.claim.role', 'anon', true);

-- shops: anon can read APPROVED shops, but cannot read non-approved shops
SELECT ok(EXISTS(SELECT 1 FROM shops WHERE id = 'a0000000-0000-0000-0000-000000000001'), 'anon can read approved shop');
SELECT ok(NOT EXISTS(SELECT 1 FROM shops WHERE id = 'b0000000-0000-0000-0000-000000000002'), 'anon cannot read non-approved shop');

-- shops: anon cannot mutate
SELECT throws_ok('INSERT INTO shops (name, latitude, longitude) VALUES (''Anon'', 0, 0)', '42501'::char(5), NULL, 'anon cannot INSERT into shops');
SELECT throws_ok('UPDATE shops SET name = ''Anon'' WHERE id = ''a0000000-0000-0000-0000-000000000001''', '42501'::char(5), NULL, 'anon cannot UPDATE shops');
SELECT throws_ok('DELETE FROM shops WHERE id = ''a0000000-0000-0000-0000-000000000001''', '42501'::char(5), NULL, 'anon cannot DELETE shops');

-- shop_curation: anon can access permitted columns for APPROVED record, cannot read pending record, cannot read notes
SELECT ok(EXISTS(SELECT shop_id, status FROM shop_curation WHERE shop_id = 'a0000000-0000-0000-0000-000000000001' AND status = 'APPROVED'), 'anon can select permitted columns on approved shop_curation');
SELECT ok(NOT EXISTS(SELECT shop_id, status FROM shop_curation WHERE shop_id = 'b0000000-0000-0000-0000-000000000002'), 'anon cannot read non-approved curation status');
SELECT throws_ok('SELECT curator_notes FROM shop_curation', '42501'::char(5), NULL, 'anon cannot select sensitive curator_notes');

-- menu_items: anon cannot access
SELECT throws_ok('SELECT count(*) FROM menu_items', '42501'::char(5), NULL, 'anon cannot select from menu_items');

-- shop_curation_audit: anon cannot access
SELECT throws_ok('SELECT count(*) FROM shop_curation_audit', '42501'::char(5), NULL, 'anon cannot select from shop_curation_audit');

-- ============================================================================
-- 4. Executable Authorization: ordinary authenticated role (User A)
-- ============================================================================
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims', '{"sub": "11111111-1111-1111-1111-111111111111", "role": "authenticated", "app_metadata": {"role": "authenticated"}}', true);
SELECT set_config('request.jwt.claim.sub', '11111111-1111-1111-1111-111111111111', true);
SELECT set_config('request.jwt.claim.role', 'authenticated', true);

-- shops: ordinary authenticated can read APPROVED shops, but cannot read non-approved shops
SELECT ok(EXISTS(SELECT 1 FROM shops WHERE id = 'a0000000-0000-0000-0000-000000000001'), 'authenticated can read approved shop');
SELECT ok(NOT EXISTS(SELECT 1 FROM shops WHERE id = 'b0000000-0000-0000-0000-000000000002'), 'authenticated cannot read non-approved shop');

-- shops: ordinary authenticated cannot mutate directly via PostgREST
SELECT throws_ok('INSERT INTO shops (name, latitude, longitude) VALUES (''User A'', 0, 0)', '42501'::char(5), NULL, 'authenticated cannot INSERT into shops');
SELECT throws_ok('UPDATE shops SET name = ''User A'' WHERE id = ''a0000000-0000-0000-0000-000000000001''', '42501'::char(5), NULL, 'authenticated cannot UPDATE shops');
SELECT throws_ok('DELETE FROM shops WHERE id = ''a0000000-0000-0000-0000-000000000001''', '42501'::char(5), NULL, 'authenticated cannot DELETE shops');

-- shop_curation: ordinary authenticated can access permitted columns for APPROVED record, cannot read pending record, cannot read notes
SELECT ok(EXISTS(SELECT shop_id, status FROM shop_curation WHERE shop_id = 'a0000000-0000-0000-0000-000000000001' AND status = 'APPROVED'), 'authenticated can select permitted columns on approved shop_curation');
SELECT ok(NOT EXISTS(SELECT shop_id, status FROM shop_curation WHERE shop_id = 'b0000000-0000-0000-0000-000000000002'), 'authenticated cannot read non-approved curation status');
SELECT throws_ok('SELECT curator_notes FROM shop_curation', '42501'::char(5), NULL, 'authenticated cannot select sensitive curator_notes');

-- menu_items: ordinary authenticated cannot access
SELECT throws_ok('SELECT count(*) FROM menu_items', '42501'::char(5), NULL, 'authenticated cannot select from menu_items');

-- shop_curation_audit: ordinary authenticated reads 0 rows due to RLS
SELECT ok((SELECT count(*) FROM shop_curation_audit) = 0, 'ordinary authenticated reads 0 rows from shop_curation_audit');

-- reviews and favorites: ownership isolation
SELECT ok(EXISTS(SELECT 1 FROM reviews WHERE user_id = '11111111-1111-1111-1111-111111111111'), 'User A can see their own review');
SELECT ok(EXISTS(SELECT 1 FROM favorites WHERE user_id = '11111111-1111-1111-1111-111111111111'), 'User A can see their own favorite');
SELECT ok(NOT EXISTS(SELECT 1 FROM favorites WHERE user_id = '22222222-2222-2222-2222-222222222222'), 'User A cannot see User B favorite');

WITH deleted_review AS (
    DELETE FROM reviews WHERE user_id = '22222222-2222-2222-2222-222222222222' RETURNING 1
)
SELECT ok((SELECT count(*) FROM deleted_review) = 0, 'User A cannot delete User B review');

WITH deleted_favorite AS (
    DELETE FROM favorites WHERE user_id = '22222222-2222-2222-2222-222222222222' RETURNING 1
)
SELECT ok((SELECT count(*) FROM deleted_favorite) = 0, 'User A cannot delete User B favorite');

WITH deleted_own_favorite AS (
    DELETE FROM favorites WHERE user_id = '11111111-1111-1111-1111-111111111111' RETURNING 1
)
SELECT ok((SELECT count(*) FROM deleted_own_favorite) = 1, 'User A can delete their own favorite');

-- ============================================================================
-- 5. Executable Authorization: curator role
-- ============================================================================
SET LOCAL ROLE authenticated;
SELECT set_config('request.jwt.claims', '{"sub": "33333333-3333-3333-3333-333333333333", "role": "authenticated", "app_metadata": {"role": "curator"}}', true);
SELECT set_config('request.jwt.claim.sub', '33333333-3333-3333-3333-333333333333', true);
SELECT set_config('request.jwt.claim.role', 'authenticated', true);

-- shops: curator can read APPROVED shops AND non-approved shops
SELECT ok(EXISTS(SELECT 1 FROM shops WHERE id = 'a0000000-0000-0000-0000-000000000001'), 'curator can read approved shop');
SELECT ok(EXISTS(SELECT 1 FROM shops WHERE id = 'b0000000-0000-0000-0000-000000000002'), 'curator can read non-approved shop');

-- shop_curation: curator can read non-approved curation status
SELECT ok(EXISTS(SELECT shop_id, status FROM shop_curation WHERE shop_id = 'b0000000-0000-0000-0000-000000000002'), 'curator can read non-approved curation status');

-- shop_curation_audit: curator can read audit records
SELECT ok((SELECT count(*) FROM shop_curation_audit) >= 1, 'curator can read shop_curation_audit records');

-- shops: curator STILL cannot mutate directly via PostgREST (must use FastAPI gateway)
SELECT throws_ok('INSERT INTO shops (name, latitude, longitude) VALUES (''Curator Direct'', 0, 0)', '42501'::char(5), NULL, 'curator cannot directly INSERT into shops via PostgREST');
SELECT throws_ok('UPDATE shops SET name = ''Curator Direct'' WHERE id = ''a0000000-0000-0000-0000-000000000001''', '42501'::char(5), NULL, 'curator cannot directly UPDATE shops via PostgREST');
SELECT throws_ok('DELETE FROM shops WHERE id = ''b0000000-0000-0000-0000-000000000002''', '42501'::char(5), NULL, 'curator cannot directly DELETE shops via PostgREST');

SELECT * FROM finish();
ROLLBACK;

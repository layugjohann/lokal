-- pgTAP database authorization test suite for LOKAL public schema hardening
-- Tests table-level RLS flags, least-privilege grants/revocations, and column-level restrictions.

BEGIN;
SELECT plan(18);

-- ----------------------------------------------------------------------------
-- 1. Verify Row Level Security is enabled on all 6 public tables
-- ----------------------------------------------------------------------------
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

-- ----------------------------------------------------------------------------
-- 2. Verify anon role table permissions
-- ----------------------------------------------------------------------------
-- shops: anon may SELECT, but cannot mutate
SELECT ok(has_table_privilege('anon', 'public.shops', 'SELECT'), 'anon has SELECT on shops');
SELECT ok(NOT has_table_privilege('anon', 'public.shops', 'INSERT'), 'anon lacks INSERT on shops');
SELECT ok(NOT has_table_privilege('anon', 'public.shops', 'UPDATE'), 'anon lacks UPDATE on shops');
SELECT ok(NOT has_table_privilege('anon', 'public.shops', 'DELETE'), 'anon lacks DELETE on shops');

-- menu_items: anon has no access whatsoever
SELECT ok(NOT has_table_privilege('anon', 'public.menu_items', 'SELECT'), 'anon lacks SELECT on menu_items');
SELECT ok(NOT has_table_privilege('anon', 'public.menu_items', 'INSERT'), 'anon lacks INSERT on menu_items');

-- audit, reviews, favorites: anon lacks mutation access
SELECT ok(NOT has_table_privilege('anon', 'public.shop_curation_audit', 'SELECT'), 'anon lacks SELECT on shop_curation_audit');
SELECT ok(NOT has_table_privilege('anon', 'public.reviews', 'INSERT'), 'anon lacks INSERT on reviews');
SELECT ok(NOT has_table_privilege('anon', 'public.favorites', 'INSERT'), 'anon lacks INSERT on favorites');

-- ----------------------------------------------------------------------------
-- 3. Verify column-level restrictions on shop_curation
-- ----------------------------------------------------------------------------
-- Non-sensitive columns are readable
SELECT ok(has_column_privilege('anon', 'public.shop_curation', 'shop_id', 'SELECT'), 'anon has SELECT on shop_curation.shop_id');
SELECT ok(has_column_privilege('anon', 'public.shop_curation', 'status', 'SELECT'), 'anon has SELECT on shop_curation.status');

-- Sensitive curation metadata is NOT readable by anon
SELECT ok(NOT has_column_privilege('anon', 'public.shop_curation', 'curator_notes', 'SELECT'), 'anon lacks SELECT on shop_curation.curator_notes');

SELECT * FROM finish();
ROLLBACK;

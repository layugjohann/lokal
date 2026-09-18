-- Migration: 20260919000000_user_reviews.sql
-- Description: LOKAL first-party user reviews schema, constraints, indexes, and authenticated RLS

-- 1. Table Schema Enhancements
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE;
ALTER TABLE reviews ADD COLUMN IF NOT EXISTS author_name TEXT NOT NULL DEFAULT 'LOKAL User';
ALTER TABLE reviews ALTER COLUMN source SET DEFAULT 'lokal';

-- 2. Single review per user per shop constraint
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_reviews_user_shop') THEN
        ALTER TABLE reviews ADD CONSTRAINT uq_reviews_user_shop UNIQUE (user_id, shop_id);
    END IF;
END $$;

-- 3. Performance & lookup indexes
CREATE INDEX IF NOT EXISTS idx_reviews_shop_id ON reviews (shop_id);
CREATE INDEX IF NOT EXISTS idx_reviews_user_id ON reviews (user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_reviews_user_shop ON reviews (user_id, shop_id);

-- 4. Row Level Security
ALTER TABLE reviews ENABLE ROW LEVEL SECURITY;

-- Authenticated users only can read reviews
DROP POLICY IF EXISTS "Allow authenticated read access on reviews" ON reviews;
CREATE POLICY "Allow authenticated read access on reviews" ON reviews
    FOR SELECT TO authenticated USING (true);

-- Authenticated users can insert only their own review
DROP POLICY IF EXISTS "Allow users to insert own review" ON reviews;
CREATE POLICY "Allow users to insert own review" ON reviews
    FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);

-- Authenticated users can update only their own review
DROP POLICY IF EXISTS "Allow users to update own review" ON reviews;
CREATE POLICY "Allow users to update own review" ON reviews
    FOR UPDATE TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);

-- Authenticated users can delete only their own review
DROP POLICY IF EXISTS "Allow users to delete own review" ON reviews;
CREATE POLICY "Allow users to delete own review" ON reviews
    FOR DELETE TO authenticated USING (auth.uid() = user_id);

-- Service role full access for internal backend tasks
DROP POLICY IF EXISTS "Allow service role full access on reviews" ON reviews;
CREATE POLICY "Allow service role full access on reviews" ON reviews
    TO service_role USING (true) WITH CHECK (true);

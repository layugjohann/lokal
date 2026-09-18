-- Migration: 20260918000000_shop_curation.sql
-- Description: Independent business eligibility and shop curation tables, audit log, and updated nearby shops RPC

-- 1. Create Enums for Curation Status and Confidence
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'shop_eligibility_status') THEN
        CREATE TYPE shop_eligibility_status AS ENUM ('APPROVED', 'EXCLUDED', 'PENDING_REVIEW');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'curation_confidence') THEN
        CREATE TYPE curation_confidence AS ENUM ('HIGH', 'MEDIUM', 'LOW');
    END IF;
END $$;

-- 2. Dedicated Shop Curation Table
CREATE TABLE IF NOT EXISTS shop_curation (
    shop_id UUID PRIMARY KEY REFERENCES shops(id) ON DELETE CASCADE,
    status shop_eligibility_status NOT NULL DEFAULT 'PENDING_REVIEW',
    location_count INTEGER CHECK (location_count IS NULL OR location_count >= 0),
    evidence_source TEXT,
    confidence curation_confidence NOT NULL DEFAULT 'LOW',
    is_manual_override BOOLEAN NOT NULL DEFAULT FALSE,
    curator_id UUID,
    curator_notes TEXT,
    evaluated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for status filtering and fast joins
CREATE INDEX IF NOT EXISTS idx_shop_curation_status ON shop_curation (status);

-- Trigger for shop_curation.updated_at
DROP TRIGGER IF EXISTS set_shop_curation_updated_at ON shop_curation;
CREATE TRIGGER set_shop_curation_updated_at
    BEFORE UPDATE ON shop_curation
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- 3. Append-Only Curation Audit Table
CREATE TABLE IF NOT EXISTS shop_curation_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE CASCADE,
    old_status shop_eligibility_status,
    new_status shop_eligibility_status NOT NULL,
    old_location_count INTEGER,
    new_location_count INTEGER,
    changed_by UUID,
    change_source TEXT NOT NULL,
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_shop_curation_audit_shop_id ON shop_curation_audit (shop_id);

-- Backfill initial curation status for any existing shops
INSERT INTO shop_curation (shop_id, status, confidence)
SELECT id, 'PENDING_REVIEW', 'LOW'
FROM shops
ON CONFLICT (shop_id) DO NOTHING;

-- 4. Update get_nearby_shops SQL RPC to enforce APPROVED eligibility
CREATE OR REPLACE FUNCTION get_nearby_shops(
    user_lat DOUBLE PRECISION,
    user_lng DOUBLE PRECISION,
    radius_meters DOUBLE PRECISION DEFAULT 5000,
    result_limit INTEGER DEFAULT 50,
    result_offset INTEGER DEFAULT 0
)
RETURNS TABLE (
    id UUID,
    name TEXT,
    address TEXT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    rating NUMERIC(3, 2),
    google_place_id TEXT,
    created_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ,
    distance_meters DOUBLE PRECISION
)
LANGUAGE plpgsql
SECURITY INVOKER
STABLE
AS $$
DECLARE
    earth_radius CONSTANT DOUBLE PRECISION := 6371000.0;
    rad_lat DOUBLE PRECISION;
    rad_lng DOUBLE PRECISION;
    delta_lat DOUBLE PRECISION;
    delta_lng DOUBLE PRECISION;
    lat_min DOUBLE PRECISION;
    lat_max DOUBLE PRECISION;
    lng_min DOUBLE PRECISION;
    lng_max DOUBLE PRECISION;
    crosses_antimeridian BOOLEAN := FALSE;
    spans_all_lng BOOLEAN := FALSE;
    cos_lat DOUBLE PRECISION;
    max_abs_lat DOUBLE PRECISION;
BEGIN
    -- Clamp and fallback for pagination and radius safety
    IF radius_meters IS NULL OR radius_meters <= 0 THEN
        radius_meters := 5000.0;
    ELSIF radius_meters > 50000.0 THEN
        radius_meters := 50000.0;
    END IF;

    IF result_limit IS NULL OR result_limit <= 0 THEN
        result_limit := 50;
    ELSIF result_limit > 100 THEN
        result_limit := 100;
    END IF;

    IF result_offset IS NULL OR result_offset < 0 THEN
        result_offset := 0;
    END IF;

    -- Calculate latitude bounding box delta (in degrees)
    delta_lat := (radius_meters / earth_radius) * (180.0 / PI());
    lat_min := GREATEST(-90.0, user_lat - delta_lat);
    lat_max := LEAST(90.0, user_lat + delta_lat);

    max_abs_lat := GREATEST(ABS(lat_min), ABS(lat_max));

    -- Handle polar regions or wide bounds spanning all longitudes
    IF max_abs_lat >= 89.9 OR delta_lat >= 180.0 THEN
        spans_all_lng := TRUE;
    ELSE
        cos_lat := COS(RADIANS(max_abs_lat));
        IF cos_lat < 1e-6 THEN
            spans_all_lng := TRUE;
        ELSE
            delta_lng := delta_lat / cos_lat;
            IF delta_lng >= 180.0 THEN
                spans_all_lng := TRUE;
            ELSE
                lng_min := user_lng - delta_lng;
                lng_max := user_lng + delta_lng;

                IF lng_min < -180.0 THEN
                    crosses_antimeridian := TRUE;
                    lng_min := lng_min + 360.0;
                ELSIF lng_max > 180.0 THEN
                    crosses_antimeridian := TRUE;
                    lng_max := lng_max - 360.0;
                END IF;
            END IF;
        END IF;
    END IF;

    rad_lat := RADIANS(user_lat);
    rad_lng := RADIANS(user_lng);

    RETURN QUERY
    WITH candidate_shops AS (
        SELECT
            s.id,
            s.name,
            s.address,
            s.latitude,
            s.longitude,
            s.rating,
            s.google_place_id,
            s.created_at,
            s.updated_at
        FROM shops s
        INNER JOIN shop_curation sc ON s.id = sc.shop_id
        WHERE sc.status = 'APPROVED'
          AND s.latitude BETWEEN lat_min AND lat_max
          AND (
              spans_all_lng
              OR (NOT crosses_antimeridian AND s.longitude BETWEEN lng_min AND lng_max)
              OR (crosses_antimeridian AND (s.longitude >= lng_min OR s.longitude <= lng_max))
          )
    ),
    calculated_shops AS (
        SELECT
            cs.id,
            cs.name,
            cs.address,
            cs.latitude,
            cs.longitude,
            cs.rating,
            cs.google_place_id,
            cs.created_at,
            cs.updated_at,
            (
                2.0 * earth_radius * ASIN(
                    SQRT(
                        LEAST(
                            1.0,
                            GREATEST(
                                0.0,
                                POWER(SIN((RADIANS(cs.latitude) - rad_lat) / 2.0), 2) +
                                COS(rad_lat) * COS(RADIANS(cs.latitude)) *
                                POWER(SIN((RADIANS(cs.longitude) - rad_lng) / 2.0), 2)
                            )
                        )
                    )
                )
            ) AS distance_meters
        FROM candidate_shops cs
    )
    SELECT
        calc.id,
        calc.name,
        calc.address,
        calc.latitude,
        calc.longitude,
        calc.rating,
        calc.google_place_id,
        calc.created_at,
        calc.updated_at,
        calc.distance_meters
    FROM calculated_shops calc
    WHERE calc.distance_meters <= radius_meters
    ORDER BY calc.distance_meters ASC, calc.id ASC
    LIMIT result_limit
    OFFSET result_offset;
END;
$$;

-- 5. Row Level Security (RLS)
ALTER TABLE shop_curation ENABLE ROW LEVEL SECURITY;
ALTER TABLE shop_curation_audit ENABLE ROW LEVEL SECURITY;

-- Public can view shop curation status (e.g., in client apps)
CREATE POLICY "Allow public read access on shop_curation" ON shop_curation
    FOR SELECT USING (true);

-- Service role full access for trusted backend operations
CREATE POLICY "Allow service role full access on shop_curation" ON shop_curation
    TO service_role USING (true) WITH CHECK (true);

-- Only curators/admins can inspect the curation audit trail directly
CREATE POLICY "Allow curator read access on shop_curation_audit" ON shop_curation_audit
    FOR SELECT TO authenticated USING (
        (auth.jwt() -> 'app_metadata' ->> 'role') IN ('curator', 'admin')
    );

-- Service role full access on audit table for trusted backend operations
CREATE POLICY "Allow service role full access on shop_curation_audit" ON shop_curation_audit
    TO service_role USING (true) WITH CHECK (true);

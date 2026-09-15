-- Migration: 20260916000000_nearby_shops_rpc.sql
-- Description: Coffee shop nearby search SQL RPC using bounding box prefilter and Haversine distance formula

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
        WHERE s.latitude BETWEEN lat_min AND lat_max
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

import type { Shop, NearbySearchParams } from '../types/shop';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

export function getApiBaseUrl(): string {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }
  return DEFAULT_API_BASE_URL;
}

/**
 * Formats a distance in meters into a readable string (e.g. "350 m" or "1.2 km").
 */
export function formatDistance(meters?: number | null): string {
  if (meters === undefined || meters === null || isNaN(meters)) {
    return '';
  }
  if (meters < 1000) {
    return `${Math.round(meters)} m`;
  }
  return `${(meters / 1000).toFixed(1)} km`;
}

/**
 * Formats a numeric rating into a star display string (e.g. "★ 4.8" or "No rating").
 */
export function formatRating(rating?: number | null): string {
  if (rating === undefined || rating === null || isNaN(rating)) {
    return 'No rating';
  }
  return `★ ${Number(rating).toFixed(1)}`;
}

/**
 * Retrieves nearby coffee shops from the FastAPI backend.
 */
export async function fetchNearbyShops(
  params: NearbySearchParams,
  authToken?: string | null
): Promise<Shop[]> {
  const { latitude, longitude, radius = 5000, limit = 50, offset = 0 } = params;
  const baseUrl = getApiBaseUrl();

  const queryParams = new URLSearchParams({
    latitude: latitude.toString(),
    longitude: longitude.toString(),
    radius: radius.toString(),
    limit: limit.toString(),
    offset: offset.toString(),
  });

  const url = `${baseUrl}/api/v1/shops/nearby?${queryParams.toString()}`;

  const headers: Record<string, string> = {
    Accept: 'application/json',
  };

  const token = authToken || process.env.EXPO_PUBLIC_AUTH_TOKEN;
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    let errorDetail = 'Failed to fetch nearby coffee shops.';
    try {
      const data = await response.json();
      if (data && typeof data.detail === 'string') {
        errorDetail = data.detail;
      }
    } catch {
      // Ignore JSON parse errors on non-json error responses
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

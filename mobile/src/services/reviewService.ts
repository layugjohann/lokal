import type { ShopReviewsResponse } from '../types/review';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

export function getApiBaseUrl(): string {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }
  return DEFAULT_API_BASE_URL;
}

/**
 * Retrieves normalized reviews and provider attributions for a coffee shop from FastAPI.
 */
export async function fetchShopReviews(
  shopId: string,
  authToken?: string | null
): Promise<ShopReviewsResponse> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/shops/${encodeURIComponent(shopId)}/reviews`;

  const headers: Record<string, string> = {
    Accept: 'application/json',
  };

  if (authToken) {
    headers['Authorization'] = `Bearer ${authToken}`;
  }

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    let errorDetail = 'Failed to fetch coffee shop reviews.';
    try {
      const data = await response.json();
      if (data && typeof data.detail === 'string') {
        errorDetail = data.detail;
      }
    } catch {
      // Non-JSON error response fallback
    }

    const error = new Error(errorDetail);
    (error as { status?: number }).status = response.status;
    throw error;
  }

  return response.json();
}

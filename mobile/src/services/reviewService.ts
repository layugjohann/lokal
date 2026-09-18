import type {
  MessageResponse,
  ReviewCreateInput,
  ReviewUpdateInput,
  ShopReviewsResponse,
  UnifiedReview,
} from '../types/review';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

export function getApiBaseUrl(): string {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }
  return DEFAULT_API_BASE_URL;
}

function getAuthHeaders(authToken: string): Record<string, string> {
  if (!authToken || !authToken.trim()) {
    throw new Error('Authentication token is required.');
  }
  return {
    Accept: 'application/json',
    Authorization: `Bearer ${authToken.trim()}`,
  };
}

/**
 * Retrieves normalized reviews and provider attributions for a coffee shop from FastAPI.
 * Requires a valid authenticated caller JWT.
 */
export async function fetchShopReviews(
  shopId: string,
  authToken: string
): Promise<ShopReviewsResponse> {
  if (!authToken || !authToken.trim()) {
    throw new Error('Authentication token is required to fetch reviews.');
  }
  const headers = getAuthHeaders(authToken);
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/shops/${encodeURIComponent(shopId)}/reviews`;

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

/**
 * Retrieves the authenticated user's own review for a coffee shop.
 * Returns null if the user has not reviewed the coffee shop.
 */
export async function fetchMyReview(
  shopId: string,
  authToken: string
): Promise<UnifiedReview | null> {
  const headers = getAuthHeaders(authToken);
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/shops/${encodeURIComponent(shopId)}/reviews/mine`;

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    let errorDetail = 'Failed to fetch your review.';
    try {
      const data = await response.json();
      if (data && typeof data.detail === 'string') {
        errorDetail = data.detail;
      }
    } catch {
      // Non-JSON fallback
    }
    const error = new Error(errorDetail);
    (error as { status?: number }).status = response.status;
    throw error;
  }

  return response.json();
}

/**
 * Submits a new first-party LOKAL user review for an approved coffee shop.
 */
export async function createUserReview(
  shopId: string,
  input: ReviewCreateInput,
  authToken: string
): Promise<UnifiedReview> {
  const headers = {
    ...getAuthHeaders(authToken),
    'Content-Type': 'application/json',
  };
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/shops/${encodeURIComponent(shopId)}/reviews`;

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    let errorDetail = 'Failed to submit your review.';
    try {
      const data = await response.json();
      if (data && typeof data.detail === 'string') {
        errorDetail = data.detail;
      }
    } catch {
      // Non-JSON fallback
    }
    const error = new Error(errorDetail);
    (error as { status?: number }).status = response.status;
    throw error;
  }

  return response.json();
}

/**
 * Partially updates an existing LOKAL user review with field-presence semantics.
 */
export async function updateUserReview(
  shopId: string,
  input: ReviewUpdateInput,
  authToken: string
): Promise<UnifiedReview> {
  const headers = {
    ...getAuthHeaders(authToken),
    'Content-Type': 'application/json',
  };
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/shops/${encodeURIComponent(shopId)}/reviews/mine`;

  const response = await fetch(url, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    let errorDetail = 'Failed to update your review.';
    try {
      const data = await response.json();
      if (data && typeof data.detail === 'string') {
        errorDetail = data.detail;
      }
    } catch {
      // Non-JSON fallback
    }
    const error = new Error(errorDetail);
    (error as { status?: number }).status = response.status;
    throw error;
  }

  return response.json();
}

/**
 * Permanently deletes the authenticated user's review for a coffee shop.
 */
export async function deleteUserReview(
  shopId: string,
  authToken: string
): Promise<MessageResponse> {
  const headers = getAuthHeaders(authToken);
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/shops/${encodeURIComponent(shopId)}/reviews/mine`;

  const response = await fetch(url, {
    method: 'DELETE',
    headers,
  });

  if (!response.ok) {
    let errorDetail = 'Failed to delete your review.';
    try {
      const data = await response.json();
      if (data && typeof data.detail === 'string') {
        errorDetail = data.detail;
      }
    } catch {
      // Non-JSON fallback
    }
    const error = new Error(errorDetail);
    (error as { status?: number }).status = response.status;
    throw error;
  }

  return response.json();
}

import type { FavoriteStatusResponse } from '../types/favorite';

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
    'Content-Type': 'application/json',
    Authorization: `Bearer ${authToken.trim()}`,
  };
}

/**
 * Retrieves the favorite status of a coffee shop for the authenticated user.
 */
export async function fetchFavoriteStatus(
  shopId: string,
  authToken: string
): Promise<FavoriteStatusResponse> {
  if (!authToken || !authToken.trim()) {
    throw new Error('Authentication token is required to fetch favorite status.');
  }
  const headers = getAuthHeaders(authToken);
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/shops/${encodeURIComponent(shopId)}/favorite`;

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    let errorDetail = 'Failed to fetch favorite status.';
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
 * Adds an approved coffee shop to the authenticated user's favorites.
 */
export async function addFavorite(
  shopId: string,
  authToken: string
): Promise<FavoriteStatusResponse> {
  if (!authToken || !authToken.trim()) {
    throw new Error('Authentication token is required to favorite a coffee shop.');
  }
  const headers = getAuthHeaders(authToken);
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/shops/${encodeURIComponent(shopId)}/favorite`;

  const response = await fetch(url, {
    method: 'POST',
    headers,
  });

  if (!response.ok) {
    let errorDetail = 'Failed to favorite coffee shop.';
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
 * Removes a coffee shop from the authenticated user's favorites.
 */
export async function removeFavorite(
  shopId: string,
  authToken: string
): Promise<void> {
  if (!authToken || !authToken.trim()) {
    throw new Error('Authentication token is required to remove a favorite.');
  }
  const headers = getAuthHeaders(authToken);
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/shops/${encodeURIComponent(shopId)}/favorite`;

  const response = await fetch(url, {
    method: 'DELETE',
    headers,
  });

  if (!response.ok) {
    let errorDetail = 'Failed to remove favorite.';
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
}

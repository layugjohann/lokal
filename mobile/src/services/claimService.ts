import type {
  ClaimSubmissionPayload,
  OwnerDashboardData,
  OwnerShopUpdatePayload,
  ShopClaim,
} from '../types/claim.ts';
import type { Shop } from '../types/shop.ts';

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

async function handleResponseError(response: Response, defaultMessage: string): Promise<never> {
  let errorDetail = defaultMessage;
  try {
    const data = await response.json();
    if (data && typeof data.detail === 'string') {
      errorDetail = data.detail;
    } else if (data && Array.isArray(data.detail)) {
      errorDetail = data.detail.map((d: { msg?: string }) => d.msg || '').join(', ');
    }
  } catch {
    // Non-JSON error response fallback
  }

  const error = new Error(errorDetail);
  (error as { status?: number }).status = response.status;
  throw error;
}

/**
 * Retrieve current user's claim status for a specific coffee shop.
 */
export async function fetchShopClaimStatus(
  shopId: string,
  authToken: string
): Promise<ShopClaim | null> {
  if (!authToken || !authToken.trim()) {
    throw new Error('Authentication token is required to fetch claim status.');
  }
  const headers = getAuthHeaders(authToken);
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/shops/${encodeURIComponent(shopId)}/claim`;

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    return handleResponseError(response, 'Failed to fetch shop claim status.');
  }

  const data = await response.json();
  return data ?? null;
}

/**
 * Submit an ownership claim for an eligible coffee shop.
 */
export async function submitShopClaim(
  shopId: string,
  payload: ClaimSubmissionPayload,
  authToken: string
): Promise<ShopClaim> {
  if (!authToken || !authToken.trim()) {
    throw new Error('Authentication token is required to submit a claim.');
  }
  const headers = getAuthHeaders(authToken);
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/shops/${encodeURIComponent(shopId)}/claim`;

  const response = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    return handleResponseError(response, 'Failed to submit ownership claim.');
  }

  return response.json();
}

/**
 * Retrieve all coffee shop claims submitted by the authenticated user.
 */
export async function fetchMyClaims(authToken: string): Promise<ShopClaim[]> {
  if (!authToken || !authToken.trim()) {
    throw new Error('Authentication token is required to fetch your claims.');
  }
  const headers = getAuthHeaders(authToken);
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/claims/mine`;

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    return handleResponseError(response, 'Failed to fetch user claims.');
  }

  return response.json();
}

/**
 * Retrieve owner dashboard data for a claimed coffee shop.
 */
export async function fetchOwnerDashboard(
  shopId: string,
  authToken: string
): Promise<OwnerDashboardData> {
  if (!authToken || !authToken.trim()) {
    throw new Error('Authentication token is required to view owner dashboard.');
  }
  const headers = getAuthHeaders(authToken);
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/owner/shops/${encodeURIComponent(shopId)}/dashboard`;

  const response = await fetch(url, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    return handleResponseError(response, 'Failed to load owner dashboard.');
  }

  return response.json();
}

/**
 * Update safe listing fields (name, address) for a claimed coffee shop.
 */
export async function updateOwnerShop(
  shopId: string,
  payload: OwnerShopUpdatePayload,
  authToken: string
): Promise<Shop> {
  if (!authToken || !authToken.trim()) {
    throw new Error('Authentication token is required to update shop.');
  }
  const headers = getAuthHeaders(authToken);
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/owner/shops/${encodeURIComponent(shopId)}`;

  const response = await fetch(url, {
    method: 'PATCH',
    headers,
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    return handleResponseError(response, 'Failed to update shop details.');
  }

  return response.json();
}

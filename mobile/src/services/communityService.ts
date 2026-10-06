import type { CommunityFeedItem, CommunityFeedResponse } from '../types/community';

export type ShareAction = { action: string };
export type ShareFn = (content: { message: string; title?: string }) => Promise<ShareAction>;

let customShareFn: ShareFn | null = null;

export function setShareFn(fn: ShareFn | null): void {
  customShareFn = fn;
}

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
 * Retrieves the paginated community feed of recent first-party LOKAL reviews.
 * Requires a valid authenticated caller JWT.
 */
export async function fetchCommunityFeed(
  authToken: string,
  limit: number = 20,
  offset: number = 0
): Promise<CommunityFeedResponse> {
  if (!authToken || !authToken.trim()) {
    throw new Error('Authentication token is required to fetch community feed.');
  }

  const headers = getAuthHeaders(authToken);
  const baseUrl = getApiBaseUrl();
  const queryParams = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });

  const response = await fetch(`${baseUrl}/api/v1/community/feed?${queryParams.toString()}`, {
    method: 'GET',
    headers,
  });

  if (!response.ok) {
    let errorDetail = 'Failed to fetch community feed.';
    try {
      const data = await response.json();
      if (data && typeof data.detail === 'string') {
        errorDetail = data.detail;
      }
    } catch {
      // Non-JSON error response fallback
    }
    throw new Error(errorDetail);
  }

  return response.json();
}

/**
 * Truncates review content to a bounded excerpt (at most maxLength chars) with ellipsis.
 */
export function formatShareReviewExcerpt(
  content: string | null | undefined,
  maxLength: number = 180
): string | null {
  if (!content) {
    return null;
  }
  const trimmed = content.trim();
  if (!trimmed) {
    return null;
  }
  if (trimmed.length <= maxLength) {
    return trimmed;
  }
  return `${trimmed.slice(0, maxLength - 3).trimEnd()}...`;
}

/**
 * Formats a sanitized, public-only plain-text message for sharing a review.
 * Strictly excludes review IDs, shop IDs, user UUIDs, and emails.
 */
export function formatShareReviewMessage(review: CommunityFeedItem): string {
  const excerpt = formatShareReviewExcerpt(review.content, 180);
  if (excerpt) {
    return `☕ ${review.shop_name}\nRating: ★ ${review.rating}/5\n"${excerpt}"\n— Shared by ${review.author_name} on LOKAL`;
  }
  return `☕ ${review.shop_name} - Rated ★ ${review.rating}/5 by ${review.author_name} on LOKAL`;
}

/**
 * Formats a sanitized, public-only plain-text message for sharing a coffee shop.
 * Strictly excludes shop IDs, Place IDs, and internal metadata.
 */
export function formatShareShopMessage(shop: {
  name: string;
  address?: string | null;
  rating?: number | null;
}): string {
  const addressLine = shop.address ? `\n📍 ${shop.address}` : '';
  const ratingLine = shop.rating != null ? `\n★ ${shop.rating}` : '';
  return `☕ ${shop.name}${addressLine}${ratingLine}\nDiscovered on LOKAL`;
}

/**
 * Invokes native sharing for a community review.
 * Fails gracefully if the user cancels or the native share surface is unavailable.
 */
export async function shareCommunityReview(
  review: CommunityFeedItem,
  shareFn?: ShareFn
): Promise<boolean> {
  try {
    const message = formatShareReviewMessage(review);
    const fn = shareFn || customShareFn;
    if (fn) {
      const result = await fn({
        message,
        title: `${review.shop_name} on LOKAL`,
      });
      return result.action !== 'dismissedAction';
    }
    const RN: any = await import('react-native').catch(() => null);
    if (RN?.Share?.share) {
      const result = await RN.Share.share({
        message,
        title: `${review.shop_name} on LOKAL`,
      });
      return result.action === RN.Share.sharedAction;
    }
    return false;
  } catch {
    // Graceful error/cancellation handling without throwing
    return false;
  }
}

/**
 * Invokes native sharing for a coffee shop.
 * Fails gracefully if the user cancels or the native share surface is unavailable.
 */
export async function shareShop(
  shop: {
    name: string;
    address?: string | null;
    rating?: number | null;
  },
  shareFn?: ShareFn
): Promise<boolean> {
  try {
    const message = formatShareShopMessage(shop);
    const fn = shareFn || customShareFn;
    if (fn) {
      const result = await fn({
        message,
        title: `${shop.name} on LOKAL`,
      });
      return result.action !== 'dismissedAction';
    }
    const RN: any = await import('react-native').catch(() => null);
    if (RN?.Share?.share) {
      const result = await RN.Share.share({
        message,
        title: `${shop.name} on LOKAL`,
      });
      return result.action === RN.Share.sharedAction;
    }
    return false;
  } catch {
    // Graceful error/cancellation handling without throwing
    return false;
  }
}


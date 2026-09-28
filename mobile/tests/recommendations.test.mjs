import test from 'node:test';
import assert from 'node:assert';
import { fetchShopRecommendations } from '../src/services/reviewService.ts';

test('fetchShopRecommendations constructs request with auth token and returns recommendations on success', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedHeaders = {};

  const mockRecommendationsResponse = {
    shop_id: 'shop-123',
    status: 'available',
    items: [
      {
        item_name: 'Spanish Latte',
        reason: 'Consistently praised for its rich and creamy sweetness.',
      },
      {
        item_name: 'Pistachio Croissant',
        reason: 'Loved for its flaky layers and generous pistachio cream.',
      },
    ],
    review_count_analyzed: 5,
  };

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      status: 200,
      json: async () => mockRecommendationsResponse,
    };
  };

  try {
    const data = await fetchShopRecommendations('shop-123', 'mock-token-xyz');
    assert.strictEqual(
      requestedUrl,
      'http://localhost:8000/api/v1/shops/shop-123/reviews/recommendations'
    );
    assert.strictEqual(requestedHeaders.Authorization, 'Bearer mock-token-xyz');
    assert.strictEqual(requestedHeaders.Accept, 'application/json');
    assert.strictEqual(data.status, 'available');
    assert.strictEqual(data.items.length, 2);
    assert.strictEqual(data.items[0].item_name, 'Spanish Latte');
    assert.strictEqual(data.review_count_analyzed, 5);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopRecommendations returns insufficient_reviews when usable reviews are under threshold', async () => {
  const originalFetch = globalThis.fetch;

  const mockInsufficientResponse = {
    shop_id: 'shop-456',
    status: 'insufficient_reviews',
    items: [],
    review_count_analyzed: 2,
  };

  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => mockInsufficientResponse,
  });

  try {
    const data = await fetchShopRecommendations('shop-456', 'mock-token');
    assert.strictEqual(data.status, 'insufficient_reviews');
    assert.deepStrictEqual(data.items, []);
    assert.strictEqual(data.review_count_analyzed, 2);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopRecommendations returns available with empty items when 3+ reviews have no menu items', async () => {
  const originalFetch = globalThis.fetch;

  const mockEmptyResponse = {
    shop_id: 'shop-789',
    status: 'available',
    items: [],
    review_count_analyzed: 4,
  };

  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => mockEmptyResponse,
  });

  try {
    const data = await fetchShopRecommendations('shop-789', 'mock-token');
    assert.strictEqual(data.status, 'available');
    assert.deepStrictEqual(data.items, []);
    assert.strictEqual(data.review_count_analyzed, 4);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopRecommendations throws error when authToken is missing or whitespace', async () => {
  await assert.rejects(
    async () => fetchShopRecommendations('shop-123', ''),
    { message: 'Authentication token is required to fetch recommendations.' }
  );

  await assert.rejects(
    async () => fetchShopRecommendations('shop-123', '   '),
    { message: 'Authentication token is required to fetch recommendations.' }
  );
});

test('fetchShopRecommendations handles 401 Unauthorized', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: 'Authentication token is missing or invalid.' }),
  });

  try {
    await assert.rejects(
      async () => fetchShopRecommendations('shop-123', 'invalid-token'),
      (err) => {
        assert.strictEqual(err.message, 'Authentication token is missing or invalid.');
        assert.strictEqual(err.status, 401);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopRecommendations handles 404 Not Found', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 404,
    json: async () => ({ detail: 'Coffee shop not found.' }),
  });

  try {
    await assert.rejects(
      async () => fetchShopRecommendations('shop-999', 'valid-token'),
      (err) => {
        assert.strictEqual(err.message, 'Coffee shop not found.');
        assert.strictEqual(err.status, 404);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopRecommendations handles 502 Bad Gateway from AI provider failure', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 502,
    json: async () => ({ detail: 'AI recommendation service is temporarily unavailable.' }),
  });

  try {
    await assert.rejects(
      async () => fetchShopRecommendations('shop-123', 'valid-token'),
      (err) => {
        assert.strictEqual(
          err.message,
          'AI recommendation service is temporarily unavailable.'
        );
        assert.strictEqual(err.status, 502);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopRecommendations handles 503 Service Unavailable', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 503,
    json: async () => ({ detail: 'AI recommendation service is not configured.' }),
  });

  try {
    await assert.rejects(
      async () => fetchShopRecommendations('shop-123', 'valid-token'),
      (err) => {
        assert.strictEqual(
          err.message,
          'AI recommendation service is not configured.'
        );
        assert.strictEqual(err.status, 503);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopRecommendations handles non-JSON error response fallback', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 500,
    json: async () => {
      throw new Error('Not JSON');
    },
  });

  try {
    await assert.rejects(
      async () => fetchShopRecommendations('shop-123', 'valid-token'),
      (err) => {
        assert.strictEqual(err.message, 'Failed to fetch recommendations.');
        assert.strictEqual(err.status, 500);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

/**
 * Harness modeling ShopDetailCard's recommendation state management,
 * monotonic request tracking, and context invalidation.
 */
class ShopDetailCardRecommendationsStateHarness {
  constructor(initialShop, initialAuthToken = 'mock-token') {
    this.shop = initialShop;
    this.authToken = initialAuthToken;

    this.recommendationsData = null;
    this.isLoadingRecommendations = false;
    this.recommendationsError = null;

    this.currentRecommendationsRequestId = 0;
  }

  // Simulates UI condition branches in ShopDetailCard.tsx based on semantic status
  getRenderedRecommendationState() {
    if (this.isLoadingRecommendations) return 'loading';
    if (this.recommendationsError) return 'error';
    if (!this.recommendationsData) return 'none';
    if (this.recommendationsData.status === 'insufficient_reviews') return 'insufficient_reviews';
    if (this.recommendationsData.status === 'available' && this.recommendationsData.items.length === 0) return 'available_empty';
    if (this.recommendationsData.status === 'available' && this.recommendationsData.items.length > 0) return 'available_with_items';
    return 'none';
  }

  // Simulates useEffect cleanup and re-trigger when shop.id or authToken changes in ShopDetailCard.tsx
  switchContext(newShop, newAuthToken = this.authToken) {
    this.currentRecommendationsRequestId += 1;

    this.shop = newShop;
    this.authToken = newAuthToken;

    this.currentRecommendationsRequestId += 1;
    this.recommendationsData = null;
    this.recommendationsError = null;
    if (!this.authToken) {
      this.isLoadingRecommendations = false;
    }
  }

  // Simulates loadRecommendations callback in ShopDetailCard.tsx
  async loadRecommendations(fetchFn) {
    if (!this.authToken) {
      this.isLoadingRecommendations = false;
      this.recommendationsData = null;
      this.recommendationsError = null;
      return;
    }

    const requestId = ++this.currentRecommendationsRequestId;
    this.isLoadingRecommendations = true;
    this.recommendationsError = null;

    try {
      const data = await fetchFn(this.shop.id, this.authToken);
      if (requestId === this.currentRecommendationsRequestId) {
        this.recommendationsData = data;
      }
    } catch (err) {
      if (requestId === this.currentRecommendationsRequestId) {
        const message =
          err instanceof Error ? err.message : 'Unable to load recommendations.';
        this.recommendationsError = message;
      }
    } finally {
      if (requestId === this.currentRecommendationsRequestId) {
        this.isLoadingRecommendations = false;
      }
    }
  }
}

test('Stale recommendation protection: Shop A -> Shop B while loading does not apply stale recommendations', async () => {
  const harness = new ShopDetailCardRecommendationsStateHarness(
    { id: 'shop-A', name: 'Shop A' },
    'token-xyz'
  );

  let resolveShopA;
  const shopAPromise = new Promise((resolve) => {
    resolveShopA = resolve;
  });

  const mockFetch = async (shopId) => {
    if (shopId === 'shop-A') {
      return await shopAPromise;
    }
    return {
      shop_id: 'shop-B',
      status: 'available',
      items: [{ item_name: 'Shop B Drink', reason: 'Freshly roasted' }],
      review_count_analyzed: 5,
    };
  };

  // Start loading Shop A recommendations
  const loadAPromise = harness.loadRecommendations(mockFetch);
  assert.strictEqual(harness.isLoadingRecommendations, true);

  // User immediately switches to Shop B before Shop A finishes
  harness.switchContext({ id: 'shop-B', name: 'Shop B' });
  const loadBPromise = harness.loadRecommendations(mockFetch);
  await loadBPromise;

  assert.strictEqual(harness.recommendationsData.shop_id, 'shop-B');
  assert.strictEqual(harness.recommendationsData.items[0].item_name, 'Shop B Drink');

  // Now resolve Shop A late
  resolveShopA({
    shop_id: 'shop-A',
    status: 'available',
    items: [{ item_name: 'Shop A Stale Drink', reason: 'Old reason' }],
    review_count_analyzed: 10,
  });
  await loadAPromise;

  // Verify Shop A response was discarded and Shop B remains intact
  assert.strictEqual(harness.recommendationsData.shop_id, 'shop-B');
  assert.strictEqual(harness.recommendationsData.items[0].item_name, 'Shop B Drink');
});

test('Stale recommendation protection: failed stale recommendation request does not set error on newly selected shop', async () => {
  const harness = new ShopDetailCardRecommendationsStateHarness(
    { id: 'shop-A', name: 'Shop A' },
    'token-xyz'
  );

  let rejectShopA;
  const shopAPromise = new Promise((_, reject) => {
    rejectShopA = reject;
  });

  const mockFetch = async (shopId) => {
    if (shopId === 'shop-A') {
      return await shopAPromise;
    }
    return {
      shop_id: 'shop-B',
      status: 'available',
      items: [{ item_name: 'Shop B Coffee', reason: 'Delicious' }],
      review_count_analyzed: 3,
    };
  };

  const loadAPromise = harness.loadRecommendations(mockFetch);
  harness.switchContext({ id: 'shop-B', name: 'Shop B' });
  await harness.loadRecommendations(mockFetch);

  assert.strictEqual(harness.recommendationsError, null);
  assert.strictEqual(harness.recommendationsData.shop_id, 'shop-B');

  // Shop A fails after user switched to Shop B
  rejectShopA(new Error('Shop A AI failure'));
  await loadAPromise;

  // Verify error did not bleed into Shop B
  assert.strictEqual(harness.recommendationsError, null);
  assert.strictEqual(harness.recommendationsData.shop_id, 'shop-B');
});

test('Stale recommendation protection: auth token invalidation during in-flight fetch discards stale recommendations', async () => {
  const harness = new ShopDetailCardRecommendationsStateHarness(
    { id: 'shop-A', name: 'Shop A' },
    'token-xyz'
  );

  let resolveShopA;
  const shopAPromise = new Promise((resolve) => {
    resolveShopA = resolve;
  });

  const mockFetch = async () => await shopAPromise;

  const loadPromise = harness.loadRecommendations(mockFetch);
  assert.strictEqual(harness.isLoadingRecommendations, true);

  // User logs out while recommendation fetch is in flight
  harness.switchContext({ id: 'shop-A', name: 'Shop A' }, null);
  assert.strictEqual(harness.authToken, null);
  assert.strictEqual(harness.isLoadingRecommendations, false);

  // Now resolve late
  resolveShopA({
    shop_id: 'shop-A',
    status: 'available',
    items: [{ item_name: 'Secret Drink', reason: 'Members only' }],
    review_count_analyzed: 5,
  });
  await loadPromise;

  // Stale authenticated data must NOT be shown to unauthenticated user
  assert.strictEqual(harness.recommendationsData, null);
  assert.strictEqual(harness.isLoadingRecommendations, false);
});

test('ShopDetailCard semantic status rendering: insufficient_reviews status renders insufficient message', async () => {
  const harness = new ShopDetailCardRecommendationsStateHarness(
    { id: 'shop-1', name: 'Shop 1' },
    'token-xyz'
  );
  await harness.loadRecommendations(async () => ({
    shop_id: 'shop-1',
    status: 'insufficient_reviews',
    items: [],
    review_count_analyzed: 2,
  }));

  assert.strictEqual(harness.getRenderedRecommendationState(), 'insufficient_reviews');
});

test('ShopDetailCard semantic status rendering: available status with 0 items renders empty message', async () => {
  const harness = new ShopDetailCardRecommendationsStateHarness(
    { id: 'shop-1', name: 'Shop 1' },
    'token-xyz'
  );
  await harness.loadRecommendations(async () => ({
    shop_id: 'shop-1',
    status: 'available',
    items: [],
    review_count_analyzed: 5,
  }));

  assert.strictEqual(harness.getRenderedRecommendationState(), 'available_empty');
});

test('ShopDetailCard semantic status rendering: available status with items renders recommendations card', async () => {
  const harness = new ShopDetailCardRecommendationsStateHarness(
    { id: 'shop-1', name: 'Shop 1' },
    'token-xyz'
  );
  await harness.loadRecommendations(async () => ({
    shop_id: 'shop-1',
    status: 'available',
    items: [{ item_name: 'Spanish Latte', reason: 'Delicious' }],
    review_count_analyzed: 5,
  }));

  assert.strictEqual(harness.getRenderedRecommendationState(), 'available_with_items');
});


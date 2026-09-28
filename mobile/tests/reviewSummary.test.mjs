import test from 'node:test';
import assert from 'node:assert';
import { fetchShopReviewSummary } from '../src/services/reviewService.ts';

test('fetchShopReviewSummary constructs request with auth token and returns available summary on success', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedHeaders = {};

  const mockSummaryResponse = {
    shop_id: 'shop-123',
    status: 'available',
    summary: 'Great specialty pour-overs and friendly baristas, with limited afternoon seating.',
    positive_themes: ['Great specialty pour-overs', 'Friendly baristas'],
    negative_themes: ['Limited afternoon seating'],
    review_count_analyzed: 6,
  };

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      status: 200,
      json: async () => mockSummaryResponse,
    };
  };

  try {
    const data = await fetchShopReviewSummary('shop-123', 'mock-token-xyz');
    assert.strictEqual(requestedUrl, 'http://localhost:8000/api/v1/shops/shop-123/reviews/summary');
    assert.strictEqual(requestedHeaders.Authorization, 'Bearer mock-token-xyz');
    assert.strictEqual(requestedHeaders.Accept, 'application/json');
    assert.strictEqual(data.status, 'available');
    assert.strictEqual(data.summary, mockSummaryResponse.summary);
    assert.strictEqual(data.positive_themes.length, 2);
    assert.strictEqual(data.negative_themes.length, 1);
    assert.strictEqual(data.review_count_analyzed, 6);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopReviewSummary returns insufficient_reviews status correctly', async () => {
  const originalFetch = globalThis.fetch;

  const mockInsufficientResponse = {
    shop_id: 'shop-456',
    status: 'insufficient_reviews',
    summary: null,
    positive_themes: [],
    negative_themes: [],
    review_count_analyzed: 1,
  };

  globalThis.fetch = async () => ({
    ok: true,
    status: 200,
    json: async () => mockInsufficientResponse,
  });

  try {
    const data = await fetchShopReviewSummary('shop-456', 'mock-token');
    assert.strictEqual(data.status, 'insufficient_reviews');
    assert.strictEqual(data.summary, null);
    assert.deepStrictEqual(data.positive_themes, []);
    assert.deepStrictEqual(data.negative_themes, []);
    assert.strictEqual(data.review_count_analyzed, 1);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopReviewSummary throws error when authToken is missing or whitespace', async () => {
  await assert.rejects(
    async () => fetchShopReviewSummary('shop-123', ''),
    { message: 'Authentication token is required to fetch review summary.' }
  );

  await assert.rejects(
    async () => fetchShopReviewSummary('shop-123', '   '),
    { message: 'Authentication token is required to fetch review summary.' }
  );
});

test('fetchShopReviewSummary handles 401 Unauthorized', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: 'Authentication token is missing or invalid.' }),
  });

  try {
    await assert.rejects(
      async () => fetchShopReviewSummary('shop-123', 'invalid-token'),
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

test('fetchShopReviewSummary handles 404 Not Found', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 404,
    json: async () => ({ detail: 'Coffee shop not found.' }),
  });

  try {
    await assert.rejects(
      async () => fetchShopReviewSummary('shop-missing', 'valid-token'),
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

test('fetchShopReviewSummary handles 502 Bad Gateway from AI provider failure', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 502,
    json: async () => ({ detail: 'AI review summarization is temporarily unavailable.' }),
  });

  try {
    await assert.rejects(
      async () => fetchShopReviewSummary('shop-123', 'valid-token'),
      (err) => {
        assert.strictEqual(err.message, 'AI review summarization is temporarily unavailable.');
        assert.strictEqual(err.status, 502);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopReviewSummary handles 503 Service Unavailable', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 503,
    json: async () => ({ detail: 'AI review summarization service is not configured.' }),
  });

  try {
    await assert.rejects(
      async () => fetchShopReviewSummary('shop-123', 'valid-token'),
      (err) => {
        assert.strictEqual(err.message, 'AI review summarization service is not configured.');
        assert.strictEqual(err.status, 503);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopReviewSummary handles non-JSON error response fallback', async () => {
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
      async () => fetchShopReviewSummary('shop-123', 'valid-token'),
      (err) => {
        assert.strictEqual(err.message, 'Failed to fetch review summary.');
        assert.strictEqual(err.status, 500);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

/**
 * Harness modeling ShopDetailCard's summary state management,
 * monotonic request tracking, and context invalidation.
 */
class ShopDetailCardSummaryStateHarness {
  constructor(initialShop, initialAuthToken = 'mock-token') {
    this.shop = initialShop;
    this.authToken = initialAuthToken;

    this.summaryData = null;
    this.isLoadingSummary = false;
    this.summaryError = null;

    this.currentSummaryRequestId = 0;
  }

  // Simulates useEffect cleanup and re-trigger when shop.id or authToken changes in ShopDetailCard.tsx
  switchContext(newShop, newAuthToken = this.authToken) {
    // 1. useEffect cleanup of previous context
    this.currentSummaryRequestId += 1;

    this.shop = newShop;
    this.authToken = newAuthToken;

    // 2. useEffect setup for new context
    this.currentSummaryRequestId += 1;
    this.summaryData = null;
    this.summaryError = null;
    if (!this.authToken) {
      this.isLoadingSummary = false;
    }
  }

  // Simulates loadSummary callback in ShopDetailCard.tsx
  async loadSummary(fetchFn) {
    if (!this.authToken) {
      this.isLoadingSummary = false;
      this.summaryData = null;
      this.summaryError = null;
      return;
    }

    const requestId = ++this.currentSummaryRequestId;
    this.isLoadingSummary = true;
    this.summaryError = null;

    try {
      const data = await fetchFn(this.shop.id, this.authToken);
      if (requestId === this.currentSummaryRequestId) {
        this.summaryData = data;
      }
    } catch (err) {
      if (requestId === this.currentSummaryRequestId) {
        const message =
          err instanceof Error ? err.message : 'Unable to load review summary.';
        this.summaryError = message;
      }
    } finally {
      if (requestId === this.currentSummaryRequestId) {
        this.isLoadingSummary = false;
      }
    }
  }
}

test('Stale summary protection: Shop A -> Shop B while summary loading is in progress does not apply stale summary', async () => {
  const originalFetch = globalThis.fetch;

  let resolveShopA;
  const shopAPromise = new Promise((resolve) => {
    resolveShopA = resolve;
  });

  globalThis.fetch = async (input) => {
    const url = input.toString();
    if (url.includes('shop-A')) {
      // Keep Shop A's response pending until explicitly resolved
      await shopAPromise;
      return {
        ok: true,
        status: 200,
        json: async () => ({
          shop_id: 'shop-A',
          status: 'available',
          summary: 'Summary for Shop A',
          positive_themes: [],
          negative_themes: [],
          review_count_analyzed: 5,
        }),
      };
    }
    // Immediate response for Shop B
    return {
      ok: true,
      status: 200,
      json: async () => ({
        shop_id: 'shop-B',
        status: 'available',
        summary: 'Summary for Shop B',
        positive_themes: [],
        negative_themes: [],
        review_count_analyzed: 4,
      }),
    };
  };

  try {
    const harness = new ShopDetailCardSummaryStateHarness({ id: 'shop-A' }, 'token-xyz');

    // 1. Start Shop A summary request
    const promiseA = harness.loadSummary(fetchShopReviewSummary);
    assert.strictEqual(harness.isLoadingSummary, true);

    // 2. Switch the test context to Shop B while Shop A is still pending
    harness.switchContext({ id: 'shop-B' });
    assert.strictEqual(harness.summaryData, null);

    // 3. Start Shop B summary request and wait for it to complete
    const promiseB = harness.loadSummary(fetchShopReviewSummary);
    await promiseB;

    // 4. Assert that Shop B's summary is active and its loading state is correct
    assert.strictEqual(harness.shop.id, 'shop-B');
    assert.strictEqual(harness.summaryData?.summary, 'Summary for Shop B');
    assert.strictEqual(harness.isLoadingSummary, false);
    assert.strictEqual(harness.summaryError, null);

    // 5. Now explicitly resolve Shop A
    resolveShopA();
    await promiseA;

    // 6. Assert that Shop A's late response did not overwrite Shop B's summary or loading/error state
    assert.strictEqual(harness.shop.id, 'shop-B');
    assert.strictEqual(harness.summaryData?.summary, 'Summary for Shop B');
    assert.strictEqual(harness.isLoadingSummary, false);
    assert.strictEqual(harness.summaryError, null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('Stale summary protection: failed stale summary request does not set error on newly selected shop', async () => {
  const originalFetch = globalThis.fetch;

  let resolveShopA;
  const shopAPromise = new Promise((resolve) => {
    resolveShopA = resolve;
  });

  globalThis.fetch = async (input) => {
    const url = input.toString();
    if (url.includes('shop-A')) {
      // Keep Shop A pending until explicitly resolved with an error response
      await shopAPromise;
      return {
        ok: false,
        status: 502,
        json: async () => ({ detail: 'AI review summarization is temporarily unavailable.' }),
      };
    }
    // Immediate response for Shop B
    return {
      ok: true,
      status: 200,
      json: async () => ({
        shop_id: 'shop-B',
        status: 'available',
        summary: 'Summary for Shop B',
        positive_themes: [],
        negative_themes: [],
        review_count_analyzed: 4,
      }),
    };
  };

  try {
    const harness = new ShopDetailCardSummaryStateHarness({ id: 'shop-A' }, 'token-xyz');

    // 1. Start Shop A summary request
    const promiseA = harness.loadSummary(fetchShopReviewSummary);
    assert.strictEqual(harness.isLoadingSummary, true);

    // 2. Switch context to Shop B while Shop A is pending
    harness.switchContext({ id: 'shop-B' });
    assert.strictEqual(harness.summaryData, null);

    // 3. Start Shop B summary request and await resolution
    const promiseB = harness.loadSummary(fetchShopReviewSummary);
    await promiseB;

    // 4. Assert Shop B's successful state
    assert.strictEqual(harness.shop.id, 'shop-B');
    assert.strictEqual(harness.summaryData?.summary, 'Summary for Shop B');
    assert.strictEqual(harness.isLoadingSummary, false);
    assert.strictEqual(harness.summaryError, null);

    // 5. Now resolve Shop A with the error response
    resolveShopA();
    await promiseA;

    // 6. Assert that Shop A's late failure does not populate Shop B's error state or overwrite Shop B's summary
    assert.strictEqual(harness.shop.id, 'shop-B');
    assert.strictEqual(harness.summaryData?.summary, 'Summary for Shop B');
    assert.strictEqual(harness.isLoadingSummary, false);
    assert.strictEqual(harness.summaryError, null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('Stale summary protection: auth token invalidation during in-flight summary request discards stale summary', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => {
    await new Promise((resolve) => setTimeout(resolve, 30));
    return {
      ok: true,
      status: 200,
      json: async () => ({
        shop_id: 'shop-A',
        status: 'available',
        summary: 'Summary for Shop A',
        positive_themes: [],
        negative_themes: [],
        review_count_analyzed: 5,
      }),
    };
  };

  try {
    const harness = new ShopDetailCardSummaryStateHarness({ id: 'shop-A' }, 'token-xyz');
    const promise = harness.loadSummary(fetchShopReviewSummary);

    // User logs out while request is in flight
    await new Promise((resolve) => setTimeout(resolve, 10));
    harness.switchContext(harness.shop, null);

    await promise;

    // Logged out context must have null summary data
    assert.strictEqual(harness.summaryData, null);
    assert.strictEqual(harness.authToken, null);
    assert.strictEqual(harness.isLoadingSummary, false);
  } finally {
    globalThis.fetch = originalFetch;
  }
});


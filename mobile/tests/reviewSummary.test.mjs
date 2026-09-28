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

test('Stale summary protection: switching shops ignores in-flight response from previous shop', async () => {
  const originalFetch = globalThis.fetch;
  let currentSummaryRequestId = 0;
  let renderedSummary = null;

  globalThis.fetch = async (input) => {
    const url = input.toString();
    if (url.includes('shop-A')) {
      // Simulate delayed response for Shop A
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
    }
    // Faster response for Shop B
    await new Promise((resolve) => setTimeout(resolve, 5));
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
    // 1. User selects Shop A
    const reqA = ++currentSummaryRequestId;
    const promiseA = fetchShopReviewSummary('shop-A', 'token').then((data) => {
      if (reqA === currentSummaryRequestId) {
        renderedSummary = data.summary;
      }
    });

    // 2. User immediately switches to Shop B before Shop A resolves
    await new Promise((resolve) => setTimeout(resolve, 10));
    const reqB = ++currentSummaryRequestId;
    const promiseB = fetchShopReviewSummary('shop-B', 'token').then((data) => {
      if (reqB === currentSummaryRequestId) {
        renderedSummary = data.summary;
      }
    });

    await Promise.all([promiseA, promiseB]);

    // Shop B summary must win; Shop A must be discarded
    assert.strictEqual(renderedSummary, 'Summary for Shop B');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

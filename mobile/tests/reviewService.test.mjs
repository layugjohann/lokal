import test from 'node:test';
import assert from 'node:assert';
import { fetchShopReviews } from '../src/services/reviewService.ts';

test('fetchShopReviews constructs request with auth token and returns data on success', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedHeaders = {};

  const mockReviewResponse = {
    shop_id: 'shop-123',
    average_rating: 4.8,
    total_reviews_count: 35,
    has_more: false,
    attributions: [
      {
        provider: 'google',
        display_name: 'Google Maps',
        source_url: 'https://maps.google.com/?cid=123',
        required_notice: 'Reviews provided by Google Maps',
      },
    ],
    reviews: [
      {
        id: 'google:places/p1/reviews/r1',
        source: 'google',
        rating: 5,
        text: 'Great coffee!',
        author: {
          display_name: 'Maria',
        },
      },
    ],
  };

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      status: 200,
      json: async () => mockReviewResponse,
    };
  };

  try {
    const result = await fetchShopReviews('shop-123', 'test-token-xyz');

    assert.deepStrictEqual(result, mockReviewResponse);
    assert.ok(requestedUrl.includes('/api/v1/shops/shop-123/reviews'));
    assert.strictEqual(requestedHeaders['Authorization'], 'Bearer test-token-xyz');
    assert.strictEqual(requestedHeaders['Accept'], 'application/json');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopReviews throws error when authToken is missing or whitespace', async () => {
  await assert.rejects(
    async () => {
      await fetchShopReviews('shop-123', '');
    },
    (err) => {
      assert.ok(err instanceof Error);
      assert.strictEqual(
        err.message,
        'Authentication token is required to fetch reviews.'
      );
      return true;
    }
  );

  await assert.rejects(
    async () => {
      await fetchShopReviews('shop-123', '   ');
    },
    (err) => {
      assert.ok(err instanceof Error);
      assert.strictEqual(
        err.message,
        'Authentication token is required to fetch reviews.'
      );
      return true;
    }
  );
});

test('fetchShopReviews throws descriptive error when backend fails with JSON detail', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => {
    return {
      ok: false,
      status: 404,
      json: async () => ({ detail: 'Coffee shop not found.' }),
    };
  };

  try {
    await assert.rejects(
      async () => {
        await fetchShopReviews('nonexistent-id', 'test-token');
      },
      (err) => {
        assert.ok(err instanceof Error);
        assert.strictEqual(err.message, 'Coffee shop not found.');
        assert.strictEqual(err.status, 404);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopReviews handles 502 Bad Gateway from external review provider failure', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => {
    return {
      ok: false,
      status: 502,
      json: async () => ({
        detail: 'External review provider temporarily unavailable.',
      }),
    };
  };

  try {
    await assert.rejects(
      async () => {
        await fetchShopReviews('shop-upstream-fail', 'test-token');
      },
      (err) => {
        assert.ok(err instanceof Error);
        assert.strictEqual(
          err.message,
          'External review provider temporarily unavailable.'
        );
        assert.strictEqual(err.status, 502);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchShopReviews fallback error when response is non-JSON', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => {
    return {
      ok: false,
      status: 500,
      json: async () => {
        throw new Error('Not JSON');
      },
    };
  };

  try {
    await assert.rejects(
      async () => {
        await fetchShopReviews('shop-error', 'test-token');
      },
      (err) => {
        assert.ok(err instanceof Error);
        assert.strictEqual(err.message, 'Failed to fetch coffee shop reviews.');
        assert.strictEqual(err.status, 500);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

import test from 'node:test';
import assert from 'node:assert';
import {
  fetchShopReviews,
  fetchMyReview,
  createUserReview,
  updateUserReview,
  deleteUserReview,
} from '../src/services/reviewService.ts';

test('fetchShopReviews constructs request with auth token and returns data on success', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedHeaders = {};

  const mockReviewResponse = {
    shop_id: 'shop-123',
    average_rating: 4.8,
    total_reviews_count: 35,
    lokal_average_rating: 5.0,
    lokal_reviews_count: 2,
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
        id: 'lokal:rev-1',
        source: 'lokal',
        rating: 5,
        text: 'Best espresso in town!',
        author: {
          display_name: 'Maria Santos',
        },
      },
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

// --- Tests for fetchMyReview ---

test('fetchMyReview returns review when user has reviewed shop', async () => {
  const originalFetch = globalThis.fetch;
  const mockReview = {
    id: 'lokal:rev-123',
    source: 'lokal',
    rating: 5,
    text: 'Loved it!',
    author: { display_name: 'Elena' },
  };

  globalThis.fetch = async (input, init) => {
    assert.ok(input.toString().includes('/api/v1/shops/shop-123/reviews/mine'));
    assert.strictEqual(init?.method, 'GET');
    return {
      ok: true,
      status: 200,
      json: async () => mockReview,
    };
  };

  try {
    const result = await fetchMyReview('shop-123', 'token-abc');
    assert.deepStrictEqual(result, mockReview);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchMyReview returns null on 404 when unreviewed', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => ({
    ok: false,
    status: 404,
    json: async () => ({ detail: 'You have not reviewed this coffee shop.' }),
  });

  try {
    const result = await fetchMyReview('shop-123', 'token-abc');
    assert.strictEqual(result, null);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

// --- Tests for createUserReview ---

test('createUserReview posts payload and returns created review', async () => {
  const originalFetch = globalThis.fetch;
  let postedBody = null;

  globalThis.fetch = async (input, init) => {
    assert.ok(input.toString().includes('/api/v1/shops/shop-123/reviews'));
    assert.strictEqual(init?.method, 'POST');
    assert.strictEqual(init?.headers?.['Content-Type'], 'application/json');
    postedBody = JSON.parse(init?.body);
    return {
      ok: true,
      status: 201,
      json: async () => ({
        id: 'lokal:new-rev',
        source: 'lokal',
        rating: postedBody.rating,
        text: postedBody.content,
        author: { display_name: 'Juan Cruz' },
      }),
    };
  };

  try {
    const result = await createUserReview(
      'shop-123',
      { rating: 5, content: 'Great brew!' },
      'token-abc'
    );
    assert.strictEqual(result.rating, 5);
    assert.strictEqual(result.text, 'Great brew!');
    assert.deepStrictEqual(postedBody, { rating: 5, content: 'Great brew!' });
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('createUserReview throws on conflict 409', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => ({
    ok: false,
    status: 409,
    json: async () => ({ detail: 'You have already reviewed this coffee shop.' }),
  });

  try {
    await assert.rejects(
      async () => {
        await createUserReview('shop-123', { rating: 5 }, 'token-abc');
      },
      (err) => {
        assert.ok(err instanceof Error);
        assert.strictEqual(err.message, 'You have already reviewed this coffee shop.');
        assert.strictEqual(err.status, 409);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

// --- Tests for updateUserReview ---

test('updateUserReview patches review and returns updated review', async () => {
  const originalFetch = globalThis.fetch;
  let patchedBody = null;

  globalThis.fetch = async (input, init) => {
    assert.ok(input.toString().includes('/api/v1/shops/shop-123/reviews/mine'));
    assert.strictEqual(init?.method, 'PATCH');
    patchedBody = JSON.parse(init?.body);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        id: 'lokal:rev-123',
        source: 'lokal',
        rating: patchedBody.rating,
        is_edited: true,
        author: { display_name: 'Juan Cruz' },
      }),
    };
  };

  try {
    const result = await updateUserReview('shop-123', { rating: 4 }, 'token-abc');
    assert.strictEqual(result.rating, 4);
    assert.strictEqual(result.is_edited, true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

// --- Tests for deleteUserReview ---

test('deleteUserReview sends DELETE request and succeeds', async () => {
  const originalFetch = globalThis.fetch;
  let deleteMethod = '';

  globalThis.fetch = async (input, init) => {
    assert.ok(input.toString().includes('/api/v1/shops/shop-123/reviews/mine'));
    deleteMethod = init?.method;
    return {
      ok: true,
      status: 200,
      json: async () => ({ message: 'Review deleted successfully.' }),
    };
  };

  try {
    const result = await deleteUserReview('shop-123', 'token-abc');
    assert.strictEqual(deleteMethod, 'DELETE');
    assert.strictEqual(result.message, 'Review deleted successfully.');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

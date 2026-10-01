import test from 'node:test';
import assert from 'node:assert';
import {
  fetchFavoriteStatus,
  fetchUserFavorites,
  addFavorite,
  removeFavorite,
} from '../src/services/favoriteService.ts';

test('fetchFavoriteStatus constructs request with auth token and returns data on success', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedHeaders = {};

  const mockResponse = {
    shop_id: 'shop-123',
    is_favorite: true,
    favorited_at: '2026-09-30T01:00:00Z',
  };

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      status: 200,
      json: async () => mockResponse,
    };
  };

  try {
    const result = await fetchFavoriteStatus('shop-123', 'test-token');
    assert.strictEqual(requestedUrl, 'http://localhost:8000/api/v1/shops/shop-123/favorite');
    assert.strictEqual(requestedHeaders.Authorization, 'Bearer test-token');
    assert.strictEqual(result.is_favorite, true);
    assert.strictEqual(result.shop_id, 'shop-123');
    assert.strictEqual(result.favorited_at, '2026-09-30T01:00:00Z');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchFavoriteStatus throws error when authToken is missing or whitespace', async () => {
  await assert.rejects(
    async () => fetchFavoriteStatus('shop-123', ''),
    {
      name: 'Error',
      message: 'Authentication token is required to fetch favorite status.',
    }
  );

  await assert.rejects(
    async () => fetchFavoriteStatus('shop-123', '   '),
    {
      name: 'Error',
      message: 'Authentication token is required to fetch favorite status.',
    }
  );
});

test('fetchFavoriteStatus handles 401 Unauthorized', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: 'Invalid or expired authentication token.' }),
  });

  try {
    await assert.rejects(
      async () => fetchFavoriteStatus('shop-123', 'invalid-token'),
      (err) => {
        assert.strictEqual(err.message, 'Invalid or expired authentication token.');
        assert.strictEqual(err.status, 401);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchFavoriteStatus handles 404 Not Found', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 404,
    json: async () => ({ detail: 'Coffee shop not found or is not approved for public discovery.' }),
  });

  try {
    await assert.rejects(
      async () => fetchFavoriteStatus('shop-999', 'valid-token'),
      (err) => {
        assert.strictEqual(err.message, 'Coffee shop not found or is not approved for public discovery.');
        assert.strictEqual(err.status, 404);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchFavoriteStatus handles non-JSON error response fallback', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 500,
    json: async () => {
      throw new Error('Non-JSON response');
    },
  });

  try {
    await assert.rejects(
      async () => fetchFavoriteStatus('shop-123', 'valid-token'),
      (err) => {
        assert.strictEqual(err.message, 'Failed to fetch favorite status.');
        assert.strictEqual(err.status, 500);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('addFavorite constructs POST request and returns created favorite status', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedMethod = '';
  let requestedHeaders = {};

  const mockResponse = {
    shop_id: 'shop-123',
    is_favorite: true,
    favorited_at: '2026-09-30T02:00:00Z',
  };

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedMethod = init?.method || '';
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      status: 201,
      json: async () => mockResponse,
    };
  };

  try {
    const result = await addFavorite('shop-123', 'test-token');
    assert.strictEqual(requestedUrl, 'http://localhost:8000/api/v1/shops/shop-123/favorite');
    assert.strictEqual(requestedMethod, 'POST');
    assert.strictEqual(requestedHeaders.Authorization, 'Bearer test-token');
    assert.strictEqual(result.is_favorite, true);
    assert.strictEqual(result.shop_id, 'shop-123');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('addFavorite handles 409 Conflict when already favorited', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 409,
    json: async () => ({ detail: 'You have already favorited this coffee shop.' }),
  });

  try {
    await assert.rejects(
      async () => addFavorite('shop-123', 'valid-token'),
      (err) => {
        assert.strictEqual(err.message, 'You have already favorited this coffee shop.');
        assert.strictEqual(err.status, 409);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('addFavorite handles 400 Bad Request when shop is not approved', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 400,
    json: async () => ({ detail: 'Cannot favorite a coffee shop that is not approved for public discovery.' }),
  });

  try {
    await assert.rejects(
      async () => addFavorite('shop-123', 'valid-token'),
      (err) => {
        assert.strictEqual(err.message, 'Cannot favorite a coffee shop that is not approved for public discovery.');
        assert.strictEqual(err.status, 400);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('removeFavorite constructs DELETE request and succeeds', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedMethod = '';
  let requestedHeaders = {};

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedMethod = init?.method || '';
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      status: 200,
      json: async () => ({ message: 'Coffee shop removed from favorites.' }),
    };
  };

  try {
    await removeFavorite('shop-123', 'test-token');
    assert.strictEqual(requestedUrl, 'http://localhost:8000/api/v1/shops/shop-123/favorite');
    assert.strictEqual(requestedMethod, 'DELETE');
    assert.strictEqual(requestedHeaders.Authorization, 'Bearer test-token');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('removeFavorite handles 404 Not Found when shop is not in favorites', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 404,
    json: async () => ({ detail: 'Coffee shop is not in your favorites.' }),
  });

  try {
    await assert.rejects(
      async () => removeFavorite('shop-123', 'valid-token'),
      (err) => {
        assert.strictEqual(err.message, 'Coffee shop is not in your favorites.');
        assert.strictEqual(err.status, 404);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

// ============================================================================
// fetchUserFavorites Tests (Issue #39)
// ============================================================================

test('fetchUserFavorites constructs request with auth token and returns data on success', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedHeaders = {};

  const mockResponse = [
    {
      id: 'shop-1',
      name: 'Coffee Central',
      address: '123 Main St',
      latitude: 14.5995,
      longitude: 120.9842,
      rating: 4.8,
      google_place_id: 'place-1',
      favorited_at: '2026-10-01T10:00:00Z',
    },
  ];

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      status: 200,
      json: async () => mockResponse,
    };
  };

  try {
    const result = await fetchUserFavorites('test-token');
    assert.strictEqual(requestedUrl, 'http://localhost:8000/api/v1/favorites');
    assert.strictEqual(requestedHeaders.Authorization, 'Bearer test-token');
    assert.strictEqual(result.length, 1);
    assert.strictEqual(result[0].id, 'shop-1');
    assert.strictEqual(result[0].name, 'Coffee Central');
    assert.strictEqual(result[0].favorited_at, '2026-10-01T10:00:00Z');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchUserFavorites throws error when authToken is missing or whitespace', async () => {
  await assert.rejects(
    async () => fetchUserFavorites(''),
    {
      name: 'Error',
      message: 'Authentication token is required to fetch favorites.',
    }
  );

  await assert.rejects(
    async () => fetchUserFavorites('   '),
    {
      name: 'Error',
      message: 'Authentication token is required to fetch favorites.',
    }
  );
});

test('fetchUserFavorites handles 401 Unauthorized', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: 'Could not validate credentials' }),
  });

  try {
    await assert.rejects(
      async () => fetchUserFavorites('expired-token'),
      (err) => {
        assert.strictEqual(err.message, 'Could not validate credentials');
        assert.strictEqual(err.status, 401);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchUserFavorites handles 500 server error', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 500,
    json: async () => ({ detail: 'A database error occurred while retrieving favorites.' }),
  });

  try {
    await assert.rejects(
      async () => fetchUserFavorites('valid-token'),
      (err) => {
        assert.strictEqual(err.message, 'A database error occurred while retrieving favorites.');
        assert.strictEqual(err.status, 500);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchUserFavorites fallback error when response is non-JSON', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 502,
    json: async () => {
      throw new Error('Not JSON');
    },
  });

  try {
    await assert.rejects(
      async () => fetchUserFavorites('valid-token'),
      (err) => {
        assert.strictEqual(err.message, 'Failed to fetch favorites.');
        assert.strictEqual(err.status, 502);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});


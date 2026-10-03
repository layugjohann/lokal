import test from 'node:test';
import assert from 'node:assert';
import { fetchPersonalizedRecommendations } from '../src/services/recommendationService.ts';

test('fetchPersonalizedRecommendations throws error when authToken is missing or whitespace', async () => {
  await assert.rejects(
    async () => {
      await fetchPersonalizedRecommendations({}, '');
    },
    {
      message: 'Authentication is required to view personalized recommendations.',
    }
  );

  await assert.rejects(
    async () => {
      await fetchPersonalizedRecommendations({}, '   ');
    },
    {
      message: 'Authentication is required to view personalized recommendations.',
    }
  );
});

test('fetchPersonalizedRecommendations constructs request with Authorization header and returns data', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedHeaders = {};

  const mockResponse = {
    status: 'personalized',
    message: null,
    recommendations: [
      {
        shop: {
          id: 'shop-1',
          name: 'Single Origin Cafe',
          address: '123 Coffee Lane',
          latitude: 14.55,
          longitude: 121.02,
          rating: 4.8,
          distance_meters: 350,
        },
        explanation: 'Recommended because you appreciate fruity pour-overs.',
      },
    ],
    total_candidates_evaluated: 15,
  };

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      json: async () => mockResponse,
    };
  };

  try {
    const result = await fetchPersonalizedRecommendations(
      {
        latitude: 14.5547,
        longitude: 121.0244,
        radius: 3000,
        limit: 5,
      },
      'valid-auth-jwt'
    );

    assert.deepStrictEqual(result, mockResponse);
    assert.ok(requestedUrl.includes('/api/v1/shops/recommendations/personalized'));
    assert.ok(requestedUrl.includes('latitude=14.5547'));
    assert.ok(requestedUrl.includes('longitude=121.0244'));
    assert.ok(requestedUrl.includes('radius=3000'));
    assert.ok(requestedUrl.includes('limit=5'));
    assert.strictEqual(requestedHeaders['Authorization'], 'Bearer valid-auth-jwt');
    assert.strictEqual(requestedHeaders['Accept'], 'application/json');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchPersonalizedRecommendations omits coordinates query params when null or undefined', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';

  globalThis.fetch = async (input) => {
    requestedUrl = input.toString();
    return {
      ok: true,
      json: async () => ({
        status: 'personalized',
        recommendations: [],
        total_candidates_evaluated: 0,
      }),
    };
  };

  try {
    await fetchPersonalizedRecommendations({}, 'valid-jwt');
    assert.ok(!requestedUrl.includes('latitude='));
    assert.ok(!requestedUrl.includes('longitude='));
    assert.ok(!requestedUrl.includes('radius='));
    assert.ok(!requestedUrl.includes('limit='));
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchPersonalizedRecommendations throws descriptive error when backend fails with detail', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => {
    return {
      ok: false,
      json: async () => ({ detail: 'Invalid or expired token.' }),
    };
  };

  try {
    await assert.rejects(
      async () => {
        await fetchPersonalizedRecommendations({}, 'expired-jwt');
      },
      {
        message: 'Invalid or expired token.',
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchPersonalizedRecommendations fallback error when non-JSON error response is returned', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => {
    return {
      ok: false,
      json: async () => {
        throw new Error('Not JSON');
      },
    };
  };

  try {
    await assert.rejects(
      async () => {
        await fetchPersonalizedRecommendations({}, 'test-jwt');
      },
      {
        message: 'Failed to fetch personalized recommendations.',
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

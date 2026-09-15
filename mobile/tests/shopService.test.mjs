import test from 'node:test';
import assert from 'node:assert';
import {
  formatDistance,
  formatRating,
  getApiBaseUrl,
  fetchNearbyShops,
} from '../src/services/shopService.ts';

test('formatDistance formats meters properly', () => {
  assert.strictEqual(formatDistance(undefined), '');
  assert.strictEqual(formatDistance(null), '');
  assert.strictEqual(formatDistance(NaN), '');
  assert.strictEqual(formatDistance(0), '0 m');
  assert.strictEqual(formatDistance(120), '120 m');
  assert.strictEqual(formatDistance(999), '999 m');
  assert.strictEqual(formatDistance(1000), '1.0 km');
  assert.strictEqual(formatDistance(1500), '1.5 km');
  assert.strictEqual(formatDistance(12345), '12.3 km');
});

test('formatRating formats rating properly', () => {
  assert.strictEqual(formatRating(undefined), 'No rating');
  assert.strictEqual(formatRating(null), 'No rating');
  assert.strictEqual(formatRating(NaN), 'No rating');
  assert.strictEqual(formatRating(5), '★ 5.0');
  assert.strictEqual(formatRating(4.75), '★ 4.8');
  assert.strictEqual(formatRating(0), '★ 0.0');
});

test('getApiBaseUrl returns default or env override', () => {
  const originalEnv = process.env.EXPO_PUBLIC_API_URL;
  try {
    delete process.env.EXPO_PUBLIC_API_URL;
    assert.strictEqual(getApiBaseUrl(), 'http://localhost:8000');

    process.env.EXPO_PUBLIC_API_URL = 'https://api.lokal.ph';
    assert.strictEqual(getApiBaseUrl(), 'https://api.lokal.ph');
  } finally {
    if (originalEnv === undefined) {
      delete process.env.EXPO_PUBLIC_API_URL;
    } else {
      process.env.EXPO_PUBLIC_API_URL = originalEnv;
    }
  }
});

test('fetchNearbyShops constructs request and returns data on success', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedHeaders = {};

  const mockShops = [
    {
      id: 'shop-1',
      name: 'Kape Lokal',
      address: '123 St',
      latitude: 14.5,
      longitude: 121.0,
      rating: 4.8,
      distance_meters: 250,
    },
  ];

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      json: async () => mockShops,
    };
  };

  try {
    const result = await fetchNearbyShops(
      {
        latitude: 14.5995,
        longitude: 120.9842,
        radius: 3000,
        limit: 10,
        offset: 0,
      },
      'test-auth-jwt'
    );

    assert.deepStrictEqual(result, mockShops);
    assert.ok(requestedUrl.includes('/api/v1/shops/nearby'));
    assert.ok(requestedUrl.includes('latitude=14.5995'));
    assert.ok(requestedUrl.includes('longitude=120.9842'));
    assert.ok(requestedUrl.includes('radius=3000'));
    assert.ok(requestedUrl.includes('limit=10'));
    assert.ok(requestedUrl.includes('offset=0'));
    assert.strictEqual(requestedHeaders['Authorization'], 'Bearer test-auth-jwt');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchNearbyShops does not set Authorization header when authToken is not provided', async () => {
  const originalFetch = globalThis.fetch;
  let requestedHeaders = {};

  globalThis.fetch = async (input, init) => {
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      json: async () => [],
    };
  };

  try {
    await fetchNearbyShops({ latitude: 14.5, longitude: 121.0 });
    assert.strictEqual(requestedHeaders['Authorization'], undefined);
  } finally {
    globalThis.fetch = originalFetch;
  }
});


test('fetchNearbyShops throws descriptive error when backend fails with detail', async () => {
  const originalFetch = globalThis.fetch;

  globalThis.fetch = async () => {
    return {
      ok: false,
      json: async () => ({ detail: 'Database connection failed.' }),
    };
  };

  try {
    await assert.rejects(
      async () => {
        await fetchNearbyShops({ latitude: 14.5, longitude: 121.0 });
      },
      {
        message: 'Database connection failed.',
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchNearbyShops fallback error when response is not json', async () => {
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
        await fetchNearbyShops({ latitude: 14.5, longitude: 121.0 });
      },
      {
        message: 'Failed to fetch nearby coffee shops.',
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

import test from 'node:test';
import assert from 'node:assert';
import {
  fetchCommunityFeed,
  formatShareReviewExcerpt,
  formatShareReviewMessage,
  formatShareShopMessage,
  shareCommunityReview,
  shareShop,
  setShareFn,
} from '../src/services/communityService.ts';

test('fetchCommunityFeed throws error when authToken is missing or whitespace', async () => {
  await assert.rejects(
    async () => {
      await fetchCommunityFeed('');
    },
    {
      message: 'Authentication token is required to fetch community feed.',
    }
  );

  await assert.rejects(
    async () => {
      await fetchCommunityFeed('   ');
    },
    {
      message: 'Authentication token is required to fetch community feed.',
    }
  );
});

test('fetchCommunityFeed constructs GET request with auth headers and returns data', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedHeaders = {};
  let requestedMethod = '';

  const mockResponse = {
    items: [
      {
        id: 'review-1',
        shop_id: 'shop-1',
        shop_name: 'Escolta Coffee',
        shop_address: 'Escolta St',
        author_name: 'Bob',
        rating: 5,
        content: 'Superb pour-over',
        created_at: '2026-10-07T00:00:00Z',
        updated_at: '2026-10-07T00:00:00Z',
        is_edited: false,
      },
    ],
    limit: 20,
    offset: 0,
    has_more: false,
  };

  globalThis.fetch = async (input, init) => {
    requestedUrl = input.toString();
    requestedMethod = init?.method || 'GET';
    requestedHeaders = init?.headers || {};
    return {
      ok: true,
      json: async () => mockResponse,
    };
  };

  try {
    const result = await fetchCommunityFeed('jwt-token-xyz', 20, 0);
    assert.deepStrictEqual(result, mockResponse);
    assert.strictEqual(requestedMethod, 'GET');
    assert.ok(requestedUrl.includes('/api/v1/community/feed?limit=20&offset=0'));
    assert.strictEqual(requestedHeaders.Authorization, 'Bearer jwt-token-xyz');
    assert.strictEqual(requestedHeaders.Accept, 'application/json');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchCommunityFeed throws descriptive error when backend fails with JSON detail', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 500,
    json: async () => ({ detail: 'Database query failed.' }),
  });

  try {
    await assert.rejects(
      async () => {
        await fetchCommunityFeed('valid-token');
      },
      {
        message: 'Database query failed.',
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('fetchCommunityFeed fallback error when response is non-JSON', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 502,
    json: async () => {
      throw new Error('Bad gateway html');
    },
  });

  try {
    await assert.rejects(
      async () => {
        await fetchCommunityFeed('valid-token');
      },
      {
        message: 'Failed to fetch community feed.',
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('formatShareReviewExcerpt returns null for empty or whitespace content', () => {
  assert.strictEqual(formatShareReviewExcerpt(null), null);
  assert.strictEqual(formatShareReviewExcerpt(undefined), null);
  assert.strictEqual(formatShareReviewExcerpt(''), null);
  assert.strictEqual(formatShareReviewExcerpt('   '), null);
});

test('formatShareReviewExcerpt preserves short text and truncates text exceeding 180 chars with ellipsis', () => {
  const shortText = 'Incredible pour-over and friendly baristas!';
  assert.strictEqual(formatShareReviewExcerpt(shortText, 180), shortText);

  const longText = 'A'.repeat(250);
  const excerpt = formatShareReviewExcerpt(longText, 180);
  assert.ok(excerpt !== null);
  assert.ok(excerpt.length <= 180);
  assert.ok(excerpt.endsWith('...'));
  assert.strictEqual(excerpt.length, 180);
});

test('formatShareReviewMessage creates sanitized message with bounded excerpt and zero IDs', () => {
  const mockReview = {
    id: 'rev-uuid-12345',
    shop_id: 'shop-uuid-67890',
    shop_name: 'Kape Escolta',
    shop_address: '123 Escolta St',
    author_name: 'Maria Clara',
    rating: 5,
    content: 'The cold brew here is absolute perfection.',
    created_at: '2026-10-07T00:00:00Z',
    updated_at: null,
    is_edited: false,
  };

  const message = formatShareReviewMessage(mockReview);

  // Must contain public metadata
  assert.ok(message.includes('☕ Kape Escolta'));
  assert.ok(message.includes('Rating: ★ 5/5'));
  assert.ok(message.includes('"The cold brew here is absolute perfection."'));
  assert.ok(message.includes('— Shared by Maria Clara on LOKAL'));

  // Must NOT contain internal IDs
  assert.ok(!message.includes('rev-uuid-12345'));
  assert.ok(!message.includes('shop-uuid-67890'));
});

test('formatShareReviewMessage formats rating-only review when content is missing', () => {
  const mockReview = {
    id: 'rev-uuid-123',
    shop_id: 'shop-uuid-456',
    shop_name: 'Binondo Brews',
    shop_address: 'Ongpin St',
    author_name: 'Juan Dela Cruz',
    rating: 4,
    content: null,
    created_at: '2026-10-07T00:00:00Z',
    updated_at: null,
    is_edited: false,
  };

  const message = formatShareReviewMessage(mockReview);
  assert.strictEqual(message, '☕ Binondo Brews - Rated ★ 4/5 by Juan Dela Cruz on LOKAL');
  assert.ok(!message.includes('rev-uuid-123'));
});

test('formatShareShopMessage creates sanitized message with zero IDs', () => {
  const shop = {
    id: 'shop-id-private',
    name: 'Intramuros Roasters',
    address: 'General Luna St',
    rating: 4.8,
  };

  const message = formatShareShopMessage(shop);
  assert.ok(message.includes('☕ Intramuros Roasters'));
  assert.ok(message.includes('📍 General Luna St'));
  assert.ok(message.includes('★ 4.8'));
  assert.ok(message.includes('Discovered on LOKAL'));
  assert.ok(!message.includes('shop-id-private'));
});

test('shareCommunityReview calls shareFn and handles success, dismissal, and failure gracefully', async () => {
  const mockReview = {
    id: 'r1',
    shop_id: 's1',
    shop_name: 'Cafe Alpha',
    shop_address: null,
    author_name: 'User 1',
    rating: 5,
    content: 'Loved it!',
    created_at: '2026-10-07T00:00:00Z',
    updated_at: null,
    is_edited: false,
  };

  let capturedPayload = null;
  // 1. Successful share
  const successShareFn = async (payload) => {
    capturedPayload = payload;
    return { action: 'sharedAction' };
  };

  const successResult = await shareCommunityReview(mockReview, successShareFn);
  assert.strictEqual(successResult, true);
  assert.ok(capturedPayload.message.includes('Cafe Alpha'));
  assert.strictEqual(capturedPayload.title, 'Cafe Alpha on LOKAL');

  // 2. Dismissed share
  const dismissedShareFn = async () => ({ action: 'dismissedAction' });
  const dismissedResult = await shareCommunityReview(mockReview, dismissedShareFn);
  assert.strictEqual(dismissedResult, false);

  // 3. Error throwing share (e.g. platform unavailable)
  const throwingShareFn = async () => {
    throw new Error('Native share unavailable');
  };
  const errorResult = await shareCommunityReview(mockReview, throwingShareFn);
  assert.strictEqual(errorResult, false);
});

test('shareShop calls shareFn and handles success and errors gracefully', async () => {
  const shop = {
    name: 'Cafe Beta',
    address: 'Main St',
    rating: 4.5,
  };

  let captured = null;
  const successShareFn = async (payload) => {
    captured = payload;
    return { action: 'sharedAction' };
  };

  const ok = await shareShop(shop, successShareFn);
  assert.strictEqual(ok, true);
  assert.ok(captured.message.includes('Cafe Beta'));
  assert.strictEqual(captured.title, 'Cafe Beta on LOKAL');

  // Error case
  const failingShareFn = async () => {
    throw new Error('Share error');
  };
  const fail = await shareShop(shop, failingShareFn);
  assert.strictEqual(fail, false);
});

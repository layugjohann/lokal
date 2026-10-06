import test from 'node:test';
import assert from 'node:assert';

/**
 * Harness modeling CommunityFeedView's internal shop selection state,
 * monotonic request sequencing, stale-response discarding, and modal dismissal.
 */
class CommunityFeedShopSelectionHarness {
  constructor(initialAuthToken = 'token-123') {
    this.authToken = initialAuthToken;
    this.selectedShop = null;
    this.loadingShopId = null;
    this.shopRequestId = 0;
  }

  // Simulates modal dismissal or auth token reset (!visible || !authToken)
  onDismissOrUnauth() {
    this.shopRequestId += 1;
    this.selectedShop = null;
    this.loadingShopId = null;
  }

  // Models handleOpenShop in CommunityFeedView.tsx
  async openShop(feedItem, fetchFn) {
    const currentRequestId = ++this.shopRequestId;
    this.loadingShopId = feedItem.shop_id;

    try {
      const fullShop = await fetchFn(feedItem.shop_id, this.authToken);
      if (this.shopRequestId !== currentRequestId) {
        return;
      }
      this.selectedShop = fullShop;
    } catch {
      if (this.shopRequestId !== currentRequestId) {
        return;
      }
      const fallbackShop = {
        id: feedItem.shop_id,
        name: feedItem.shop_name,
        address: feedItem.shop_address,
        latitude: 0,
        longitude: 0,
        rating: feedItem.rating,
        google_place_id: null,
        created_at: feedItem.created_at,
        updated_at: feedItem.updated_at || feedItem.created_at,
        distance_meters: Number.NaN,
      };
      this.selectedShop = fallbackShop;
    } finally {
      if (this.shopRequestId === currentRequestId) {
        this.loadingShopId = null;
      }
    }
  }
}

test('CommunityFeedView shop selection succeeds normally for single request', async () => {
  const harness = new CommunityFeedShopSelectionHarness();
  const feedItem = {
    id: 'review-1',
    shop_id: 'shop-1',
    shop_name: 'Origin Coffee',
    shop_address: '123 Main St',
    author_name: 'Alice',
    rating: 5,
    content: 'Great pour over',
    created_at: '2026-10-07T00:00:00Z',
    updated_at: null,
    is_edited: false,
  };

  const mockShop = {
    id: 'shop-1',
    name: 'Origin Coffee',
    address: '123 Main St',
    latitude: 14.5,
    longitude: 121.0,
    rating: 4.8,
    google_place_id: null,
    created_at: '2026-10-01T00:00:00Z',
    updated_at: '2026-10-01T00:00:00Z',
    distance_meters: 150,
  };

  await harness.openShop(feedItem, async () => mockShop);

  assert.deepStrictEqual(harness.selectedShop, mockShop);
  assert.strictEqual(harness.loadingShopId, null);
});

test('CommunityFeedView discards older shop selection resolving after newer selection', async () => {
  const harness = new CommunityFeedShopSelectionHarness();
  const item1 = {
    id: 'rev-1',
    shop_id: 'shop-1',
    shop_name: 'Shop One',
    shop_address: 'Address 1',
    author_name: 'Alice',
    rating: 5,
    content: 'Nice',
    created_at: '2026-10-07T00:00:00Z',
    updated_at: null,
    is_edited: false,
  };
  const item2 = {
    id: 'rev-2',
    shop_id: 'shop-2',
    shop_name: 'Shop Two',
    shop_address: 'Address 2',
    author_name: 'Bob',
    rating: 4,
    content: 'Cozy',
    created_at: '2026-10-06T00:00:00Z',
    updated_at: null,
    is_edited: false,
  };

  let resolveShop1;
  let resolveShop2;

  const fetchShop1 = () =>
    new Promise((resolve) => {
      resolveShop1 = resolve;
    });

  const fetchShop2 = () =>
    new Promise((resolve) => {
      resolveShop2 = resolve;
    });

  // User clicks item 1, then quickly clicks item 2
  const p1 = harness.openShop(item1, fetchShop1);
  assert.strictEqual(harness.loadingShopId, 'shop-1');

  const p2 = harness.openShop(item2, fetchShop2);
  assert.strictEqual(harness.loadingShopId, 'shop-2');

  // Shop 2 resolves first
  resolveShop2({ id: 'shop-2', name: 'Shop Two' });
  await p2;

  assert.strictEqual(harness.selectedShop?.id, 'shop-2');
  assert.strictEqual(harness.loadingShopId, null);

  // Shop 1 resolves late
  resolveShop1({ id: 'shop-1', name: 'Shop One' });
  await p1;

  // Stale shop 1 must not overwrite shop 2
  assert.strictEqual(harness.selectedShop?.id, 'shop-2');
  assert.strictEqual(harness.loadingShopId, null);
});

test('CommunityFeedView ignores late shop response after modal dismissal', async () => {
  const harness = new CommunityFeedShopSelectionHarness();
  const item1 = {
    id: 'rev-1',
    shop_id: 'shop-1',
    shop_name: 'Shop One',
    shop_address: 'Address 1',
    author_name: 'Alice',
    rating: 5,
    content: 'Nice',
    created_at: '2026-10-07T00:00:00Z',
    updated_at: null,
    is_edited: false,
  };

  let resolveShop1;
  const fetchShop1 = () =>
    new Promise((resolve) => {
      resolveShop1 = resolve;
    });

  const p1 = harness.openShop(item1, fetchShop1);
  assert.strictEqual(harness.loadingShopId, 'shop-1');

  // Modal is closed while fetch is in-flight
  harness.onDismissOrUnauth();
  assert.strictEqual(harness.selectedShop, null);
  assert.strictEqual(harness.loadingShopId, null);

  // Late resolution must not repopulate selectedShop
  resolveShop1({ id: 'shop-1', name: 'Shop One' });
  await p1;

  assert.strictEqual(harness.selectedShop, null);
  assert.strictEqual(harness.loadingShopId, null);
});

test('CommunityFeedView ignores stale error and does not overwrite newer selection or clear loading', async () => {
  const harness = new CommunityFeedShopSelectionHarness();
  const item1 = {
    id: 'rev-1',
    shop_id: 'shop-1',
    shop_name: 'Shop One',
    shop_address: 'Address 1',
    author_name: 'Alice',
    rating: 5,
    content: 'Nice',
    created_at: '2026-10-07T00:00:00Z',
    updated_at: null,
    is_edited: false,
  };
  const item2 = {
    id: 'rev-2',
    shop_id: 'shop-2',
    shop_name: 'Shop Two',
    shop_address: 'Address 2',
    author_name: 'Bob',
    rating: 4,
    content: 'Cozy',
    created_at: '2026-10-06T00:00:00Z',
    updated_at: null,
    is_edited: false,
  };

  let rejectShop1;
  let resolveShop2;

  const fetchShop1 = () =>
    new Promise((_, reject) => {
      rejectShop1 = reject;
    });

  const fetchShop2 = () =>
    new Promise((resolve) => {
      resolveShop2 = resolve;
    });

  const p1 = harness.openShop(item1, fetchShop1);
  const p2 = harness.openShop(item2, fetchShop2);

  assert.strictEqual(harness.loadingShopId, 'shop-2');

  // Shop 1 fails while shop 2 is still in-flight
  rejectShop1(new Error('Network error on shop 1'));
  await p1;

  // Stale error must NOT set fallback for shop 1 and must NOT clear loadingShopId for shop 2
  assert.strictEqual(harness.selectedShop, null);
  assert.strictEqual(harness.loadingShopId, 'shop-2');

  // Shop 2 succeeds
  resolveShop2({ id: 'shop-2', name: 'Shop Two' });
  await p2;

  assert.strictEqual(harness.selectedShop?.id, 'shop-2');
  assert.strictEqual(harness.loadingShopId, null);
});

test('CommunityFeedView applies fallback shop on error when request is current', async () => {
  const harness = new CommunityFeedShopSelectionHarness();
  const item1 = {
    id: 'rev-1',
    shop_id: 'shop-fallback',
    shop_name: 'Fallback Roastery',
    shop_address: 'Fallback St',
    author_name: 'Charlie',
    rating: 4,
    content: 'Good brew',
    created_at: '2026-10-07T00:00:00Z',
    updated_at: null,
    is_edited: false,
  };

  await harness.openShop(item1, async () => {
    throw new Error('500 Internal Server Error');
  });

  assert.notStrictEqual(harness.selectedShop, null);
  assert.strictEqual(harness.selectedShop?.id, 'shop-fallback');
  assert.strictEqual(harness.selectedShop?.name, 'Fallback Roastery');
  assert.strictEqual(harness.loadingShopId, null);
});

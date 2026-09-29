import test from 'node:test';
import assert from 'node:assert';

class ShopDetailCardFavoriteStateHarness {
  constructor(initialShop, initialAuthToken = 'mock-token') {
    this.shop = initialShop;
    this.authToken = initialAuthToken;

    this.isFavorite = false;
    this.isLoadingFavorite = false;
    this.isMutatingFavorite = false;
    this.favoriteError = null;

    this.currentFavoriteRequestId = 0;
    this.currentFavoriteMutationId = 0;
  }

  switchContext(newShop, newAuthToken = this.authToken) {
    this.currentFavoriteRequestId += 1;
    this.currentFavoriteMutationId += 1;

    this.shop = newShop;
    this.authToken = newAuthToken;

    this.currentFavoriteRequestId += 1;
    this.currentFavoriteMutationId += 1;
    this.isFavorite = false;
    this.isMutatingFavorite = false;
    this.favoriteError = null;
    if (!this.authToken) {
      this.isLoadingFavorite = false;
    } else {
      this.isLoadingFavorite = true;
    }
  }

  async loadFavorite(fetchFn) {
    if (!this.authToken) {
      this.isLoadingFavorite = false;
      this.isFavorite = false;
      this.favoriteError = null;
      return;
    }

    const requestId = ++this.currentFavoriteRequestId;
    this.isLoadingFavorite = true;
    this.favoriteError = null;

    try {
      const data = await fetchFn(this.shop.id, this.authToken);
      if (requestId === this.currentFavoriteRequestId) {
        this.isFavorite = data.is_favorite;
      }
    } catch (err) {
      if (requestId === this.currentFavoriteRequestId) {
        const message = err instanceof Error ? err.message : 'Unable to load favorite status.';
        this.favoriteError = message;
      }
    } finally {
      if (requestId === this.currentFavoriteRequestId) {
        this.isLoadingFavorite = false;
      }
    }
  }

  async toggleFavorite(mutateFn) {
    if (!this.authToken) {
      this.favoriteError = 'Please sign in to favorite this coffee shop.';
      return;
    }
    if (this.isLoadingFavorite || this.isMutatingFavorite) {
      return;
    }

    const mutationId = ++this.currentFavoriteMutationId;
    const activeShopId = this.shop.id;
    const activeToken = this.authToken;
    const previousFavorite = this.isFavorite;

    // Optimistically toggle state
    this.isFavorite = !previousFavorite;
    this.isMutatingFavorite = true;
    this.favoriteError = null;

    try {
      await mutateFn(activeShopId, !previousFavorite, activeToken);
      if (
        mutationId === this.currentFavoriteMutationId &&
        activeShopId === this.shop.id &&
        activeToken === this.authToken
      ) {
        this.isFavorite = !previousFavorite;
      }
    } catch (err) {
      if (
        mutationId === this.currentFavoriteMutationId &&
        activeShopId === this.shop.id &&
        activeToken === this.authToken
      ) {
        // Rollback state on failure
        this.isFavorite = previousFavorite;
        const message =
          err instanceof Error
            ? err.message
            : previousFavorite
            ? 'Failed to remove favorite.'
            : 'Failed to favorite coffee shop.';
        this.favoriteError = message;
      }
    } finally {
      if (
        mutationId === this.currentFavoriteMutationId &&
        activeShopId === this.shop.id &&
        activeToken === this.authToken
      ) {
        this.isMutatingFavorite = false;
      }
    }
  }
}

test('loadFavorite loads and updates isFavorite to true on success', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, 'token-1');

  await harness.loadFavorite(async (shopId) => {
    assert.strictEqual(shopId, 'shop-1');
    return { shop_id: 'shop-1', is_favorite: true, favorited_at: '2026-09-30T01:00:00Z' };
  });

  assert.strictEqual(harness.isFavorite, true);
  assert.strictEqual(harness.isLoadingFavorite, false);
  assert.strictEqual(harness.favoriteError, null);
});

test('loadFavorite for unauthenticated user resets isFavorite to false and does not fetch', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, null);

  let called = false;
  await harness.loadFavorite(async () => {
    called = true;
    return { shop_id: 'shop-1', is_favorite: true, favorited_at: null };
  });

  assert.strictEqual(called, false);
  assert.strictEqual(harness.isFavorite, false);
  assert.strictEqual(harness.isLoadingFavorite, false);
});

test('Stale loadFavorite protection: Shop A -> Shop B while load is in flight ignores Shop A response', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-A', name: 'Shop A' }, 'token-1');

  let resolveShopA;
  const shopAPromise = new Promise((resolve) => {
    resolveShopA = resolve;
  });

  const loadPromiseA = harness.loadFavorite(() => shopAPromise);

  // Switch to Shop B while Shop A is still loading
  harness.switchContext({ id: 'shop-B', name: 'Shop B' });

  // Load Shop B
  const loadPromiseB = harness.loadFavorite(async () => ({
    shop_id: 'shop-B',
    is_favorite: false,
    favorited_at: null,
  }));

  await loadPromiseB;
  assert.strictEqual(harness.isFavorite, false);

  // Now resolve Shop A late with is_favorite: true
  resolveShopA({ shop_id: 'shop-A', is_favorite: true, favorited_at: '2026-09-30T01:00:00Z' });
  await loadPromiseA;

  // Harness must keep Shop B's false state, discarding Shop A's stale response
  assert.strictEqual(harness.isFavorite, false);
  assert.strictEqual(harness.shop.id, 'shop-B');
});

test('toggleFavorite performs optimistic update immediately and confirms on success', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, 'token-1');
  assert.strictEqual(harness.isFavorite, false);

  let mutateCalled = false;
  const togglePromise = harness.toggleFavorite(async (shopId, targetState) => {
    mutateCalled = true;
    assert.strictEqual(shopId, 'shop-1');
    assert.strictEqual(targetState, true);
  });

  // Optimistic update should take effect immediately
  assert.strictEqual(harness.isFavorite, true);
  assert.strictEqual(harness.isMutatingFavorite, true);

  await togglePromise;
  assert.strictEqual(mutateCalled, true);
  assert.strictEqual(harness.isFavorite, true);
  assert.strictEqual(harness.isMutatingFavorite, false);
});

test('toggleFavorite rolls back to previous state and sets error banner on mutation failure', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, 'token-1');
  harness.isFavorite = false;

  await harness.toggleFavorite(async () => {
    throw new Error('Network error favoriting shop');
  });

  // State must roll back to false
  assert.strictEqual(harness.isFavorite, false);
  assert.strictEqual(harness.isMutatingFavorite, false);
  assert.strictEqual(harness.favoriteError, 'Network error favoriting shop');
});

test('Stale toggleFavorite protection: Shop A -> Shop B while mutation is in flight ignores mutation result', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-A', name: 'Shop A' }, 'token-1');
  harness.isFavorite = false;

  let resolveMutationA;
  const mutationAPromise = new Promise((resolve) => {
    resolveMutationA = resolve;
  });

  const togglePromiseA = harness.toggleFavorite(() => mutationAPromise);
  assert.strictEqual(harness.isFavorite, true); // optimistically true for A

  // User rapidly navigates away to Shop B
  harness.switchContext({ id: 'shop-B', name: 'Shop B' });
  assert.strictEqual(harness.isFavorite, false); // reset for Shop B

  // Mutation for Shop A now resolves
  resolveMutationA();
  await togglePromiseA;

  // Shop B must not inherit Shop A's favorited state
  assert.strictEqual(harness.isFavorite, false);
  assert.strictEqual(harness.shop.id, 'shop-B');
});

test('Auth token invalidation during in-flight load discards response and stays unauthenticated', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, 'token-1');

  let resolveLoad;
  const loadPromise = new Promise((resolve) => {
    resolveLoad = resolve;
  });

  const operation = harness.loadFavorite(() => loadPromise);

  // User logs out while request was in-flight
  harness.switchContext({ id: 'shop-1', name: 'Shop 1' }, null);

  resolveLoad({ shop_id: 'shop-1', is_favorite: true, favorited_at: '2026-09-30T01:00:00Z' });
  await operation;

  assert.strictEqual(harness.isFavorite, false);
  assert.strictEqual(harness.authToken, null);
});

test('Unauthenticated user attempting to toggle favorite sets sign-in notice and does not mutate', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, null);

  let called = false;
  await harness.toggleFavorite(async () => {
    called = true;
  });

  assert.strictEqual(called, false);
  assert.strictEqual(harness.isFavorite, false);
  assert.strictEqual(harness.favoriteError, 'Please sign in to favorite this coffee shop.');
});

test('toggleFavorite returns early and does not mutate while favorite status is still loading', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, 'token-1');
  harness.isLoadingFavorite = true;

  let called = false;
  await harness.toggleFavorite(async () => {
    called = true;
  });

  assert.strictEqual(called, false);
  assert.strictEqual(harness.isFavorite, false);
  assert.strictEqual(harness.isMutatingFavorite, false);
});


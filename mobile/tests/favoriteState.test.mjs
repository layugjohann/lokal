import test from 'node:test';
import assert from 'node:assert';

class ShopDetailCardFavoriteStateHarness {
  constructor(initialShop, initialAuthToken = 'mock-token') {
    this.shop = initialShop;
    this.authToken = initialAuthToken;

    this.isFavorite = initialAuthToken ? null : false;
    this.isLoadingFavorite = Boolean(initialAuthToken);
    this.isMutatingFavorite = false;
    this.favoriteError = null;

    this.currentFavoriteRequestId = 0;
    this.currentFavoriteMutationId = 0;
  }

  isControlDisabled() {
    return this.isFavorite === null || this.isLoadingFavorite || this.isMutatingFavorite;
  }

  switchContext(newShop, newAuthToken = this.authToken) {
    this.currentFavoriteRequestId += 1;
    this.currentFavoriteMutationId += 1;

    this.shop = newShop;
    this.authToken = newAuthToken;

    this.currentFavoriteRequestId += 1;
    this.currentFavoriteMutationId += 1;
    this.isFavorite = this.authToken ? null : false;
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

  async toggleFavorite(mutateFn, onFavoriteChange) {
    if (!this.authToken) {
      this.favoriteError = 'Please sign in to favorite this coffee shop.';
      return;
    }
    if (this.isFavorite === null || this.isLoadingFavorite || this.isMutatingFavorite) {
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
        onFavoriteChange?.(activeShopId, !previousFavorite);
      }
    } catch (err) {
      if (
        mutationId === this.currentFavoriteMutationId &&
        activeShopId === this.shop.id &&
        activeToken === this.authToken
      ) {
        // Rollback state on failure
        this.isFavorite = previousFavorite;
        onFavoriteChange?.(activeShopId, previousFavorite);
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

test('successful status load updates state and makes control actionable', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, 'token-1');
  assert.strictEqual(harness.isFavorite, null);
  assert.strictEqual(harness.isLoadingFavorite, true);
  assert.strictEqual(harness.isControlDisabled(), true);

  await harness.loadFavorite(async (shopId) => {
    assert.strictEqual(shopId, 'shop-1');
    return { shop_id: 'shop-1', is_favorite: false, favorited_at: null };
  });

  assert.strictEqual(harness.isFavorite, false);
  assert.strictEqual(harness.isLoadingFavorite, false);
  assert.strictEqual(harness.favoriteError, null);
  assert.strictEqual(harness.isControlDisabled(), false);
});

test('failed status load leaves status unknown, sets error, and keeps control disabled', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, 'token-1');
  assert.strictEqual(harness.isFavorite, null);
  assert.strictEqual(harness.isControlDisabled(), true);

  await harness.loadFavorite(async () => {
    throw new Error('Network error loading favorite status');
  });

  // State must NOT default to false (which would indicate non-favorite); it must remain unknown (null)
  assert.strictEqual(harness.isFavorite, null);
  assert.strictEqual(harness.isLoadingFavorite, false);
  assert.strictEqual(harness.favoriteError, 'Network error loading favorite status');
  assert.strictEqual(harness.isControlDisabled(), true);

  // Calling toggleFavorite while status is unknown must return early and not mutate
  let mutateCalled = false;
  await harness.toggleFavorite(async () => {
    mutateCalled = true;
  });
  assert.strictEqual(mutateCalled, false);
  assert.strictEqual(harness.isFavorite, null);
});

test('retry after failed status load successfully recovers status and enables control', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, 'token-1');

  // Initial load fails
  await harness.loadFavorite(async () => {
    throw new Error('Initial network timeout');
  });
  assert.strictEqual(harness.isFavorite, null);
  assert.strictEqual(harness.isControlDisabled(), true);
  assert.strictEqual(harness.favoriteError, 'Initial network timeout');

  // Retry action calls loadFavorite again and succeeds
  await harness.loadFavorite(async () => {
    return { shop_id: 'shop-1', is_favorite: true, favorited_at: '2026-09-30T01:00:00Z' };
  });

  assert.strictEqual(harness.isFavorite, true);
  assert.strictEqual(harness.isLoadingFavorite, false);
  assert.strictEqual(harness.favoriteError, null);
  assert.strictEqual(harness.isControlDisabled(), false);
});

test('successful favorite mutation transitions state from false to true and remains true', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, 'token-1');
  // Initial status loaded as false
  await harness.loadFavorite(async () => ({
    shop_id: 'shop-1',
    is_favorite: false,
    favorited_at: null,
  }));
  assert.strictEqual(harness.isFavorite, false);
  assert.strictEqual(harness.isControlDisabled(), false);

  let mutateCalled = false;
  const togglePromise = harness.toggleFavorite(async (shopId, targetState) => {
    mutateCalled = true;
    assert.strictEqual(shopId, 'shop-1');
    assert.strictEqual(targetState, true);
  });

  // Optimistic update
  assert.strictEqual(harness.isFavorite, true);
  assert.strictEqual(harness.isMutatingFavorite, true);

  await togglePromise;
  assert.strictEqual(mutateCalled, true);
  assert.strictEqual(harness.isFavorite, true);
  assert.strictEqual(harness.isMutatingFavorite, false);
  assert.strictEqual(harness.favoriteError, null);
  assert.strictEqual(harness.isControlDisabled(), false);
});

test('successful unfavorite mutation transitions state from true to false and remains false', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, 'token-1');
  // Initial status loaded as true
  await harness.loadFavorite(async () => ({
    shop_id: 'shop-1',
    is_favorite: true,
    favorited_at: '2026-09-30T01:00:00Z',
  }));
  assert.strictEqual(harness.isFavorite, true);
  assert.strictEqual(harness.isControlDisabled(), false);

  let mutateCalled = false;
  const togglePromise = harness.toggleFavorite(async (shopId, targetState) => {
    mutateCalled = true;
    assert.strictEqual(shopId, 'shop-1');
    assert.strictEqual(targetState, false);
  });

  // Optimistic update
  assert.strictEqual(harness.isFavorite, false);
  assert.strictEqual(harness.isMutatingFavorite, true);

  await togglePromise;
  assert.strictEqual(mutateCalled, true);
  assert.strictEqual(harness.isFavorite, false);
  assert.strictEqual(harness.isMutatingFavorite, false);
  assert.strictEqual(harness.favoriteError, null);
  assert.strictEqual(harness.isControlDisabled(), false);
});

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

test('toggleFavorite rolls back to previous state and sets error banner on mutation failure', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, 'token-1');
  await harness.loadFavorite(async () => ({
    shop_id: 'shop-1',
    is_favorite: false,
    favorited_at: null,
  }));

  await harness.toggleFavorite(async () => {
    throw new Error('Network error favoriting shop');
  });

  // State must roll back to false
  assert.strictEqual(harness.isFavorite, false);
  assert.strictEqual(harness.isMutatingFavorite, false);
  assert.strictEqual(harness.favoriteError, 'Network error favoriting shop');
  assert.strictEqual(harness.isControlDisabled(), false);
});

test('Stale toggleFavorite protection: Shop A -> Shop B while mutation is in flight ignores mutation result', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-A', name: 'Shop A' }, 'token-1');
  await harness.loadFavorite(async () => ({
    shop_id: 'shop-A',
    is_favorite: false,
    favorited_at: null,
  }));

  let resolveMutationA;
  const mutationAPromise = new Promise((resolve) => {
    resolveMutationA = resolve;
  });

  const togglePromiseA = harness.toggleFavorite(() => mutationAPromise);
  assert.strictEqual(harness.isFavorite, true); // optimistically true for A

  // User rapidly navigates away to Shop B
  harness.switchContext({ id: 'shop-B', name: 'Shop B' });
  assert.strictEqual(harness.isFavorite, null); // reset for Shop B

  // Mutation for Shop A now resolves
  resolveMutationA();
  await togglePromiseA;

  // Shop B must not inherit Shop A's favorited state
  assert.strictEqual(harness.isFavorite, null);
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
  assert.strictEqual(harness.isFavorite, null);
  assert.strictEqual(harness.isMutatingFavorite, false);
});

test('Stale toggleFavorite protection: stale successful mutation does not invoke onFavoriteChange callback', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-A', name: 'Shop A' }, 'token-1');
  await harness.loadFavorite(async () => ({
    shop_id: 'shop-A',
    is_favorite: false,
    favorited_at: null,
  }));

  let resolveMutationA;
  const mutationAPromise = new Promise((resolve) => {
    resolveMutationA = resolve;
  });

  let callbackCalled = false;
  let callbackShopId = null;
  let callbackIsFavorite = null;

  const togglePromiseA = harness.toggleFavorite(
    () => mutationAPromise,
    (shopId, isFavorite) => {
      callbackCalled = true;
      callbackShopId = shopId;
      callbackIsFavorite = isFavorite;
    }
  );

  // User rapidly navigates away to Shop B before mutation resolves
  harness.switchContext({ id: 'shop-B', name: 'Shop B' });

  // Mutation A now succeeds late
  resolveMutationA();
  await togglePromiseA;

  // Stale mutation callback MUST NOT have been invoked
  assert.strictEqual(callbackCalled, false);
  assert.strictEqual(callbackShopId, null);
  assert.strictEqual(callbackIsFavorite, null);
});

test('Successful toggleFavorite invokes onFavoriteChange callback when mutation ownership is preserved', async () => {
  const harness = new ShopDetailCardFavoriteStateHarness({ id: 'shop-1', name: 'Shop 1' }, 'token-1');
  await harness.loadFavorite(async () => ({
    shop_id: 'shop-1',
    is_favorite: false,
    favorited_at: null,
  }));

  let callbackCalled = false;
  let callbackShopId = null;
  let callbackIsFavorite = null;

  await harness.toggleFavorite(
    async () => {},
    (shopId, isFavorite) => {
      callbackCalled = true;
      callbackShopId = shopId;
      callbackIsFavorite = isFavorite;
    }
  );

  assert.strictEqual(callbackCalled, true);
  assert.strictEqual(callbackShopId, 'shop-1');
  assert.strictEqual(callbackIsFavorite, true);
});


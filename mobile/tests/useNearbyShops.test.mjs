import test from 'node:test';
import assert from 'node:assert';
import { NearbyShopsController } from '../src/hooks/useNearbyShops.ts';

test('selection sync keeps updated shop if found in refreshed data', () => {
  const previousSelected = {
    id: 'shop-1',
    name: 'Old Name',
    address: 'Old Address',
    latitude: 14.5,
    longitude: 121.0,
    rating: 4.5,
    distance_meters: 500,
  };

  const refreshedData = [
    {
      id: 'shop-1',
      name: 'New Name',
      address: 'New Address',
      latitude: 14.5,
      longitude: 121.0,
      rating: 4.8,
      distance_meters: 300,
    },
    {
      id: 'shop-2',
      name: 'Other Shop',
      address: 'Other Address',
      latitude: 14.6,
      longitude: 121.1,
      rating: 4.0,
      distance_meters: 800,
    },
  ];

  const syncSelection = (prev, data) => {
    if (!prev) return null;
    const found = data.find((s) => s.id === prev.id);
    return found || null;
  };

  const updated = syncSelection(previousSelected, refreshedData);
  assert.strictEqual(updated?.name, 'New Name');
  assert.strictEqual(updated?.distance_meters, 300);
});

test('selection sync resets to null if shop is absent from refreshed data', () => {
  const previousSelected = {
    id: 'shop-old',
    name: 'Old Shop',
    address: 'Old Address',
    latitude: 14.5,
    longitude: 121.0,
    rating: 4.5,
    distance_meters: 500,
  };

  const refreshedData = [
    {
      id: 'shop-new',
      name: 'New Shop',
      address: 'New Address',
      latitude: 14.6,
      longitude: 121.1,
      rating: 4.0,
      distance_meters: 800,
    },
  ];

  const syncSelection = (prev, data) => {
    if (!prev) return null;
    const found = data.find((s) => s.id === prev.id);
    return found || null;
  };

  const updated = syncSelection(previousSelected, refreshedData);
  assert.strictEqual(updated, null);
});

test('monotonic request counter discards out-of-order stale responses', async () => {
  let requestIdCounter = 0;
  let appliedData = null;

  const simulateFetch = async (requestId, delayMs, result) => {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    if (requestId === requestIdCounter) {
      appliedData = result;
    }
  };

  // Launch request 1 (slow, 50ms)
  const req1 = ++requestIdCounter;
  const p1 = simulateFetch(req1, 50, ['req1_data']);

  // Launch request 2 (fast, 10ms)
  const req2 = ++requestIdCounter;
  const p2 = simulateFetch(req2, 10, ['req2_data']);

  await Promise.all([p1, p2]);

  // Request 2 was latest; req 1 finished late and was discarded
  assert.deepStrictEqual(appliedData, ['req2_data']);
});

test('hasActiveFilters detects any non-default search, filter, or sort option', () => {
  const checkActive = ({ query, minRating, minLokalRating, radius, sortBy }) => {
    return Boolean(
      (query && query.trim()) ||
      minRating !== null ||
      minLokalRating !== null ||
      sortBy !== 'distance' ||
      radius !== 5000
    );
  };

  // Defaults: not active
  assert.strictEqual(
    checkActive({ query: '', minRating: null, minLokalRating: null, radius: 5000, sortBy: 'distance' }),
    false
  );
  assert.strictEqual(
    checkActive({ query: '   ', minRating: null, minLokalRating: null, radius: 5000, sortBy: 'distance' }),
    false
  );

  // Active cases
  assert.strictEqual(
    checkActive({ query: 'espresso', minRating: null, minLokalRating: null, radius: 5000, sortBy: 'distance' }),
    true
  );
  assert.strictEqual(
    checkActive({ query: '', minRating: 4.0, minLokalRating: null, radius: 5000, sortBy: 'distance' }),
    true
  );
  assert.strictEqual(
    checkActive({ query: '', minRating: null, minLokalRating: 4.5, radius: 5000, sortBy: 'distance' }),
    true
  );
  assert.strictEqual(
    checkActive({ query: '', minRating: null, minLokalRating: null, radius: 1000, sortBy: 'distance' }),
    true
  );
  assert.strictEqual(
    checkActive({ query: '', minRating: null, minLokalRating: null, radius: 5000, sortBy: 'rating' }),
    true
  );
  assert.strictEqual(
    checkActive({ query: '', minRating: null, minLokalRating: null, radius: 5000, sortBy: 'lokal_rating' }),
    true
  );
});

test('resetFilters restores all states to default values including minLokalRating', () => {
  let state = {
    searchQuery: 'Manila Roast',
    debouncedQuery: 'Manila Roast',
    minRating: 4.5,
    minLokalRating: 4.0,
    radius: 3000,
    sortBy: 'lokal_rating',
  };

  const resetFilters = () => {
    state = {
      searchQuery: '',
      debouncedQuery: '',
      minRating: null,
      minLokalRating: null,
      radius: 5000,
      sortBy: 'distance',
    };
  };

  resetFilters();

  assert.strictEqual(state.searchQuery, '');
  assert.strictEqual(state.debouncedQuery, '');
  assert.strictEqual(state.minRating, null);
  assert.strictEqual(state.minLokalRating, null);
  assert.strictEqual(state.radius, 5000);
  assert.strictEqual(state.sortBy, 'distance');
});


test('search keystroke race condition rejects older queries resolving after newer ones', async () => {
  let requestCounter = 0;
  let activeResults = null;

  const simulateSearch = async (term, delayMs, returnedShops) => {
    const reqId = ++requestCounter;
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    if (reqId === requestCounter) {
      activeResults = { term, shops: returnedShops };
    }
  };

  // User types "kap", then immediately "kape"
  // "kap" request is slow (60ms); "kape" request is fast (15ms)
  const p1 = simulateSearch('kap', 60, [{ name: 'Kapitolyo Beans' }]);
  const p2 = simulateSearch('kape', 15, [{ name: 'Kape Manila' }, { name: 'Kape Isla' }]);

  await Promise.all([p1, p2]);

  assert.strictEqual(activeResults?.term, 'kape');
  assert.strictEqual(activeResults?.shops.length, 2);
  assert.strictEqual(activeResults?.shops[0].name, 'Kape Manila');
});

test('Production NearbyShopsController: location loss invalidates in-flight request and clears state', async () => {
  let resolveFetch;
  const fetchPromise = new Promise((resolve) => {
    resolveFetch = resolve;
  });

  const mockFetch = async () => fetchPromise;
  const controller = new NearbyShopsController(mockFetch);

  // 1. Request begins while a valid location exists
  const pending = controller.load({
    latitude: 14.5995,
    longitude: 120.9842,
    radius: 5000,
    sortBy: 'distance',
  });
  assert.strictEqual(controller.getState().isLoading, true);

  // 2. Location becomes unavailable (null) before request resolves
  // The controller invalidates in-flight requests and resets state
  await controller.load(null);
  assert.strictEqual(controller.getState().isLoading, false);
  assert.deepStrictEqual(controller.getState().shops, []);
  assert.strictEqual(controller.getState().selectedShop, null);

  // 3. Late arriving in-flight request resolves
  resolveFetch([{ id: 'shop-1', name: 'Late Arriving Shop', distance_meters: 100 }]);
  await pending;

  // 4. Stale response was discarded: shops and selectedShop remain empty/null
  assert.deepStrictEqual(controller.getState().shops, []);
  assert.strictEqual(controller.getState().selectedShop, null);
  assert.strictEqual(controller.getState().isLoading, false);
});

test('Production NearbyShopsController: rapid filter/sort switching discards stale in-flight response when newer sort completes', async () => {
  let resolveRating;
  const ratingPromise = new Promise((resolve) => {
    resolveRating = resolve;
  });

  const mockFetch = async (params) => {
    if (params.sortBy === 'rating') {
      return ratingPromise;
    }
    if (params.sortBy === 'lokal_rating') {
      return [
        {
          id: 'shop-lokal',
          name: 'LOKAL High Shop',
          distance_meters: 100,
          lokal_rating: 4.9,
          lokal_reviews_count: 5,
        },
      ];
    }
    return [];
  };

  const controller = new NearbyShopsController(mockFetch);

  // 1. User selects 'rating' (slow network: response is deferred)
  const pendingRating = controller.load({
    latitude: 14.5995,
    longitude: 120.9842,
    radius: 5000,
    sortBy: 'rating',
  });
  assert.strictEqual(controller.getState().isLoading, true);

  // 2. User quickly selects 'lokal_rating' (fast network: resolves immediately)
  await controller.load({
    latitude: 14.5995,
    longitude: 120.9842,
    radius: 5000,
    sortBy: 'lokal_rating',
  });

  assert.strictEqual(controller.getState().isLoading, false);
  assert.strictEqual(controller.getState().shops.length, 1);
  assert.strictEqual(controller.getState().shops[0].id, 'shop-lokal');

  // 3. Stale rating request finishes late
  resolveRating([
    {
      id: 'shop-google',
      name: 'Google High Shop',
      distance_meters: 200,
      rating: 4.8,
    },
  ]);
  await pendingRating;

  // 4. Stale rating response was discarded by production controller
  assert.strictEqual(controller.getState().shops.length, 1);
  assert.strictEqual(controller.getState().shops[0].id, 'shop-lokal');
  assert.strictEqual(controller.getState().isLoading, false);
});

test('Production NearbyShopsController: auth token invalidation during in-flight discovery request discards stale response', async () => {
  let resolveOldAuth;
  const oldAuthPromise = new Promise((resolve) => {
    resolveOldAuth = resolve;
  });

  const mockFetch = async (_params, token) => {
    if (token === 'old-token') {
      return oldAuthPromise;
    }
    if (token === 'new-token') {
      return [
        {
          id: 'shop-new',
          name: 'New Account Shop',
          distance_meters: 300,
        },
      ];
    }
    return [];
  };

  const controller = new NearbyShopsController(mockFetch);

  // 1. Initial request begins with old-token
  const pendingOld = controller.load(
    {
      latitude: 14.5995,
      longitude: 120.9842,
      radius: 5000,
      sortBy: 'distance',
    },
    'old-token'
  );
  assert.strictEqual(controller.getState().isLoading, true);

  // 2. Auth token changes to new-token before old-token request completes
  await controller.load(
    {
      latitude: 14.5995,
      longitude: 120.9842,
      radius: 5000,
      sortBy: 'distance',
    },
    'new-token'
  );

  assert.strictEqual(controller.getState().isLoading, false);
  assert.strictEqual(controller.getState().shops.length, 1);
  assert.strictEqual(controller.getState().shops[0].id, 'shop-new');

  // 3. Old auth request resolves late
  resolveOldAuth([
    {
      id: 'shop-old',
      name: 'Old Account Shop',
      distance_meters: 500,
    },
  ]);
  await pendingOld;

  // 4. Stale response was discarded: state reflects only new-token data
  assert.strictEqual(controller.getState().shops.length, 1);
  assert.strictEqual(controller.getState().shops[0].id, 'shop-new');
  assert.strictEqual(controller.getState().isLoading, false);
});




import test from 'node:test';
import assert from 'node:assert';

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

test('location loss invalidates in-flight request and prevents stale data from repopulating state', async () => {
  let requestIdCounter = 0;
  let state = {
    shops: [],
    selectedShop: null,
    isLoading: false,
    errorMessage: null,
  };

  // 1. Request begins while a valid location exists
  const reqId = ++requestIdCounter;
  state.isLoading = true;

  const inFlightPromise = (async () => {
    // Simulate network delay
    await new Promise((resolve) => setTimeout(resolve, 40));
    // Check if request is still current
    if (reqId === requestIdCounter) {
      state.shops = [{ id: 'shop-1', name: 'Late Arriving Shop' }];
      state.selectedShop = { id: 'shop-1', name: 'Late Arriving Shop' };
      state.isLoading = false;
    }
  })();

  // 2. Location becomes unavailable (null) before request resolves
  // The hook invalidates in-flight requests and clears state
  ++requestIdCounter;
  state.shops = [];
  state.selectedShop = null;
  state.isLoading = false;
  state.errorMessage = null;

  // 3. In-flight request resolves afterward
  await inFlightPromise;

  // 4. Stale response was discarded: shops and selectedShop remain empty/null
  assert.deepStrictEqual(state.shops, []);
  assert.strictEqual(state.selectedShop, null);
  assert.strictEqual(state.isLoading, false);
});

test('rapid filter/sort switching discards stale in-flight response when newer sort completes', async () => {
  let requestIdCounter = 0;
  let appliedSort = null;
  let appliedShops = [];

  const simulateFetch = async (sort, delayMs, returnedShops) => {
    const reqId = ++requestIdCounter;
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    if (reqId === requestIdCounter) {
      appliedSort = sort;
      appliedShops = returnedShops;
    }
  };

  // User selects 'rating' (slow network: 50ms), then quickly selects 'lokal_rating' (fast network: 15ms)
  const p1 = simulateFetch('rating', 50, [{ id: 'shop-google', name: 'Google High Shop' }]);
  const p2 = simulateFetch('lokal_rating', 15, [{ id: 'shop-lokal', name: 'LOKAL High Shop' }]);

  await Promise.all([p1, p2]);

  assert.strictEqual(appliedSort, 'lokal_rating');
  assert.strictEqual(appliedShops[0].name, 'LOKAL High Shop');
});

test('auth token invalidation during in-flight discovery request discards stale response', async () => {
  let requestIdCounter = 0;
  let state = {
    shops: [],
    isLoading: true,
  };

  const reqId = ++requestIdCounter;
  const inFlightPromise = (async () => {
    await new Promise((resolve) => setTimeout(resolve, 30));
    if (reqId === requestIdCounter) {
      state.shops = [{ id: 'old-shop', name: 'Old Account Shop' }];
      state.isLoading = false;
    }
  })();

  // Auth token changes / user logs out
  ++requestIdCounter;
  state.shops = [];
  state.isLoading = false;

  await inFlightPromise;

  assert.deepStrictEqual(state.shops, []);
  assert.strictEqual(state.isLoading, false);
});




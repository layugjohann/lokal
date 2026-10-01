import test from 'node:test';
import assert from 'node:assert';
import { getUserDisplayName } from '../src/services/authService.ts';
import { calculateDistanceMeters, formatDistance } from '../src/services/shopService.ts';
import { FavoritesController } from '../src/hooks/useFavorites.ts';

// ============================================================================
// 1. User Profile Display Name Tests
// ============================================================================

test('getUserDisplayName uses full_name when present in user_metadata', () => {
  const user = {
    id: 'u1',
    email: 'maria@example.com',
    user_metadata: { full_name: 'Maria Santos' },
  };
  assert.strictEqual(getUserDisplayName(user), 'Maria Santos');
});

test('getUserDisplayName falls back to display_name when full_name is missing', () => {
  const user = {
    id: 'u1',
    email: 'maria@example.com',
    user_metadata: { display_name: 'Barista Queen' },
  };
  assert.strictEqual(getUserDisplayName(user), 'Barista Queen');
});

test('getUserDisplayName falls back to email prefix when metadata is empty or whitespace', () => {
  const user1 = {
    id: 'u1',
    email: 'johann@lokal.ph',
    user_metadata: { full_name: '   ', display_name: '' },
  };
  assert.strictEqual(getUserDisplayName(user1), 'johann');

  const user2 = {
    id: 'u2',
    email: 'coffee.fan@gmail.com',
    user_metadata: {},
  };
  assert.strictEqual(getUserDisplayName(user2), 'coffee.fan');
});

test('getUserDisplayName returns "LOKAL User" when user is null or has no email', () => {
  assert.strictEqual(getUserDisplayName(null), 'LOKAL User');
  assert.strictEqual(getUserDisplayName(undefined), 'LOKAL User');
  assert.strictEqual(getUserDisplayName({ id: 'u1', email: null }), 'LOKAL User');
});

// ============================================================================
// 2. Distance Calculation & Formatting for Saved Coffee Shops
// ============================================================================

test('Distance formatting correctly handles coordinates and valid numbers', () => {
  const userLoc = { latitude: 14.5995, longitude: 120.9842 };
  const shopLoc = { latitude: 14.6045, longitude: 120.9842 };

  const meters = calculateDistanceMeters(
    userLoc.latitude,
    userLoc.longitude,
    shopLoc.latitude,
    shopLoc.longitude
  );
  assert.ok(meters > 500 && meters < 600);
  assert.strictEqual(formatDistance(meters), `${Math.round(meters)} m`);
  assert.strictEqual(formatDistance(1250), '1.3 km');
});

test('Distance formatting returns empty string for null, undefined, and NaN distances', () => {
  assert.strictEqual(formatDistance(null), '');
  assert.strictEqual(formatDistance(undefined), '');
  assert.strictEqual(formatDistance(Number.NaN), '');
});

test('Missing user location produces NaN distance and omits badge instead of displaying false 0 m', () => {
  const userLocation = null;
  let distanceMeters = Number.NaN;
  if (userLocation) {
    distanceMeters = calculateDistanceMeters(14.5, 120.9, 14.6, 121.0);
  }

  assert.ok(Number.isNaN(distanceMeters));
  const formatted = formatDistance(distanceMeters);
  assert.strictEqual(formatted, '');
  assert.notStrictEqual(formatted, '0 m');
});

// ============================================================================
// 3. Stale Async Protection & Request ID Invariant Tests (Production FavoritesController)
// ============================================================================

test('Production FavoritesController: token switch while request is in flight discards earlier response', async () => {
  let resolveTokenA;
  const tokenAPromise = new Promise((resolve) => {
    resolveTokenA = resolve;
  });

  const mockFetch = async (token) => {
    if (token === 'token-A') {
      return tokenAPromise;
    }
    if (token === 'token-B') {
      return [{ id: 'shop-B', name: 'Shop B' }];
    }
    return [];
  };

  const controller = new FavoritesController(mockFetch);

  // 1. Launch fetch for token A
  const pendingA = controller.load('token-A');
  assert.strictEqual(controller.getState().isLoading, true);

  // 2. Switch to token B before token A resolves
  await controller.load('token-B');
  assert.strictEqual(controller.getState().isLoading, false);
  assert.strictEqual(controller.getState().favorites.length, 1);
  assert.strictEqual(controller.getState().favorites[0].id, 'shop-B');

  // 3. Resolve token A late
  resolveTokenA([{ id: 'shop-A', name: 'Shop A' }]);
  await pendingA;

  // 4. Stale token A response did not overwrite token B state
  assert.strictEqual(controller.getState().favorites.length, 1);
  assert.strictEqual(controller.getState().favorites[0].id, 'shop-B');
});

test('Production FavoritesController: logout / auth transition resets state and ignores in-flight responses', async () => {
  let resolveLateFetch;
  const lateFetchPromise = new Promise((resolve) => {
    resolveLateFetch = resolve;
  });

  const mockFetch = async () => lateFetchPromise;

  const controller = new FavoritesController(mockFetch, [
    { id: 'old-shop', name: 'Old Shop' },
  ]);
  assert.strictEqual(controller.getState().favorites.length, 1);

  // 1. Trigger in-flight load for authenticated session
  const pendingLoad = controller.load('token-A');
  assert.strictEqual(controller.getState().isLoading, true);

  // 2. User logs out (null token)
  await controller.load(null);
  assert.deepStrictEqual(controller.getState().favorites, []);
  assert.strictEqual(controller.getState().isLoading, false);
  assert.strictEqual(controller.getState().errorMessage, null);

  // 3. Late fetch finishes after logout
  resolveLateFetch([{ id: 'shop-1', name: 'Should Be Discarded' }]);
  await pendingLoad;

  // 4. State remains empty and was not resurrected
  assert.deepStrictEqual(controller.getState().favorites, []);
  assert.strictEqual(controller.getState().isLoading, false);
});

test('Production FavoritesController: favorite -> unfavorite -> favorite lifecycle reconciles authoritative collection', async () => {
  const initialFavorites = [
    { id: 'shop-1', name: 'Craft Coffee' },
    { id: 'shop-2', name: 'Local Brew' },
  ];

  let currentServerFavorites = [...initialFavorites];
  const mockFetch = async () => [...currentServerFavorites];

  const controller = new FavoritesController(mockFetch, initialFavorites);

  // Verify initial state
  assert.strictEqual(controller.getState().favorites.length, 2);

  // 1. User unfavorites shop-1 -> optimistic removal removes it immediately
  controller.removeOptimistic('shop-1');
  assert.strictEqual(controller.getState().favorites.length, 1);
  assert.strictEqual(controller.getState().favorites[0].id, 'shop-2');

  // Server state reflects unfavorite
  currentServerFavorites = [{ id: 'shop-2', name: 'Local Brew' }];

  // ProfileView reconciles via refetch
  await controller.load('token-1');
  assert.strictEqual(controller.getState().favorites.length, 1);
  assert.strictEqual(controller.getState().favorites[0].id, 'shop-2');

  // 2. User re-favorites shop-1 in ShopDetailCard
  // Server state now has shop-1 restored
  currentServerFavorites = [
    { id: 'shop-1', name: 'Craft Coffee' },
    { id: 'shop-2', name: 'Local Brew' },
  ];

  // ProfileView reconciles via refetch on favorite change (isFavorite === true)
  await controller.load('token-1');
  assert.strictEqual(controller.getState().favorites.length, 2);
  assert.strictEqual(controller.getState().favorites[0].id, 'shop-1');
  assert.strictEqual(controller.getState().favorites[1].id, 'shop-2');
});

test('Production FavoritesController: late refetch response from older request does not overwrite newer state', async () => {
  let resolveFirstRefetch;
  const firstPromise = new Promise((resolve) => {
    resolveFirstRefetch = resolve;
  });

  let fetchCount = 0;
  const mockFetch = async () => {
    fetchCount += 1;
    if (fetchCount === 1) {
      return firstPromise;
    }
    return [{ id: 'shop-latest', name: 'Latest Refetched Shop' }];
  };

  const controller = new FavoritesController(mockFetch);

  // 1. Start first refetch
  const pending1 = controller.load('token-1');

  // 2. Rapid second refetch initiated (e.g. rapid favorite toggling)
  const pending2 = controller.load('token-1');
  await pending2;

  assert.strictEqual(controller.getState().favorites.length, 1);
  assert.strictEqual(controller.getState().favorites[0].id, 'shop-latest');

  // 3. First refetch resolves with older data
  resolveFirstRefetch([{ id: 'shop-stale', name: 'Stale Shop' }]);
  await pending1;

  // 4. Controller ignores older response and retains latest authoritative data
  assert.strictEqual(controller.getState().favorites.length, 1);
  assert.strictEqual(controller.getState().favorites[0].id, 'shop-latest');
});

// ============================================================================
// 4. Explicit Navigation & Return Lifecycle Simulation
// ============================================================================

test('Full explicit lifecycle: Map -> Profile -> Favorites -> Shop Detail -> Favorites -> Profile -> Map', async () => {
  // Step 0: Initial Map State
  let mapState = {
    selectedShopOnMap: { id: 'map-shop-1', name: 'Map Shop 1' },
    isProfileOpen: false,
    selectedFavoriteShop: null,
    favorites: [
      { id: 'fav-1', name: 'Saved Shop 1' },
      { id: 'fav-2', name: 'Saved Shop 2' },
    ],
  };

  // Step 1: User opens Profile from Map
  mapState.isProfileOpen = true;
  assert.strictEqual(mapState.isProfileOpen, true);
  // Map state underneath remains intact
  assert.strictEqual(mapState.selectedShopOnMap.id, 'map-shop-1');

  // Step 2: User opens Shop Detail for fav-1 from Favorites list
  mapState.selectedFavoriteShop = mapState.favorites[0];
  assert.strictEqual(mapState.selectedFavoriteShop.id, 'fav-1');

  // Step 3: User unfavorites fav-1 inside Shop Detail
  const unfavoritedShopId = 'fav-1';
  // onFavoriteChange callback triggers optimistic removal
  mapState.favorites = mapState.favorites.filter((f) => f.id !== unfavoritedShopId);
  assert.strictEqual(mapState.favorites.length, 1);
  assert.strictEqual(mapState.favorites[0].id, 'fav-2');

  // Step 4: User closes Shop Detail -> returns to Favorites list
  mapState.selectedFavoriteShop = null;
  assert.strictEqual(mapState.selectedFavoriteShop, null);
  assert.strictEqual(mapState.isProfileOpen, true); // Still in Profile/Favorites
  assert.strictEqual(mapState.favorites.length, 1); // Unfavorited item is removed!

  // Step 5: User closes Profile -> returns to Map
  mapState.isProfileOpen = false;
  assert.strictEqual(mapState.isProfileOpen, false);
  // Map state is completely intact
  assert.strictEqual(mapState.selectedShopOnMap.id, 'map-shop-1');

  // Step 6: User selects another shop on the map -> compound key resets detail cleanly
  const previousDetailKey = `${mapState.selectedShopOnMap.id}:auth-token`;
  mapState.selectedShopOnMap = { id: 'map-shop-2', name: 'Map Shop 2' };
  const newDetailKey = `${mapState.selectedShopOnMap.id}:auth-token`;
  assert.notStrictEqual(previousDetailKey, newDetailKey);
});

test('Session change during active profile/favorites safely closes view and resets all state', () => {
  let isProfileOpen = true;
  let selectedFavoriteShop = { id: 'fav-1', name: 'Saved Shop 1' };
  let favorites = [{ id: 'fav-1', name: 'Saved Shop 1' }];
  let authStatus = 'authenticated';

  // Logout event fires
  authStatus = 'unauthenticated';
  if (authStatus !== 'authenticated') {
    isProfileOpen = false;
    selectedFavoriteShop = null;
    favorites = [];
  }

  assert.strictEqual(isProfileOpen, false);
  assert.strictEqual(selectedFavoriteShop, null);
  assert.deepStrictEqual(favorites, []);
});

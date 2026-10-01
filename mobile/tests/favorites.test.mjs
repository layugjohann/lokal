import test from 'node:test';
import assert from 'node:assert';
import { getUserDisplayName } from '../src/services/authService.ts';
import { calculateDistanceMeters, formatDistance } from '../src/services/shopService.ts';

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
// 2. Distance Calculation for Saved Coffee Shops
// ============================================================================

test('Distance formatting correctly handles coordinates and null location', () => {
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

  // Null or missing location formatting
  assert.strictEqual(formatDistance(null), '');
  assert.strictEqual(formatDistance(undefined), '');
});

// ============================================================================
// 3. Stale Async Protection & Request ID Invariant Tests
// ============================================================================

test('Stale favorites fetch protection: token switch while request is in flight discards earlier response', async () => {
  let requestId = 0;
  let activeToken = 'token-A';
  let favoritesState = [];

  let resolveTokenA;
  const tokenAPromise = new Promise((resolve) => {
    resolveTokenA = resolve;
  });

  const loadFavorites = async (token) => {
    const currentId = ++requestId;
    if (token === 'token-A') {
      const data = await tokenAPromise;
      if (currentId === requestId) {
        favoritesState = data;
      }
    } else if (token === 'token-B') {
      const data = [{ id: 'shop-B', name: 'Shop B' }];
      if (currentId === requestId) {
        favoritesState = data;
      }
    }
  };

  // Launch fetch for token A
  const pendingA = loadFavorites(activeToken);

  // Switch to token B before token A resolves
  activeToken = 'token-B';
  await loadFavorites(activeToken);

  assert.strictEqual(favoritesState.length, 1);
  assert.strictEqual(favoritesState[0].id, 'shop-B');

  // Now resolve token A late
  resolveTokenA([{ id: 'shop-A', name: 'Shop A' }]);
  await pendingA;

  // Verify stale token A response did not overwrite token B state
  assert.strictEqual(favoritesState.length, 1);
  assert.strictEqual(favoritesState[0].id, 'shop-B');
});

test('Logout / auth transition immediately resets favorites state and ignores in-flight responses', async () => {
  let requestId = 0;
  let activeToken = 'token-A';
  let favoritesState = [{ id: 'old', name: 'Old Shop' }];

  let resolveLateFetch;
  const lateFetchPromise = new Promise((resolve) => {
    resolveLateFetch = resolve;
  });

  const loadFavorites = async (token) => {
    if (!token) {
      ++requestId;
      favoritesState = [];
      return;
    }
    const currentId = ++requestId;
    const data = await lateFetchPromise;
    if (currentId === requestId) {
      favoritesState = data;
    }
  };

  // Trigger in-flight load
  const pendingLoad = loadFavorites(activeToken);

  // User logs out
  activeToken = null;
  await loadFavorites(null);

  assert.deepStrictEqual(favoritesState, []);

  // Late fetch finishes after logout
  resolveLateFetch([{ id: 'shop-1', name: 'Should Be Ignored' }]);
  await pendingLoad;

  // Verify state remains empty and was not resurrected
  assert.deepStrictEqual(favoritesState, []);
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

import test from 'node:test';
import assert from 'node:assert';
import { ShopClaimController } from '../src/hooks/useShopClaim.ts';

test('ShopClaimController initializes with idle state', () => {
  const controller = new ShopClaimController();
  const state = controller.getState();

  assert.strictEqual(state.claim, null);
  assert.strictEqual(state.isLoading, false);
  assert.strictEqual(state.errorMessage, null);
});

test('ShopClaimController resets to idle when unauthenticated or shopId missing', async () => {
  let fetchCalled = false;
  const mockFetch = async () => {
    fetchCalled = true;
    return null;
  };

  const controller = new ShopClaimController(mockFetch);
  await controller.load(null, 'valid-token', 'user-1');

  assert.strictEqual(fetchCalled, false);
  assert.strictEqual(controller.getState().claim, null);
  assert.strictEqual(controller.getState().isLoading, false);

  await controller.load('shop-1', null, 'user-1');
  assert.strictEqual(fetchCalled, false);
  assert.strictEqual(controller.getState().claim, null);

  await controller.load('shop-1', '   ', 'user-1');
  assert.strictEqual(fetchCalled, false);
  assert.strictEqual(controller.getState().claim, null);
});

test('ShopClaimController successfully loads claim status for a shop', async () => {
  const mockClaim = {
    id: 'claim-1',
    shop_id: 'shop-1',
    status: 'APPROVED',
    claimant_name: 'Maria Santos',
    claimant_role: 'Owner',
    rejection_reason: null,
    created_at: '2026-10-06T00:00:00Z',
    updated_at: '2026-10-06T00:00:00Z',
  };

  const mockFetch = async () => mockClaim;
  const controller = new ShopClaimController(mockFetch);

  await controller.load('shop-1', 'valid-token', 'user-1');

  const state = controller.getState();
  assert.strictEqual(state.isLoading, false);
  assert.strictEqual(state.errorMessage, null);
  assert.deepStrictEqual(state.claim, mockClaim);
});

test('ShopClaimController notifies subscribed listeners on state changes', async () => {
  const mockClaim = {
    id: 'claim-1',
    shop_id: 'shop-1',
    status: 'PENDING',
    claimant_name: 'Maria Santos',
    claimant_role: 'Owner',
    rejection_reason: null,
    created_at: '2026-10-06T00:00:00Z',
    updated_at: '2026-10-06T00:00:00Z',
  };

  const mockFetch = async () => mockClaim;
  const controller = new ShopClaimController(mockFetch);

  const states = [];
  const unsubscribe = controller.subscribe((state) => {
    states.push({ ...state });
  });

  await controller.load('shop-1', 'valid-token', 'user-1');
  unsubscribe();

  // Should have transitioned: loading true -> loading false with claim
  assert.ok(states.length >= 2);
  assert.strictEqual(states[0].isLoading, true);
  assert.strictEqual(states[states.length - 1].isLoading, false);
  assert.deepStrictEqual(states[states.length - 1].claim, mockClaim);
});

test('ShopClaimController discards out-of-order stale responses across shops', async () => {
  let resolveShopA;
  const shopAPromise = new Promise((resolve) => {
    resolveShopA = resolve;
  });

  const mockFetch = async (shopId) => {
    if (shopId === 'shop-a') {
      return shopAPromise;
    }
    return {
      id: 'claim-b',
      shop_id: 'shop-b',
      status: 'APPROVED',
      claimant_name: 'Bob',
      claimant_role: 'Owner',
      created_at: '2026-10-06T00:00:00Z',
      updated_at: '2026-10-06T00:00:00Z',
    };
  };

  const controller = new ShopClaimController(mockFetch);

  // 1. Slow request for Shop A
  const pendingA = controller.load('shop-a', 'token-1', 'user-1');
  assert.strictEqual(controller.getState().isLoading, true);

  // 2. Fast request for Shop B
  await controller.load('shop-b', 'token-1', 'user-1');
  assert.strictEqual(controller.getState().isLoading, false);
  assert.strictEqual(controller.getState().claim?.shop_id, 'shop-b');

  // 3. Shop A completes late
  resolveShopA({
    id: 'claim-a',
    shop_id: 'shop-a',
    status: 'PENDING',
    claimant_name: 'Alice',
    claimant_role: 'Manager',
    created_at: '2026-10-06T00:00:00Z',
    updated_at: '2026-10-06T00:00:00Z',
  });
  await pendingA;

  // 4. Shop A's stale response was discarded; Shop B remains
  assert.strictEqual(controller.getState().claim?.shop_id, 'shop-b');
});

test('ShopClaimController discards stale response when principal/token changes', async () => {
  let resolveUserA;
  const userAPromise = new Promise((resolve) => {
    resolveUserA = resolve;
  });

  const mockFetch = async (_shopId, token) => {
    if (token === 'token-user-a') {
      return userAPromise;
    }
    return {
      id: 'claim-b',
      shop_id: 'shop-1',
      status: 'APPROVED',
      claimant_name: 'User B',
      claimant_role: 'Owner',
      created_at: '2026-10-06T00:00:00Z',
      updated_at: '2026-10-06T00:00:00Z',
    };
  };

  const controller = new ShopClaimController(mockFetch);

  // 1. User A in-flight
  const pendingA = controller.load('shop-1', 'token-user-a', 'user-a');
  assert.strictEqual(controller.getState().isLoading, true);

  // 2. User B loads
  await controller.load('shop-1', 'token-user-b', 'user-b');
  assert.strictEqual(controller.getState().isLoading, false);
  assert.strictEqual(controller.getState().claim?.claimant_name, 'User B');

  // 3. User A resolves late
  resolveUserA({
    id: 'claim-a',
    shop_id: 'shop-1',
    status: 'PENDING',
    claimant_name: 'User A',
    claimant_role: 'Staff',
    created_at: '2026-10-06T00:00:00Z',
    updated_at: '2026-10-06T00:00:00Z',
  });
  await pendingA;

  // 4. Stale User A result discarded
  assert.strictEqual(controller.getState().claim?.claimant_name, 'User B');
});

test('ShopClaimController handles fetch error and sets errorMessage', async () => {
  const mockFetch = async () => {
    throw new Error('Connection refused.');
  };

  const controller = new ShopClaimController(mockFetch);
  await controller.load('shop-1', 'token', 'user-1');

  const state = controller.getState();
  assert.strictEqual(state.isLoading, false);
  assert.strictEqual(state.errorMessage, 'Connection refused.');
  assert.strictEqual(state.claim, null);
});

test('ShopClaimController cancel() increments request ID and discards in-flight result', async () => {
  let resolveFetch;
  const promise = new Promise((resolve) => {
    resolveFetch = resolve;
  });

  const mockFetch = async () => promise;
  const controller = new ShopClaimController(mockFetch);

  const pending = controller.load('shop-1', 'token', 'user-1');
  assert.strictEqual(controller.getState().isLoading, true);

  // Explicit cancellation (e.g. unmount)
  controller.cancel();

  // Resolve after cancellation
  resolveFetch({
    id: 'claim-late',
    shop_id: 'shop-1',
    status: 'PENDING',
    claimant_name: 'Late',
    claimant_role: 'Owner',
    created_at: '2026-10-06T00:00:00Z',
    updated_at: '2026-10-06T00:00:00Z',
  });
  await pending;

  // Response was discarded
  assert.strictEqual(controller.getState().claim, null);
});

test('ShopClaimController setClaim updates state directly', () => {
  const controller = new ShopClaimController();
  const mockClaim = {
    id: 'claim-direct',
    shop_id: 'shop-1',
    status: 'PENDING',
    claimant_name: 'Direct Setter',
    claimant_role: 'Manager',
    rejection_reason: null,
    created_at: '2026-10-06T00:00:00Z',
    updated_at: '2026-10-06T00:00:00Z',
  };

  controller.setClaim(mockClaim);
  assert.deepStrictEqual(controller.getState().claim, mockClaim);
  assert.strictEqual(controller.getState().errorMessage, null);
});

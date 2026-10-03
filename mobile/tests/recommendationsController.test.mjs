import test from 'node:test';
import assert from 'node:assert';
import { PersonalizedRecommendationsController } from '../src/hooks/usePersonalizedRecommendations.ts';

test('PersonalizedRecommendationsController initializes with idle state', () => {
  const controller = new PersonalizedRecommendationsController();
  const state = controller.getState();

  assert.strictEqual(state.status, 'idle');
  assert.strictEqual(state.isLoading, false);
  assert.strictEqual(state.errorMessage, null);
  assert.strictEqual(state.userMessage, null);
  assert.deepStrictEqual(state.recommendations, []);
  assert.strictEqual(state.totalCandidatesEvaluated, 0);
});

test('PersonalizedRecommendationsController resets to idle when unauthenticated or userId missing', async () => {
  let fetchCalled = false;
  const mockFetch = async () => {
    fetchCalled = true;
    return {
      status: 'personalized',
      recommendations: [],
      total_candidates_evaluated: 0,
    };
  };

  const controller = new PersonalizedRecommendationsController(mockFetch);
  await controller.load({}, null, null);

  assert.strictEqual(fetchCalled, false);
  assert.strictEqual(controller.getState().status, 'idle');
  assert.strictEqual(controller.getState().isLoading, false);
  assert.deepStrictEqual(controller.getState().recommendations, []);
});

test('PersonalizedRecommendationsController successfully loads personalized recommendations', async () => {
  const mockData = {
    status: 'personalized',
    message: null,
    recommendations: [
      {
        shop: {
          id: 'shop-1',
          name: 'Single Origin Cafe',
          latitude: 14.55,
          longitude: 121.02,
          rating: 4.8,
          distance_meters: 250,
        },
        explanation: 'Matches your preference for pour-over coffee.',
      },
    ],
    total_candidates_evaluated: 10,
  };

  const mockFetch = async () => mockData;
  const controller = new PersonalizedRecommendationsController(mockFetch);

  await controller.load({ latitude: 14.55, longitude: 121.02 }, 'test-token', 'user-123');

  const state = controller.getState();
  assert.strictEqual(state.status, 'personalized');
  assert.strictEqual(state.isLoading, false);
  assert.strictEqual(state.errorMessage, null);
  assert.strictEqual(state.recommendations.length, 1);
  assert.strictEqual(state.recommendations[0].shop.id, 'shop-1');
  assert.strictEqual(state.totalCandidatesEvaluated, 10);
});

test('PersonalizedRecommendationsController discards out-of-order stale responses', async () => {
  let resolveSlow;
  const slowPromise = new Promise((resolve) => {
    resolveSlow = resolve;
  });

  const mockFetch = async (params) => {
    if (params.radius === 1000) {
      return slowPromise;
    }
    return {
      status: 'personalized',
      recommendations: [
        {
          shop: { id: 'shop-fast', name: 'Fast Shop' },
          explanation: 'Fast match',
        },
      ],
      total_candidates_evaluated: 5,
    };
  };

  const controller = new PersonalizedRecommendationsController(mockFetch);

  // 1. Slow request launched (radius: 1000)
  const pendingSlow = controller.load({ radius: 1000 }, 'token-1', 'user-1');
  assert.strictEqual(controller.getState().isLoading, true);

  // 2. Fast request launched (radius: 5000)
  await controller.load({ radius: 5000 }, 'token-1', 'user-1');

  assert.strictEqual(controller.getState().isLoading, false);
  assert.strictEqual(controller.getState().recommendations.length, 1);
  assert.strictEqual(controller.getState().recommendations[0].shop.id, 'shop-fast');

  // 3. Slow request finishes late
  resolveSlow({
    status: 'personalized',
    recommendations: [
      {
        shop: { id: 'shop-slow', name: 'Slow Shop' },
        explanation: 'Slow match',
      },
    ],
    total_candidates_evaluated: 1,
  });
  await pendingSlow;

  // 4. Stale slow response was discarded
  assert.strictEqual(controller.getState().recommendations.length, 1);
  assert.strictEqual(controller.getState().recommendations[0].shop.id, 'shop-fast');
});

test('PersonalizedRecommendationsController principal change immediately clears state and discards previous user response', async () => {
  let resolveUserA;
  const userAPromise = new Promise((resolve) => {
    resolveUserA = resolve;
  });

  const mockFetch = async (_params, token) => {
    if (token === 'token-user-a') {
      return userAPromise;
    }
    return {
      status: 'personalized',
      recommendations: [
        {
          shop: { id: 'shop-b', name: 'User B Shop' },
          explanation: 'User B match',
        },
      ],
      total_candidates_evaluated: 2,
    };
  };

  const controller = new PersonalizedRecommendationsController(mockFetch);

  // 1. Start loading for User A
  const pendingA = controller.load({}, 'token-user-a', 'user-a');
  assert.strictEqual(controller.getState().isLoading, true);

  // 2. Switch principal to User B
  await controller.load({}, 'token-user-b', 'user-b');

  assert.strictEqual(controller.getState().isLoading, false);
  assert.strictEqual(controller.getState().recommendations[0].shop.id, 'shop-b');

  // 3. User A request resolves late
  resolveUserA({
    status: 'personalized',
    recommendations: [
      {
        shop: { id: 'shop-a', name: 'User A Shop' },
        explanation: 'User A match',
      },
    ],
    total_candidates_evaluated: 8,
  });
  await pendingA;

  // 4. User A's response was discarded
  assert.strictEqual(controller.getState().recommendations.length, 1);
  assert.strictEqual(controller.getState().recommendations[0].shop.id, 'shop-b');
});

test('PersonalizedRecommendationsController handles fetch error and sets errorMessage', async () => {
  const mockFetch = async () => {
    throw new Error('Network timeout loading recommendations.');
  };

  const controller = new PersonalizedRecommendationsController(mockFetch);
  await controller.load({}, 'token', 'user-1');

  const state = controller.getState();
  assert.strictEqual(state.isLoading, false);
  assert.strictEqual(state.errorMessage, 'Network timeout loading recommendations.');
  assert.deepStrictEqual(state.recommendations, []);
});

test('PersonalizedRecommendationsController cancel() increments request ID and discards in-flight result', async () => {
  let resolveFetch;
  const promise = new Promise((resolve) => {
    resolveFetch = resolve;
  });

  const mockFetch = async () => promise;
  const controller = new PersonalizedRecommendationsController(mockFetch);

  const pending = controller.load({}, 'token', 'user-1');
  assert.strictEqual(controller.getState().isLoading, true);

  // Cancel explicitly (e.g. unmount)
  controller.cancel();

  // Resolve after cancellation
  resolveFetch({
    status: 'personalized',
    recommendations: [{ shop: { id: 's1' }, explanation: 'exp' }],
    total_candidates_evaluated: 1,
  });
  await pending;

  // Response was discarded
  assert.deepStrictEqual(controller.getState().recommendations, []);
});

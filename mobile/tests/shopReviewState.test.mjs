import test from 'node:test';
import assert from 'node:assert';

/**
 * Harness modeling ShopDetailCard's internal state management,
 * monotonic request/mutation tracking, and context invalidation.
 */
class ShopDetailCardStateHarness {
  constructor(initialShop, initialAuthToken = 'token-1') {
    this.shop = initialShop;
    this.authToken = initialAuthToken;

    this.reviewsData = null;
    this.myReview = null;
    this.isLoadingReviews = false;
    this.reviewsError = null;

    this.isFormOpen = false;
    this.formRating = 5;
    this.formContent = '';
    this.isSubmitting = false;
    this.isDeleting = false;
    this.formError = null;
    this.deleteError = null;

    this.currentRequestId = 0;
    this.currentMutationId = 0;
    this.loadReviewsCallCount = 0;
  }

  // Simulates context change (shop.id or authToken change)
  switchContext(newShop, newAuthToken = this.authToken) {
    this.currentRequestId += 1;
    this.currentMutationId += 1;

    this.shop = newShop;
    this.authToken = newAuthToken;

    this.isFormOpen = false;
    this.formRating = 5;
    this.formContent = '';
    this.isSubmitting = false;
    this.isDeleting = false;
    this.formError = null;
    this.deleteError = null;
    this.myReview = null;
    this.reviewsData = null;
    this.reviewsError = null;
  }

  // Simulates asynchronous review loading
  async loadReviews(fetchFn, delayMs = 10) {
    const requestId = ++this.currentRequestId;
    this.isLoadingReviews = true;
    this.reviewsError = null;
    this.loadReviewsCallCount += 1;

    try {
      const data = await fetchFn(this.shop.id, this.authToken, delayMs);
      if (requestId === this.currentRequestId) {
        this.reviewsData = data.reviewsData;
        this.myReview = data.myReview;
        this.deleteError = null;
      }
    } catch (err) {
      if (requestId === this.currentRequestId) {
        this.reviewsError = err.message;
      }
    } finally {
      if (requestId === this.currentRequestId) {
        this.isLoadingReviews = false;
      }
    }
  }

  // Simulates review submission
  async submitReview(submitFn, delayMs = 10) {
    if (!this.authToken) return;
    const mutationId = ++this.currentMutationId;
    const activeShopId = this.shop.id;
    const activeToken = this.authToken;
    this.isSubmitting = true;
    this.formError = null;

    try {
      await submitFn(activeShopId, activeToken, delayMs);
      if (
        mutationId === this.currentMutationId &&
        activeShopId === this.shop.id &&
        activeToken === this.authToken
      ) {
        this.isFormOpen = false;
        this.loadReviewsCallCount += 1;
      }
    } catch (err) {
      if (
        mutationId === this.currentMutationId &&
        activeShopId === this.shop.id &&
        activeToken === this.authToken
      ) {
        this.formError = err.message;
      }
    } finally {
      if (
        mutationId === this.currentMutationId &&
        activeShopId === this.shop.id &&
        activeToken === this.authToken
      ) {
        this.isSubmitting = false;
      }
    }
  }

  // Simulates review deletion
  async deleteReview(deleteFn, delayMs = 10) {
    if (!this.authToken) return;
    const mutationId = ++this.currentMutationId;
    const activeShopId = this.shop.id;
    const activeToken = this.authToken;
    this.isDeleting = true;
    this.deleteError = null;

    try {
      await deleteFn(activeShopId, activeToken, delayMs);
      if (
        mutationId === this.currentMutationId &&
        activeShopId === this.shop.id &&
        activeToken === this.authToken
      ) {
        this.isFormOpen = false;
        this.myReview = null;
        this.loadReviewsCallCount += 1;
      }
    } catch (err) {
      if (
        mutationId === this.currentMutationId &&
        activeShopId === this.shop.id &&
        activeToken === this.authToken
      ) {
        this.deleteError = err.message;
      }
    } finally {
      if (
        mutationId === this.currentMutationId &&
        activeShopId === this.shop.id &&
        activeToken === this.authToken
      ) {
        this.isDeleting = false;
      }
    }
  }
}

test('Shop A -> Shop B while review loading is in progress does not apply stale reviews', async () => {
  const harness = new ShopDetailCardStateHarness({ id: 'shop-A', name: 'Shop A' });

  // Slow fetch for Shop A (50ms)
  const slowFetchA = harness.loadReviews(async () => {
    await new Promise((resolve) => setTimeout(resolve, 50));
    return { reviewsData: { total_reviews_count: 10, source: 'shop-A' }, myReview: null };
  });

  // Switch to Shop B immediately
  harness.switchContext({ id: 'shop-B', name: 'Shop B' });

  // Fast fetch for Shop B (10ms)
  const fastFetchB = harness.loadReviews(async () => {
    await new Promise((resolve) => setTimeout(resolve, 10));
    return { reviewsData: { total_reviews_count: 3, source: 'shop-B' }, myReview: { rating: 5 } };
  });

  await Promise.all([slowFetchA, fastFetchB]);

  // Assert Shop B data is retained, and Shop A was discarded
  assert.strictEqual(harness.shop.id, 'shop-B');
  assert.strictEqual(harness.reviewsData?.source, 'shop-B');
  assert.strictEqual(harness.reviewsData?.total_reviews_count, 3);
  assert.strictEqual(harness.myReview?.rating, 5);
  assert.strictEqual(harness.isLoadingReviews, false);
});

test('Shop A -> Shop B while submission is in progress resets state and ignores stale mutation', async () => {
  const harness = new ShopDetailCardStateHarness({ id: 'shop-A', name: 'Shop A' });

  // Open form for Shop A and start typing
  harness.isFormOpen = true;
  harness.formRating = 4;
  harness.formContent = 'Review for Shop A';

  // Trigger submission (slow 40ms)
  const submissionPromise = harness.submitReview(async () => {
    await new Promise((resolve) => setTimeout(resolve, 40));
  });

  assert.strictEqual(harness.isSubmitting, true);

  // User switches to Shop B while Shop A submission is in flight
  harness.switchContext({ id: 'shop-B', name: 'Shop B' });

  // User opens form for Shop B and types fresh content
  harness.isFormOpen = true;
  harness.formRating = 5;
  harness.formContent = 'Review for Shop B';

  // Submission for Shop B must not be stuck in submitting
  assert.strictEqual(harness.isSubmitting, false);
  const initialLoadCount = harness.loadReviewsCallCount;

  // Wait for Shop A's slow submission to finish
  await submissionPromise;

  // Verify Shop A's completion did NOT close Shop B's form or trigger loadReviews on Shop B
  assert.strictEqual(harness.shop.id, 'shop-B');
  assert.strictEqual(harness.isFormOpen, true);
  assert.strictEqual(harness.formContent, 'Review for Shop B');
  assert.strictEqual(harness.formRating, 5);
  assert.strictEqual(harness.isSubmitting, false);
  assert.strictEqual(harness.loadReviewsCallCount, initialLoadCount);
});

test('Shop A -> Shop B while deletion is in progress resets state and ignores stale deletion', async () => {
  const harness = new ShopDetailCardStateHarness({ id: 'shop-A', name: 'Shop A' });
  harness.myReview = { id: 'rev-A', rating: 3 };

  // Trigger deletion for Shop A (slow 40ms)
  const deletionPromise = harness.deleteReview(async () => {
    await new Promise((resolve) => setTimeout(resolve, 40));
  });

  assert.strictEqual(harness.isDeleting, true);

  // Switch to Shop B with its own review
  harness.switchContext({ id: 'shop-B', name: 'Shop B' });
  harness.myReview = { id: 'rev-B', rating: 5 };

  assert.strictEqual(harness.isDeleting, false);
  const initialLoadCount = harness.loadReviewsCallCount;

  // Wait for Shop A's deletion to finish
  await deletionPromise;

  // Verify Shop B's review was NOT cleared by Shop A's deletion
  assert.strictEqual(harness.shop.id, 'shop-B');
  assert.strictEqual(harness.myReview?.id, 'rev-B');
  assert.strictEqual(harness.isDeleting, false);
  assert.strictEqual(harness.loadReviewsCallCount, initialLoadCount);
});

test('Auth token changes while an operation is in flight discards stale results', async () => {
  const harness = new ShopDetailCardStateHarness({ id: 'shop-A', name: 'Shop A' }, 'token-user-1');

  // Trigger review submission under user 1
  const submitPromise = harness.submitReview(async () => {
    await new Promise((resolve) => setTimeout(resolve, 30));
  });

  // User logs out or switches accounts to user 2
  harness.switchContext(harness.shop, 'token-user-2');

  await submitPromise;

  // Verify user 1's operation did not trigger reloads or leave submitting stuck
  assert.strictEqual(harness.authToken, 'token-user-2');
  assert.strictEqual(harness.isSubmitting, false);
  assert.strictEqual(harness.formError, null);
});

test('Failed stale operation does not set error on newly selected shop', async () => {
  const harness = new ShopDetailCardStateHarness({ id: 'shop-A', name: 'Shop A' });

  // Start submission for Shop A that will fail
  const failingSubmitPromise = harness.submitReview(async () => {
    await new Promise((resolve) => setTimeout(resolve, 30));
    throw new Error('Network timeout for Shop A');
  });

  // Switch to Shop B before failure resolves
  harness.switchContext({ id: 'shop-B', name: 'Shop B' });

  await failingSubmitPromise;

  // Shop B must not display Shop A's error
  assert.strictEqual(harness.shop.id, 'shop-B');
  assert.strictEqual(harness.formError, null);
  assert.strictEqual(harness.deleteError, null);
  assert.strictEqual(harness.isSubmitting, false);
});

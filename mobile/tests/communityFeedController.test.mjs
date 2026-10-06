import test from 'node:test';
import assert from 'node:assert';
import { CommunityFeedController } from '../src/hooks/useCommunityFeed.ts';

test('CommunityFeedController initializes with empty state', () => {
  const controller = new CommunityFeedController();
  const state = controller.getState();
  assert.deepStrictEqual(state.items, []);
  assert.strictEqual(state.isLoading, false);
  assert.strictEqual(state.isLoadingMore, false);
  assert.strictEqual(state.isRefreshing, false);
  assert.strictEqual(state.hasMore, false);
  assert.strictEqual(state.errorMessage, null);
});

test('CommunityFeedController resets state when unauthenticated or token missing', async () => {
  const controller = new CommunityFeedController();
  await controller.loadInitial(null, null);
  const state = controller.getState();
  assert.deepStrictEqual(state.items, []);
  assert.strictEqual(state.isLoading, false);

  await controller.loadInitial('   ', 'user-1');
  assert.deepStrictEqual(controller.getState().items, []);
});

test('CommunityFeedController loadInitial successfully loads page 0 and updates state', async () => {
  const mockItems = [
    { id: '1', shop_id: 's1', shop_name: 'Shop 1', author_name: 'A', rating: 5, content: 'Good', created_at: '2026-10-07T00:00:00Z', updated_at: null, is_edited: false },
    { id: '2', shop_id: 's2', shop_name: 'Shop 2', author_name: 'B', rating: 4, content: 'Nice', created_at: '2026-10-06T00:00:00Z', updated_at: null, is_edited: false },
  ];

  let capturedLimit = 0;
  let capturedOffset = 0;
  const mockFetch = async (_token, limit, offset) => {
    capturedLimit = limit;
    capturedOffset = offset;
    return {
      items: mockItems,
      limit,
      offset,
      has_more: true,
    };
  };

  const controller = new CommunityFeedController(mockFetch);
  let listenerCalled = false;
  controller.subscribe((state) => {
    if (state.items.length > 0) {
      listenerCalled = true;
    }
  });

  await controller.loadInitial('token-123', 'user-1');
  const state = controller.getState();

  assert.strictEqual(listenerCalled, true);
  assert.deepStrictEqual(state.items, mockItems);
  assert.strictEqual(state.hasMore, true);
  assert.strictEqual(state.isLoading, false);
  assert.strictEqual(state.errorMessage, null);
  assert.strictEqual(capturedLimit, 20);
  assert.strictEqual(capturedOffset, 0);
});

test('CommunityFeedController loadMore appends items and deduplicates by id', async () => {
  const page1 = [
    { id: '1', shop_id: 's1', shop_name: 'Shop 1', author_name: 'A', rating: 5, content: 'Good', created_at: '2026-10-07T00:00:00Z', updated_at: null, is_edited: false },
  ];
  const page2 = [
    // Includes duplicate '1' and new '2'
    { id: '1', shop_id: 's1', shop_name: 'Shop 1', author_name: 'A', rating: 5, content: 'Good', created_at: '2026-10-07T00:00:00Z', updated_at: null, is_edited: false },
    { id: '2', shop_id: 's2', shop_name: 'Shop 2', author_name: 'B', rating: 4, content: 'Nice', created_at: '2026-10-06T00:00:00Z', updated_at: null, is_edited: false },
  ];

  let callCount = 0;
  const mockFetch = async (_token, limit, offset) => {
    callCount += 1;
    if (offset === 0) {
      return { items: page1, limit, offset: 0, has_more: true };
    }
    return { items: page2, limit, offset, has_more: false };
  };

  const controller = new CommunityFeedController(mockFetch);
  await controller.loadInitial('token-123', 'user-1');
  assert.strictEqual(controller.getState().items.length, 1);
  assert.strictEqual(controller.getState().hasMore, true);

  await controller.loadMore('token-123', 'user-1');
  const finalState = controller.getState();
  assert.strictEqual(finalState.items.length, 2);
  assert.strictEqual(finalState.items[0].id, '1');
  assert.strictEqual(finalState.items[1].id, '2');
  assert.strictEqual(finalState.hasMore, false);
  assert.strictEqual(finalState.isLoadingMore, false);
});

test('CommunityFeedController loadMore does nothing when hasMore is false', async () => {
  let fetchCalls = 0;
  const mockFetch = async () => {
    fetchCalls += 1;
    return { items: [{ id: '1' }], limit: 20, offset: 0, has_more: false };
  };

  const controller = new CommunityFeedController(mockFetch);
  await controller.loadInitial('token-123', 'user-1');
  assert.strictEqual(fetchCalls, 1);

  // Calling loadMore when hasMore is false must exit early
  await controller.loadMore('token-123', 'user-1');
  assert.strictEqual(fetchCalls, 1);
});

test('CommunityFeedController refresh reloads page 0 with isRefreshing state', async () => {
  const freshItems = [
    { id: 'new-1', shop_id: 's1', shop_name: 'Fresh Cafe', author_name: 'New', rating: 5, content: 'Fresh', created_at: '2026-10-07T00:00:00Z', updated_at: null, is_edited: false },
  ];

  const mockFetch = async () => ({
    items: freshItems,
    limit: 20,
    offset: 0,
    has_more: false,
  });

  const controller = new CommunityFeedController(mockFetch);
  await controller.refresh('token-123', 'user-1');
  const state = controller.getState();
  assert.deepStrictEqual(state.items, freshItems);
  assert.strictEqual(state.isRefreshing, false);
  assert.strictEqual(state.hasMore, false);
});

test('CommunityFeedController discards out-of-order stale responses', async () => {
  let resolveReq1;
  let resolveReq2;
  let callIndex = 0;

  const mockFetch = () => {
    callIndex += 1;
    if (callIndex === 1) {
      return new Promise((resolve) => {
        resolveReq1 = resolve;
      });
    }
    return new Promise((resolve) => {
      resolveReq2 = resolve;
    });
  };

  const controller = new CommunityFeedController(mockFetch);

  // Start request 1 (initial)
  const promise1 = controller.loadInitial('token-1', 'user-1');

  // Start request 2 (trigger another initial reload with newer parameters)
  const promise2 = controller.loadInitial('token-2', 'user-1');

  // Resolve request 2 first
  resolveReq2({
    items: [{ id: 'newer' }],
    limit: 20,
    offset: 0,
    has_more: false,
  });
  await promise2;

  assert.strictEqual(controller.getState().items[0].id, 'newer');

  // Late resolution of request 1
  resolveReq1({
    items: [{ id: 'older' }],
    limit: 20,
    offset: 0,
    has_more: true,
  });
  await promise1;

  // Stale response must be discarded; state remains 'newer'
  assert.strictEqual(controller.getState().items[0].id, 'newer');
});

test('CommunityFeedController principal switch immediately clears state and isolates accounts', async () => {
  const mockFetch = async (_token, _limit, _offset) => ({
    items: [{ id: 'user-a-item' }],
    limit: 20,
    offset: 0,
    has_more: false,
  });

  const controller = new CommunityFeedController(mockFetch);
  await controller.loadInitial('token-a', 'user-A');
  assert.strictEqual(controller.getState().items[0].id, 'user-a-item');

  // Switch to user-B
  let clearedDuringSwitch = false;
  controller.subscribe((state) => {
    if (state.items.length === 0 && state.isLoading) {
      clearedDuringSwitch = true;
    }
  });

  const userBPromise = controller.loadInitial('token-b', 'user-B');
  assert.strictEqual(clearedDuringSwitch, true);
  await userBPromise;
});

test('CommunityFeedController cancel() during initial load clears isLoading and drops active in-flight request', async () => {
  let resolveReq;
  const mockFetch = () =>
    new Promise((resolve) => {
      resolveReq = resolve;
    });

  const controller = new CommunityFeedController(mockFetch);
  const loadPromise = controller.loadInitial('token-1', 'user-1');
  assert.strictEqual(controller.getState().isLoading, true);

  // Cancel while in flight
  controller.cancel();
  assert.strictEqual(controller.getState().isLoading, false);

  // Resolve late
  resolveReq({
    items: [{ id: 'late-item' }],
    limit: 20,
    offset: 0,
    has_more: false,
  });
  await loadPromise;

  // Items must remain empty and isLoading false
  assert.deepStrictEqual(controller.getState().items, []);
  assert.strictEqual(controller.getState().isLoading, false);
});

test('CommunityFeedController cancel() during loadMore clears isLoadingMore and preserves items/metadata', async () => {
  const initialItems = [{ id: '1', shop_id: 's1' }];
  let resolveLoadMore;
  let callCount = 0;

  const mockFetch = async (_token, limit, offset) => {
    callCount += 1;
    if (offset === 0) {
      return { items: initialItems, limit, offset: 0, has_more: true };
    }
    return new Promise((resolve) => {
      resolveLoadMore = resolve;
    });
  };

  const controller = new CommunityFeedController(mockFetch);
  await controller.loadInitial('token-1', 'user-1');
  assert.strictEqual(controller.getState().items.length, 1);
  assert.strictEqual(controller.getState().hasMore, true);

  // Start loadMore
  const loadMorePromise = controller.loadMore('token-1', 'user-1');
  assert.strictEqual(controller.getState().isLoadingMore, true);

  // Cancel while in-flight
  controller.cancel();
  assert.strictEqual(controller.getState().isLoadingMore, false);
  assert.strictEqual(controller.getState().items.length, 1);
  assert.strictEqual(controller.getState().hasMore, true);

  // Resolve late
  resolveLoadMore({
    items: [{ id: '2', shop_id: 's2' }],
    limit: 20,
    offset: 1,
    has_more: false,
  });
  await loadMorePromise;

  // Stale append must be dropped; state remains unchanged
  assert.strictEqual(controller.getState().items.length, 1);
  assert.strictEqual(controller.getState().isLoadingMore, false);
});

test('CommunityFeedController cancel() during refresh clears isRefreshing and preserves items/metadata', async () => {
  const initialItems = [{ id: '1', shop_id: 's1' }];
  let resolveRefresh;
  let callCount = 0;
  const mockFetch = async (_token, limit, offset) => {
    callCount += 1;
    if (callCount === 1) {
      return { items: initialItems, limit, offset: 0, has_more: true };
    }
    return new Promise((resolve) => {
      resolveRefresh = resolve;
    });
  };

  const controller = new CommunityFeedController(mockFetch);
  await controller.loadInitial('token-1', 'user-1');
  assert.strictEqual(controller.getState().items.length, 1);

  // Start refresh
  const refreshPromise = controller.refresh('token-1', 'user-1');
  assert.strictEqual(controller.getState().isRefreshing, true);

  // Cancel while in-flight
  controller.cancel();
  assert.strictEqual(controller.getState().isRefreshing, false);
  assert.strictEqual(controller.getState().items.length, 1);

  // Resolve refresh late with different items
  resolveRefresh({
    items: [{ id: 'fresh-1', shop_id: 's9' }],
    limit: 20,
    offset: 0,
    has_more: false,
  });
  await refreshPromise;

  // Stale refresh dropped
  assert.strictEqual(controller.getState().items[0].id, '1');
  assert.strictEqual(controller.getState().isRefreshing, false);
});

test('CommunityFeedController refresh failure clears isLoadingMore and unblocks subsequent loadMore', async () => {
  let resolveLoadMore;
  let rejectRefresh;
  let resolveSecondLoadMore;
  let callCount = 0;

  const initialItems = [{ id: '1', shop_id: 's1' }];

  const mockFetch = async (_token, limit, offset) => {
    callCount += 1;
    if (callCount === 1) {
      // initial load
      return { items: initialItems, limit, offset: 0, has_more: true };
    }
    if (callCount === 2) {
      // first loadMore
      return new Promise((resolve) => {
        resolveLoadMore = resolve;
      });
    }
    if (callCount === 3) {
      // refresh
      return new Promise((_, reject) => {
        rejectRefresh = reject;
      });
    }
    if (callCount === 4) {
      // second loadMore
      return new Promise((resolve) => {
        resolveSecondLoadMore = resolve;
      });
    }
    throw new Error('Unexpected call');
  };

  const controller = new CommunityFeedController(mockFetch);
  await controller.loadInitial('token-1', 'user-1');
  assert.strictEqual(controller.getState().items.length, 1);
  assert.strictEqual(controller.getState().hasMore, true);

  // 1. Start loadMore()
  const loadMorePromise1 = controller.loadMore('token-1', 'user-1');
  assert.strictEqual(controller.getState().isLoadingMore, true);

  // 2. Start refresh() so loadMore becomes stale
  const refreshPromise = controller.refresh('token-1', 'user-1');
  assert.strictEqual(controller.getState().isRefreshing, true);
  // isLoadingMore was set by loadMore
  assert.strictEqual(controller.getState().isLoadingMore, true);

  // 3. Make refresh fail
  rejectRefresh(new Error('Refresh network error'));
  await refreshPromise;

  // 4. Verify isLoadingMore === false and error reported
  assert.strictEqual(controller.getState().isLoadingMore, false);
  assert.strictEqual(controller.getState().isRefreshing, false);
  assert.strictEqual(controller.getState().errorMessage, 'Refresh network error');

  // Finish stale loadMore promise to ensure no pending unhandled rejection
  resolveLoadMore({ items: [{ id: 'stale-2' }], limit: 20, offset: 1, has_more: false });
  await loadMorePromise1;

  // Stale loadMore result was dropped
  assert.strictEqual(controller.getState().items.length, 1);
  assert.strictEqual(controller.getState().isLoadingMore, false);

  // 5. Verify a later loadMore() can run normally
  const loadMorePromise2 = controller.loadMore('token-1', 'user-1');
  assert.strictEqual(controller.getState().isLoadingMore, true);

  resolveSecondLoadMore({
    items: [{ id: '2', shop_id: 's2' }],
    limit: 20,
    offset: 1,
    has_more: false,
  });
  await loadMorePromise2;

  assert.strictEqual(controller.getState().items.length, 2);
  assert.strictEqual(controller.getState().items[1].id, '2');
  assert.strictEqual(controller.getState().isLoadingMore, false);
  assert.strictEqual(controller.getState().hasMore, false);
});

test('CommunityFeedController handles fetch error and updates errorMessage', async () => {
  const failingFetch = async () => {
    throw new Error('Network timeout');
  };

  const controller = new CommunityFeedController(failingFetch);
  await controller.loadInitial('token-1', 'user-1');
  const state = controller.getState();
  assert.strictEqual(state.isLoading, false);
  assert.strictEqual(state.errorMessage, 'Network timeout');
  assert.deepStrictEqual(state.items, []);
});

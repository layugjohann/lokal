import { useState, useEffect, useCallback, useRef } from 'react';
import type { CommunityFeedItem, CommunityFeedResponse } from '../types/community';
import { fetchCommunityFeed } from '../services/communityService.ts';

export interface CommunityFeedState {
  items: CommunityFeedItem[];
  isLoading: boolean;
  isLoadingMore: boolean;
  isRefreshing: boolean;
  hasMore: boolean;
  errorMessage: string | null;
}

export type CommunityFeedListener = (state: CommunityFeedState) => void;

const PAGE_SIZE = 20;

/**
 * Encapsulates asynchronous community feed pagination, monotonic request sequencing,
 * stale-response discarding, and user-principal isolation.
 */
export class CommunityFeedController {
  private requestId = 0;
  private currentPrincipal: string | null = null;
  private state: CommunityFeedState;
  private listeners = new Set<CommunityFeedListener>();
  private fetchFn: (
    token: string,
    limit: number,
    offset: number
  ) => Promise<CommunityFeedResponse>;

  constructor(
    fetchFn: (
      token: string,
      limit: number,
      offset: number
    ) => Promise<CommunityFeedResponse> = fetchCommunityFeed,
    initialItems: CommunityFeedItem[] = [],
    initialPrincipal: string | null = null
  ) {
    this.fetchFn = fetchFn;
    this.currentPrincipal = initialPrincipal;
    this.state = {
      items: initialItems,
      isLoading: false,
      isLoadingMore: false,
      isRefreshing: false,
      hasMore: false,
      errorMessage: null,
    };
  }

  /**
   * Returns the current immutable snapshot of feed state.
   */
  getState(): CommunityFeedState {
    return this.state;
  }

  /**
   * Subscribes a listener to feed state updates and returns an unsubscribe function.
   */
  subscribe(listener: CommunityFeedListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private setState(nextState: CommunityFeedState): void {
    this.state = nextState;
    this.listeners.forEach((listener) => listener(nextState));
  }

  /**
   * Invalidates any active in-flight requests by bumping the monotonic sequence counter
   * and clearing active loading flags.
   */
  cancel(): void {
    this.requestId += 1;
    if (this.state.isLoading || this.state.isLoadingMore || this.state.isRefreshing) {
      this.setState({
        ...this.state,
        isLoading: false,
        isLoadingMore: false,
        isRefreshing: false,
      });
    }
  }

  /**
   * Loads the initial page (offset = 0) for the given token and authenticated principal.
   * Clears cached feed items immediately if the principal changed.
   */
  async loadInitial(
    authToken?: string | null,
    principalId?: string | null
  ): Promise<void> {
    const trimmed = authToken?.trim() || null;
    const effectivePrincipal = principalId !== undefined ? principalId : trimmed;

    if (!trimmed || !effectivePrincipal) {
      this.requestId += 1;
      this.currentPrincipal = null;
      this.setState({
        items: [],
        isLoading: false,
        isLoadingMore: false,
        isRefreshing: false,
        hasMore: false,
        errorMessage: null,
      });
      return;
    }

    const currentId = ++this.requestId;
    const isNewPrincipal = effectivePrincipal !== this.currentPrincipal;
    this.currentPrincipal = effectivePrincipal;

    this.setState({
      items: isNewPrincipal ? [] : this.state.items,
      isLoading: true,
      isLoadingMore: false,
      isRefreshing: false,
      hasMore: isNewPrincipal ? false : this.state.hasMore,
      errorMessage: null,
    });

    try {
      const data = await this.fetchFn(trimmed, PAGE_SIZE, 0);
      if (currentId !== this.requestId) {
        return;
      }
      this.setState({
        items: data.items,
        isLoading: false,
        isLoadingMore: false,
        isRefreshing: false,
        hasMore: data.has_more,
        errorMessage: null,
      });
    } catch (err: unknown) {
      if (currentId !== this.requestId) {
        return;
      }
      const message =
        err instanceof Error ? err.message : 'Unable to load community feed.';
      this.setState({
        items: isNewPrincipal ? [] : this.state.items,
        isLoading: false,
        isLoadingMore: false,
        isRefreshing: false,
        hasMore: isNewPrincipal ? false : this.state.hasMore,
        errorMessage: message,
      });
    }
  }

  /**
   * Fetches the next page of feed items and appends unique items.
   */
  async loadMore(
    authToken?: string | null,
    principalId?: string | null
  ): Promise<void> {
    const trimmed = authToken?.trim() || null;
    const effectivePrincipal = principalId !== undefined ? principalId : trimmed;

    if (
      !trimmed ||
      !effectivePrincipal ||
      this.state.isLoading ||
      this.state.isLoadingMore ||
      this.state.isRefreshing ||
      !this.state.hasMore
    ) {
      return;
    }

    if (effectivePrincipal !== this.currentPrincipal) {
      return this.loadInitial(authToken, principalId);
    }

    const currentId = ++this.requestId;
    const offset = this.state.items.length;

    this.setState({
      ...this.state,
      isLoadingMore: true,
      errorMessage: null,
    });

    try {
      const data = await this.fetchFn(trimmed, PAGE_SIZE, offset);
      if (currentId !== this.requestId) {
        return;
      }

      // Deduplicate appended items against existing IDs
      const existingIds = new Set(this.state.items.map((i) => i.id));
      const incomingUnique = data.items.filter((i) => !existingIds.has(i.id));

      this.setState({
        items: [...this.state.items, ...incomingUnique],
        isLoading: false,
        isLoadingMore: false,
        isRefreshing: false,
        hasMore: data.has_more,
        errorMessage: null,
      });
    } catch (err: unknown) {
      if (currentId !== this.requestId) {
        return;
      }
      const message =
        err instanceof Error ? err.message : 'Unable to load additional feed items.';
      this.setState({
        ...this.state,
        isLoadingMore: false,
        errorMessage: message,
      });
    }
  }

  /**
   * Refreshes the feed (offset = 0) with a pull-to-refresh spinner.
   */
  async refresh(
    authToken?: string | null,
    principalId?: string | null
  ): Promise<void> {
    const trimmed = authToken?.trim() || null;
    const effectivePrincipal = principalId !== undefined ? principalId : trimmed;

    if (!trimmed || !effectivePrincipal || this.state.isLoading || this.state.isRefreshing) {
      return;
    }

    const currentId = ++this.requestId;
    this.currentPrincipal = effectivePrincipal;

    this.setState({
      ...this.state,
      isRefreshing: true,
      errorMessage: null,
    });

    try {
      const data = await this.fetchFn(trimmed, PAGE_SIZE, 0);
      if (currentId !== this.requestId) {
        return;
      }
      this.setState({
        items: data.items,
        isLoading: false,
        isLoadingMore: false,
        isRefreshing: false,
        hasMore: data.has_more,
        errorMessage: null,
      });
    } catch (err: unknown) {
      if (currentId !== this.requestId) {
        return;
      }
      const message =
        err instanceof Error ? err.message : 'Unable to refresh community feed.';
      this.setState({
        ...this.state,
        isLoadingMore: false,
        isRefreshing: false,
        errorMessage: message,
      });
    }
  }
}

/**
 * React hook connecting components to CommunityFeedController.
 */
export function useCommunityFeed(
  authToken?: string | null,
  userId?: string | null,
  enabled: boolean = true
) {
  const controllerRef = useRef<CommunityFeedController | null>(null);

  if (!controllerRef.current) {
    controllerRef.current = new CommunityFeedController();
  }

  const [state, setState] = useState<CommunityFeedState>(
    controllerRef.current.getState()
  );

  useEffect(() => {
    const controller = controllerRef.current;
    if (!controller) return;

    const unsubscribe = controller.subscribe((nextState) => {
      setState(nextState);
    });

    return () => {
      unsubscribe();
    };
  }, []);

  useEffect(() => {
    const controller = controllerRef.current;
    if (!controller) return;

    if (enabled && authToken && userId) {
      void controller.loadInitial(authToken, userId);
    } else {
      controller.cancel();
    }
  }, [enabled, authToken, userId]);

  const loadMore = useCallback(() => {
    if (enabled && authToken && userId) {
      void controllerRef.current?.loadMore(authToken, userId);
    }
  }, [enabled, authToken, userId]);

  const refresh = useCallback(() => {
    if (enabled && authToken && userId) {
      void controllerRef.current?.refresh(authToken, userId);
    }
  }, [enabled, authToken, userId]);

  const refetch = useCallback(() => {
    if (enabled && authToken && userId) {
      void controllerRef.current?.loadInitial(authToken, userId);
    }
  }, [enabled, authToken, userId]);

  return {
    items: state.items,
    isLoading: state.isLoading,
    isLoadingMore: state.isLoadingMore,
    isRefreshing: state.isRefreshing,
    hasMore: state.hasMore,
    errorMessage: state.errorMessage,
    loadMore,
    refresh,
    refetch,
    cancel: useCallback(() => controllerRef.current?.cancel(), []),
  };
}

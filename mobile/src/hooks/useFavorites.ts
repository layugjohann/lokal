import { useState, useEffect, useCallback, useRef } from 'react';
import type { FavoriteShop } from '../types/favorite';
import { fetchUserFavorites } from '../services/favoriteService.ts';

export interface FavoritesState {
  favorites: FavoriteShop[];
  isLoading: boolean;
  errorMessage: string | null;
}

export type FavoritesListener = (state: FavoritesState) => void;

/**
 * Encapsulates asynchronous favorites lifecycle, optimistic removal, and
 * monotonic request sequencing to prevent stale or race-conditioned state.
 */
export class FavoritesController {
  private requestId = 0;
  private currentPrincipal: string | null;
  private state: FavoritesState;
  private listeners = new Set<FavoritesListener>();
  private fetchFn: (token: string) => Promise<FavoriteShop[]>;

  constructor(
    fetchFn: (token: string) => Promise<FavoriteShop[]> = fetchUserFavorites,
    initialFavorites: FavoriteShop[] = [],
    initialPrincipal: string | null = null
  ) {
    this.fetchFn = fetchFn;
    this.currentPrincipal = initialPrincipal;
    this.state = {
      favorites: initialFavorites,
      isLoading: false,
      errorMessage: null,
    };
  }

  /**
   * Returns the current immutable snapshot of favorites state.
   */
  getState(): FavoritesState {
    return this.state;
  }

  /**
   * Subscribes a listener to favorites state updates and returns an unsubscribe cleanup function.
   */
  subscribe(listener: FavoritesListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private setState(nextState: FavoritesState): void {
    this.state = nextState;
    this.listeners.forEach((listener) => listener(nextState));
  }

  /**
   * Invalidates any active in-flight requests by bumping the monotonic request ID.
   */
  cancel(): void {
    this.requestId += 1;
  }

  /**
   * Authoritatively loads favorites for the given token and principal.
   * Clears cached favorites immediately if the authenticated principal has changed.
   */
  async load(
    authToken?: string | null,
    principalId?: string | null
  ): Promise<void> {
    const trimmed = authToken?.trim() || null;
    const effectivePrincipal = principalId !== undefined ? principalId : trimmed;

    if (!trimmed || !effectivePrincipal) {
      this.requestId += 1;
      this.currentPrincipal = null;
      this.setState({
        favorites: [],
        isLoading: false,
        errorMessage: null,
      });
      return;
    }

    const currentId = ++this.requestId;
    const isNewPrincipal = effectivePrincipal !== this.currentPrincipal;
    this.currentPrincipal = effectivePrincipal;

    this.setState({
      favorites: isNewPrincipal ? [] : this.state.favorites,
      isLoading: true,
      errorMessage: null,
    });

    try {
      const data = await this.fetchFn(trimmed);
      if (currentId !== this.requestId) {
        return;
      }
      this.setState({
        favorites: data,
        isLoading: false,
        errorMessage: null,
      });
    } catch (err: unknown) {
      if (currentId !== this.requestId) {
        return;
      }
      const message =
        err instanceof Error ? err.message : 'Unable to load favorite coffee shops.';
      this.setState({
        favorites: isNewPrincipal ? [] : this.state.favorites,
        isLoading: false,
        errorMessage: message,
      });
    }
  }

  /**
   * Optimistically removes a coffee shop from current favorites without waiting for network.
   */
  removeOptimistic(shopId: string): void {
    this.setState({
      ...this.state,
      favorites: this.state.favorites.filter((item) => item.id !== shopId),
    });
  }
}

export interface UseFavoritesResult {
  favorites: FavoriteShop[];
  isLoading: boolean;
  errorMessage: string | null;
  refetch: () => Promise<void>;
  removeFavoriteOptimistic: (shopId: string) => void;
}

/**
 * Custom React hook managing the authenticated user's favorites list,
 * providing monotonic request sequencing, optimistic removal, and state isolation.
 */
export function useFavorites(
  authToken?: string | null,
  principalId?: string | null
): UseFavoritesResult {
  const controllerRef = useRef<FavoritesController | null>(null);
  if (!controllerRef.current) {
    controllerRef.current = new FavoritesController();
  }
  const controller = controllerRef.current;

  const [state, setState] = useState<FavoritesState>(() => controller.getState());

  useEffect(() => {
    const unsubscribe = controller.subscribe((nextState) => {
      setState(nextState);
    });
    return () => {
      unsubscribe();
    };
  }, [controller]);

  useEffect(() => {
    controller.load(authToken, principalId);
    return () => {
      controller.cancel();
    };
  }, [controller, authToken, principalId]);

  const refetch = useCallback(async () => {
    await controller.load(authToken, principalId);
  }, [controller, authToken, principalId]);

  const removeFavoriteOptimistic = useCallback(
    (shopId: string) => {
      controller.removeOptimistic(shopId);
    },
    [controller]
  );

  return {
    favorites: state.favorites,
    isLoading: state.isLoading,
    errorMessage: state.errorMessage,
    refetch,
    removeFavoriteOptimistic,
  };
}

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
  private state: FavoritesState;
  private listeners = new Set<FavoritesListener>();
  private fetchFn: (token: string) => Promise<FavoriteShop[]>;

  constructor(
    fetchFn: (token: string) => Promise<FavoriteShop[]> = fetchUserFavorites,
    initialFavorites: FavoriteShop[] = []
  ) {
    this.fetchFn = fetchFn;
    this.state = {
      favorites: initialFavorites,
      isLoading: false,
      errorMessage: null,
    };
  }

  getState(): FavoritesState {
    return this.state;
  }

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

  cancel(): void {
    this.requestId += 1;
  }

  async load(authToken?: string | null): Promise<void> {
    const trimmed = authToken?.trim();
    if (!trimmed) {
      this.requestId += 1;
      this.setState({
        favorites: [],
        isLoading: false,
        errorMessage: null,
      });
      return;
    }

    const currentId = ++this.requestId;
    this.setState({
      ...this.state,
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
        ...this.state,
        isLoading: false,
        errorMessage: message,
      });
    }
  }

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

export function useFavorites(authToken?: string | null): UseFavoritesResult {
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
    controller.load(authToken);
    return () => {
      controller.cancel();
    };
  }, [controller, authToken]);

  const refetch = useCallback(async () => {
    await controller.load(authToken);
  }, [controller, authToken]);

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

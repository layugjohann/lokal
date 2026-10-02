import { useState, useEffect, useCallback, useRef } from 'react';
import type { Shop, NearbySearchParams } from '../types/shop.ts';
import type { LocationCoordinates } from '../types/location.ts';
import { fetchNearbyShops } from '../services/shopService.ts';

export interface NearbyShopsState {
  shops: Shop[];
  isLoading: boolean;
  errorMessage: string | null;
  selectedShop: Shop | null;
}

export type NearbyShopsListener = (state: NearbyShopsState) => void;

/**
 * Encapsulates asynchronous nearby coffee shop discovery lifecycle,
 * monotonic request sequencing, selection synchronization, and
 * stale-response discarding.
 */
export class NearbyShopsController {
  private requestId = 0;
  private state: NearbyShopsState;
  private listeners = new Set<NearbyShopsListener>();
  private fetchFn: (
    params: NearbySearchParams,
    authToken?: string | null
  ) => Promise<Shop[]>;

  constructor(
    fetchFn: (
      params: NearbySearchParams,
      authToken?: string | null
    ) => Promise<Shop[]> = fetchNearbyShops,
    initialShops: Shop[] = []
  ) {
    this.fetchFn = fetchFn;
    this.state = {
      shops: initialShops,
      isLoading: false,
      errorMessage: null,
      selectedShop: null,
    };
  }

  /**
   * Returns the current immutable snapshot of nearby shops state.
   */
  getState(): NearbyShopsState {
    return this.state;
  }

  /**
   * Subscribes a listener to state updates and returns an unsubscribe cleanup function.
   */
  subscribe(listener: NearbyShopsListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  private setState(nextState: NearbyShopsState): void {
    this.state = nextState;
    this.listeners.forEach((listener) => listener(nextState));
  }

  /**
   * Updates the currently selected coffee shop.
   */
  setSelectedShop(shop: Shop | null): void {
    this.setState({
      ...this.state,
      selectedShop: shop,
    });
  }

  /**
   * Invalidates any active in-flight requests by bumping the monotonic request ID.
   */
  cancel(): void {
    this.requestId += 1;
  }

  /**
   * Loads nearby shops for the given parameters and auth token.
   * If parameters are null (e.g. location missing), invalidates in-flight requests
   * and resets state.
   */
  async load(
    params: NearbySearchParams | null,
    authToken?: string | null
  ): Promise<void> {
    if (!params) {
      this.requestId += 1;
      this.setState({
        shops: [],
        isLoading: false,
        errorMessage: null,
        selectedShop: null,
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
      const data = await this.fetchFn(params, authToken);

      if (currentId !== this.requestId) {
        return;
      }

      const prevSelected = this.state.selectedShop;
      const nextSelected = prevSelected
        ? data.find((s) => s.id === prevSelected.id) ?? null
        : null;

      this.setState({
        shops: data,
        isLoading: false,
        errorMessage: null,
        selectedShop: nextSelected,
      });
    } catch (err) {
      if (currentId !== this.requestId) {
        return;
      }

      const message =
        err instanceof Error
          ? err.message
          : 'Unable to load nearby coffee shops.';

      this.setState({
        ...this.state,
        isLoading: false,
        errorMessage: message,
      });
    }
  }
}

export interface UseNearbyShopsResult {
  shops: Shop[];
  isLoading: boolean;
  errorMessage: string | null;
  selectedShop: Shop | null;
  selectShop: (shop: Shop | null) => void;
  refetch: () => Promise<void>;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  minRating: number | null;
  setMinRating: (rating: number | null) => void;
  minLokalRating: number | null;
  setMinLokalRating: (rating: number | null) => void;
  radius: number;
  setRadius: (radius: number) => void;
  sortBy: 'distance' | 'rating' | 'lokal_rating';
  setSortBy: (sortBy: 'distance' | 'rating' | 'lokal_rating') => void;
  resetFilters: () => void;
  hasActiveFilters: boolean;
}

export function useNearbyShops(
  location: LocationCoordinates | null,
  authToken?: string | null
): UseNearbyShopsResult {
  const controllerRef = useRef<NearbyShopsController | null>(null);
  if (!controllerRef.current) {
    controllerRef.current = new NearbyShopsController();
  }
  const controller = controllerRef.current;

  const [state, setState] = useState<NearbyShopsState>(() => controller.getState());

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedQuery, setDebouncedQuery] = useState<string>('');
  const [minRating, setMinRating] = useState<number | null>(null);
  const [minLokalRating, setMinLokalRating] = useState<number | null>(null);
  const [radius, setRadius] = useState<number>(5000);
  const [sortBy, setSortBy] = useState<'distance' | 'rating' | 'lokal_rating'>('distance');

  useEffect(() => {
    const unsubscribe = controller.subscribe((nextState) => {
      setState(nextState);
    });
    return () => {
      unsubscribe();
    };
  }, [controller]);

  useEffect(() => {
    return () => {
      controller.cancel();
    };
  }, [controller]);

  // Debounce search query input by 350ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const hasActiveFilters = Boolean(
    searchQuery.trim() ||
      minRating !== null ||
      minLokalRating !== null ||
      sortBy !== 'distance' ||
      radius !== 5000
  );

  const resetFilters = useCallback(() => {
    setSearchQuery('');
    setDebouncedQuery('');
    setMinRating(null);
    setMinLokalRating(null);
    setRadius(5000);
    setSortBy('distance');
  }, []);

  const fetchShops = useCallback(async () => {
    await controller.load(
      location
        ? {
            latitude: location.latitude,
            longitude: location.longitude,
            radius,
            query: debouncedQuery,
            minRating: minRating ?? undefined,
            minLokalRating: minLokalRating ?? undefined,
            sortBy,
          }
        : null,
      authToken
    );
  }, [
    controller,
    location?.latitude,
    location?.longitude,
    radius,
    debouncedQuery,
    minRating,
    minLokalRating,
    sortBy,
    authToken,
  ]);

  useEffect(() => {
    fetchShops();
  }, [fetchShops]);

  const selectShop = useCallback(
    (shop: Shop | null) => {
      controller.setSelectedShop(shop);
    },
    [controller]
  );

  return {
    shops: state.shops,
    isLoading: state.isLoading,
    errorMessage: state.errorMessage,
    selectedShop: state.selectedShop,
    selectShop,
    refetch: fetchShops,
    searchQuery,
    setSearchQuery,
    minRating,
    setMinRating,
    minLokalRating,
    setMinLokalRating,
    radius,
    setRadius,
    sortBy,
    setSortBy,
    resetFilters,
    hasActiveFilters,
  };
}

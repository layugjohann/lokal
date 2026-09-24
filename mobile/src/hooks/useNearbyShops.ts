import { useState, useEffect, useCallback, useRef } from 'react';
import { Shop } from '../types/shop';
import { LocationCoordinates } from '../types/location';
import { fetchNearbyShops } from '../services/shopService';

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
  radius: number;
  setRadius: (radius: number) => void;
  sortBy: 'distance' | 'rating';
  setSortBy: (sortBy: 'distance' | 'rating') => void;
  resetFilters: () => void;
  hasActiveFilters: boolean;
}

export function useNearbyShops(
  location: LocationCoordinates | null,
  authToken?: string | null
): UseNearbyShopsResult {
  const [shops, setShops] = useState<Shop[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedShop, setSelectedShop] = useState<Shop | null>(null);

  const [searchQuery, setSearchQuery] = useState<string>('');
  const [debouncedQuery, setDebouncedQuery] = useState<string>('');
  const [minRating, setMinRating] = useState<number | null>(null);
  const [radius, setRadius] = useState<number>(5000);
  const [sortBy, setSortBy] = useState<'distance' | 'rating'>('distance');

  const requestIdRef = useRef<number>(0);

  // Debounce search query input by 350ms
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 350);
    return () => clearTimeout(timer);
  }, [searchQuery]);

  const hasActiveFilters = Boolean(
    searchQuery.trim() || minRating !== null || sortBy !== 'distance' || radius !== 5000
  );

  const resetFilters = useCallback(() => {
    setSearchQuery('');
    setDebouncedQuery('');
    setMinRating(null);
    setRadius(5000);
    setSortBy('distance');
  }, []);

  const fetchShops = useCallback(async () => {
    if (!location) {
      ++requestIdRef.current;
      setShops([]);
      setSelectedShop(null);
      setIsLoading(false);
      setErrorMessage(null);
      return;
    }

    const currentRequestId = ++requestIdRef.current;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const data = await fetchNearbyShops(
        {
          latitude: location.latitude,
          longitude: location.longitude,
          radius,
          query: debouncedQuery,
          minRating: minRating ?? undefined,
          sortBy,
        },
        authToken
      );

      if (currentRequestId !== requestIdRef.current) {
        return;
      }

      setShops(data);
      setSelectedShop((prev) => {
        if (!prev) {
          return null;
        }
        const found = data.find((s) => s.id === prev.id);
        return found || null;
      });
    } catch (err) {
      if (currentRequestId !== requestIdRef.current) {
        return;
      }
      const message =
        err instanceof Error
          ? err.message
          : 'Unable to load nearby coffee shops.';
      setErrorMessage(message);
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setIsLoading(false);
      }
    }
  }, [location?.latitude, location?.longitude, radius, debouncedQuery, minRating, sortBy, authToken]);

  useEffect(() => {
    if (location) {
      fetchShops();
    } else {
      ++requestIdRef.current;
      setShops([]);
      setSelectedShop(null);
      setIsLoading(false);
      setErrorMessage(null);
    }
  }, [location?.latitude, location?.longitude, fetchShops]);

  return {
    shops,
    isLoading,
    errorMessage,
    selectedShop,
    selectShop: setSelectedShop,
    refetch: fetchShops,
    searchQuery,
    setSearchQuery,
    minRating,
    setMinRating,
    radius,
    setRadius,
    sortBy,
    setSortBy,
    resetFilters,
    hasActiveFilters,
  };
}

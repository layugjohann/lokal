import { useState, useEffect, useCallback, useRef } from 'react';
import { FavoriteShop } from '../types/favorite';
import { fetchUserFavorites } from '../services/favoriteService';

export interface UseFavoritesResult {
  favorites: FavoriteShop[];
  isLoading: boolean;
  errorMessage: string | null;
  refetch: () => Promise<void>;
  removeFavoriteOptimistic: (shopId: string) => void;
}

export function useFavorites(authToken?: string | null): UseFavoritesResult {
  const [favorites, setFavorites] = useState<FavoriteShop[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const requestIdRef = useRef<number>(0);

  const loadFavorites = useCallback(async () => {
    if (!authToken || !authToken.trim()) {
      ++requestIdRef.current;
      setFavorites([]);
      setIsLoading(false);
      setErrorMessage(null);
      return;
    }

    const currentRequestId = ++requestIdRef.current;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const data = await fetchUserFavorites(authToken);
      if (currentRequestId !== requestIdRef.current) {
        return;
      }
      setFavorites(data);
    } catch (err: unknown) {
      if (currentRequestId !== requestIdRef.current) {
        return;
      }
      const message =
        err instanceof Error ? err.message : 'Unable to load favorite coffee shops.';
      setErrorMessage(message);
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setIsLoading(false);
      }
    }
  }, [authToken]);

  useEffect(() => {
    loadFavorites();
    return () => {
      ++requestIdRef.current;
    };
  }, [loadFavorites]);

  const removeFavoriteOptimistic = useCallback((shopId: string) => {
    setFavorites((prev) => prev.filter((item) => item.id !== shopId));
  }, []);

  return {
    favorites,
    isLoading,
    errorMessage,
    refetch: loadFavorites,
    removeFavoriteOptimistic,
  };
}

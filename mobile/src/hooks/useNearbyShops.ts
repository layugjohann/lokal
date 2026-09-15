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
}

export function useNearbyShops(
  location: LocationCoordinates | null,
  authToken?: string | null
): UseNearbyShopsResult {
  const [shops, setShops] = useState<Shop[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [selectedShop, setSelectedShop] = useState<Shop | null>(null);
  const requestIdRef = useRef<number>(0);

  const fetchShops = useCallback(async () => {
    if (!location) {
      setShops([]);
      setSelectedShop(null);
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
  }, [location?.latitude, location?.longitude, authToken]);

  useEffect(() => {
    if (location) {
      fetchShops();
    } else {
      setShops([]);
      setSelectedShop(null);
      setErrorMessage(null);
    }
  }, [location?.latitude, location?.longitude, authToken, fetchShops]);

  return {
    shops,
    isLoading,
    errorMessage,
    selectedShop,
    selectShop: setSelectedShop,
    refetch: fetchShops,
  };
}

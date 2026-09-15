import { useState, useEffect, useCallback } from 'react';
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

  const fetchShops = useCallback(async () => {
    if (!location) {
      setShops([]);
      setSelectedShop(null);
      return;
    }

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
      setShops(data);
      if (selectedShop) {
        const found = data.find((s) => s.id === selectedShop.id);
        if (found) {
          setSelectedShop(found);
        }
      }
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : 'Unable to load nearby coffee shops.';
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
    }
  }, [location?.latitude, location?.longitude, authToken, selectedShop]);

  useEffect(() => {
    if (location) {
      fetchShops();
    } else {
      setShops([]);
      setSelectedShop(null);
      setErrorMessage(null);
    }
  }, [location?.latitude, location?.longitude]);

  return {
    shops,
    isLoading,
    errorMessage,
    selectedShop,
    selectShop: setSelectedShop,
    refetch: fetchShops,
  };
}

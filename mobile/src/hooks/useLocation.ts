import { useState, useEffect, useCallback } from 'react';
import {
  LocationCoordinates,
  LocationPermissionStatus,
  UseLocationResult,
} from '../types/location';
import {
  requestForegroundPermission,
  getCurrentCoordinates,
} from '../services/locationService';

export function useLocation(): UseLocationResult {
  const [permissionStatus, setPermissionStatus] =
    useState<LocationPermissionStatus>('undetermined');
  const [location, setLocation] = useState<LocationCoordinates | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchLocation = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const status = await requestForegroundPermission();
      setPermissionStatus(status);

      if (status !== 'granted') {
        setErrorMessage('Location permission was denied.');
        setLocation(null);
        return;
      }

      const coords = await getCurrentCoordinates();
      if (coords) {
        setLocation(coords);
      } else {
        setErrorMessage('Unable to determine current location.');
      }
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'An unexpected error occurred while fetching location.';
      setErrorMessage(message);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchLocation();
  }, [fetchLocation]);

  return {
    permissionStatus,
    location,
    isLoading,
    errorMessage,
    retry: fetchLocation,
  };
}

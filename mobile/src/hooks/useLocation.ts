import { useState, useEffect, useCallback } from 'react';
import { Linking } from 'react-native';
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
  const [canAskAgain, setCanAskAgain] = useState<boolean>(true);
  const [location, setLocation] = useState<LocationCoordinates | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchLocation = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const permissionInfo = await requestForegroundPermission();
      setPermissionStatus(permissionInfo.status);
      setCanAskAgain(permissionInfo.canAskAgain);

      if (permissionInfo.status === 'undetermined') {
        setErrorMessage(
          'Location permission has not been granted yet. Grant permission to view your location.'
        );
        setLocation(null);
        return;
      }

      if (permissionInfo.status === 'denied') {
        if (!permissionInfo.canAskAgain) {
          setErrorMessage(
            'Location permission is permanently disabled. Please enable it in system settings.'
          );
        } else {
          setErrorMessage('Location permission was denied.');
        }
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

  const openSettings = useCallback(async () => {
    try {
      await Linking.openSettings();
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : 'Unable to open system settings.';
      setErrorMessage(message);
    }
  }, []);

  useEffect(() => {
    fetchLocation();
  }, [fetchLocation]);

  return {
    permissionStatus,
    canAskAgain,
    location,
    isLoading,
    errorMessage,
    retry: fetchLocation,
    openSettings,
  };
}

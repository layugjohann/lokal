import * as Location from 'expo-location';
import { LocationCoordinates, LocationPermissionStatus } from '../types/location';

/**
 * Requests foreground location permission from the user.
 * Returns normalized permission status ('granted', 'denied', or 'undetermined').
 */
export async function requestForegroundPermission(): Promise<LocationPermissionStatus> {
  const { status } = await Location.requestForegroundPermissionsAsync();
  if (status === Location.PermissionStatus.GRANTED) {
    return 'granted';
  }
  if (status === Location.PermissionStatus.DENIED) {
    return 'denied';
  }
  return 'undetermined';
}

/**
 * Checks current foreground location permission status without triggering a system prompt.
 */
export async function checkForegroundPermission(): Promise<LocationPermissionStatus> {
  const { status } = await Location.getForegroundPermissionsAsync();
  if (status === Location.PermissionStatus.GRANTED) {
    return 'granted';
  }
  if (status === Location.PermissionStatus.DENIED) {
    return 'denied';
  }
  return 'undetermined';
}

/**
 * Retrieves the current coordinates of the device.
 * Returns null if location cannot be obtained.
 */
export async function getCurrentCoordinates(): Promise<LocationCoordinates | null> {
  const position = await Location.getCurrentPositionAsync({
    accuracy: Location.Accuracy.Balanced,
  });

  if (!position || !position.coords) {
    return null;
  }

  return {
    latitude: position.coords.latitude,
    longitude: position.coords.longitude,
  };
}

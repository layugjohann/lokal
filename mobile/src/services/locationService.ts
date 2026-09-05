import * as Location from 'expo-location';
import {
  LocationCoordinates,
  LocationPermissionInfo,
  LocationPermissionStatus,
} from '../types/location';

function normalizePermissionResponse(
  response: Location.PermissionResponse
): LocationPermissionInfo {
  let status: LocationPermissionStatus = 'undetermined';
  if (response.status === Location.PermissionStatus.GRANTED) {
    status = 'granted';
  } else if (response.status === Location.PermissionStatus.DENIED) {
    status = 'denied';
  }

  return {
    status,
    canAskAgain: response.canAskAgain,
  };
}

/**
 * Requests foreground location permission from the user.
 * Returns normalized permission status and canAskAgain flag.
 */
export async function requestForegroundPermission(): Promise<LocationPermissionInfo> {
  const response = await Location.requestForegroundPermissionsAsync();
  return normalizePermissionResponse(response);
}

/**
 * Checks current foreground location permission status without triggering a system prompt.
 */
export async function checkForegroundPermission(): Promise<LocationPermissionInfo> {
  const response = await Location.getForegroundPermissionsAsync();
  return normalizePermissionResponse(response);
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

export interface LocationCoordinates {
  latitude: number;
  longitude: number;
}

export type LocationPermissionStatus = 'undetermined' | 'granted' | 'denied';

export interface LocationPermissionInfo {
  status: LocationPermissionStatus;
  canAskAgain: boolean;
}

export interface MapRegion {
  latitude: number;
  longitude: number;
  latitudeDelta: number;
  longitudeDelta: number;
}

export interface UseLocationResult {
  permissionStatus: LocationPermissionStatus;
  canAskAgain: boolean;
  location: LocationCoordinates | null;
  isLoading: boolean;
  errorMessage: string | null;
  retry: () => Promise<void>;
  openSettings: () => Promise<void>;
}

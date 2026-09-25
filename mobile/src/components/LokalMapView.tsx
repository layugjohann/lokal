import React, { useContext, useEffect, useRef } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import MapView, { Marker, Region } from 'react-native-maps';
import { AuthContext } from '../context/AuthContext';
import { useLocation } from '../hooks/useLocation';
import { useNearbyShops } from '../hooks/useNearbyShops';
import NearbyShopsSheet from './NearbyShopsSheet';
import { formatDistance } from '../services/shopService';
import { Shop } from '../types/shop';

const DEFAULT_REGION: Region = {
  latitude: 14.5995,
  longitude: 120.9842,
  latitudeDelta: 0.05,
  longitudeDelta: 0.05,
};

export interface LokalMapViewProps {
  authToken?: string | null;
}

export default function LokalMapView({ authToken }: LokalMapViewProps = {}) {
  const auth = useContext(AuthContext);
  const activeAuthToken = authToken !== undefined ? authToken : (auth?.token ?? null);

  const {
    location,
    permissionStatus,
    canAskAgain,
    isLoading,
    errorMessage,
    retry,
    openSettings,
  } = useLocation();

  const {
    shops,
    isLoading: isLoadingNearby,
    errorMessage: nearbyError,
    selectedShop,
    selectShop,
    refetch: refetchShops,
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
  } = useNearbyShops(location, activeAuthToken);

  const mapRef = useRef<MapView>(null);

  useEffect(() => {
    if (location && mapRef.current) {
      mapRef.current.animateToRegion(
        {
          latitude: location.latitude,
          longitude: location.longitude,
          latitudeDelta: 0.015,
          longitudeDelta: 0.015,
        },
        800
      );
    }
  }, [location]);

  const handleSelectShop = (shop: Shop) => {
    selectShop(shop);
    if (mapRef.current) {
      mapRef.current.animateToRegion(
        {
          latitude: shop.latitude,
          longitude: shop.longitude,
          latitudeDelta: 0.012,
          longitudeDelta: 0.012,
        },
        500
      );
    }
  };

  const handleCloseDetail = () => {
    selectShop(null);
  };

  return (
    <View style={styles.container}>
      <MapView
        ref={mapRef}
        style={styles.map}
        initialRegion={DEFAULT_REGION}
        showsUserLocation={permissionStatus === 'granted'}
        showsMyLocationButton={permissionStatus === 'granted'}
        onPress={() => selectShop(null)}
      >
        {location && (
          <Marker
            coordinate={{
              latitude: location.latitude,
              longitude: location.longitude,
            }}
            title="Current Location"
            description="You are here"
          />
        )}

        {shops.map((shop) => (
          <Marker
            key={shop.id}
            coordinate={{
              latitude: shop.latitude,
              longitude: shop.longitude,
            }}
            title={shop.name}
            description={formatDistance(shop.distance_meters)}
            pinColor={selectedShop?.id === shop.id ? '#D4A373' : '#4A2E18'}
            onPress={() => handleSelectShop(shop)}
          />
        ))}
      </MapView>

      {location && permissionStatus === 'granted' && !errorMessage && (
        <NearbyShopsSheet
          shops={shops}
          isLoading={isLoadingNearby}
          errorMessage={nearbyError}
          selectedShop={selectedShop}
          onSelectShop={handleSelectShop}
          onCloseDetail={handleCloseDetail}
          onRetry={refetchShops}
          authToken={activeAuthToken}
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          minRating={minRating}
          onMinRatingChange={setMinRating}
          radius={radius}
          onRadiusChange={setRadius}
          sortBy={sortBy}
          onSortByChange={setSortBy}
          onResetFilters={resetFilters}
          hasActiveFilters={hasActiveFilters}
        />
      )}

      {auth && auth.status === 'authenticated' && (
        <TouchableOpacity
          style={styles.logoutButton}
          onPress={auth.logout}
          accessibilityRole="button"
          accessibilityLabel="Log out of LOKAL"
          activeOpacity={0.8}
        >
          <Text style={styles.logoutButtonText}>Log Out</Text>
        </TouchableOpacity>
      )}

      {isLoading && (
        <View style={styles.loadingBanner}>
          <ActivityIndicator size="small" color="#4A2E18" />
          <Text style={styles.loadingText}>Locating you...</Text>
        </View>
      )}

      {errorMessage && !isLoading && (
        <View style={styles.errorBanner}>
          <Text style={styles.errorText}>{errorMessage}</Text>
          {permissionStatus === 'denied' && !canAskAgain ? (
            <View style={styles.buttonGroup}>
              <TouchableOpacity
                style={styles.secondaryButton}
                onPress={retry}
                activeOpacity={0.8}
                accessibilityRole="button"
                accessibilityLabel="Check location permission again"
              >
                <Text style={styles.secondaryButtonText}>Check Again</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.primaryButton}
                onPress={openSettings}
                activeOpacity={0.8}
                accessibilityRole="button"
                accessibilityLabel="Open device settings"
              >
                <Text style={styles.primaryButtonText}>Open Settings</Text>
              </TouchableOpacity>
            </View>
          ) : permissionStatus === 'undetermined' ? (
            <TouchableOpacity
              style={styles.primaryButton}
              onPress={retry}
              activeOpacity={0.8}
              accessibilityRole="button"
              accessibilityLabel="Grant location permission"
            >
              <Text style={styles.primaryButtonText}>Grant Permission</Text>
            </TouchableOpacity>
          ) : (
            <TouchableOpacity
              style={styles.primaryButton}
              onPress={retry}
              activeOpacity={0.8}
              accessibilityRole="button"
              accessibilityLabel="Retry location request"
            >
              <Text style={styles.primaryButtonText}>Retry</Text>
            </TouchableOpacity>
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#FAF8F5',
  },
  map: {
    ...StyleSheet.absoluteFill,
  },
  loadingBanner: {
    position: 'absolute',
    top: 50,
    alignSelf: 'center',
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(250, 248, 245, 0.95)',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 3,
    gap: 8,
  },
  loadingText: {
    color: '#4A2E18',
    fontSize: 14,
    fontWeight: '500',
  },
  errorBanner: {
    position: 'absolute',
    bottom: 30,
    left: 20,
    right: 20,
    backgroundColor: '#FFF',
    paddingVertical: 12,
    paddingHorizontal: 16,
    borderRadius: 12,
    flexDirection: 'column',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 6,
    elevation: 4,
    gap: 10,
  },
  errorText: {
    color: '#6B5E55',
    fontSize: 14,
    lineHeight: 20,
  },
  buttonGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: 10,
  },
  primaryButton: {
    backgroundColor: '#4A2E18',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 8,
    alignSelf: 'flex-end',
  },
  primaryButtonText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
  },
  secondaryButton: {
    backgroundColor: 'transparent',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#D4C8BE',
  },
  secondaryButtonText: {
    color: '#4A2E18',
    fontSize: 14,
    fontWeight: '500',
  },
  logoutButton: {
    position: 'absolute',
    top: 50,
    right: 16,
    backgroundColor: 'rgba(250, 248, 245, 0.95)',
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 3,
  },
  logoutButtonText: {
    color: '#4A2E18',
    fontSize: 13,
    fontWeight: '600',
  },
});

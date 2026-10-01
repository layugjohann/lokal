import React, { useState, useEffect } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  Modal,
  SafeAreaView,
} from 'react-native';
import { AuthUser } from '../types/auth';
import { Shop } from '../types/shop';
import { FavoriteShop } from '../types/favorite';
import { LocationCoordinates } from '../types/location';
import { useFavorites } from '../hooks/useFavorites';
import { getUserDisplayName } from '../services/authService';
import {
  formatDistance,
  formatRating,
  calculateDistanceMeters,
} from '../services/shopService';
import ShopDetailCard from './ShopDetailCard';

export { getUserDisplayName };

export interface ProfileViewProps {
  user: AuthUser | null;
  authToken: string | null;
  userLocation: LocationCoordinates | null;
  visible: boolean;
  onClose: () => void;
  onLogout: () => void;
}

export default function ProfileView({
  user,
  authToken,
  userLocation,
  visible,
  onClose,
  onLogout,
}: ProfileViewProps) {
  const [selectedFavoriteShop, setSelectedFavoriteShop] = useState<Shop | null>(null);

  const {
    favorites,
    isLoading,
    errorMessage,
    refetch,
    removeFavoriteOptimistic,
  } = useFavorites(visible && authToken ? authToken : null);

  // Reset selected shop when profile closes or auth token changes
  useEffect(() => {
    if (!visible || !authToken) {
      setSelectedFavoriteShop(null);
    }
  }, [visible, authToken]);

  const displayName = getUserDisplayName(user);
  const email = user?.email || '';

  const handleOpenShopDetail = (fav: FavoriteShop) => {
    let distanceMeters = 0;
    if (userLocation) {
      distanceMeters = calculateDistanceMeters(
        userLocation.latitude,
        userLocation.longitude,
        fav.latitude,
        fav.longitude
      );
    }

    const shop: Shop = {
      id: fav.id,
      name: fav.name,
      address: fav.address,
      latitude: fav.latitude,
      longitude: fav.longitude,
      rating: fav.rating,
      google_place_id: fav.google_place_id,
      created_at: fav.created_at,
      updated_at: fav.updated_at,
      distance_meters: distanceMeters,
    };
    setSelectedFavoriteShop(shop);
  };

  const handleCloseShopDetail = () => {
    setSelectedFavoriteShop(null);
  };

  const handleFavoriteChange = (shopId: string, isFavorite: boolean) => {
    if (!isFavorite) {
      removeFavoriteOptimistic(shopId);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.container}>
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.headerTitleRow}>
              <Text style={styles.headerTitle}>Profile</Text>
            </View>
            <TouchableOpacity
              style={styles.closeButton}
              onPress={onClose}
              accessibilityRole="button"
              accessibilityLabel="Close profile"
              activeOpacity={0.7}
            >
              <Text style={styles.closeButtonText}>✕</Text>
            </TouchableOpacity>
          </View>

          {/* Shop Detail Mode within Profile */}
          {selectedFavoriteShop ? (
            <View style={styles.detailContainer}>
              <View style={styles.detailHeaderBar}>
                <TouchableOpacity
                  style={styles.backToFavoritesButton}
                  onPress={handleCloseShopDetail}
                  accessibilityRole="button"
                  accessibilityLabel="Back to saved coffee shops"
                  activeOpacity={0.7}
                >
                  <Text style={styles.backToFavoritesText}>← Back to Saved Shops</Text>
                </TouchableOpacity>
              </View>
              <ShopDetailCard
                key={`${selectedFavoriteShop.id}:${authToken || 'anon'}`}
                shop={selectedFavoriteShop}
                onClose={handleCloseShopDetail}
                authToken={authToken}
                onFavoriteChange={handleFavoriteChange}
              />
            </View>
          ) : (
            <>
              {/* User Profile Info Card */}
              <View style={styles.userCard}>
                <View style={styles.avatarCircle}>
                  <Text style={styles.avatarInitial}>
                    {displayName.charAt(0).toUpperCase()}
                  </Text>
                </View>
                <View style={styles.userInfo}>
                  <Text style={styles.userName} numberOfLines={1}>
                    {displayName}
                  </Text>
                  {Boolean(email) && (
                    <Text style={styles.userEmail} numberOfLines={1}>
                      {email}
                    </Text>
                  )}
                </View>
                <TouchableOpacity
                  style={styles.logoutButton}
                  onPress={() => {
                    onClose();
                    onLogout();
                  }}
                  accessibilityRole="button"
                  accessibilityLabel="Log out of LOKAL"
                  activeOpacity={0.8}
                >
                  <Text style={styles.logoutButtonText}>Log Out</Text>
                </TouchableOpacity>
              </View>

              {/* Favorites Section Header */}
              <View style={styles.sectionHeader}>
                <Text style={styles.sectionTitle}>Saved Coffee Shops</Text>
                {!isLoading && !errorMessage && favorites.length > 0 && (
                  <View style={styles.countBadge}>
                    <Text style={styles.countText}>{favorites.length}</Text>
                  </View>
                )}
              </View>

              {/* Loading State */}
              {isLoading && (
                <View style={styles.stateContainer}>
                  <ActivityIndicator size="small" color="#4A2E18" />
                  <Text style={styles.stateText}>Loading your favorites...</Text>
                </View>
              )}

              {/* Error State */}
              {errorMessage && !isLoading && (
                <View style={styles.stateContainer}>
                  <Text style={styles.errorText}>{errorMessage}</Text>
                  <TouchableOpacity
                    style={styles.retryButton}
                    onPress={refetch}
                    accessibilityRole="button"
                    accessibilityLabel="Retry loading favorites"
                    activeOpacity={0.8}
                  >
                    <Text style={styles.retryButtonText}>Retry</Text>
                  </TouchableOpacity>
                </View>
              )}

              {/* Empty State */}
              {!isLoading && !errorMessage && favorites.length === 0 && (
                <View style={styles.emptyContainer}>
                  <Text style={styles.emptyIcon}>☕</Text>
                  <Text style={styles.emptyTitle}>No saved coffee shops yet</Text>
                  <Text style={styles.emptySubtitle}>
                    Tap the heart icon on any coffee shop to save it to your favorites.
                  </Text>
                </View>
              )}

              {/* Favorites List */}
              {!isLoading && !errorMessage && favorites.length > 0 && (
                <FlatList
                  data={favorites}
                  keyExtractor={(item) => item.id}
                  contentContainerStyle={styles.listContent}
                  renderItem={({ item }) => {
                    let distText = '';
                    if (userLocation) {
                      const dist = calculateDistanceMeters(
                        userLocation.latitude,
                        userLocation.longitude,
                        item.latitude,
                        item.longitude
                      );
                      distText = formatDistance(dist);
                    }
                    const ratingText = formatRating(item.rating);

                    return (
                      <TouchableOpacity
                        style={styles.favoriteCard}
                        onPress={() => handleOpenShopDetail(item)}
                        accessibilityRole="button"
                        accessibilityLabel={`Open ${item.name} details`}
                        activeOpacity={0.7}
                      >
                        <View style={styles.cardHeaderRow}>
                          <Text style={styles.cardShopName} numberOfLines={1}>
                            {item.name}
                          </Text>
                          <Text style={styles.heartIcon}>♥</Text>
                        </View>
                        <View style={styles.metaRow}>
                          <Text style={styles.ratingText}>{ratingText}</Text>
                          {Boolean(distText) && <Text style={styles.dot}>•</Text>}
                          {Boolean(distText) && (
                            <Text style={styles.distanceText}>{distText}</Text>
                          )}
                        </View>
                        {item.address ? (
                          <Text style={styles.cardAddress} numberOfLines={1}>
                            {item.address}
                          </Text>
                        ) : (
                          <Text style={styles.cardAddressMuted}>
                            Address not available
                          </Text>
                        )}
                      </TouchableOpacity>
                    );
                  }}
                />
              )}
            </>
          )}
        </View>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#FAF8F5',
  },
  container: {
    flex: 1,
    paddingHorizontal: 20,
    paddingTop: 12,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingBottom: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#E8E1D9',
  },
  headerTitleRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#4A2E18',
  },
  closeButton: {
    padding: 6,
    borderRadius: 20,
    backgroundColor: '#EFEAE4',
  },
  closeButtonText: {
    color: '#4A2E18',
    fontSize: 16,
    fontWeight: '600',
    paddingHorizontal: 4,
  },
  userCard: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 14,
    padding: 14,
    marginTop: 16,
    borderWidth: 1,
    borderColor: '#EFEAE4',
    gap: 12,
  },
  avatarCircle: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: '#4A2E18',
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarInitial: {
    color: '#FAF8F5',
    fontSize: 18,
    fontWeight: '700',
  },
  userInfo: {
    flex: 1,
  },
  userName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#4A2E18',
    marginBottom: 2,
  },
  userEmail: {
    fontSize: 13,
    color: '#6B5E55',
  },
  logoutButton: {
    backgroundColor: 'transparent',
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#D4C8BE',
  },
  logoutButtonText: {
    color: '#8A3B28',
    fontSize: 12,
    fontWeight: '600',
  },
  sectionHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 24,
    marginBottom: 12,
    gap: 8,
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#4A2E18',
  },
  countBadge: {
    backgroundColor: '#4A2E18',
    borderRadius: 10,
    paddingHorizontal: 7,
    paddingVertical: 1,
  },
  countText: {
    color: '#FAF8F5',
    fontSize: 12,
    fontWeight: '600',
  },
  stateContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 32,
    gap: 10,
  },
  stateText: {
    color: '#6B5E55',
    fontSize: 14,
    fontWeight: '500',
  },
  errorText: {
    color: '#8A3B28',
    fontSize: 14,
    textAlign: 'center',
    lineHeight: 20,
    paddingHorizontal: 16,
  },
  retryButton: {
    backgroundColor: '#4A2E18',
    paddingVertical: 8,
    paddingHorizontal: 18,
    borderRadius: 8,
    marginTop: 4,
  },
  retryButtonText: {
    color: '#FAF8F5',
    fontSize: 13,
    fontWeight: '600',
  },
  emptyContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 48,
    paddingHorizontal: 24,
  },
  emptyIcon: {
    fontSize: 40,
    marginBottom: 12,
  },
  emptyTitle: {
    color: '#4A2E18',
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 6,
    textAlign: 'center',
  },
  emptySubtitle: {
    color: '#8C7D73',
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 18,
  },
  listContent: {
    gap: 10,
    paddingBottom: 24,
  },
  favoriteCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: '#EFEAE4',
  },
  cardHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 4,
  },
  cardShopName: {
    flex: 1,
    fontSize: 15,
    fontWeight: '700',
    color: '#4A2E18',
    marginRight: 8,
  },
  heartIcon: {
    color: '#C44536',
    fontSize: 16,
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginBottom: 4,
  },
  ratingText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#A06D00',
  },
  dot: {
    color: '#C4B8AE',
    fontSize: 10,
  },
  distanceText: {
    fontSize: 12,
    fontWeight: '500',
    color: '#6B5E55',
  },
  cardAddress: {
    fontSize: 12,
    color: '#6B5E55',
  },
  cardAddressMuted: {
    fontSize: 12,
    color: '#A4988F',
    fontStyle: 'italic',
  },
  detailContainer: {
    flex: 1,
    marginTop: 8,
  },
  detailHeaderBar: {
    marginBottom: 8,
  },
  backToFavoritesButton: {
    paddingVertical: 6,
    paddingHorizontal: 10,
    alignSelf: 'flex-start',
  },
  backToFavoritesText: {
    color: '#4A2E18',
    fontSize: 14,
    fontWeight: '600',
  },
});

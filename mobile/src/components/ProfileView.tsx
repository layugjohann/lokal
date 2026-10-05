import React, { useState, useEffect, useRef, useCallback } from 'react';
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
import { ShopClaim } from '../types/claim';
import { useFavorites } from '../hooks/useFavorites';
import { getUserDisplayName } from '../services/authService';
import { fetchMyClaims } from '../services/claimService';
import {
  formatDistance,
  formatRating,
  calculateDistanceMeters,
} from '../services/shopService';
import ShopDetailCard from './ShopDetailCard';
import OwnerDashboardModal from './OwnerDashboardModal';

export { getUserDisplayName };

export interface ProfileViewProps {
  user: AuthUser | null;
  authToken: string | null;
  userLocation: LocationCoordinates | null;
  visible: boolean;
  onClose: () => void;
  onLogout: () => void;
}

/**
 * Modal view presenting the authenticated user's profile information,
 * saved favorite coffee shops list, and seamless navigation to shop details.
 */
export default function ProfileView({
  user,
  authToken,
  userLocation,
  visible,
  onClose,
  onLogout,
}: ProfileViewProps) {
  const [selectedFavoriteShop, setSelectedFavoriteShop] = useState<Shop | null>(null);
  const [activeTab, setActiveTab] = useState<'favorites' | 'claims'>('favorites');
  const [claims, setClaims] = useState<ShopClaim[]>([]);
  const [isClaimsLoading, setIsClaimsLoading] = useState<boolean>(false);
  const [claimsErrorMessage, setClaimsErrorMessage] = useState<string | null>(null);
  const [ownerDashboardShopId, setOwnerDashboardShopId] = useState<string | null>(null);

  const claimsRequestId = useRef<number>(0);

  const {
    favorites,
    isLoading,
    errorMessage,
    refetch,
    removeFavoriteOptimistic,
  } = useFavorites(
    visible && authToken ? authToken : null,
    visible ? user?.id : null
  );

  const loadClaims = useCallback(async () => {
    if (!authToken) {
      setClaims([]);
      setIsClaimsLoading(false);
      return;
    }

    const requestId = ++claimsRequestId.current;
    setIsClaimsLoading(true);
    setClaimsErrorMessage(null);

    try {
      const claimsData = await fetchMyClaims(authToken);
      if (requestId === claimsRequestId.current) {
        setClaims(claimsData);
        setIsClaimsLoading(false);
      }
    } catch (err: unknown) {
      if (requestId === claimsRequestId.current) {
        const message = err instanceof Error ? err.message : 'Failed to load your claims.';
        setClaimsErrorMessage(message);
        setIsClaimsLoading(false);
      }
    }
  }, [authToken]);

  useEffect(() => {
    if (visible && authToken && activeTab === 'claims') {
      loadClaims();
    }
  }, [visible, authToken, activeTab, loadClaims]);

  // Reset selected shop & claims when profile closes or auth token becomes unavailable
  useEffect(() => {
    if (!visible || !authToken) {
      setSelectedFavoriteShop(null);
      setOwnerDashboardShopId(null);
      setClaims([]);
    }
  }, [visible, authToken]);

  const displayName = getUserDisplayName(user);
  const email = user?.email || '';

  const handleOpenShopDetail = (fav: FavoriteShop) => {
    let distanceMeters = Number.NaN;
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
    void refetch();
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

              {/* Tab Selector */}
              <View style={styles.tabContainer}>
                <TouchableOpacity
                  style={[styles.tabButton, activeTab === 'favorites' && styles.tabButtonActive]}
                  onPress={() => setActiveTab('favorites')}
                  accessibilityRole="button"
                  accessibilityLabel="Saved coffee shops tab"
                  activeOpacity={0.7}
                >
                  <Text
                    style={[
                      styles.tabButtonText,
                      activeTab === 'favorites' && styles.tabButtonTextActive,
                    ]}
                  >
                    Saved Shops
                  </Text>
                  {!isLoading && !errorMessage && favorites.length > 0 && (
                    <View
                      style={[
                        styles.tabBadge,
                        activeTab === 'favorites' && styles.tabBadgeActive,
                      ]}
                    >
                      <Text
                        style={[
                          styles.tabBadgeText,
                          activeTab === 'favorites' && styles.tabBadgeTextActive,
                        ]}
                      >
                        {favorites.length}
                      </Text>
                    </View>
                  )}
                </TouchableOpacity>

                <TouchableOpacity
                  style={[styles.tabButton, activeTab === 'claims' && styles.tabButtonActive]}
                  onPress={() => setActiveTab('claims')}
                  accessibilityRole="button"
                  accessibilityLabel="My claims tab"
                  activeOpacity={0.7}
                >
                  <Text
                    style={[
                      styles.tabButtonText,
                      activeTab === 'claims' && styles.tabButtonTextActive,
                    ]}
                  >
                    My Claims
                  </Text>
                  {!isClaimsLoading && !claimsErrorMessage && claims.length > 0 && (
                    <View
                      style={[
                        styles.tabBadge,
                        activeTab === 'claims' && styles.tabBadgeActive,
                      ]}
                    >
                      <Text
                        style={[
                          styles.tabBadgeText,
                          activeTab === 'claims' && styles.tabBadgeTextActive,
                        ]}
                      >
                        {claims.length}
                      </Text>
                    </View>
                  )}
                </TouchableOpacity>
              </View>

              {activeTab === 'favorites' ? (
                <>
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
              ) : (
                <>
                  {/* Claims Section Header */}
                  <View style={styles.sectionHeader}>
                    <Text style={styles.sectionTitle}>My Ownership Claims</Text>
                    {!isClaimsLoading && !claimsErrorMessage && claims.length > 0 && (
                      <View style={styles.countBadge}>
                        <Text style={styles.countText}>{claims.length}</Text>
                      </View>
                    )}
                  </View>

                  {/* Claims Loading State */}
                  {isClaimsLoading && (
                    <View style={styles.stateContainer}>
                      <ActivityIndicator size="small" color="#4A2E18" />
                      <Text style={styles.stateText}>Loading your claims...</Text>
                    </View>
                  )}

                  {/* Claims Error State */}
                  {claimsErrorMessage && !isClaimsLoading && (
                    <View style={styles.stateContainer}>
                      <Text style={styles.errorText}>{claimsErrorMessage}</Text>
                      <TouchableOpacity
                        style={styles.retryButton}
                        onPress={loadClaims}
                        accessibilityRole="button"
                        accessibilityLabel="Retry loading claims"
                        activeOpacity={0.8}
                      >
                        <Text style={styles.retryButtonText}>Retry</Text>
                      </TouchableOpacity>
                    </View>
                  )}

                  {/* Claims Empty State */}
                  {!isClaimsLoading && !claimsErrorMessage && claims.length === 0 && (
                    <View style={styles.emptyContainer}>
                      <Text style={styles.emptyIcon}>📋</Text>
                      <Text style={styles.emptyTitle}>No ownership claims yet</Text>
                      <Text style={styles.emptySubtitle}>
                        Are you a coffee shop owner or manager? You can submit an ownership claim directly from any coffee shop detail page.
                      </Text>
                    </View>
                  )}

                  {/* Claims List */}
                  {!isClaimsLoading && !claimsErrorMessage && claims.length > 0 && (
                    <FlatList
                      data={claims}
                      keyExtractor={(item) => item.id}
                      contentContainerStyle={styles.listContent}
                      renderItem={({ item }) => {
                        const getStatusConfig = (status: ShopClaim['status']) => {
                          switch (status) {
                            case 'APPROVED':
                              return {
                                label: 'Verified Owner',
                                badgeStyle: styles.badgeApproved,
                                textStyle: styles.badgeTextApproved,
                              };
                            case 'PENDING':
                              return {
                                label: 'Under Review',
                                badgeStyle: styles.badgePending,
                                textStyle: styles.badgeTextPending,
                              };
                            case 'REJECTED':
                              return {
                                label: 'Claim Rejected',
                                badgeStyle: styles.badgeRejected,
                                textStyle: styles.badgeTextRejected,
                              };
                            case 'REVOKED':
                              return {
                                label: 'Claim Revoked',
                                badgeStyle: styles.badgeRevoked,
                                textStyle: styles.badgeTextRevoked,
                              };
                            default:
                              return {
                                label: status,
                                badgeStyle: styles.badgeDefault,
                                textStyle: styles.badgeTextDefault,
                              };
                          }
                        };

                        const config = getStatusConfig(item.status);
                        const formattedDate = new Date(item.created_at).toLocaleDateString(undefined, {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                        });

                        return (
                          <View style={styles.claimCard}>
                            <View style={styles.claimHeaderRow}>
                              <View style={[styles.statusBadge, config.badgeStyle]}>
                                <Text style={[styles.statusBadgeText, config.textStyle]}>
                                  {config.label}
                                </Text>
                              </View>
                              <Text style={styles.claimDateText}>{formattedDate}</Text>
                            </View>

                            <View style={styles.claimMetaRow}>
                              <Text style={styles.claimantText}>
                                Claimed as <Text style={styles.claimantBold}>{item.claimant_name}</Text> ({item.claimant_role})
                              </Text>
                            </View>

                            {item.rejection_reason ? (
                              <View style={styles.rejectionBox}>
                                <Text style={styles.rejectionLabel}>Review Note:</Text>
                                <Text style={styles.rejectionText}>{item.rejection_reason}</Text>
                              </View>
                            ) : null}

                            {item.status === 'APPROVED' ? (
                              <TouchableOpacity
                                style={styles.dashboardButton}
                                onPress={() => setOwnerDashboardShopId(item.shop_id)}
                                accessibilityRole="button"
                                accessibilityLabel="Open Owner Dashboard"
                                activeOpacity={0.8}
                              >
                                <Text style={styles.dashboardButtonText}>Open Owner Dashboard →</Text>
                              </TouchableOpacity>
                            ) : null}
                          </View>
                        );
                      }}
                    />
                  )}
                </>
              )}
            </>
          )}

          {/* Owner Dashboard Modal */}
          <OwnerDashboardModal
            visible={Boolean(ownerDashboardShopId)}
            shopId={ownerDashboardShopId || ''}
            authToken={authToken}
            onClose={() => setOwnerDashboardShopId(null)}
          />
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
  tabContainer: {
    flexDirection: 'row',
    marginTop: 18,
    marginBottom: 6,
    backgroundColor: '#EFEAE4',
    borderRadius: 10,
    padding: 3,
    gap: 4,
  },
  tabButton: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 8,
    gap: 6,
  },
  tabButtonActive: {
    backgroundColor: '#FFFFFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
    elevation: 2,
  },
  tabButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#8A7E72',
  },
  tabButtonTextActive: {
    color: '#4A2E18',
  },
  tabBadge: {
    backgroundColor: '#DCD4CB',
    borderRadius: 8,
    paddingHorizontal: 6,
    paddingVertical: 1,
  },
  tabBadgeActive: {
    backgroundColor: '#4A2E18',
  },
  tabBadgeText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#6B5E55',
  },
  tabBadgeTextActive: {
    color: '#FAF8F5',
  },
  claimCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#EFEAE4',
    gap: 10,
  },
  claimHeaderRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  statusBadge: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusBadgeText: {
    fontSize: 12,
    fontWeight: '700',
  },
  badgeApproved: {
    backgroundColor: '#DEF7EC',
    borderWidth: 1,
    borderColor: '#BCF0DA',
  },
  badgeTextApproved: {
    color: '#03543F',
  },
  badgePending: {
    backgroundColor: '#FEF3C7',
    borderWidth: 1,
    borderColor: '#FDE68A',
  },
  badgeTextPending: {
    color: '#92400E',
  },
  badgeRejected: {
    backgroundColor: '#FDE8E8',
    borderWidth: 1,
    borderColor: '#FBD5D5',
  },
  badgeTextRejected: {
    color: '#9B1C1C',
  },
  badgeRevoked: {
    backgroundColor: '#F3F4F6',
    borderWidth: 1,
    borderColor: '#E5E7EB',
  },
  badgeTextRevoked: {
    color: '#4B5563',
  },
  badgeDefault: {
    backgroundColor: '#EFEAE4',
  },
  badgeTextDefault: {
    color: '#4A2E18',
  },
  claimDateText: {
    fontSize: 12,
    color: '#8A7E72',
  },
  claimMetaRow: {
    marginTop: 2,
  },
  claimantText: {
    fontSize: 14,
    color: '#6B5E55',
  },
  claimantBold: {
    fontWeight: '600',
    color: '#2C1810',
  },
  rejectionBox: {
    backgroundColor: '#FAF5F5',
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: '#F5E6E6',
  },
  rejectionLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: '#8A3B28',
    marginBottom: 2,
  },
  rejectionText: {
    fontSize: 13,
    color: '#5C382C',
  },
  dashboardButton: {
    backgroundColor: '#4A2E18',
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 4,
  },
  dashboardButtonText: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '700',
  },
});

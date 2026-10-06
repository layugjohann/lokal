import React, { useState, useEffect, useCallback } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  FlatList,
  ActivityIndicator,
  Modal,
  SafeAreaView,
  RefreshControl,
} from 'react-native';
import type { CommunityFeedItem } from '../types/community';
import type { Shop } from '../types/shop';
import { useCommunityFeed } from '../hooks/useCommunityFeed';
import { shareCommunityReview } from '../services/communityService';
import { fetchShopById } from '../services/shopService';
import ShopDetailCard from './ShopDetailCard';

export interface CommunityFeedViewProps {
  visible: boolean;
  authToken: string | null;
  userId: string | null;
  onClose: () => void;
}

export default function CommunityFeedView({
  visible,
  authToken,
  userId,
  onClose,
}: CommunityFeedViewProps) {
  const [selectedShop, setSelectedShop] = useState<Shop | null>(null);
  const [loadingShopId, setLoadingShopId] = useState<string | null>(null);

  const {
    items,
    isLoading,
    isLoadingMore,
    isRefreshing,
    errorMessage,
    loadMore,
    refresh,
    refetch,
    cancel,
  } = useCommunityFeed(authToken, userId, visible);

  // Invalidate in-flight operations and reset selected shop on modal dismiss
  useEffect(() => {
    if (!visible || !authToken) {
      cancel();
      setSelectedShop(null);
      setLoadingShopId(null);
    }
  }, [visible, authToken, cancel]);

  const handleOpenShop = useCallback(
    async (feedItem: CommunityFeedItem) => {
      setLoadingShopId(feedItem.shop_id);
      try {
        const fullShop = await fetchShopById(feedItem.shop_id, authToken);
        setSelectedShop(fullShop);
      } catch {
        // Fallback: construct minimum shop object to preserve offline / transient navigation
        const fallbackShop: Shop = {
          id: feedItem.shop_id,
          name: feedItem.shop_name,
          address: feedItem.shop_address,
          latitude: 0,
          longitude: 0,
          rating: feedItem.rating,
          google_place_id: null,
          created_at: feedItem.created_at,
          updated_at: feedItem.updated_at || feedItem.created_at,
          distance_meters: Number.NaN,
        };
        setSelectedShop(fallbackShop);
      } finally {
        setLoadingShopId(null);
      }
    },
    [authToken]
  );

  const handleShareReview = useCallback(async (item: CommunityFeedItem) => {
    await shareCommunityReview(item);
  }, []);

  const formatDate = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return '';
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
          {selectedShop ? (
            <View style={styles.detailContainer}>
              <View style={styles.detailHeader}>
                <TouchableOpacity
                  style={styles.backButton}
                  onPress={() => setSelectedShop(null)}
                  accessibilityRole="button"
                  accessibilityLabel="Back to Community Feed"
                  activeOpacity={0.8}
                >
                  <Text style={styles.backButtonText}>← Back to Community</Text>
                </TouchableOpacity>
              </View>
              <ShopDetailCard
                key={`${selectedShop.id}:${authToken || 'anon'}`}
                shop={selectedShop}
                onClose={() => setSelectedShop(null)}
                authToken={authToken}
              />
            </View>
          ) : (
            <>
              {/* Feed Header */}
              <View style={styles.header}>
                <View style={styles.headerTitleRow}>
                  <Text style={styles.headerTitle}>👥 Community Feed</Text>
                  <Text style={styles.headerSubtitle}>
                    Recent first-party reviews from the LOKAL community
                  </Text>
                </View>
                <TouchableOpacity
                  style={styles.closeButton}
                  onPress={onClose}
                  accessibilityRole="button"
                  accessibilityLabel="Close Community Feed"
                  activeOpacity={0.8}
                >
                  <Text style={styles.closeButtonText}>✕</Text>
                </TouchableOpacity>
              </View>

              {/* Initial Loading State */}
              {isLoading && items.length === 0 && (
                <View style={styles.stateContainer}>
                  <ActivityIndicator size="large" color="#4A2E18" />
                  <Text style={styles.stateText}>Loading community feed...</Text>
                </View>
              )}

              {/* Initial Error State */}
              {errorMessage && items.length === 0 && (
                <View style={styles.stateContainer}>
                  <Text style={styles.errorText}>{errorMessage}</Text>
                  <TouchableOpacity
                    style={styles.retryButton}
                    onPress={refetch}
                    accessibilityRole="button"
                    accessibilityLabel="Retry loading community feed"
                    activeOpacity={0.8}
                  >
                    <Text style={styles.retryButtonText}>Retry</Text>
                  </TouchableOpacity>
                </View>
              )}

              {/* Empty State */}
              {!isLoading && !errorMessage && items.length === 0 && (
                <View style={styles.emptyContainer}>
                  <Text style={styles.emptyIcon}>☕</Text>
                  <Text style={styles.emptyTitle}>No community reviews yet</Text>
                  <Text style={styles.emptySubtitle}>
                    Be the first to share your thoughts on a local coffee shop!
                  </Text>
                </View>
              )}

              {/* Feed List */}
              {items.length > 0 && (
                <FlatList
                  data={items}
                  keyExtractor={(item) => item.id}
                  contentContainerStyle={styles.listContent}
                  refreshControl={
                    <RefreshControl
                      refreshing={isRefreshing}
                      onRefresh={refresh}
                      colors={['#4A2E18']}
                      tintColor="#4A2E18"
                    />
                  }
                  onEndReached={loadMore}
                  onEndReachedThreshold={0.4}
                  renderItem={({ item }) => (
                    <View style={styles.feedCard}>
                      {/* Card Header: Shop info & Rating */}
                      <View style={styles.cardHeader}>
                        <TouchableOpacity
                          style={styles.shopNameTouch}
                          onPress={() => handleOpenShop(item)}
                          activeOpacity={0.7}
                          accessibilityRole="button"
                          accessibilityLabel={`View shop ${item.shop_name}`}
                        >
                          <Text style={styles.shopName} numberOfLines={1}>
                            ☕ {item.shop_name}
                          </Text>
                          {item.shop_address ? (
                            <Text style={styles.shopAddress} numberOfLines={1}>
                              📍 {item.shop_address}
                            </Text>
                          ) : null}
                        </TouchableOpacity>
                        <View style={styles.ratingBadge}>
                          <Text style={styles.ratingBadgeText}>★ {item.rating}</Text>
                        </View>
                      </View>

                      {/* Author & Timestamp Row */}
                      <View style={styles.authorRow}>
                        <Text style={styles.authorName}>👤 {item.author_name}</Text>
                        <Text style={styles.timestampDot}>•</Text>
                        <Text style={styles.timestampText}>{formatDate(item.created_at)}</Text>
                        {item.is_edited ? (
                          <View style={styles.editedBadge}>
                            <Text style={styles.editedBadgeText}>Edited</Text>
                          </View>
                        ) : null}
                      </View>

                      {/* Review Content */}
                      {item.content ? (
                        <Text style={styles.reviewContent}>{item.content}</Text>
                      ) : null}

                      {/* Card Action Buttons */}
                      <View style={styles.cardActionsRow}>
                        <TouchableOpacity
                          style={styles.actionButton}
                          onPress={() => handleOpenShop(item)}
                          disabled={loadingShopId === item.shop_id}
                          activeOpacity={0.8}
                          accessibilityRole="button"
                          accessibilityLabel={`Open details for ${item.shop_name}`}
                        >
                          {loadingShopId === item.shop_id ? (
                            <ActivityIndicator size="small" color="#4A2E18" />
                          ) : (
                            <Text style={styles.actionButtonText}>View Shop →</Text>
                          )}
                        </TouchableOpacity>

                        <TouchableOpacity
                          style={styles.shareButton}
                          onPress={() => handleShareReview(item)}
                          activeOpacity={0.8}
                          accessibilityRole="button"
                          accessibilityLabel={`Share review for ${item.shop_name}`}
                        >
                          <Text style={styles.shareButtonText}>🔗 Share</Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                  )}
                  ListFooterComponent={
                    isLoadingMore ? (
                      <View style={styles.footerLoading}>
                        <ActivityIndicator size="small" color="#4A2E18" />
                        <Text style={styles.footerLoadingText}>Loading more reviews...</Text>
                      </View>
                    ) : null
                  }
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
    backgroundColor: '#FAF8F5',
  },
  detailContainer: {
    flex: 1,
  },
  detailHeader: {
    paddingHorizontal: 16,
    paddingVertical: 10,
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#EFEAE2',
  },
  backButton: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 8,
    backgroundColor: '#F3EFEA',
    alignSelf: 'flex-start',
  },
  backButtonText: {
    color: '#4A2E18',
    fontSize: 14,
    fontWeight: '600',
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    paddingHorizontal: 20,
    paddingTop: 16,
    paddingBottom: 14,
    backgroundColor: '#FFF',
    borderBottomWidth: 1,
    borderBottomColor: '#EFEAE2',
  },
  headerTitleRow: {
    flex: 1,
  },
  headerTitle: {
    fontSize: 20,
    fontWeight: '700',
    color: '#4A2E18',
  },
  headerSubtitle: {
    fontSize: 12,
    color: '#8A7A6E',
    marginTop: 2,
  },
  closeButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#F3EFEA',
    justifyContent: 'center',
    alignItems: 'center',
    marginLeft: 12,
  },
  closeButtonText: {
    fontSize: 16,
    color: '#4A2E18',
    fontWeight: '600',
  },
  stateContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
    gap: 12,
  },
  stateText: {
    fontSize: 14,
    color: '#6B5E55',
    fontWeight: '500',
  },
  errorText: {
    fontSize: 14,
    color: '#C0392B',
    textAlign: 'center',
    lineHeight: 20,
  },
  retryButton: {
    backgroundColor: '#4A2E18',
    paddingVertical: 10,
    paddingHorizontal: 20,
    borderRadius: 8,
    marginTop: 8,
  },
  retryButtonText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 32,
  },
  emptyIcon: {
    fontSize: 48,
    marginBottom: 16,
  },
  emptyTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#4A2E18',
    marginBottom: 8,
  },
  emptySubtitle: {
    fontSize: 14,
    color: '#8A7A6E',
    textAlign: 'center',
    lineHeight: 20,
    maxWidth: 280,
  },
  listContent: {
    padding: 16,
    gap: 12,
  },
  feedCard: {
    backgroundColor: '#FFF',
    borderRadius: 14,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 4,
    elevation: 2,
    borderWidth: 1,
    borderColor: '#F0ECE6',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  shopNameTouch: {
    flex: 1,
    marginRight: 10,
  },
  shopName: {
    fontSize: 16,
    fontWeight: '700',
    color: '#4A2E18',
    marginBottom: 2,
  },
  shopAddress: {
    fontSize: 12,
    color: '#8A7A6E',
  },
  ratingBadge: {
    backgroundColor: '#FFF9E6',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#FFE082',
  },
  ratingBadgeText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#B78103',
  },
  authorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 10,
    flexWrap: 'wrap',
    gap: 6,
  },
  authorName: {
    fontSize: 13,
    fontWeight: '600',
    color: '#4A2E18',
  },
  timestampDot: {
    fontSize: 12,
    color: '#BDB3AA',
  },
  timestampText: {
    fontSize: 12,
    color: '#8A7A6E',
  },
  editedBadge: {
    backgroundColor: '#F3EFEA',
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
  },
  editedBadgeText: {
    fontSize: 10,
    color: '#8A7A6E',
    fontWeight: '500',
  },
  reviewContent: {
    fontSize: 14,
    color: '#333',
    lineHeight: 20,
    marginBottom: 12,
  },
  cardActionsRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: 8,
    borderTopWidth: 1,
    borderTopColor: '#F7F4F0',
    paddingTop: 10,
  },
  actionButton: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    backgroundColor: '#F3EFEA',
  },
  actionButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#4A2E18',
  },
  shareButton: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#D4C8BE',
    backgroundColor: 'transparent',
  },
  shareButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#4A2E18',
  },
  footerLoading: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 16,
    gap: 8,
  },
  footerLoadingText: {
    fontSize: 12,
    color: '#8A7A6E',
  },
});

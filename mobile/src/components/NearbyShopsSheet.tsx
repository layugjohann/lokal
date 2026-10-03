import React, { useState } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  ScrollView,
  FlatList,
  TouchableOpacity,
  ActivityIndicator,
} from 'react-native';
import { Shop } from '../types/shop';
import {
  RecommendedShopItem,
  RecommendationStatus,
} from '../types/recommendation';
import { formatDistance, formatRating } from '../services/shopService';
import ShopDetailCard from './ShopDetailCard';

interface NearbyShopsSheetProps {
  shops: Shop[];
  isLoading: boolean;
  errorMessage: string | null;
  selectedShop: Shop | null;
  onSelectShop: (shop: Shop) => void;
  onCloseDetail: () => void;
  onRetry: () => void;
  authToken?: string | null;
  searchQuery?: string;
  onSearchChange?: (text: string) => void;
  minRating?: number | null;
  onMinRatingChange?: (rating: number | null) => void;
  minLokalRating?: number | null;
  onMinLokalRatingChange?: (rating: number | null) => void;
  radius?: number;
  onRadiusChange?: (radius: number) => void;
  sortBy?: 'distance' | 'rating' | 'lokal_rating';
  onSortByChange?: (sort: 'distance' | 'rating' | 'lokal_rating') => void;
  onResetFilters?: () => void;
  hasActiveFilters?: boolean;

  // Personalized recommendations props
  recommendations?: RecommendedShopItem[];
  recommendationsStatus?: RecommendationStatus | 'idle';
  isLoadingRecommendations?: boolean;
  recommendationsError?: string | null;
  recommendationsUserMessage?: string | null;
  onRetryRecommendations?: () => void;
  onFavoriteChange?: (shopId: string, isFavorite: boolean) => void;
  onReviewChange?: (shopId: string) => void;
}

export default function NearbyShopsSheet({
  shops,
  isLoading,
  errorMessage,
  selectedShop,
  onSelectShop,
  onCloseDetail,
  onRetry,
  authToken,
  searchQuery = '',
  onSearchChange,
  minRating = null,
  onMinRatingChange,
  minLokalRating = null,
  onMinLokalRatingChange,
  radius = 5000,
  onRadiusChange,
  sortBy = 'distance',
  onSortByChange,
  onResetFilters,
  hasActiveFilters = false,
  recommendations = [],
  recommendationsStatus = 'idle',
  isLoadingRecommendations = false,
  recommendationsError = null,
  recommendationsUserMessage = null,
  onRetryRecommendations,
  onFavoriteChange,
  onReviewChange,
}: NearbyShopsSheetProps) {
  const [activeTab, setActiveTab] = useState<'nearby' | 'for_you'>('nearby');

  if (selectedShop) {
    return (
      <View style={styles.container}>
        <ShopDetailCard
          key={`${selectedShop.id}:${authToken || 'anon'}`}
          shop={selectedShop}
          onClose={onCloseDetail}
          authToken={authToken}
          onFavoriteChange={onFavoriteChange}
          onReviewChange={onReviewChange}
        />
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Segmented Tab Header when authenticated */}
      {Boolean(authToken) && (
        <View style={styles.tabBar}>
          <TouchableOpacity
            style={[
              styles.tabButton,
              activeTab === 'nearby' && styles.tabButtonActive,
            ]}
            onPress={() => setActiveTab('nearby')}
            activeOpacity={0.7}
            accessibilityRole="tab"
            accessibilityLabel="Explore nearby coffee shops"
            accessibilityState={{ selected: activeTab === 'nearby' }}
          >
            <Text
              style={[
                styles.tabButtonText,
                activeTab === 'nearby' && styles.tabButtonTextActive,
              ]}
            >
              📍 Nearby
            </Text>
          </TouchableOpacity>
          <TouchableOpacity
            style={[
              styles.tabButton,
              activeTab === 'for_you' && styles.tabButtonActive,
            ]}
            onPress={() => setActiveTab('for_you')}
            activeOpacity={0.7}
            accessibilityRole="tab"
            accessibilityLabel="Personalized recommendations for you"
            accessibilityState={{ selected: activeTab === 'for_you' }}
          >
            <Text
              style={[
                styles.tabButtonText,
                activeTab === 'for_you' && styles.tabButtonTextActive,
              ]}
            >
              ✨ For You
            </Text>
          </TouchableOpacity>
        </View>
      )}

      {/* NEARBY TAB CONTENT */}
      {(!authToken || activeTab === 'nearby') && (
        <>
          <View style={styles.sheetHeader}>
            <View style={styles.titleRow}>
              <Text style={styles.sheetTitle}>Nearby Coffee Shops</Text>
              {!isLoading && !errorMessage && shops.length > 0 && (
                <View style={styles.countBadge}>
                  <Text style={styles.countText}>{shops.length}</Text>
                </View>
              )}
            </View>
            {hasActiveFilters && (
              <TouchableOpacity
                onPress={onResetFilters}
                activeOpacity={0.7}
                accessibilityRole="button"
                accessibilityLabel="Reset all filters"
              >
                <Text style={styles.headerResetText}>Reset</Text>
              </TouchableOpacity>
            )}
          </View>

          {/* Search Input Bar */}
          <View style={styles.searchContainer}>
            <TextInput
              style={styles.searchInput}
              placeholder="Search by name or address..."
              placeholderTextColor="#8C7D73"
              value={searchQuery}
              onChangeText={onSearchChange}
              returnKeyType="search"
              autoCorrect={false}
              accessibilityRole="search"
              accessibilityLabel="Search coffee shops by name or address"
            />
            {Boolean(searchQuery) && (
              <TouchableOpacity
                style={styles.clearButton}
                onPress={() => onSearchChange?.('')}
                activeOpacity={0.7}
                accessibilityRole="button"
                accessibilityLabel="Clear search input"
              >
                <Text style={styles.clearButtonText}>✕</Text>
              </TouchableOpacity>
            )}
          </View>

          {/* Filter and Sort Controls */}
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={styles.filterBarContent}
            style={styles.filterBar}
          >
            {/* Distance presets */}
            {[1000, 3000, 5000].map((r) => {
              const isActive = radius === r;
              const label = `${r / 1000} km`;
              return (
                <TouchableOpacity
                  key={`dist-${r}`}
                  style={[
                    styles.filterChip,
                    isActive && styles.filterChipActive,
                  ]}
                  onPress={() =>
                    onRadiusChange?.(isActive && r !== 5000 ? 5000 : r)
                  }
                  activeOpacity={0.7}
                  accessibilityRole="button"
                  accessibilityLabel={`Filter within ${label}`}
                >
                  <Text
                    style={[
                      styles.filterChipText,
                      isActive && styles.filterChipTextActive,
                    ]}
                  >
                    {label}
                  </Text>
                </TouchableOpacity>
              );
            })}

            {/* External rating filter presets */}
            {[4.0, 4.5].map((rate) => {
              const isActive = minRating === rate;
              return (
                <TouchableOpacity
                  key={`rate-${rate}`}
                  style={[
                    styles.filterChip,
                    isActive && styles.filterChipActive,
                  ]}
                  onPress={() => onMinRatingChange?.(isActive ? null : rate)}
                  activeOpacity={0.7}
                  accessibilityRole="button"
                  accessibilityLabel={`Filter minimum Google rating ${rate}`}
                >
                  <Text
                    style={[
                      styles.filterChipText,
                      isActive && styles.filterChipTextActive,
                    ]}
                  >
                    {`Google ★ ${rate}+`}
                  </Text>
                </TouchableOpacity>
              );
            })}

            {/* LOKAL Community rating filter presets */}
            {[4.0, 4.5].map((rate) => {
              const isActive = minLokalRating === rate;
              return (
                <TouchableOpacity
                  key={`lokal-rate-${rate}`}
                  style={[
                    styles.filterChip,
                    isActive && styles.filterChipActive,
                  ]}
                  onPress={() =>
                    onMinLokalRatingChange?.(isActive ? null : rate)
                  }
                  activeOpacity={0.7}
                  accessibilityRole="button"
                  accessibilityLabel={`Filter minimum LOKAL community rating ${rate}`}
                >
                  <Text
                    style={[
                      styles.filterChipText,
                      isActive && styles.filterChipTextActive,
                    ]}
                  >
                    {`LOKAL ★ ${rate}+`}
                  </Text>
                </TouchableOpacity>
              );
            })}

            {/* Sort controls */}
            <TouchableOpacity
              style={[
                styles.filterChip,
                sortBy === 'distance' && styles.filterChipActive,
              ]}
              onPress={() => onSortByChange?.('distance')}
              activeOpacity={0.7}
              accessibilityRole="button"
              accessibilityLabel="Sort by distance"
            >
              <Text
                style={[
                  styles.filterChipText,
                  sortBy === 'distance' && styles.filterChipTextActive,
                ]}
              >
                Nearest
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.filterChip,
                sortBy === 'rating' && styles.filterChipActive,
              ]}
              onPress={() => onSortByChange?.('rating')}
              activeOpacity={0.7}
              accessibilityRole="button"
              accessibilityLabel="Sort by Google rating"
            >
              <Text
                style={[
                  styles.filterChipText,
                  sortBy === 'rating' && styles.filterChipTextActive,
                ]}
              >
                Top Rated
              </Text>
            </TouchableOpacity>

            <TouchableOpacity
              style={[
                styles.filterChip,
                sortBy === 'lokal_rating' && styles.filterChipActive,
              ]}
              onPress={() => onSortByChange?.('lokal_rating')}
              activeOpacity={0.7}
              accessibilityRole="button"
              accessibilityLabel="Sort by LOKAL community rating"
            >
              <Text
                style={[
                  styles.filterChipText,
                  sortBy === 'lokal_rating' && styles.filterChipTextActive,
                ]}
              >
                Top LOKAL
              </Text>
            </TouchableOpacity>
          </ScrollView>

          {/* Loading state */}
          {isLoading && (
            <View style={styles.stateContainer}>
              <ActivityIndicator size="small" color="#4A2E18" />
              <Text style={styles.stateText}>Finding coffee shops...</Text>
            </View>
          )}

          {/* Error state */}
          {errorMessage && !isLoading && (
            <View style={styles.stateContainer}>
              <Text style={styles.errorText}>{errorMessage}</Text>
              <TouchableOpacity
                style={styles.retryButton}
                onPress={onRetry}
                activeOpacity={0.8}
                accessibilityRole="button"
                accessibilityLabel="Retry loading nearby coffee shops"
              >
                <Text style={styles.retryButtonText}>Retry</Text>
              </TouchableOpacity>
            </View>
          )}

          {/* Empty state */}
          {!isLoading && !errorMessage && shops.length === 0 && (
            <View style={styles.stateContainer}>
              <Text style={styles.emptyTitle}>
                {hasActiveFilters
                  ? 'No coffee shops match your criteria'
                  : 'No independent coffee shops found'}
              </Text>
              <Text style={styles.emptySubtitle}>
                {hasActiveFilters
                  ? 'Try adjusting your search query, distance, or rating filters.'
                  : 'We could not find any coffee shops within your selected search radius.'}
              </Text>
              {hasActiveFilters && (
                <TouchableOpacity
                  style={styles.resetButton}
                  onPress={onResetFilters}
                  activeOpacity={0.8}
                  accessibilityRole="button"
                  accessibilityLabel="Reset filters"
                >
                  <Text style={styles.resetButtonText}>Reset Filters</Text>
                </TouchableOpacity>
              )}
            </View>
          )}

          {/* Shop card list */}
          {!isLoading && !errorMessage && shops.length > 0 && (
            <FlatList
              data={shops}
              keyExtractor={(item) => item.id}
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.listContent}
              renderItem={({ item }) => {
                const dist = formatDistance(item.distance_meters);
                const rating = formatRating(item.rating);

                return (
                  <TouchableOpacity
                    style={styles.shopCard}
                    onPress={() => onSelectShop(item)}
                    activeOpacity={0.7}
                    accessibilityRole="button"
                    accessibilityLabel={`Select ${item.name}`}
                  >
                    <Text style={styles.shopName} numberOfLines={1}>
                      {item.name}
                    </Text>
                    <View style={styles.metaRow}>
                      <Text style={styles.ratingText}>{rating}</Text>
                      {item.lokal_rating !== undefined &&
                      item.lokal_rating !== null ? (
                        <>
                          <Text style={styles.dot}>•</Text>
                          <Text style={styles.lokalRatingText}>
                            ☕ {Number(item.lokal_rating).toFixed(1)} ★
                            {item.lokal_reviews_count
                              ? ` (${item.lokal_reviews_count})`
                              : ''}
                          </Text>
                        </>
                      ) : null}
                      {dist ? <Text style={styles.dot}>•</Text> : null}
                      {dist ? (
                        <Text style={styles.distanceText}>{dist}</Text>
                      ) : null}
                    </View>
                    {item.address ? (
                      <Text style={styles.shopAddress} numberOfLines={1}>
                        {item.address}
                      </Text>
                    ) : (
                      <Text style={styles.shopAddressMuted}>
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

      {/* FOR YOU TAB CONTENT */}
      {Boolean(authToken) && activeTab === 'for_you' && (
        <>
          <View style={styles.sheetHeader}>
            <View style={styles.titleRow}>
              <Text style={styles.sheetTitle}>Recommended For You</Text>
              {!isLoadingRecommendations &&
                !recommendationsError &&
                recommendationsStatus === 'personalized' &&
                recommendations.length > 0 && (
                  <View style={styles.countBadge}>
                    <Text style={styles.countText}>
                      {recommendations.length}
                    </Text>
                  </View>
                )}
            </View>
          </View>

          <Text style={styles.forYouSubtitle}>
            Personalized picks based on your favorites and reviews
          </Text>

          {/* Loading state */}
          {isLoadingRecommendations && (
            <View style={styles.stateContainer}>
              <ActivityIndicator size="small" color="#4A2E18" />
              <Text style={styles.stateText}>
                Finding coffee shops tailored to your taste...
              </Text>
            </View>
          )}

          {/* Error state */}
          {recommendationsError && !isLoadingRecommendations && (
            <View style={styles.stateContainer}>
              <Text style={styles.errorText}>{recommendationsError}</Text>
              {onRetryRecommendations && (
                <TouchableOpacity
                  style={styles.retryButton}
                  onPress={onRetryRecommendations}
                  activeOpacity={0.8}
                  accessibilityRole="button"
                  accessibilityLabel="Retry loading recommendations"
                >
                  <Text style={styles.retryButtonText}>Retry</Text>
                </TouchableOpacity>
              )}
            </View>
          )}

          {/* Insufficient data state */}
          {!isLoadingRecommendations &&
            !recommendationsError &&
            recommendationsStatus === 'insufficient_data' && (
              <View style={styles.stateContainer}>
                <Text style={styles.emptyTitle}>Help us learn your taste</Text>
                <Text style={styles.emptySubtitle}>
                  {recommendationsUserMessage ||
                    'Favorite your go-to coffee spots or leave reviews to unlock personalized recommendations tailored to your taste!'}
                </Text>
              </View>
            )}

          {/* Empty state */}
          {!isLoadingRecommendations &&
            !recommendationsError &&
            (recommendationsStatus === 'empty' ||
              (recommendationsStatus === 'personalized' &&
                recommendations.length === 0)) && (
              <View style={styles.stateContainer}>
                <Text style={styles.emptyTitle}>No recommendations nearby</Text>
                <Text style={styles.emptySubtitle}>
                  {recommendationsUserMessage ||
                    'We could not find any recommended coffee shops matching your preferences in this area.'}
                </Text>
              </View>
            )}

          {/* Recommendations List */}
          {!isLoadingRecommendations &&
            !recommendationsError &&
            recommendationsStatus === 'personalized' &&
            recommendations.length > 0 && (
              <FlatList
                data={recommendations}
                keyExtractor={(item) => `rec-${item.shop.id}`}
                horizontal
                showsHorizontalScrollIndicator={false}
                contentContainerStyle={styles.listContent}
                renderItem={({ item }) => {
                  const dist = formatDistance(item.shop.distance_meters);
                  const rating = formatRating(item.shop.rating);

                  return (
                    <TouchableOpacity
                      style={styles.recommendationCard}
                      onPress={() => onSelectShop(item.shop)}
                      activeOpacity={0.7}
                      accessibilityRole="button"
                      accessibilityLabel={`Recommended: ${item.shop.name}. ${item.explanation}`}
                    >
                      <Text style={styles.shopName} numberOfLines={1}>
                        {item.shop.name}
                      </Text>
                      <View style={styles.metaRow}>
                        <Text style={styles.ratingText}>{rating}</Text>
                        {item.shop.lokal_rating !== undefined &&
                        item.shop.lokal_rating !== null ? (
                          <>
                            <Text style={styles.dot}>•</Text>
                            <Text style={styles.lokalRatingText}>
                              ☕ {Number(item.shop.lokal_rating).toFixed(1)} ★
                              {item.shop.lokal_reviews_count
                                ? ` (${item.shop.lokal_reviews_count})`
                                : ''}
                            </Text>
                          </>
                        ) : null}
                        {dist ? <Text style={styles.dot}>•</Text> : null}
                        {dist ? (
                          <Text style={styles.distanceText}>{dist}</Text>
                        ) : null}
                      </View>

                      {/* Grounded explanation badge */}
                      <View style={styles.explanationBox}>
                        <Text style={styles.explanationLabel}>
                          ✨ Why it matches:
                        </Text>
                        <Text style={styles.explanationText} numberOfLines={3}>
                          {item.explanation}
                        </Text>
                      </View>

                      {item.shop.address ? (
                        <Text style={styles.shopAddress} numberOfLines={1}>
                          {item.shop.address}
                        </Text>
                      ) : (
                        <Text style={styles.shopAddressMuted}>
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
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 24,
    left: 16,
    right: 16,
    backgroundColor: '#FAF8F5',
    borderRadius: 16,
    paddingVertical: 12,
    paddingHorizontal: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.18,
    shadowRadius: 8,
    elevation: 5,
    borderWidth: 1,
    borderColor: '#E8E1D9',
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: '#EFEAE4',
    borderRadius: 10,
    padding: 3,
    marginBottom: 10,
  },
  tabButton: {
    flex: 1,
    paddingVertical: 6,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 8,
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
    fontSize: 13,
    fontWeight: '600',
    color: '#8C7D73',
  },
  tabButtonTextActive: {
    color: '#4A2E18',
    fontWeight: '700',
  },
  sheetHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 6,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  sheetTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#4A2E18',
  },
  forYouSubtitle: {
    fontSize: 12,
    color: '#8C7D73',
    marginBottom: 8,
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
  headerResetText: {
    color: '#8A3B28',
    fontSize: 13,
    fontWeight: '600',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#D4C7BC',
    paddingHorizontal: 10,
    marginBottom: 8,
  },
  searchInput: {
    flex: 1,
    height: 38,
    fontSize: 13,
    color: '#4A2E18',
    paddingVertical: 0,
  },
  clearButton: {
    padding: 6,
  },
  clearButtonText: {
    color: '#8C7D73',
    fontSize: 14,
    fontWeight: '600',
  },
  filterBar: {
    marginBottom: 8,
  },
  filterBarContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  filterChip: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderWidth: 1,
    borderColor: '#D4C7BC',
  },
  filterChipActive: {
    backgroundColor: '#4A2E18',
    borderColor: '#4A2E18',
  },
  filterChipText: {
    color: '#6B5E55',
    fontSize: 12,
    fontWeight: '600',
  },
  filterChipTextActive: {
    color: '#FAF8F5',
  },
  stateContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 14,
    gap: 8,
  },
  stateText: {
    color: '#6B5E55',
    fontSize: 13,
    fontWeight: '500',
  },
  errorText: {
    color: '#8A3B28',
    fontSize: 13,
    textAlign: 'center',
    lineHeight: 18,
  },
  retryButton: {
    backgroundColor: '#4A2E18',
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 8,
    marginTop: 4,
  },
  retryButtonText: {
    color: '#FAF8F5',
    fontSize: 13,
    fontWeight: '600',
  },
  emptyTitle: {
    color: '#4A2E18',
    fontSize: 14,
    fontWeight: '600',
    textAlign: 'center',
  },
  emptySubtitle: {
    color: '#8C7D73',
    fontSize: 12,
    textAlign: 'center',
    lineHeight: 16,
    paddingHorizontal: 8,
  },
  resetButton: {
    backgroundColor: '#4A2E18',
    paddingVertical: 6,
    paddingHorizontal: 14,
    borderRadius: 8,
    marginTop: 4,
  },
  resetButtonText: {
    color: '#FAF8F5',
    fontSize: 13,
    fontWeight: '600',
  },
  listContent: {
    gap: 12,
    paddingVertical: 4,
  },
  shopCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 12,
    width: 220,
    borderWidth: 1,
    borderColor: '#EFEAE4',
  },
  recommendationCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 12,
    width: 250,
    borderWidth: 1,
    borderColor: '#EFEAE4',
  },
  explanationBox: {
    backgroundColor: '#F5EFE6',
    borderRadius: 8,
    padding: 8,
    marginVertical: 6,
    borderWidth: 1,
    borderColor: '#E6D9CC',
  },
  explanationLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#6B3E14',
    marginBottom: 2,
  },
  explanationText: {
    fontSize: 12,
    color: '#4A2E18',
    lineHeight: 16,
  },
  shopName: {
    fontSize: 14,
    fontWeight: '700',
    color: '#4A2E18',
    marginBottom: 4,
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
  lokalRatingText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#8A3B28',
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
  shopAddress: {
    fontSize: 12,
    color: '#6B5E55',
  },
  shopAddressMuted: {
    fontSize: 12,
    color: '#A4988F',
    fontStyle: 'italic',
  },
});

import React from 'react';
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
  radius?: number;
  onRadiusChange?: (radius: number) => void;
  sortBy?: 'distance' | 'rating';
  onSortByChange?: (sort: 'distance' | 'rating') => void;
  onResetFilters?: () => void;
  hasActiveFilters?: boolean;
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
  radius = 5000,
  onRadiusChange,
  sortBy = 'distance',
  onSortByChange,
  onResetFilters,
  hasActiveFilters = false,
}: NearbyShopsSheetProps) {
  if (selectedShop) {
    return (
      <View style={styles.container}>
        <ShopDetailCard
          key={`${selectedShop.id}:${authToken || 'anon'}`}
          shop={selectedShop}
          onClose={onCloseDetail}
          authToken={authToken}
        />
      </View>
    );
  }

  return (
    <View style={styles.container}>
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
          placeholder="Search coffee shops by name..."
          placeholderTextColor="#8C7D73"
          value={searchQuery}
          onChangeText={onSearchChange}
          returnKeyType="search"
          autoCorrect={false}
          accessibilityRole="search"
          accessibilityLabel="Search coffee shops by name"
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
              style={[styles.filterChip, isActive && styles.filterChipActive]}
              onPress={() => onRadiusChange?.(isActive && r !== 5000 ? 5000 : r)}
              activeOpacity={0.7}
              accessibilityRole="button"
              accessibilityLabel={`Filter within ${label}`}
            >
              <Text style={[styles.filterChipText, isActive && styles.filterChipTextActive]}>
                {label}
              </Text>
            </TouchableOpacity>
          );
        })}

        {/* Rating filter presets */}
        {[4.0, 4.5].map((rate) => {
          const isActive = minRating === rate;
          return (
            <TouchableOpacity
              key={`rate-${rate}`}
              style={[styles.filterChip, isActive && styles.filterChipActive]}
              onPress={() => onMinRatingChange?.(isActive ? null : rate)}
              activeOpacity={0.7}
              accessibilityRole="button"
              accessibilityLabel={`Filter minimum rating ${rate}`}
            >
              <Text style={[styles.filterChipText, isActive && styles.filterChipTextActive]}>
                {`★ ${rate}+`}
              </Text>
            </TouchableOpacity>
          );
        })}

        {/* Sort controls */}
        <TouchableOpacity
          style={[styles.filterChip, sortBy === 'distance' && styles.filterChipActive]}
          onPress={() => onSortByChange?.('distance')}
          activeOpacity={0.7}
          accessibilityRole="button"
          accessibilityLabel="Sort by distance"
        >
          <Text style={[styles.filterChipText, sortBy === 'distance' && styles.filterChipTextActive]}>
            Nearest
          </Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.filterChip, sortBy === 'rating' && styles.filterChipActive]}
          onPress={() => onSortByChange?.('rating')}
          activeOpacity={0.7}
          accessibilityRole="button"
          accessibilityLabel="Sort by rating"
        >
          <Text style={[styles.filterChipText, sortBy === 'rating' && styles.filterChipTextActive]}>
            Top Rated
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
                  {dist ? <Text style={styles.dot}>•</Text> : null}
                  {dist ? <Text style={styles.distanceText}>{dist}</Text> : null}
                </View>
                {item.address ? (
                  <Text style={styles.shopAddress} numberOfLines={1}>
                    {item.address}
                  </Text>
                ) : (
                  <Text style={styles.shopAddressMuted}>Address not available</Text>
                )}
              </TouchableOpacity>
            );
          }}
        />
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
  sheetHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
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

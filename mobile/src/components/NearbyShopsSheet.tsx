import React from 'react';
import {
  StyleSheet,
  View,
  Text,
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
        <Text style={styles.sheetTitle}>Nearby Coffee Shops</Text>
        {!isLoading && !errorMessage && shops.length > 0 && (
          <View style={styles.countBadge}>
            <Text style={styles.countText}>{shops.length}</Text>
          </View>
        )}
      </View>

      {isLoading && (
        <View style={styles.stateContainer}>
          <ActivityIndicator size="small" color="#4A2E18" />
          <Text style={styles.stateText}>Finding nearby coffee shops...</Text>
        </View>
      )}

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

      {!isLoading && !errorMessage && shops.length === 0 && (
        <View style={styles.stateContainer}>
          <Text style={styles.emptyTitle}>No independent coffee shops found</Text>
          <Text style={styles.emptySubtitle}>
            We could not find any coffee shops within 5 km of your location.
          </Text>
        </View>
      )}

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
    gap: 8,
    marginBottom: 8,
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

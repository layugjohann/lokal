import React from 'react';
import { StyleSheet, View, Text, TouchableOpacity } from 'react-native';
import { Shop } from '../types/shop';
import { formatDistance, formatRating } from '../services/shopService';

interface ShopDetailCardProps {
  shop: Shop;
  onClose: () => void;
}

export default function ShopDetailCard({ shop, onClose }: ShopDetailCardProps) {
  const formattedDistance = formatDistance(shop.distance_meters);
  const formattedRating = formatRating(shop.rating);

  return (
    <View style={styles.card}>
      <View style={styles.headerRow}>
        <Text style={styles.name} numberOfLines={2}>
          {shop.name}
        </Text>
        <TouchableOpacity
          style={styles.closeButton}
          onPress={onClose}
          activeOpacity={0.7}
          accessibilityRole="button"
          accessibilityLabel="Close shop details"
        >
          <Text style={styles.closeText}>✕</Text>
        </TouchableOpacity>
      </View>

      <View style={styles.badgeRow}>
        <View style={styles.ratingBadge}>
          <Text style={styles.ratingText}>{formattedRating}</Text>
        </View>
        {formattedDistance ? (
          <View style={styles.distanceBadge}>
            <Text style={styles.distanceText}>{formattedDistance}</Text>
          </View>
        ) : null}
      </View>

      {shop.address ? (
        <Text style={styles.address} numberOfLines={2}>
          {shop.address}
        </Text>
      ) : (
        <Text style={styles.noAddress}>Address not available</Text>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 6,
    elevation: 4,
    borderWidth: 1,
    borderColor: '#EFEAE4',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 8,
    marginBottom: 8,
  },
  name: {
    flex: 1,
    fontSize: 18,
    fontWeight: '700',
    color: '#4A2E18',
    lineHeight: 22,
  },
  closeButton: {
    padding: 4,
    borderRadius: 12,
    backgroundColor: '#F3EFEA',
    width: 28,
    height: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  closeText: {
    fontSize: 14,
    color: '#6B5E55',
    fontWeight: '600',
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 10,
  },
  ratingBadge: {
    backgroundColor: '#FDF6EC',
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#F3D9A2',
  },
  ratingText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#A06D00',
  },
  distanceBadge: {
    backgroundColor: '#F3EFEA',
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
  },
  distanceText: {
    fontSize: 13,
    fontWeight: '500',
    color: '#6B5E55',
  },
  address: {
    fontSize: 14,
    color: '#6B5E55',
    lineHeight: 18,
  },
  noAddress: {
    fontSize: 13,
    color: '#A4988F',
    fontStyle: 'italic',
  },
});

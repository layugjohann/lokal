import React, { useEffect, useState, useCallback } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
  Image,
  Linking,
} from 'react-native';
import { Shop } from '../types/shop';
import { ShopReviewsResponse, UnifiedReview, ProviderAttribution } from '../types/review';
import { formatDistance, formatRating } from '../services/shopService';
import { fetchShopReviews } from '../services/reviewService';

interface ShopDetailCardProps {
  shop: Shop;
  onClose: () => void;
  authToken?: string | null;
}

export default function ShopDetailCard({ shop, onClose, authToken }: ShopDetailCardProps) {
  const formattedDistance = formatDistance(shop.distance_meters);
  const formattedRating = formatRating(shop.rating);

  const [reviewsData, setReviewsData] = useState<ShopReviewsResponse | null>(null);
  const [isLoadingReviews, setIsLoadingReviews] = useState<boolean>(true);
  const [reviewsError, setReviewsError] = useState<string | null>(null);

  const loadReviews = useCallback(async () => {
    setIsLoadingReviews(true);
    setReviewsError(null);
    try {
      const data = await fetchShopReviews(shop.id, authToken);
      setReviewsData(data);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Unable to load reviews right now.';
      setReviewsError(message);
    } finally {
      setIsLoadingReviews(false);
    }
  }, [shop.id, authToken]);

  useEffect(() => {
    loadReviews();
  }, [loadReviews]);

  const handleOpenUrl = async (url?: string | null) => {
    if (!url) return;
    try {
      const supported = await Linking.canOpenURL(url);
      if (supported) {
        await Linking.openURL(url);
      }
    } catch {
      // Gracefully ignore browser open errors
    }
  };

  const googleAttribution = reviewsData?.attributions.find(
    (attr: ProviderAttribution) => attr.provider === 'google'
  );

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

      <View style={styles.divider} />

      <ScrollView
        style={styles.reviewsScroll}
        showsVerticalScrollIndicator={false}
        contentContainerStyle={styles.reviewsContent}
        nestedScrollEnabled={true}
      >
        <View style={styles.reviewsHeaderRow}>
          <View style={styles.reviewsTitleGroup}>
            <Text style={styles.reviewsSectionTitle}>Reviews</Text>
            {reviewsData?.total_reviews_count ? (
              <Text style={styles.reviewsCountText}>
                ({reviewsData.total_reviews_count})
              </Text>
            ) : null}
          </View>

          {googleAttribution ? (
            <TouchableOpacity
              onPress={() => handleOpenUrl(googleAttribution.source_url)}
              activeOpacity={0.7}
              style={styles.providerBadge}
              accessibilityRole="link"
              accessibilityLabel="View on Google Maps"
            >
              <Text style={styles.providerBadgeText}>Google Maps</Text>
            </TouchableOpacity>
          ) : null}
        </View>

        {isLoadingReviews && (
          <View style={styles.stateContainer}>
            <ActivityIndicator size="small" color="#4A2E18" />
            <Text style={styles.stateText}>Loading reviews...</Text>
          </View>
        )}

        {!isLoadingReviews && reviewsError && (
          <View style={styles.stateContainer}>
            <Text style={styles.errorText}>{reviewsError}</Text>
            <TouchableOpacity
              style={styles.retryButton}
              onPress={loadReviews}
              activeOpacity={0.8}
              accessibilityRole="button"
              accessibilityLabel="Retry loading reviews"
            >
              <Text style={styles.retryButtonText}>Retry</Text>
            </TouchableOpacity>
          </View>
        )}

        {!isLoadingReviews && !reviewsError && reviewsData?.reviews.length === 0 && (
          <View style={styles.stateContainer}>
            <Text style={styles.emptyText}>No reviews available yet for this café.</Text>
          </View>
        )}

        {!isLoadingReviews &&
          !reviewsError &&
          reviewsData &&
          reviewsData.reviews.length > 0 && (
            <View style={styles.reviewsList}>
              {reviewsData.reviews.map((review: UnifiedReview) => (
                <View key={review.id} style={styles.reviewItem}>
                  <View style={styles.reviewAuthorRow}>
                    {review.author.avatar_url ? (
                      <Image
                        source={{ uri: review.author.avatar_url }}
                        style={styles.authorAvatar}
                      />
                    ) : (
                      <View style={styles.authorAvatarFallback}>
                        <Text style={styles.authorInitial}>
                          {review.author.display_name.charAt(0).toUpperCase()}
                        </Text>
                      </View>
                    )}

                    <View style={styles.authorMeta}>
                      {review.author.profile_url ? (
                        <TouchableOpacity
                          onPress={() => handleOpenUrl(review.author.profile_url)}
                          activeOpacity={0.7}
                          accessibilityRole="link"
                          accessibilityLabel={`View ${review.author.display_name}'s profile`}
                        >
                          <Text style={styles.authorNameLink}>
                            {review.author.display_name}
                          </Text>
                        </TouchableOpacity>
                      ) : (
                        <Text style={styles.authorName}>
                          {review.author.display_name}
                        </Text>
                      )}

                      <View style={styles.reviewRatingRow}>
                        <Text style={styles.stars}>
                          {'★'.repeat(review.rating)}
                          {'☆'.repeat(Math.max(0, 5 - review.rating))}
                        </Text>
                        {review.relative_time ? (
                          <Text style={styles.relativeTime}>
                            • {review.relative_time}
                          </Text>
                        ) : null}
                      </View>
                    </View>
                  </View>

                  {review.text ? (
                    <Text style={styles.reviewBody}>{review.text}</Text>
                  ) : null}

                  {review.report_url ? (
                    <View style={styles.reviewFooter}>
                      <TouchableOpacity
                        onPress={() => handleOpenUrl(review.report_url)}
                        activeOpacity={0.6}
                        accessibilityRole="link"
                        accessibilityLabel="Report this review"
                      >
                        <Text style={styles.reportLink}>Report</Text>
                      </TouchableOpacity>
                    </View>
                  ) : null}
                </View>
              ))}

              {googleAttribution?.source_url ? (
                <TouchableOpacity
                  style={styles.viewAllButton}
                  onPress={() => handleOpenUrl(googleAttribution.source_url)}
                  activeOpacity={0.8}
                  accessibilityRole="link"
                  accessibilityLabel="View all reviews on Google Maps"
                >
                  <Text style={styles.viewAllButtonText}>
                    View on Google Maps ↗
                  </Text>
                </TouchableOpacity>
              ) : null}

              <Text style={styles.attributionNotice}>
                {googleAttribution?.required_notice || 'Reviews provided by Google Maps'}
              </Text>
            </View>
          )}
      </ScrollView>
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
    maxHeight: 460,
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
    marginBottom: 8,
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
    fontSize: 13,
    color: '#6B5E55',
    lineHeight: 18,
  },
  noAddress: {
    fontSize: 13,
    color: '#A4988F',
    fontStyle: 'italic',
  },
  divider: {
    height: 1,
    backgroundColor: '#EFEAE4',
    marginVertical: 12,
  },
  reviewsScroll: {
    flexGrow: 0,
  },
  reviewsContent: {
    paddingBottom: 4,
  },
  reviewsHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  reviewsTitleGroup: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  reviewsSectionTitle: {
    fontSize: 15,
    fontWeight: '700',
    color: '#4A2E18',
  },
  reviewsCountText: {
    fontSize: 13,
    color: '#8C7D73',
    fontWeight: '500',
  },
  providerBadge: {
    backgroundColor: '#E8F0FE',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderWidth: 1,
    borderColor: '#D2E3FC',
  },
  providerBadgeText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#1967D2',
  },
  stateContainer: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    gap: 8,
  },
  stateText: {
    fontSize: 13,
    color: '#6B5E55',
  },
  errorText: {
    fontSize: 13,
    color: '#8A3B28',
    textAlign: 'center',
    lineHeight: 18,
  },
  retryButton: {
    backgroundColor: '#4A2E18',
    paddingVertical: 5,
    paddingHorizontal: 12,
    borderRadius: 6,
    marginTop: 4,
  },
  retryButtonText: {
    color: '#FAF8F5',
    fontSize: 12,
    fontWeight: '600',
  },
  emptyText: {
    fontSize: 13,
    color: '#8C7D73',
    fontStyle: 'italic',
  },
  reviewsList: {
    gap: 12,
  },
  reviewItem: {
    backgroundColor: '#FAF8F5',
    borderRadius: 10,
    padding: 10,
    borderWidth: 1,
    borderColor: '#EFEAE4',
  },
  reviewAuthorRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 6,
  },
  authorAvatar: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#EFEAE4',
  },
  authorAvatarFallback: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#D4A373',
    alignItems: 'center',
    justifyContent: 'center',
  },
  authorInitial: {
    fontSize: 13,
    fontWeight: '700',
    color: '#FAF8F5',
  },
  authorMeta: {
    flex: 1,
  },
  authorName: {
    fontSize: 13,
    fontWeight: '600',
    color: '#4A2E18',
  },
  authorNameLink: {
    fontSize: 13,
    fontWeight: '600',
    color: '#1967D2',
    textDecorationLine: 'underline',
  },
  reviewRatingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 1,
  },
  stars: {
    fontSize: 11,
    color: '#A06D00',
  },
  relativeTime: {
    fontSize: 11,
    color: '#8C7D73',
  },
  reviewBody: {
    fontSize: 13,
    color: '#4A2E18',
    lineHeight: 18,
  },
  reviewFooter: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    marginTop: 6,
  },
  reportLink: {
    fontSize: 11,
    color: '#8C7D73',
    textDecorationLine: 'underline',
  },
  viewAllButton: {
    backgroundColor: '#F3EFEA',
    borderRadius: 8,
    paddingVertical: 8,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E8E1D9',
    marginTop: 4,
  },
  viewAllButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#4A2E18',
  },
  attributionNotice: {
    fontSize: 10,
    color: '#A4988F',
    textAlign: 'center',
    marginTop: 2,
    fontStyle: 'italic',
  },
});

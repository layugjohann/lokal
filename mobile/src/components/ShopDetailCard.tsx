import React, { useEffect, useState, useCallback, useRef } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TouchableOpacity,
  ActivityIndicator,
  ScrollView,
  Image,
  Linking,
  TextInput,
} from 'react-native';
import { Shop } from '../types/shop';
import { ShopReviewsResponse, ShopReviewSummaryResponse, ShopRecommendationsResponse, UnifiedReview, ProviderAttribution } from '../types/review';
import { formatDistance, formatRating } from '../services/shopService';
import {
  fetchShopReviews,
  fetchShopReviewSummary,
  fetchShopRecommendations,
  fetchMyReview,
  createUserReview,
  updateUserReview,
  deleteUserReview,
} from '../services/reviewService';
import {
  fetchFavoriteStatus,
  addFavorite,
  removeFavorite,
} from '../services/favoriteService';

interface ShopDetailCardProps {
  shop: Shop;
  onClose: () => void;
  authToken?: string | null;
}

export default function ShopDetailCard({ shop, onClose, authToken }: ShopDetailCardProps) {
  const formattedDistance = formatDistance(shop.distance_meters);
  const formattedRating = formatRating(shop.rating);

  const [reviewsData, setReviewsData] = useState<ShopReviewsResponse | null>(null);
  const [myReview, setMyReview] = useState<UnifiedReview | null>(null);
  const [isLoadingReviews, setIsLoadingReviews] = useState<boolean>(true);
  const [reviewsError, setReviewsError] = useState<string | null>(null);
  const currentRequestId = useRef<number>(0);
  const currentMutationId = useRef<number>(0);

  // AI Review Summary state
  const [summaryData, setSummaryData] = useState<ShopReviewSummaryResponse | null>(null);
  const [isLoadingSummary, setIsLoadingSummary] = useState<boolean>(true);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const currentSummaryRequestId = useRef<number>(0);

  // AI Must-Try Recommendations state
  const [recommendationsData, setRecommendationsData] = useState<ShopRecommendationsResponse | null>(null);
  const [isLoadingRecommendations, setIsLoadingRecommendations] = useState<boolean>(true);
  const [recommendationsError, setRecommendationsError] = useState<string | null>(null);
  const currentRecommendationsRequestId = useRef<number>(0);

  // Favorite coffee shop state
  const [isFavorite, setIsFavorite] = useState<boolean>(false);
  const [isLoadingFavorite, setIsLoadingFavorite] = useState<boolean>(true);
  const [isMutatingFavorite, setIsMutatingFavorite] = useState<boolean>(false);
  const [favoriteError, setFavoriteError] = useState<string | null>(null);
  const currentFavoriteRequestId = useRef<number>(0);
  const currentFavoriteMutationId = useRef<number>(0);

  // User review form state
  const [isFormOpen, setIsFormOpen] = useState<boolean>(false);
  const [formRating, setFormRating] = useState<number>(5);
  const [formContent, setFormContent] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const loadReviews = useCallback(async () => {
    if (!authToken) {
      setIsLoadingReviews(false);
      setReviewsData(null);
      setMyReview(null);
      setReviewsError(null);
      setDeleteError(null);
      return;
    }

    const requestId = ++currentRequestId.current;
    setIsLoadingReviews(true);
    setReviewsError(null);

    try {
      const reviewsPromise = fetchShopReviews(shop.id, authToken);
      const myReviewPromise = fetchMyReview(shop.id, authToken).catch(() => null);

      const [data, userReview] = await Promise.all([reviewsPromise, myReviewPromise]);
      if (requestId === currentRequestId.current) {
        setReviewsData(data);
        setMyReview(userReview);
        setDeleteError(null);
      }
    } catch (err) {
      if (requestId === currentRequestId.current) {
        const message =
          err instanceof Error ? err.message : 'Unable to load reviews right now.';
        setReviewsError(message);
      }
    } finally {
      if (requestId === currentRequestId.current) {
        setIsLoadingReviews(false);
      }
    }
  }, [shop.id, authToken]);

  const loadSummary = useCallback(async () => {
    if (!authToken) {
      setIsLoadingSummary(false);
      setSummaryData(null);
      setSummaryError(null);
      return;
    }

    const requestId = ++currentSummaryRequestId.current;
    setIsLoadingSummary(true);
    setSummaryError(null);

    try {
      const data = await fetchShopReviewSummary(shop.id, authToken);
      if (requestId === currentSummaryRequestId.current) {
        setSummaryData(data);
      }
    } catch (err) {
      if (requestId === currentSummaryRequestId.current) {
        const message =
          err instanceof Error ? err.message : 'Unable to load review summary.';
        setSummaryError(message);
      }
    } finally {
      if (requestId === currentSummaryRequestId.current) {
        setIsLoadingSummary(false);
      }
    }
  }, [shop.id, authToken]);

  const loadRecommendations = useCallback(async () => {
    if (!authToken) {
      setIsLoadingRecommendations(false);
      setRecommendationsData(null);
      setRecommendationsError(null);
      return;
    }

    const requestId = ++currentRecommendationsRequestId.current;
    setIsLoadingRecommendations(true);
    setRecommendationsError(null);

    try {
      const data = await fetchShopRecommendations(shop.id, authToken);
      if (requestId === currentRecommendationsRequestId.current) {
        setRecommendationsData(data);
      }
    } catch (err) {
      if (requestId === currentRecommendationsRequestId.current) {
        const message =
          err instanceof Error ? err.message : 'Unable to load recommendations.';
        setRecommendationsError(message);
      }
    } finally {
      if (requestId === currentRecommendationsRequestId.current) {
        setIsLoadingRecommendations(false);
      }
    }
  }, [shop.id, authToken]);

  const loadFavorite = useCallback(async () => {
    if (!authToken) {
      setIsLoadingFavorite(false);
      setIsFavorite(false);
      setFavoriteError(null);
      return;
    }

    const requestId = ++currentFavoriteRequestId.current;
    setIsLoadingFavorite(true);
    setFavoriteError(null);

    try {
      const data = await fetchFavoriteStatus(shop.id, authToken);
      if (requestId === currentFavoriteRequestId.current) {
        setIsFavorite(data.is_favorite);
      }
    } catch (err) {
      if (requestId === currentFavoriteRequestId.current) {
        const message =
          err instanceof Error ? err.message : 'Unable to load favorite status.';
        setFavoriteError(message);
      }
    } finally {
      if (requestId === currentFavoriteRequestId.current) {
        setIsLoadingFavorite(false);
      }
    }
  }, [shop.id, authToken]);

  useEffect(() => {
    currentRequestId.current += 1;
    currentMutationId.current += 1;
    currentSummaryRequestId.current += 1;
    currentRecommendationsRequestId.current += 1;
    currentFavoriteRequestId.current += 1;
    currentFavoriteMutationId.current += 1;

    setIsFormOpen(false);
    setFormRating(5);
    setFormContent('');
    setIsSubmitting(false);
    setIsDeleting(false);
    setFormError(null);
    setDeleteError(null);
    setMyReview(null);
    setReviewsData(null);
    setReviewsError(null);
    setSummaryData(null);
    setSummaryError(null);
    setRecommendationsData(null);
    setRecommendationsError(null);
    setIsFavorite(false);
    setIsLoadingFavorite(true);
    setIsMutatingFavorite(false);
    setFavoriteError(null);

    loadReviews();
    loadSummary();
    loadRecommendations();
    loadFavorite();
    return () => {
      currentRequestId.current += 1;
      currentMutationId.current += 1;
      currentSummaryRequestId.current += 1;
      currentRecommendationsRequestId.current += 1;
      currentFavoriteRequestId.current += 1;
      currentFavoriteMutationId.current += 1;
    };
  }, [shop.id, authToken, loadReviews, loadSummary, loadRecommendations, loadFavorite]);

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

  const handleOpenForm = (existing?: UnifiedReview | null) => {
    if (existing) {
      setFormRating(existing.rating);
      setFormContent(existing.text || '');
    } else {
      setFormRating(5);
      setFormContent('');
    }
    setFormError(null);
    setDeleteError(null);
    setIsFormOpen(true);
  };

  const handleCancelForm = () => {
    setIsFormOpen(false);
    setFormError(null);
  };

  const handleSubmitReview = async () => {
    if (!authToken) return;
    const mutationId = ++currentMutationId.current;
    const activeShopId = shop.id;
    const activeToken = authToken;
    setIsSubmitting(true);
    setFormError(null);

    try {
      if (myReview) {
        await updateUserReview(
          shop.id,
          { rating: formRating, content: formContent },
          authToken
        );
      } else {
        await createUserReview(
          shop.id,
          { rating: formRating, content: formContent },
          authToken
        );
      }
      if (
        mutationId === currentMutationId.current &&
        activeShopId === shop.id &&
        activeToken === authToken
      ) {
        setIsFormOpen(false);
        await Promise.all([loadReviews(), loadSummary(), loadRecommendations()]);
      }
    } catch (err) {
      if (
        mutationId === currentMutationId.current &&
        activeShopId === shop.id &&
        activeToken === authToken
      ) {
        const message =
          err instanceof Error ? err.message : 'Failed to save review.';
        setFormError(message);
      }
    } finally {
      if (
        mutationId === currentMutationId.current &&
        activeShopId === shop.id &&
        activeToken === authToken
      ) {
        setIsSubmitting(false);
      }
    }
  };

  const handleDeleteReview = async () => {
    if (!authToken) return;
    const mutationId = ++currentMutationId.current;
    const activeShopId = shop.id;
    const activeToken = authToken;
    setIsDeleting(true);
    setDeleteError(null);

    try {
      await deleteUserReview(shop.id, authToken);
      if (
        mutationId === currentMutationId.current &&
        activeShopId === shop.id &&
        activeToken === authToken
      ) {
        setIsFormOpen(false);
        setMyReview(null);
        await Promise.all([loadReviews(), loadSummary(), loadRecommendations()]);
      }
    } catch (err) {
      if (
        mutationId === currentMutationId.current &&
        activeShopId === shop.id &&
        activeToken === authToken
      ) {
        const message =
          err instanceof Error ? err.message : 'Failed to delete review.';
        setDeleteError(message);
      }
    } finally {
      if (
        mutationId === currentMutationId.current &&
        activeShopId === shop.id &&
        activeToken === authToken
      ) {
        setIsDeleting(false);
      }
    }
  };

  const handleToggleFavorite = async () => {
    if (!authToken) {
      setFavoriteError('Please sign in to favorite this coffee shop.');
      return;
    }
    if (isMutatingFavorite) {
      return;
    }

    const mutationId = ++currentFavoriteMutationId.current;
    const activeShopId = shop.id;
    const activeToken = authToken;
    const previousFavorite = isFavorite;

    // Optimistically toggle state
    setIsFavorite(!previousFavorite);
    setIsMutatingFavorite(true);
    setFavoriteError(null);

    try {
      if (previousFavorite) {
        await removeFavorite(activeShopId, activeToken);
      } else {
        await addFavorite(activeShopId, activeToken);
      }
      if (
        mutationId === currentFavoriteMutationId.current &&
        activeShopId === shop.id &&
        activeToken === authToken
      ) {
        setIsFavorite(!previousFavorite);
      }
    } catch (err) {
      if (
        mutationId === currentFavoriteMutationId.current &&
        activeShopId === shop.id &&
        activeToken === authToken
      ) {
        // Rollback state on failure
        setIsFavorite(previousFavorite);
        const message =
          err instanceof Error
            ? err.message
            : previousFavorite
            ? 'Failed to remove favorite.'
            : 'Failed to favorite coffee shop.';
        setFavoriteError(message);
      }
    } finally {
      if (
        mutationId === currentFavoriteMutationId.current &&
        activeShopId === shop.id &&
        activeToken === authToken
      ) {
        setIsMutatingFavorite(false);
      }
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
        <View style={styles.headerActions}>
          <TouchableOpacity
            style={[styles.favoriteButton, isFavorite && styles.favoriteButtonActive]}
            onPress={handleToggleFavorite}
            disabled={isMutatingFavorite}
            activeOpacity={0.7}
            accessibilityRole="button"
            accessibilityLabel={isFavorite ? 'Remove from favorites' : 'Add to favorites'}
          >
            {isMutatingFavorite ? (
              <ActivityIndicator size="small" color={isFavorite ? '#D9534F' : '#8C7D73'} />
            ) : (
              <Text style={[styles.favoriteIcon, isFavorite && styles.favoriteIconActive]}>
                {isFavorite ? '♥' : '♡'}
              </Text>
            )}
          </TouchableOpacity>
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
      </View>

      {favoriteError ? (
        <View style={styles.favoriteErrorBanner}>
          <Text style={styles.favoriteErrorText}>{favoriteError}</Text>
          <TouchableOpacity
            onPress={() => setFavoriteError(null)}
            style={styles.favoriteErrorDismiss}
            accessibilityRole="button"
            accessibilityLabel="Dismiss favorite error"
          >
            <Text style={styles.favoriteErrorDismissText}>✕</Text>
          </TouchableOpacity>
        </View>
      ) : null}

      <View style={styles.badgeRow}>
        {reviewsData?.lokal_reviews_count ? (
          <View style={styles.lokalRatingBadge}>
            <Text style={styles.lokalRatingText}>
              ☕ LOKAL {reviewsData.lokal_average_rating?.toFixed(1) ?? '—'} ★ ({reviewsData.lokal_reviews_count})
            </Text>
          </View>
        ) : null}
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
            {reviewsData ? (
              <Text style={styles.reviewsCountText}>
                ({(reviewsData.lokal_reviews_count || 0) + (reviewsData.total_reviews_count || 0)})
              </Text>
            ) : null}
          </View>

          {googleAttribution ? (
            googleAttribution.source_url ? (
              <TouchableOpacity
                onPress={() => handleOpenUrl(googleAttribution.source_url)}
                activeOpacity={0.7}
                style={styles.providerBadge}
                accessibilityRole="link"
                accessibilityLabel="View on Google Maps"
              >
                <Text style={styles.providerBadgeText}>Google Maps</Text>
              </TouchableOpacity>
            ) : (
              <View style={styles.providerBadge}>
                <Text style={styles.providerBadgeText}>Google Maps</Text>
              </View>
            )
          ) : null}
        </View>

        {/* AI Review Summary Section */}
        {authToken && (
          <View style={styles.aiSummaryContainer}>
            {isLoadingSummary && (
              <View style={styles.aiSummaryLoading}>
                <ActivityIndicator size="small" color="#4A2E18" />
                <Text style={styles.aiSummaryLoadingText}>
                  Synthesizing review summary...
                </Text>
              </View>
            )}

            {!isLoadingSummary && summaryError && (
              <View style={styles.aiSummaryErrorContainer}>
                <Text style={styles.aiSummaryErrorText}>{summaryError}</Text>
                <TouchableOpacity
                  style={styles.aiSummaryRetryButton}
                  onPress={loadSummary}
                  activeOpacity={0.7}
                  accessibilityRole="button"
                  accessibilityLabel="Retry loading review summary"
                >
                  <Text style={styles.aiSummaryRetryText}>Retry</Text>
                </TouchableOpacity>
              </View>
            )}

            {!isLoadingSummary && !summaryError && summaryData?.status === 'insufficient_reviews' && (
              <View style={styles.aiSummaryInsufficient}>
                <Text style={styles.aiSummaryInsufficientText}>
                  ✨ Not enough customer reviews yet to generate an AI summary.
                </Text>
              </View>
            )}

            {!isLoadingSummary && !summaryError && summaryData?.status === 'available' && summaryData.summary && (
              <View style={styles.aiSummaryCard}>
                <View style={styles.aiSummaryHeader}>
                  <Text style={styles.aiSummaryBadge}>✨ AI Review Summary</Text>
                  {summaryData.review_count_analyzed > 0 ? (
                    <Text style={styles.aiSummaryCountText}>
                      Based on {summaryData.review_count_analyzed} reviews
                    </Text>
                  ) : null}
                </View>

                <Text style={styles.aiSummaryText}>{summaryData.summary}</Text>

                {summaryData.positive_themes && summaryData.positive_themes.length > 0 && (
                  <View style={styles.themeGroup}>
                    <Text style={styles.themeGroupLabel}>Highlights</Text>
                    <View style={styles.themePillContainer}>
                      {summaryData.positive_themes.map((theme, idx) => (
                        <View key={`pos-${idx}`} style={styles.positivePill}>
                          <Text style={styles.positivePillText}>+ {theme}</Text>
                        </View>
                      ))}
                    </View>
                  </View>
                )}

                {summaryData.negative_themes && summaryData.negative_themes.length > 0 && (
                  <View style={styles.themeGroup}>
                    <Text style={styles.themeGroupLabel}>Things to Note</Text>
                    <View style={styles.themePillContainer}>
                      {summaryData.negative_themes.map((theme, idx) => (
                        <View key={`neg-${idx}`} style={styles.negativePill}>
                          <Text style={styles.negativePillText}>- {theme}</Text>
                        </View>
                      ))}
                    </View>
                  </View>
                )}
              </View>
            )}
          </View>
        )}

        {/* AI Must Try Recommendations Section */}
        {authToken && (
          <View style={styles.aiRecommendationsContainer}>
            {isLoadingRecommendations && (
              <View style={styles.aiRecommendationsLoading}>
                <ActivityIndicator size="small" color="#4A2E18" />
                <Text style={styles.aiRecommendationsLoadingText}>
                  Finding customer favorites...
                </Text>
              </View>
            )}

            {!isLoadingRecommendations && recommendationsError && (
              <View style={styles.aiRecommendationsErrorContainer}>
                <Text style={styles.aiRecommendationsErrorText}>{recommendationsError}</Text>
                <TouchableOpacity
                  style={styles.aiRecommendationsRetryButton}
                  onPress={loadRecommendations}
                  activeOpacity={0.7}
                  accessibilityRole="button"
                  accessibilityLabel="Retry loading recommendations"
                >
                  <Text style={styles.aiRecommendationsRetryText}>Retry</Text>
                </TouchableOpacity>
              </View>
            )}

            {!isLoadingRecommendations &&
              !recommendationsError &&
              recommendationsData &&
              recommendationsData.status === 'insufficient_reviews' && (
                <View style={styles.aiRecommendationsInsufficient}>
                  <Text style={styles.aiRecommendationsInsufficientText}>
                    ✨ Not enough customer reviews yet to generate recommendations.
                  </Text>
                </View>
              )}

            {!isLoadingRecommendations &&
              !recommendationsError &&
              recommendationsData &&
              recommendationsData.status === 'available' &&
              recommendationsData.items.length === 0 && (
                <View style={styles.aiRecommendationsEmpty}>
                  <Text style={styles.aiRecommendationsEmptyText}>
                    ✨ No specific menu recommendations found in the available reviews.
                  </Text>
                </View>
              )}

            {!isLoadingRecommendations &&
              !recommendationsError &&
              recommendationsData &&
              recommendationsData.status === 'available' &&
              recommendationsData.items.length > 0 && (
                <View style={styles.aiRecommendationsCard}>
                  <View style={styles.aiRecommendationsHeader}>
                    <Text style={styles.aiRecommendationsBadge}>☕ Must Try</Text>
                    {recommendationsData.review_count_analyzed > 0 ? (
                      <Text style={styles.aiRecommendationsCountText}>
                        Based on {recommendationsData.review_count_analyzed} reviews
                      </Text>
                    ) : null}
                  </View>

                  <View style={styles.recommendationList}>
                    {recommendationsData.items.map((item, idx) => (
                      <View key={`rec-${idx}`} style={styles.recommendationItemCard}>
                        <Text style={styles.recommendationItemName}>{item.item_name}</Text>
                        <Text style={styles.recommendationItemReason}>{item.reason}</Text>
                      </View>
                    ))}
                  </View>
                </View>
              )}
          </View>
        )}

        {/* User Review Management Section */}
        {authToken && !isLoadingReviews && !reviewsError && (
          <View style={styles.userReviewSection}>
            {!isFormOpen && myReview && (
              <View style={styles.myReviewCard}>
                <View style={styles.myReviewHeader}>
                  <View>
                    <Text style={styles.myReviewLabel}>Your Review</Text>
                    <View style={styles.reviewRatingRow}>
                      <Text style={styles.stars}>
                        {'★'.repeat(myReview.rating)}
                        {'☆'.repeat(Math.max(0, 5 - myReview.rating))}
                      </Text>
                      {myReview.is_edited ? (
                        <Text style={styles.editedIndicator}>• Edited</Text>
                      ) : null}
                    </View>
                  </View>
                  <View style={styles.myReviewActions}>
                    <TouchableOpacity
                      onPress={() => handleOpenForm(myReview)}
                      style={styles.actionLinkButton}
                      accessibilityRole="button"
                      accessibilityLabel="Edit your review"
                    >
                      <Text style={styles.actionLinkText}>Edit</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      onPress={handleDeleteReview}
                      style={styles.actionLinkButton}
                      disabled={isDeleting}
                      accessibilityRole="button"
                      accessibilityLabel="Delete your review"
                    >
                      <Text style={styles.actionDeleteText}>
                        {isDeleting ? 'Deleting...' : 'Delete'}
                      </Text>
                    </TouchableOpacity>
                  </View>
                </View>
                {myReview.text ? (
                  <Text style={styles.myReviewBody}>{myReview.text}</Text>
                ) : null}
                {deleteError ? (
                  <Text style={styles.deleteErrorText}>{deleteError}</Text>
                ) : null}
              </View>
            )}

            {!isFormOpen && !myReview && (
              <TouchableOpacity
                style={styles.writeReviewButton}
                onPress={() => handleOpenForm(null)}
                activeOpacity={0.8}
                accessibilityRole="button"
                accessibilityLabel="Write a review"
              >
                <Text style={styles.writeReviewButtonText}>✍️ Write a Review</Text>
              </TouchableOpacity>
            )}

            {isFormOpen && (
              <View style={styles.reviewFormContainer}>
                <Text style={styles.formTitle}>
                  {myReview ? 'Edit Your Review' : 'Write a Review'}
                </Text>

                {/* Interactive Star Picker */}
                <View style={styles.starPickerRow}>
                  {[1, 2, 3, 4, 5].map((star) => (
                    <TouchableOpacity
                      key={star}
                      onPress={() => setFormRating(star)}
                      activeOpacity={0.7}
                      style={styles.starTouchTarget}
                      accessibilityRole="button"
                      accessibilityLabel={`Rate ${star} star${star > 1 ? 's' : ''}`}
                    >
                      <Text style={styles.starPickerText}>
                        {star <= formRating ? '★' : '☆'}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>

                <TextInput
                  style={styles.reviewTextInput}
                  placeholder="Share what you loved about this café (optional)"
                  placeholderTextColor="#A4988F"
                  value={formContent}
                  onChangeText={setFormContent}
                  maxLength={1000}
                  multiline={true}
                  numberOfLines={4}
                  textAlignVertical="top"
                />

                <View style={styles.formFooterRow}>
                  <Text style={styles.charCountText}>
                    {formContent.length} / 1000
                  </Text>
                  {formError ? (
                    <Text style={styles.formErrorText}>{formError}</Text>
                  ) : null}
                </View>

                <View style={styles.formButtonRow}>
                  <TouchableOpacity
                    style={styles.formCancelButton}
                    onPress={handleCancelForm}
                    disabled={isSubmitting || isDeleting}
                    accessibilityRole="button"
                    accessibilityLabel="Cancel review editing"
                  >
                    <Text style={styles.formCancelButtonText}>Cancel</Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    style={styles.formSubmitButton}
                    onPress={handleSubmitReview}
                    disabled={isSubmitting || isDeleting}
                    accessibilityRole="button"
                    accessibilityLabel="Submit review"
                  >
                    {isSubmitting ? (
                      <ActivityIndicator size="small" color="#FAF8F5" />
                    ) : (
                      <Text style={styles.formSubmitButtonText}>
                        {myReview ? 'Save Changes' : 'Post Review'}
                      </Text>
                    )}
                  </TouchableOpacity>
                </View>
              </View>
            )}
          </View>
        )}

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
                      <View style={styles.authorNameBadgeRow}>
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

                        {review.source === 'lokal' ? (
                          <View style={styles.lokalBadge}>
                            <Text style={styles.lokalBadgeText}>LOKAL</Text>
                          </View>
                        ) : null}
                      </View>

                      <View style={styles.reviewRatingRow}>
                        <Text style={styles.stars}>
                          {'★'.repeat(review.rating)}
                          {'☆'.repeat(Math.max(0, 5 - review.rating))}
                        </Text>
                        {review.is_edited ? (
                          <Text style={styles.editedIndicator}>• Edited</Text>
                        ) : null}
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
            </View>
          )}

        {!isLoadingReviews && !reviewsError && googleAttribution && (
          <Text style={styles.attributionNotice}>
            {googleAttribution.required_notice || 'Reviews provided by Google Maps'}
          </Text>
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
    maxHeight: 520,
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
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  favoriteButton: {
    padding: 4,
    borderRadius: 12,
    backgroundColor: '#F3EFEA',
    width: 28,
    height: 28,
    alignItems: 'center',
    justifyContent: 'center',
  },
  favoriteButtonActive: {
    backgroundColor: '#FDF2F2',
  },
  favoriteIcon: {
    fontSize: 16,
    color: '#8C7D73',
    lineHeight: 18,
  },
  favoriteIconActive: {
    color: '#D9534F',
  },
  favoriteErrorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 6,
    paddingHorizontal: 10,
    backgroundColor: '#FDF2F2',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#F8D7DA',
    marginBottom: 8,
    gap: 8,
  },
  favoriteErrorText: {
    flex: 1,
    fontSize: 12,
    color: '#9C3434',
  },
  favoriteErrorDismiss: {
    padding: 2,
  },
  favoriteErrorDismissText: {
    fontSize: 12,
    color: '#9C3434',
    fontWeight: '600',
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
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  lokalRatingBadge: {
    backgroundColor: '#FAF2EB',
    paddingVertical: 4,
    paddingHorizontal: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#D4A373',
  },
  lokalRatingText: {
    fontSize: 13,
    fontWeight: '700',
    color: '#4A2E18',
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
  userReviewSection: {
    marginBottom: 14,
  },
  writeReviewButton: {
    backgroundColor: '#F3EFEA',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#E8E1D9',
  },
  writeReviewButtonText: {
    fontSize: 13,
    fontWeight: '600',
    color: '#4A2E18',
  },
  myReviewCard: {
    backgroundColor: '#FAF2EB',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#D4A373',
  },
  myReviewHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  myReviewLabel: {
    fontSize: 13,
    fontWeight: '700',
    color: '#4A2E18',
  },
  myReviewActions: {
    flexDirection: 'row',
    gap: 12,
  },
  actionLinkButton: {
    padding: 2,
  },
  actionLinkText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#1967D2',
  },
  actionDeleteText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#8A3B28',
  },
  myReviewBody: {
    fontSize: 13,
    color: '#4A2E18',
    marginTop: 6,
    lineHeight: 18,
  },
  deleteErrorText: {
    fontSize: 12,
    color: '#8A3B28',
    marginTop: 6,
  },
  reviewFormContainer: {
    backgroundColor: '#FAF8F5',
    borderRadius: 10,
    padding: 12,
    borderWidth: 1,
    borderColor: '#D4A373',
  },
  formTitle: {
    fontSize: 14,
    fontWeight: '700',
    color: '#4A2E18',
    marginBottom: 8,
  },
  starPickerRow: {
    flexDirection: 'row',
    gap: 6,
    marginBottom: 10,
  },
  starTouchTarget: {
    padding: 4,
  },
  starPickerText: {
    fontSize: 26,
    color: '#A06D00',
  },
  reviewTextInput: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#EFEAE4',
    borderRadius: 8,
    padding: 10,
    fontSize: 13,
    color: '#4A2E18',
    minHeight: 80,
  },
  formFooterRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginTop: 4,
    marginBottom: 10,
  },
  charCountText: {
    fontSize: 11,
    color: '#8C7D73',
  },
  formErrorText: {
    fontSize: 11,
    color: '#8A3B28',
    flex: 1,
    textAlign: 'right',
  },
  formButtonRow: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 8,
  },
  formCancelButton: {
    paddingVertical: 8,
    paddingHorizontal: 14,
    borderRadius: 6,
    backgroundColor: '#F3EFEA',
  },
  formCancelButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#6B5E55',
  },
  formSubmitButton: {
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 6,
    backgroundColor: '#4A2E18',
    minWidth: 90,
    alignItems: 'center',
  },
  formSubmitButtonText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#FAF8F5',
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
  authorNameBadgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
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
  lokalBadge: {
    backgroundColor: '#FAF2EB',
    borderRadius: 4,
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderWidth: 1,
    borderColor: '#D4A373',
  },
  lokalBadgeText: {
    fontSize: 10,
    fontWeight: '700',
    color: '#4A2E18',
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
  editedIndicator: {
    fontSize: 11,
    color: '#8C7D73',
    fontStyle: 'italic',
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
    marginTop: 6,
    fontStyle: 'italic',
  },
  aiSummaryContainer: {
    marginBottom: 12,
  },
  aiSummaryLoading: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
    backgroundColor: '#FAF8F5',
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#EFEAE4',
    gap: 8,
  },
  aiSummaryLoadingText: {
    fontSize: 12,
    color: '#6B5E55',
    fontStyle: 'italic',
  },
  aiSummaryErrorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 10,
    backgroundColor: '#FDF2F2',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#F8D7DA',
    gap: 8,
  },
  aiSummaryErrorText: {
    flex: 1,
    fontSize: 12,
    color: '#9C3434',
  },
  aiSummaryRetryButton: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    backgroundColor: '#9C3434',
    borderRadius: 6,
  },
  aiSummaryRetryText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  aiSummaryInsufficient: {
    padding: 10,
    backgroundColor: '#FAF8F5',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#EFEAE4',
  },
  aiSummaryInsufficientText: {
    fontSize: 12,
    color: '#8C7D73',
    fontStyle: 'italic',
    textAlign: 'center',
  },
  aiSummaryCard: {
    backgroundColor: '#FAF8F5',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: '#EFEAE4',
  },
  aiSummaryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  aiSummaryBadge: {
    fontSize: 12,
    fontWeight: '700',
    color: '#4A2E18',
    backgroundColor: '#FAF2EB',
    paddingVertical: 2,
    paddingHorizontal: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#D4A373',
  },
  aiSummaryCountText: {
    fontSize: 11,
    color: '#8C7D73',
  },
  aiSummaryText: {
    fontSize: 13,
    color: '#3A2B20',
    lineHeight: 18,
    marginBottom: 8,
  },
  themeGroup: {
    marginTop: 6,
  },
  themeGroupLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: '#6B5E55',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 4,
  },
  themePillContainer: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  positivePill: {
    backgroundColor: '#EDF7ED',
    borderWidth: 1,
    borderColor: '#C8E6C9',
    borderRadius: 6,
    paddingVertical: 3,
    paddingHorizontal: 8,
  },
  positivePillText: {
    fontSize: 11,
    color: '#2E7D32',
    fontWeight: '600',
  },
  negativePill: {
    backgroundColor: '#FFF8E1',
    borderWidth: 1,
    borderColor: '#FFE082',
    borderRadius: 6,
    paddingVertical: 3,
    paddingHorizontal: 8,
  },
  negativePillText: {
    fontSize: 11,
    color: '#8D6E63',
    fontWeight: '600',
  },
  aiRecommendationsContainer: {
    marginTop: 10,
    marginBottom: 6,
  },
  aiRecommendationsLoading: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 10,
    backgroundColor: '#FAF8F5',
    borderRadius: 8,
    gap: 8,
  },
  aiRecommendationsLoadingText: {
    fontSize: 12,
    color: '#6B5E55',
  },
  aiRecommendationsErrorContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 10,
    backgroundColor: '#FDF2F2',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#F8D7DA',
    gap: 8,
  },
  aiRecommendationsErrorText: {
    flex: 1,
    fontSize: 12,
    color: '#9C3434',
  },
  aiRecommendationsRetryButton: {
    paddingVertical: 4,
    paddingHorizontal: 8,
    backgroundColor: '#9C3434',
    borderRadius: 6,
  },
  aiRecommendationsRetryText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  aiRecommendationsInsufficient: {
    padding: 10,
    backgroundColor: '#FAF8F5',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#EFEAE4',
  },
  aiRecommendationsInsufficientText: {
    fontSize: 12,
    color: '#8C7D73',
    fontStyle: 'italic',
    textAlign: 'center',
  },
  aiRecommendationsEmpty: {
    padding: 10,
    backgroundColor: '#FAF8F5',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#EFEAE4',
  },
  aiRecommendationsEmptyText: {
    fontSize: 12,
    color: '#8C7D73',
    fontStyle: 'italic',
    textAlign: 'center',
  },
  aiRecommendationsCard: {
    backgroundColor: '#FAF8F5',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: '#EFEAE4',
  },
  aiRecommendationsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  aiRecommendationsBadge: {
    fontSize: 12,
    fontWeight: '700',
    color: '#4A2E18',
    backgroundColor: '#FAF2EB',
    paddingVertical: 2,
    paddingHorizontal: 8,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: '#D4A373',
  },
  aiRecommendationsCountText: {
    fontSize: 11,
    color: '#8C7D73',
  },
  recommendationList: {
    gap: 8,
  },
  recommendationItemCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: '#EFEAE4',
  },
  recommendationItemName: {
    fontSize: 13,
    fontWeight: '700',
    color: '#4A2E18',
    marginBottom: 2,
  },
  recommendationItemReason: {
    fontSize: 12,
    color: '#55433C',
    lineHeight: 16,
  },
});

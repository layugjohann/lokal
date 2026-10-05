import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  StyleSheet,
  View,
  Text,
  TextInput,
  TouchableOpacity,
  ActivityIndicator,
  Modal,
  SafeAreaView,
  ScrollView,
  Alert,
} from 'react-native';
import { Shop } from '../types/shop';
import { OwnerDashboardData } from '../types/claim';
import { fetchOwnerDashboard, updateOwnerShop } from '../services/claimService';
import { formatRating } from '../services/shopService';

export interface OwnerDashboardModalProps {
  visible: boolean;
  shopId: string;
  authToken: string | null;
  onClose: () => void;
  onShopUpdated?: (updatedShop: Shop) => void;
}

export default function OwnerDashboardModal({
  visible,
  shopId,
  authToken,
  onClose,
  onShopUpdated,
}: OwnerDashboardModalProps) {
  const [data, setData] = useState<OwnerDashboardData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Edit Listing state
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editName, setEditName] = useState<string>('');
  const [editAddress, setEditAddress] = useState<string>('');
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [editError, setEditError] = useState<string | null>(null);

  const currentRequestId = useRef<number>(0);

  const loadDashboard = useCallback(async () => {
    if (!authToken || !shopId) {
      setData(null);
      setIsLoading(false);
      return;
    }

    const requestId = ++currentRequestId.current;
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const dashboardData = await fetchOwnerDashboard(shopId, authToken);
      if (requestId === currentRequestId.current) {
        setData(dashboardData);
        setEditName(dashboardData.shop.name);
        setEditAddress(dashboardData.shop.address || '');
        setIsLoading(false);
      }
    } catch (err: unknown) {
      if (requestId === currentRequestId.current) {
        const message = err instanceof Error ? err.message : 'Failed to load dashboard.';
        setErrorMessage(message);
        setIsLoading(false);
      }
    }
  }, [shopId, authToken]);

  useEffect(() => {
    if (visible) {
      loadDashboard();
      setIsEditing(false);
      setEditError(null);
    } else {
      setData(null);
      setIsEditing(false);
    }
  }, [visible, loadDashboard]);

  const handleStartEdit = () => {
    if (data) {
      setEditName(data.shop.name);
      setEditAddress(data.shop.address || '');
      setEditError(null);
      setIsEditing(true);
    }
  };

  const handleCancelEdit = () => {
    if (data) {
      setEditName(data.shop.name);
      setEditAddress(data.shop.address || '');
    }
    setEditError(null);
    setIsEditing(false);
  };

  const handleSaveListing = async () => {
    if (!authToken || !data) return;

    const trimmedName = editName.trim();
    const trimmedAddress = editAddress.trim();

    if (!trimmedName) {
      setEditError('Coffee shop name cannot be empty.');
      return;
    }

    setIsSaving(true);
    setEditError(null);

    try {
      const updatedShop = await updateOwnerShop(
        shopId,
        {
          name: trimmedName,
          address: trimmedAddress || undefined,
        },
        authToken
      );

      setData((prev) =>
        prev
          ? {
              ...prev,
              shop: {
                ...prev.shop,
                name: updatedShop.name,
                address: updatedShop.address,
              },
            }
          : null
      );
      setIsEditing(false);
      if (onShopUpdated) {
        onShopUpdated(updatedShop);
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to save changes.';
      setEditError(message);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={false}
      onRequestClose={onClose}
    >
      <SafeAreaView style={styles.safeArea}>
        <View style={styles.header}>
          <TouchableOpacity
            onPress={onClose}
            accessibilityRole="button"
            accessibilityLabel="Close owner dashboard"
            hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
          >
            <Text style={styles.closeText}>Close</Text>
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Owner Dashboard</Text>
          <View style={styles.headerPlaceholder} />
        </View>

        {isLoading ? (
          <View style={styles.centerContainer}>
            <ActivityIndicator size="large" color="#4A2E18" />
            <Text style={styles.loadingText}>Loading owner dashboard...</Text>
          </View>
        ) : errorMessage ? (
          <View style={styles.errorContainer}>
            <Text style={styles.errorTitle}>Dashboard Unavailable</Text>
            <Text style={styles.errorDescription}>{errorMessage}</Text>
            <TouchableOpacity
              style={styles.retryButton}
              onPress={loadDashboard}
              accessibilityRole="button"
              accessibilityLabel="Retry loading dashboard"
              activeOpacity={0.8}
            >
              <Text style={styles.retryButtonText}>Retry</Text>
            </TouchableOpacity>
          </View>
        ) : data ? (
          <ScrollView contentContainerStyle={styles.scrollContent}>
            {/* Shop Overview Header */}
            <View style={styles.shopOverviewCard}>
              <View style={styles.badgeRow}>
                <View style={styles.ownerBadge}>
                  <Text style={styles.ownerBadgeText}>👑 Verified Owner</Text>
                </View>
                <Text style={styles.claimantRoleText}>
                  Managed by {data.claim.claimant_name} ({data.claim.claimant_role})
                </Text>
              </View>

              <Text style={styles.shopTitle}>{data.shop.name}</Text>
              {data.shop.address ? (
                <Text style={styles.shopAddressText}>{data.shop.address}</Text>
              ) : null}

              {/* Metrics Grid */}
              <View style={styles.metricsRow}>
                <View style={styles.metricCard}>
                  <Text style={styles.metricLabel}>LOKAL Community</Text>
                  <Text style={styles.metricValue}>
                    {data.lokal_rating !== null && data.lokal_rating !== undefined
                      ? `☕ ${data.lokal_rating.toFixed(1)} ★`
                      : 'No reviews'}
                  </Text>
                  <Text style={styles.metricSub}>
                    {data.lokal_reviews_count} {data.lokal_reviews_count === 1 ? 'review' : 'reviews'}
                  </Text>
                </View>

                <View style={styles.metricCard}>
                  <Text style={styles.metricLabel}>Google Places</Text>
                  <Text style={styles.metricValue}>
                    {data.rating !== null && data.rating !== undefined
                      ? `★ ${formatRating(data.rating)}`
                      : 'N/A'}
                  </Text>
                  <Text style={styles.metricSub}>External rating</Text>
                </View>
              </View>
            </View>

            {/* Listing Management Section */}
            <View style={styles.sectionCard}>
              <View style={styles.sectionHeaderRow}>
                <Text style={styles.sectionTitle}>Listing Information</Text>
                {!isEditing ? (
                  <TouchableOpacity
                    onPress={handleStartEdit}
                    accessibilityRole="button"
                    accessibilityLabel="Edit listing details"
                    activeOpacity={0.7}
                  >
                    <Text style={styles.editActionText}>✏️ Edit</Text>
                  </TouchableOpacity>
                ) : null}
              </View>

              {isEditing ? (
                <View style={styles.editForm}>
                  {editError ? (
                    <View style={styles.formErrorBanner}>
                      <Text style={styles.formErrorText}>{editError}</Text>
                    </View>
                  ) : null}

                  <View style={styles.inputGroup}>
                    <Text style={styles.inputLabel}>Shop Name *</Text>
                    <TextInput
                      style={styles.textInput}
                      value={editName}
                      onChangeText={setEditName}
                      editable={!isSaving}
                      placeholder="Coffee shop name"
                      placeholderTextColor="#A89F91"
                    />
                  </View>

                  <View style={styles.inputGroup}>
                    <Text style={styles.inputLabel}>Street Address</Text>
                    <TextInput
                      style={styles.textInput}
                      value={editAddress}
                      onChangeText={setEditAddress}
                      editable={!isSaving}
                      placeholder="Shop address"
                      placeholderTextColor="#A89F91"
                    />
                  </View>

                  <View style={styles.formButtonGroup}>
                    <TouchableOpacity
                      style={styles.cancelFormButton}
                      onPress={handleCancelEdit}
                      disabled={isSaving}
                      accessibilityRole="button"
                      accessibilityLabel="Cancel edit"
                    >
                      <Text style={styles.cancelFormButtonText}>Cancel</Text>
                    </TouchableOpacity>

                    <TouchableOpacity
                      style={[styles.saveFormButton, isSaving && styles.buttonDisabled]}
                      onPress={handleSaveListing}
                      disabled={isSaving}
                      accessibilityRole="button"
                      accessibilityLabel="Save listing changes"
                    >
                      {isSaving ? (
                        <ActivityIndicator size="small" color="#FFFFFF" />
                      ) : (
                        <Text style={styles.saveFormButtonText}>Save Changes</Text>
                      )}
                    </TouchableOpacity>
                  </View>
                </View>
              ) : (
                <View style={styles.readOnlyInfo}>
                  <View style={styles.infoRow}>
                    <Text style={styles.infoLabel}>Business Name:</Text>
                    <Text style={styles.infoValue}>{data.shop.name}</Text>
                  </View>
                  <View style={styles.infoRow}>
                    <Text style={styles.infoLabel}>Address:</Text>
                    <Text style={styles.infoValue}>{data.shop.address || 'Not specified'}</Text>
                  </View>
                  <Text style={styles.protectedNotice}>
                    ℹ️ Coordinates, curation status, and external provider IDs are managed by LOKAL curators.
                  </Text>
                </View>
              )}
            </View>

            {/* Recent Community Feedback Section */}
            <View style={styles.sectionCard}>
              <Text style={styles.sectionTitle}>Recent Community Reviews</Text>
              {data.recent_reviews.length === 0 ? (
                <Text style={styles.emptyReviewsText}>
                  No community reviews submitted yet for this coffee shop.
                </Text>
              ) : (
                data.recent_reviews.map((rev) => (
                  <View key={rev.id} style={styles.reviewItem}>
                    <View style={styles.reviewHeader}>
                      <Text style={styles.reviewAuthor}>{rev.author.display_name}</Text>
                      <Text style={styles.reviewRating}>☕ {rev.rating} ★</Text>
                    </View>
                    {rev.text ? (
                      <Text style={styles.reviewText}>{rev.text}</Text>
                    ) : null}
                  </View>
                ))
              )}
            </View>
          </ScrollView>
        ) : null}
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#FAF8F5',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 14,
    borderBottomWidth: 1,
    borderBottomColor: '#E8E2D9',
    backgroundColor: '#FAF8F5',
  },
  closeText: {
    fontSize: 15,
    color: '#8B4513',
    fontWeight: '600',
  },
  headerTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#2C1810',
  },
  headerPlaceholder: {
    width: 48,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 15,
    color: '#6B5E55',
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  errorTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#2C1810',
    marginBottom: 8,
  },
  errorDescription: {
    fontSize: 14,
    color: '#6B5E55',
    textAlign: 'center',
    marginBottom: 20,
    lineHeight: 20,
  },
  retryButton: {
    backgroundColor: '#4A2E18',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '600',
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  shopOverviewCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: '#E8E2D9',
    marginBottom: 16,
  },
  badgeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 10,
  },
  ownerBadge: {
    backgroundColor: '#FAF0E6',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderWidth: 1,
    borderColor: '#D4A373',
  },
  ownerBadgeText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#8B4513',
  },
  claimantRoleText: {
    fontSize: 12,
    color: '#6B5E55',
  },
  shopTitle: {
    fontSize: 22,
    fontWeight: '700',
    color: '#2C1810',
    marginBottom: 4,
  },
  shopAddressText: {
    fontSize: 14,
    color: '#6B5E55',
    marginBottom: 16,
  },
  metricsRow: {
    flexDirection: 'row',
    gap: 12,
  },
  metricCard: {
    flex: 1,
    backgroundColor: '#FAF8F5',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: '#E8E2D9',
  },
  metricLabel: {
    fontSize: 12,
    fontWeight: '600',
    color: '#8A7E72',
    marginBottom: 4,
  },
  metricValue: {
    fontSize: 16,
    fontWeight: '700',
    color: '#2C1810',
    marginBottom: 2,
  },
  metricSub: {
    fontSize: 11,
    color: '#6B5E55',
  },
  sectionCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 18,
    borderWidth: 1,
    borderColor: '#E8E2D9',
    marginBottom: 16,
  },
  sectionHeaderRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 14,
  },
  sectionTitle: {
    fontSize: 17,
    fontWeight: '700',
    color: '#2C1810',
  },
  editActionText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#8B4513',
  },
  readOnlyInfo: {
    gap: 10,
  },
  infoRow: {
    flexDirection: 'row',
    gap: 8,
  },
  infoLabel: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6B5E55',
    width: 110,
  },
  infoValue: {
    flex: 1,
    fontSize: 14,
    color: '#2C1810',
  },
  protectedNotice: {
    marginTop: 8,
    fontSize: 12,
    color: '#8A7E72',
    fontStyle: 'italic',
    lineHeight: 16,
  },
  editForm: {
    gap: 14,
  },
  formErrorBanner: {
    backgroundColor: '#FDECEA',
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: '#F5C6CB',
  },
  formErrorText: {
    fontSize: 13,
    color: '#721C24',
  },
  inputGroup: {
    gap: 6,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#4A2E18',
  },
  textInput: {
    backgroundColor: '#FAF8F5',
    borderWidth: 1,
    borderColor: '#D4C8BE',
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: '#2C1810',
  },
  formButtonGroup: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 6,
  },
  cancelFormButton: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#D4C8BE',
    alignItems: 'center',
  },
  cancelFormButtonText: {
    fontSize: 14,
    fontWeight: '600',
    color: '#6B5E55',
  },
  saveFormButton: {
    flex: 1,
    backgroundColor: '#4A2E18',
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  saveFormButtonText: {
    fontSize: 14,
    fontWeight: '700',
    color: '#FFFFFF',
  },
  buttonDisabled: {
    opacity: 0.6,
  },
  emptyReviewsText: {
    fontSize: 14,
    color: '#8A7E72',
    fontStyle: 'italic',
    paddingVertical: 8,
  },
  reviewItem: {
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#F0EBE5',
  },
  reviewHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  reviewAuthor: {
    fontSize: 14,
    fontWeight: '600',
    color: '#2C1810',
  },
  reviewRating: {
    fontSize: 13,
    fontWeight: '700',
    color: '#8B4513',
  },
  reviewText: {
    fontSize: 14,
    color: '#4A2E18',
    lineHeight: 19,
  },
});

import React, { useState } from 'react';
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
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { Shop } from '../types/shop';
import { ShopClaim } from '../types/claim';
import { submitShopClaim } from '../services/claimService';

export interface ClaimShopModalProps {
  visible: boolean;
  shop: Shop;
  authToken: string | null;
  onClose: () => void;
  onClaimSuccess: (claim: ShopClaim) => void;
}

export default function ClaimShopModal({
  visible,
  shop,
  authToken,
  onClose,
  onClaimSuccess,
}: ClaimShopModalProps) {
  const [claimantName, setClaimantName] = useState('');
  const [claimantRole, setClaimantRole] = useState('');
  const [claimantPhone, setClaimantPhone] = useState('');
  const [businessProof, setBusinessProof] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const resetForm = () => {
    setClaimantName('');
    setClaimantRole('');
    setClaimantPhone('');
    setBusinessProof('');
    setErrorMessage(null);
  };

  const handleClose = () => {
    if (!isSubmitting) {
      resetForm();
      onClose();
    }
  };

  const handleSubmit = async () => {
    if (!authToken) {
      setErrorMessage('You must be signed in to claim this coffee shop.');
      return;
    }

    const trimmedName = claimantName.trim();
    const trimmedRole = claimantRole.trim();

    if (!trimmedName) {
      setErrorMessage('Please enter your full name.');
      return;
    }

    if (!trimmedRole) {
      setErrorMessage('Please specify your role at this coffee shop (e.g. Owner, Store Manager).');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      const claim = await submitShopClaim(
        shop.id,
        {
          claimant_name: trimmedName,
          claimant_role: trimmedRole,
          claimant_phone: claimantPhone.trim() || undefined,
          business_proof: businessProof.trim() || undefined,
        },
        authToken
      );
      resetForm();
      onClaimSuccess(claim);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to submit ownership claim.';
      setErrorMessage(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent={false}
      onRequestClose={handleClose}
    >
      <SafeAreaView style={styles.safeArea}>
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : undefined}
          style={styles.keyboardContainer}
        >
          <View style={styles.header}>
            <TouchableOpacity
              onPress={handleClose}
              disabled={isSubmitting}
              accessibilityRole="button"
              accessibilityLabel="Cancel claim"
              hitSlop={{ top: 12, bottom: 12, left: 12, right: 12 }}
            >
              <Text style={styles.cancelText}>Cancel</Text>
            </TouchableOpacity>
            <Text style={styles.headerTitle}>Claim Coffee Shop</Text>
            <View style={styles.headerPlaceholder} />
          </View>

          <ScrollView
            contentContainerStyle={styles.scrollContent}
            keyboardShouldPersistTaps="handled"
          >
            <View style={styles.shopCard}>
              <Text style={styles.shopName}>{shop.name}</Text>
              {shop.address ? (
                <Text style={styles.shopAddress}>{shop.address}</Text>
              ) : null}
            </View>

            <Text style={styles.sectionDescription}>
              Are you the owner or an authorized representative of this café? Submit your details
              below. Our team will review your submission to verify ownership.
            </Text>

            {errorMessage ? (
              <View style={styles.errorBanner}>
                <Text style={styles.errorText}>{errorMessage}</Text>
              </View>
            ) : null}

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Your Full Name *</Text>
              <TextInput
                style={styles.textInput}
                placeholder="e.g. Juan Dela Cruz"
                placeholderTextColor="#A89F91"
                value={claimantName}
                onChangeText={setClaimantName}
                editable={!isSubmitting}
                autoCapitalize="words"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Your Role / Title *</Text>
              <TextInput
                style={styles.textInput}
                placeholder="e.g. Owner, Co-Owner, General Manager"
                placeholderTextColor="#A89F91"
                value={claimantRole}
                onChangeText={setClaimantRole}
                editable={!isSubmitting}
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Contact Phone (Optional)</Text>
              <TextInput
                style={styles.textInput}
                placeholder="e.g. +63 917 123 4567"
                placeholderTextColor="#A89F91"
                value={claimantPhone}
                onChangeText={setClaimantPhone}
                keyboardType="phone-pad"
                editable={!isSubmitting}
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Verification Details / Proof (Optional)</Text>
              <TextInput
                style={[styles.textInput, styles.multilineInput]}
                placeholder="Add any information that helps verify your affiliation (e.g. DTI permit, official Instagram or Facebook handle, store email)."
                placeholderTextColor="#A89F91"
                value={businessProof}
                onChangeText={setBusinessProof}
                multiline
                numberOfLines={4}
                textAlignVertical="top"
                editable={!isSubmitting}
              />
            </View>

            <TouchableOpacity
              style={[styles.submitButton, isSubmitting && styles.submitButtonDisabled]}
              onPress={handleSubmit}
              disabled={isSubmitting}
              accessibilityRole="button"
              accessibilityLabel="Submit claim for review"
              activeOpacity={0.8}
            >
              {isSubmitting ? (
                <ActivityIndicator size="small" color="#FFFFFF" />
              ) : (
                <Text style={styles.submitButtonText}>Submit Claim for Review</Text>
              )}
            </TouchableOpacity>
          </ScrollView>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: '#FAF8F5',
  },
  keyboardContainer: {
    flex: 1,
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
  cancelText: {
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
  scrollContent: {
    padding: 20,
    paddingBottom: 40,
  },
  shopCard: {
    backgroundColor: '#FFFFFF',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#E8E2D9',
    marginBottom: 16,
  },
  shopName: {
    fontSize: 18,
    fontWeight: '700',
    color: '#2C1810',
    marginBottom: 4,
  },
  shopAddress: {
    fontSize: 14,
    color: '#6B5E55',
  },
  sectionDescription: {
    fontSize: 14,
    color: '#6B5E55',
    lineHeight: 20,
    marginBottom: 20,
  },
  errorBanner: {
    backgroundColor: '#FDECEA',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#F5C6CB',
    marginBottom: 16,
  },
  errorText: {
    fontSize: 14,
    color: '#721C24',
    lineHeight: 18,
  },
  inputGroup: {
    marginBottom: 18,
  },
  inputLabel: {
    fontSize: 13,
    fontWeight: '600',
    color: '#4A2E18',
    marginBottom: 6,
  },
  textInput: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: '#D4C8BE',
    borderRadius: 10,
    paddingHorizontal: 14,
    paddingVertical: 12,
    fontSize: 15,
    color: '#2C1810',
  },
  multilineInput: {
    minHeight: 100,
    paddingTop: 12,
  },
  submitButton: {
    backgroundColor: '#4A2E18',
    borderRadius: 12,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 10,
    shadowColor: '#4A2E18',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.15,
    shadowRadius: 4,
    elevation: 2,
  },
  submitButtonDisabled: {
    opacity: 0.6,
  },
  submitButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '700',
  },
});

import React, { useEffect, useState } from 'react';
import {
  AccessibilityInfo,
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  TouchableOpacity,
  View,
} from 'react-native';
import { useAuth } from '../hooks/useAuth';
import { colors, spacing, radii, typography, shadows } from '../theme/tokens';
import LokalLogo from './LokalLogo';

type AuthMode = 'login' | 'register';

export default function AuthScreen() {
  const { login, register } = useAuth();

  const [mode, setMode] = useState<AuthMode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [infoMessage, setInfoMessage] = useState<string | null>(null);
  const [focusedField, setFocusedField] = useState<'email' | 'password' | null>(null);

  // Cross-platform screen-reader announcements
  // Explicitly dispatches AccessibilityInfo.announceForAccessibility across both platforms.
  // This guarantees that TalkBack on Android announces messages reliably even when
  // the banner mounts with initial text, without relying on conditionally mounted live regions.
  useEffect(() => {
    if (errorMessage) {
      AccessibilityInfo.announceForAccessibility(errorMessage);
    }
  }, [errorMessage]);

  useEffect(() => {
    if (infoMessage) {
      AccessibilityInfo.announceForAccessibility(infoMessage);
    }
  }, [infoMessage]);

  const resetFormState = (newMode: AuthMode) => {
    setMode(newMode);
    setErrorMessage(null);
    setInfoMessage(null);
  };

  const validate = (): string | null => {
    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      return 'Please enter your email address.';
    }
    const emailRegex = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
    if (!emailRegex.test(trimmedEmail)) {
      return 'Please enter a valid email address.';
    }
    if (!password) {
      return 'Please enter your password.';
    }
    if (password.length < 6) {
      return 'Password must be at least 6 characters.';
    }
    return null;
  };

  const handleSubmit = async () => {
    setErrorMessage(null);
    setInfoMessage(null);

    const validationError = validate();
    if (validationError) {
      setErrorMessage(validationError);
      return;
    }

    setIsSubmitting(true);
    try {
      if (mode === 'login') {
        await login({ email: email.trim(), password });
      } else {
        const result = await register({ email: email.trim(), password });
        if (result?.message) {
          setInfoMessage(result.message);
        }
      }
    } catch (err: any) {
      setErrorMessage(err?.message || 'Authentication failed. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <KeyboardAvoidingView
      style={styles.container}
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      <ScrollView
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
      >
        <View style={styles.contentContainer}>
          <View style={styles.header}>
            <View style={styles.titleRow}>
              <LokalLogo size={36} />
              <Text style={styles.appTitle}>LOKAL</Text>
            </View>
            <Text style={styles.appSubtitle}>
              Discover local coffee shops. Support independent cafés.
            </Text>
          </View>

          <View style={styles.tabContainer}>
            <TouchableOpacity
              style={[styles.tab, mode === 'login' && styles.activeTab]}
              onPress={() => resetFormState('login')}
              accessibilityRole="button"
              accessibilityLabel="Log In"
              accessibilityState={{ selected: mode === 'login' }}
              disabled={isSubmitting}
              activeOpacity={0.8}
            >
              <Text
                style={[styles.tabText, mode === 'login' && styles.activeTabText]}
              >
                Log In
              </Text>
            </TouchableOpacity>
            <TouchableOpacity
              style={[styles.tab, mode === 'register' && styles.activeTab]}
              onPress={() => resetFormState('register')}
              accessibilityRole="button"
              accessibilityLabel="Sign Up"
              accessibilityState={{ selected: mode === 'register' }}
              disabled={isSubmitting}
              activeOpacity={0.8}
            >
              <Text
                style={[
                  styles.tabText,
                  mode === 'register' && styles.activeTabText,
                ]}
              >
                Sign Up
              </Text>
            </TouchableOpacity>
          </View>

          <View style={styles.card}>
            {errorMessage && (
              <View
                style={styles.errorBanner}
                accessibilityRole="alert"
              >
                <Text style={styles.errorText}>{errorMessage}</Text>
              </View>
            )}

            {infoMessage && (
              <View
                style={styles.infoBanner}
                accessibilityRole="text"
              >
                <Text style={styles.infoText}>{infoMessage}</Text>
              </View>
            )}

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Email Address</Text>
              <TextInput
                style={[
                  styles.input,
                  focusedField === 'email' && styles.inputFocused,
                ]}
                placeholder="you@example.com"
                placeholderTextColor={colors.mutedGray}
                value={email}
                onChangeText={(text) => {
                  setEmail(text);
                  if (errorMessage) setErrorMessage(null);
                }}
                onFocus={() => setFocusedField('email')}
                onBlur={() =>
                  setFocusedField((prev) => (prev === 'email' ? null : prev))
                }
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="email-address"
                editable={!isSubmitting}
                accessibilityLabel="Email Address"
              />
            </View>

            <View style={styles.inputGroup}>
              <Text style={styles.inputLabel}>Password</Text>
              <TextInput
                style={[
                  styles.input,
                  focusedField === 'password' && styles.inputFocused,
                ]}
                placeholder="Minimum 6 characters"
                placeholderTextColor={colors.mutedGray}
                value={password}
                onChangeText={(text) => {
                  setPassword(text);
                  if (errorMessage) setErrorMessage(null);
                }}
                onFocus={() => setFocusedField('password')}
                onBlur={() =>
                  setFocusedField((prev) => (prev === 'password' ? null : prev))
                }
                secureTextEntry
                autoCapitalize="none"
                editable={!isSubmitting}
                accessibilityLabel="Password"
              />
            </View>

            <TouchableOpacity
              style={[
                styles.submitButton,
                isSubmitting && styles.submitButtonDisabled,
              ]}
              onPress={handleSubmit}
              disabled={isSubmitting}
              activeOpacity={0.8}
              accessibilityRole="button"
              accessibilityLabel={
                mode === 'login' ? 'Log in to LOKAL' : 'Create a LOKAL account'
              }
            >
              {isSubmitting ? (
                <ActivityIndicator size="small" color={colors.surfaceWhite} />
              ) : (
                <Text style={styles.submitButtonText}>
                  {mode === 'login' ? 'Log In' : 'Create Account'}
                </Text>
              )}
            </TouchableOpacity>
          </View>
        </View>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.softNeutral,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingHorizontal: spacing.xl,
    paddingVertical: spacing.xxxl,
  },
  contentContainer: {
    width: '100%',
    maxWidth: 420,
    alignSelf: 'center',
  },
  header: {
    alignItems: 'center',
    marginBottom: spacing.xxl,
  },
  titleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: 48,
    marginBottom: spacing.sm,
    gap: spacing.md,
  },
  appTitle: {
    fontSize: typography.title.fontSize,
    fontWeight: typography.title.fontWeight,
    color: colors.deepCaramel,
    letterSpacing: typography.title.letterSpacing,
  },
  appSubtitle: {
    fontSize: typography.subhead.fontSize,
    color: colors.mutedGray,
    textAlign: 'center',
    maxWidth: 290,
    lineHeight: typography.subhead.lineHeight,
  },
  tabContainer: {
    flexDirection: 'row',
    backgroundColor: colors.softNeutral,
    borderColor: colors.borderNeutral,
    borderWidth: 1,
    borderRadius: radii.pill,
    padding: spacing.xs,
    marginBottom: spacing.lg,
  },
  tab: {
    flex: 1,
    minHeight: 48,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: radii.control,
  },
  activeTab: {
    backgroundColor: colors.surfaceWhite,
    ...shadows.tabActive,
  },
  tabText: {
    fontSize: 14,
    fontWeight: '500',
    color: colors.mutedGray,
  },
  activeTabText: {
    fontWeight: '600',
    color: colors.charcoal,
  },
  card: {
    backgroundColor: colors.surfaceWhite,
    borderRadius: radii.card,
    borderColor: colors.borderNeutral,
    borderWidth: 1,
    padding: spacing.xl,
    ...shadows.card,
  },
  errorBanner: {
    backgroundColor: colors.errorBg,
    borderColor: colors.errorBorder,
    borderWidth: 1,
    borderRadius: radii.control,
    padding: spacing.md,
    marginBottom: spacing.base,
  },
  errorText: {
    color: colors.errorText,
    fontSize: typography.caption.fontSize,
    lineHeight: typography.caption.lineHeight,
    fontWeight: '500',
  },
  infoBanner: {
    backgroundColor: colors.successBg,
    borderColor: colors.successBorder,
    borderWidth: 1,
    borderRadius: radii.control,
    padding: spacing.md,
    marginBottom: spacing.base,
  },
  infoText: {
    color: colors.successText,
    fontSize: typography.caption.fontSize,
    lineHeight: typography.caption.lineHeight,
    fontWeight: '500',
  },
  inputGroup: {
    marginBottom: spacing.base,
  },
  inputLabel: {
    fontSize: typography.label.fontSize,
    fontWeight: typography.label.fontWeight,
    color: colors.charcoal,
    marginBottom: spacing.xs + 2,
  },
  input: {
    minHeight: 48,
    backgroundColor: colors.surfaceWhite,
    borderWidth: 1,
    borderColor: colors.borderInput,
    borderRadius: radii.control,
    paddingHorizontal: spacing.base - 2,
    paddingVertical: spacing.md,
    fontSize: typography.body.fontSize,
    color: colors.charcoal,
    justifyContent: 'center',
  },
  inputFocused: {
    borderColor: colors.borderFocus,
    borderWidth: 1.5,
  },
  submitButton: {
    minHeight: 48,
    backgroundColor: colors.deepCaramel,
    borderRadius: radii.button,
    paddingVertical: spacing.base - 2,
    alignItems: 'center',
    justifyContent: 'center',
    marginTop: spacing.sm,
  },
  submitButtonDisabled: {
    opacity: 0.65,
  },
  submitButtonText: {
    color: colors.surfaceWhite,
    fontSize: typography.button.fontSize,
    fontWeight: typography.button.fontWeight,
  },
});

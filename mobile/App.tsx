import React from 'react';
import { StatusBar } from 'expo-status-bar';
import {
  ActivityIndicator,
  StyleSheet,
  Text,
  TouchableOpacity,
  View,
} from 'react-native';
import { AuthProvider } from './src/context/AuthContext';
import { useAuth } from './src/hooks/useAuth';
import AuthScreen from './src/components/AuthScreen';
import LokalMapView from './src/components/LokalMapView';
import { colors, spacing, radii, typography, shadows } from './src/theme/tokens';

function MainAppContent(props?: { authToken?: string | null }) {
  const { status, restorationError, retryRestoration, token, logout } = useAuth();
  const effectiveToken = props?.authToken !== undefined ? props.authToken : token;

  if (status === 'restoring' && !props?.authToken) {
    return (
      <View style={styles.centerContainer}>
        {restorationError ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorTitle}>Connection Issue</Text>
            <Text style={styles.errorDescription}>{restorationError}</Text>
            <View style={styles.errorButtonGroup}>
              <TouchableOpacity
                style={styles.signOutButton}
                onPress={logout}
                accessibilityRole="button"
                accessibilityLabel="Sign out"
                activeOpacity={0.8}
              >
                <Text style={styles.signOutButtonText}>Sign Out</Text>
              </TouchableOpacity>
              <TouchableOpacity
                style={styles.retryButton}
                onPress={retryRestoration}
                accessibilityRole="button"
                accessibilityLabel="Retry connecting"
                activeOpacity={0.8}
              >
                <Text style={styles.retryButtonText}>Retry</Text>
              </TouchableOpacity>
            </View>
          </View>
        ) : (
          <View style={styles.restoringBox}>
            <ActivityIndicator size="large" color={colors.deepCaramel} />
            <Text style={styles.restoringText}>Loading LOKAL...</Text>
          </View>
        )}
      </View>
    );
  }

  if (status === 'unauthenticated' && !effectiveToken) {
    return <AuthScreen />;
  }

  return <LokalMapView authToken={effectiveToken} />;
}

export default function App(props?: { authToken?: string | null } & Record<string, unknown>) {
  return (
    <AuthProvider initialToken={props?.authToken}>
      <View style={styles.container}>
        <MainAppContent authToken={props?.authToken} />
        <StatusBar style="dark" />
      </View>
    </AuthProvider>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: colors.softNeutral,
  },
  centerContainer: {
    flex: 1,
    backgroundColor: colors.softNeutral,
    justifyContent: 'center',
    alignItems: 'center',
    padding: spacing.xl,
  },
  restoringBox: {
    alignItems: 'center',
    gap: spacing.base,
  },
  restoringText: {
    color: colors.charcoal,
    fontSize: typography.body.fontSize,
    fontWeight: '500',
  },
  errorBox: {
    backgroundColor: colors.surfaceWhite,
    borderRadius: radii.card,
    borderColor: colors.borderNeutral,
    borderWidth: 1,
    padding: spacing.xl,
    width: '100%',
    maxWidth: 360,
    alignItems: 'center',
    ...shadows.card,
  },
  errorTitle: {
    fontSize: typography.headline.fontSize,
    fontWeight: typography.headline.fontWeight,
    color: colors.charcoal,
    marginBottom: spacing.sm,
  },
  errorDescription: {
    fontSize: typography.caption.fontSize,
    color: colors.mutedGray,
    textAlign: 'center',
    marginBottom: spacing.lg,
    lineHeight: typography.body.lineHeight,
  },
  errorButtonGroup: {
    flexDirection: 'row',
    gap: spacing.md,
    justifyContent: 'center',
    alignItems: 'center',
  },
  signOutButton: {
    minHeight: 48,
    minWidth: 100,
    backgroundColor: 'transparent',
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.lg,
    borderRadius: radii.control,
    borderWidth: 1,
    borderColor: colors.borderInput,
    justifyContent: 'center',
    alignItems: 'center',
  },
  signOutButtonText: {
    color: colors.charcoal,
    fontSize: 14,
    fontWeight: '600',
  },
  retryButton: {
    minHeight: 48,
    minWidth: 100,
    backgroundColor: colors.deepCaramel,
    paddingVertical: spacing.md,
    paddingHorizontal: spacing.xl,
    borderRadius: radii.control,
    justifyContent: 'center',
    alignItems: 'center',
  },
  retryButtonText: {
    color: colors.surfaceWhite,
    fontSize: 14,
    fontWeight: '600',
  },
});

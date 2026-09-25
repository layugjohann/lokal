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

function MainAppContent(props?: { authToken?: string | null }) {
  const { status, restorationError, retryRestoration, token } = useAuth();
  const effectiveToken = props?.authToken !== undefined ? props.authToken : token;

  if (status === 'restoring' && !props?.authToken) {
    return (
      <View style={styles.centerContainer}>
        {restorationError ? (
          <View style={styles.errorBox}>
            <Text style={styles.errorTitle}>Connection Issue</Text>
            <Text style={styles.errorDescription}>{restorationError}</Text>
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
        ) : (
          <View style={styles.restoringBox}>
            <ActivityIndicator size="large" color="#4A2E18" />
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
    backgroundColor: '#FAF8F5',
  },
  centerContainer: {
    flex: 1,
    backgroundColor: '#FAF8F5',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  restoringBox: {
    alignItems: 'center',
    gap: 16,
  },
  restoringText: {
    color: '#4A2E18',
    fontSize: 16,
    fontWeight: '500',
  },
  errorBox: {
    backgroundColor: '#FFF',
    borderRadius: 16,
    padding: 24,
    width: '100%',
    maxWidth: 340,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 6,
    elevation: 3,
  },
  errorTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: '#4A2E18',
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
    paddingVertical: 10,
    paddingHorizontal: 24,
    borderRadius: 8,
  },
  retryButtonText: {
    color: '#FFF',
    fontSize: 14,
    fontWeight: '600',
  },
});

export interface StorageAdapter {
  getItemAsync(key: string): Promise<string | null>;
  setItemAsync(key: string, value: string): Promise<void>;
  deleteItemAsync(key: string): Promise<void>;
}

export const AUTH_TOKEN_KEY = 'lokal_access_token';

let customAdapter: StorageAdapter | null = null;
let nativeAdapter: StorageAdapter | null = null;

/**
 * Checks whether execution is occurring inside a headless Node.js test environment
 * rather than a native Expo / React Native device or simulator runtime.
 */
export function isHeadlessTestEnvironment(): boolean {
  return (
    typeof process !== 'undefined' &&
    Boolean(process.versions?.node) &&
    typeof navigator === 'undefined' &&
    typeof (globalThis as any).nativeCallSyncHook === 'undefined'
  );
}

/**
 * Overrides the storage adapter (primarily for automated unit tests).
 */
export function setStorageAdapter(adapter: StorageAdapter | null): void {
  customAdapter = adapter;
}

/**
 * Resets cached adapters (for test harness isolation).
 */
export function resetStorageAdapters(): void {
  customAdapter = null;
  nativeAdapter = null;
}

/**
 * Creates an in-memory storage adapter for testing and non-native environments.
 */
export function createMemoryStorageAdapter(): StorageAdapter {
  const memoryStore = new Map<string, string>();
  return {
    getItemAsync: async (key: string) => memoryStore.get(key) ?? null,
    setItemAsync: async (key: string, value: string) => {
      memoryStore.set(key, value);
    },
    deleteItemAsync: async (key: string) => {
      memoryStore.delete(key);
    },
  };
}

async function getAdapter(): Promise<StorageAdapter> {
  if (customAdapter) {
    return customAdapter;
  }
  if (nativeAdapter) {
    return nativeAdapter;
  }

  try {
    const SecureStore = await import('expo-secure-store');
    if (
      SecureStore &&
      typeof SecureStore.getItemAsync === 'function' &&
      typeof SecureStore.setItemAsync === 'function' &&
      typeof SecureStore.deleteItemAsync === 'function'
    ) {
      nativeAdapter = SecureStore;
      return nativeAdapter;
    }
    throw new Error('expo-secure-store module does not provide expected storage methods.');
  } catch (err: any) {
    if (isHeadlessTestEnvironment()) {
      // Allowed ONLY in headless test environments (node --test) where native bridge is unavailable
      nativeAdapter = createMemoryStorageAdapter();
      return nativeAdapter;
    }

    // In native/production environments, explicitly surface the failure.
    // NEVER silently downgrade credential persistence from SecureStore to in-memory storage.
    throw new Error(
      `Secure device storage is unavailable and cannot be downgraded to memory in production: ${
        err?.message || err
      }`
    );
  }
}

/**
 * Retrieves the stored access token from secure device storage.
 */
export async function getAuthToken(): Promise<string | null> {
  const adapter = await getAdapter();
  return adapter.getItemAsync(AUTH_TOKEN_KEY);
}

/**
 * Persists the access token to hardware-backed secure storage.
 */
export async function saveAuthToken(token: string): Promise<void> {
  if (!token || !token.trim()) {
    throw new Error('Cannot store empty authentication token.');
  }
  const adapter = await getAdapter();
  await adapter.setItemAsync(AUTH_TOKEN_KEY, token.trim());
}

/**
 * Removes the access token from secure storage.
 */
export async function deleteAuthToken(): Promise<void> {
  const adapter = await getAdapter();
  await adapter.deleteItemAsync(AUTH_TOKEN_KEY);
}

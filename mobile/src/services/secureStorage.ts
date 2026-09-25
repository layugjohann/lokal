export interface StorageAdapter {
  getItemAsync(key: string): Promise<string | null>;
  setItemAsync(key: string, value: string): Promise<void>;
  deleteItemAsync(key: string): Promise<void>;
}

export const AUTH_TOKEN_KEY = 'lokal_access_token';

let customAdapter: StorageAdapter | null = null;
let nativeAdapter: StorageAdapter | null = null;

/**
 * Overrides the storage adapter (primarily for automated unit tests).
 */
export function setStorageAdapter(adapter: StorageAdapter | null): void {
  customAdapter = adapter;
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
    nativeAdapter = SecureStore;
    return nativeAdapter;
  } catch {
    // Fallback for headless test runners (e.g. node --test) where native binary is unavailable
    nativeAdapter = createMemoryStorageAdapter();
    return nativeAdapter;
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

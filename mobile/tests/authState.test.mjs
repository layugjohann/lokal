import test from 'node:test';
import assert from 'node:assert';
import {
  getAuthToken,
  saveAuthToken,
  deleteAuthToken,
  setStorageAdapter,
  createMemoryStorageAdapter,
} from '../src/services/secureStorage.ts';
import { fetchNearbyShops } from '../src/services/shopService.ts';

// Test harness simulating the AuthContext state machine
class AuthStateHarness {
  constructor(storageAdapter, authServiceMock) {
    this.storage = storageAdapter;
    this.authService = authServiceMock;
    this.state = {
      status: 'restoring',
      user: null,
      token: null,
      restorationError: null,
    };
  }

  async restoreSession() {
    this.state.status = 'restoring';
    this.state.restorationError = null;

    let storedToken = null;
    try {
      storedToken = await this.storage.getItemAsync('lokal_access_token');
    } catch {
      this.state.status = 'unauthenticated';
      this.state.token = null;
      this.state.user = null;
      return;
    }

    if (!storedToken) {
      this.state.status = 'unauthenticated';
      this.state.token = null;
      this.state.user = null;
      return;
    }

    try {
      const user = await this.authService.getMe(storedToken);
      this.state.status = 'authenticated';
      this.state.token = storedToken;
      this.state.user = user;
      this.state.restorationError = null;
    } catch (err) {
      if (err?.status === 401) {
        // Invalid or expired session: delete credentials and transition to unauthenticated
        await this.storage.deleteItemAsync('lokal_access_token');
        this.state.status = 'unauthenticated';
        this.state.token = null;
        this.state.user = null;
        this.state.restorationError = null;
      } else {
        // Network or 5xx server failure: preserve stored token and expose retry error
        this.state.status = 'restoring';
        this.state.token = storedToken;
        this.state.user = null;
        this.state.restorationError = err?.message || 'Connection error';
      }
    }
  }

  async login(email, password) {
    const res = await this.authService.login({ email, password });
    const token = res.session?.access_token;
    if (!token) throw new Error('No access token returned');

    await this.storage.setItemAsync('lokal_access_token', token);
    this.state.status = 'authenticated';
    this.state.token = token;
    this.state.user = res.user;
    this.state.restorationError = null;
  }

  async register(email, password) {
    const res = await this.authService.register({ email, password });
    const token = res.session?.access_token;

    if (token) {
      await this.storage.setItemAsync('lokal_access_token', token);
      this.state.status = 'authenticated';
      this.state.token = token;
      this.state.user = res.user;
      this.state.restorationError = null;
    } else {
      this.state.status = 'unauthenticated';
      this.state.token = null;
      this.state.user = null;
      this.state.restorationError = null;
    }
    return { message: res.message };
  }

  async logout() {
    const activeToken = this.state.token;
    try {
      if (activeToken) {
        await this.authService.logout(activeToken);
      }
    } catch {
      // Best-effort: ignore backend/network errors
    } finally {
      await this.storage.deleteItemAsync('lokal_access_token');
      this.state.status = 'unauthenticated';
      this.state.token = null;
      this.state.user = null;
      this.state.restorationError = null;
    }
  }
}

test('secureStorage saves, retrieves, and deletes token correctly', async () => {
  const memoryAdapter = createMemoryStorageAdapter();
  setStorageAdapter(memoryAdapter);

  try {
    assert.strictEqual(await getAuthToken(), null);

    await saveAuthToken('secure-test-token-123');
    assert.strictEqual(await getAuthToken(), 'secure-test-token-123');

    await deleteAuthToken();
    assert.strictEqual(await getAuthToken(), null);
  } finally {
    setStorageAdapter(null);
  }
});

test('secureStorage rejects storing empty or whitespace-only token', async () => {
  const memoryAdapter = createMemoryStorageAdapter();
  setStorageAdapter(memoryAdapter);

  try {
    await assert.rejects(async () => {
      await saveAuthToken('');
    }, /Cannot store empty/);

    await assert.rejects(async () => {
      await saveAuthToken('   ');
    }, /Cannot store empty/);
  } finally {
    setStorageAdapter(null);
  }
});

test('session restoration: no stored token transitions to unauthenticated', async () => {
  const storage = createMemoryStorageAdapter();
  const mockAuthService = {
    getMe: async () => {
      throw new Error('Should not be called');
    },
  };

  const harness = new AuthStateHarness(storage, mockAuthService);
  await harness.restoreSession();

  assert.strictEqual(harness.state.status, 'unauthenticated');
  assert.strictEqual(harness.state.user, null);
  assert.strictEqual(harness.state.token, null);
  assert.strictEqual(harness.state.restorationError, null);
});

test('session restoration: valid stored token transitions to authenticated', async () => {
  const storage = createMemoryStorageAdapter();
  await storage.setItemAsync('lokal_access_token', 'valid-stored-jwt');

  const mockAuthService = {
    getMe: async (token) => {
      assert.strictEqual(token, 'valid-stored-jwt');
      return { id: 'restored-user', email: 'restored@lokal.ph' };
    },
  };

  const harness = new AuthStateHarness(storage, mockAuthService);
  await harness.restoreSession();

  assert.strictEqual(harness.state.status, 'authenticated');
  assert.strictEqual(harness.state.token, 'valid-stored-jwt');
  assert.strictEqual(harness.state.user.id, 'restored-user');
  assert.strictEqual(harness.state.restorationError, null);
});

test('session restoration: 401 Unauthorized purges token and transitions to unauthenticated', async () => {
  const storage = createMemoryStorageAdapter();
  await storage.setItemAsync('lokal_access_token', 'expired-stored-jwt');

  const mockAuthService = {
    getMe: async () => {
      const err = new Error('Invalid token');
      err.status = 401;
      throw err;
    },
  };

  const harness = new AuthStateHarness(storage, mockAuthService);
  await harness.restoreSession();

  assert.strictEqual(harness.state.status, 'unauthenticated');
  assert.strictEqual(harness.state.token, null);
  assert.strictEqual(harness.state.user, null);
  assert.strictEqual(await storage.getItemAsync('lokal_access_token'), null);
});

test('session restoration: network failure preserves stored credentials and exposes retry error', async () => {
  const storage = createMemoryStorageAdapter();
  await storage.setItemAsync('lokal_access_token', 'stored-jwt-preserved');

  let callCount = 0;
  const mockAuthService = {
    getMe: async () => {
      callCount++;
      if (callCount === 1) {
        const err = new Error('Network timeout');
        err.status = 503;
        throw err;
      }
      return { id: 'recovered-user', email: 'recovered@lokal.ph' };
    },
  };

  const harness = new AuthStateHarness(storage, mockAuthService);
  await harness.restoreSession();

  // First attempt: network error
  assert.strictEqual(harness.state.status, 'restoring');
  assert.strictEqual(harness.state.token, 'stored-jwt-preserved');
  assert.strictEqual(harness.state.restorationError, 'Network timeout');
  // Token was NOT deleted
  assert.strictEqual(await storage.getItemAsync('lokal_access_token'), 'stored-jwt-preserved');

  // Retry restoration when network is back
  await harness.restoreSession();
  assert.strictEqual(harness.state.status, 'authenticated');
  assert.strictEqual(harness.state.user.id, 'recovered-user');
  assert.strictEqual(harness.state.restorationError, null);
});

test('login flow: persists token and updates state to authenticated', async () => {
  const storage = createMemoryStorageAdapter();
  const mockAuthService = {
    login: async () => ({
      user: { id: 'user-login', email: 'user@lokal.ph' },
      session: { access_token: 'login-token-xyz' },
    }),
  };

  const harness = new AuthStateHarness(storage, mockAuthService);
  await harness.login('user@lokal.ph', 'password123');

  assert.strictEqual(harness.state.status, 'authenticated');
  assert.strictEqual(harness.state.token, 'login-token-xyz');
  assert.strictEqual(harness.state.user.id, 'user-login');
  assert.strictEqual(await storage.getItemAsync('lokal_access_token'), 'login-token-xyz');
});

test('register flow: with immediate session enters authenticated state', async () => {
  const storage = createMemoryStorageAdapter();
  const mockAuthService = {
    register: async () => ({
      user: { id: 'user-reg', email: 'reg@lokal.ph' },
      session: { access_token: 'reg-token-abc' },
      message: 'Registration successful.',
    }),
  };

  const harness = new AuthStateHarness(storage, mockAuthService);
  const result = await harness.register('reg@lokal.ph', 'password123');

  assert.strictEqual(result.message, 'Registration successful.');
  assert.strictEqual(harness.state.status, 'authenticated');
  assert.strictEqual(harness.state.token, 'reg-token-abc');
  assert.strictEqual(await storage.getItemAsync('lokal_access_token'), 'reg-token-abc');
});

test('register flow: without session stays unauthenticated and returns message', async () => {
  const storage = createMemoryStorageAdapter();
  const mockAuthService = {
    register: async () => ({
      user: { id: 'user-unconf', email: 'unconf@lokal.ph' },
      session: null,
      message: 'Please check your email.',
    }),
  };

  const harness = new AuthStateHarness(storage, mockAuthService);
  const result = await harness.register('unconf@lokal.ph', 'password123');

  assert.strictEqual(result.message, 'Please check your email.');
  assert.strictEqual(harness.state.status, 'unauthenticated');
  assert.strictEqual(harness.state.token, null);
  assert.strictEqual(await storage.getItemAsync('lokal_access_token'), null);
});

test('logout flow: always deletes stored credentials even when backend fails', async () => {
  const storage = createMemoryStorageAdapter();
  await storage.setItemAsync('lokal_access_token', 'active-token-to-logout');

  const mockAuthService = {
    logout: async () => {
      // Backend crashes or connection dropped
      throw new Error('500 Internal Server Error');
    },
  };

  const harness = new AuthStateHarness(storage, mockAuthService);
  harness.state.status = 'authenticated';
  harness.state.token = 'active-token-to-logout';
  harness.state.user = { id: 'user-1' };

  await harness.logout();

  assert.strictEqual(harness.state.status, 'unauthenticated');
  assert.strictEqual(harness.state.token, null);
  assert.strictEqual(harness.state.user, null);
  assert.strictEqual(await storage.getItemAsync('lokal_access_token'), null);
});

test('authenticated API integration: fetchNearbyShops attaches active Bearer token', async () => {
  const originalFetch = globalThis.fetch;
  let receivedAuthHeader = null;

  globalThis.fetch = async (url, options) => {
    receivedAuthHeader = options.headers['Authorization'];
    return {
      ok: true,
      status: 200,
      json: async () => [],
    };
  };

  try {
    await fetchNearbyShops({ latitude: 14.5995, longitude: 120.9842 }, 'session-bearer-token');
    assert.strictEqual(receivedAuthHeader, 'Bearer session-bearer-token');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

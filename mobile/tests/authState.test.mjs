import test from 'node:test';
import assert from 'node:assert';
import React from 'react';
import {
  getAuthToken,
  saveAuthToken,
  deleteAuthToken,
  setStorageAdapter,
  createMemoryStorageAdapter,
  resetStorageAdapters,
} from '../src/services/secureStorage.ts';
import { AuthProvider } from '../src/context/AuthContext.ts';
import { useAuth } from '../src/hooks/useAuth.ts';
import { fetchNearbyShops } from '../src/services/shopService.ts';

// Test runner helper mounting the actual production AuthProvider and exposing useAuth()
function renderProductionAuthProvider(props = {}) {
  let hookIndex = 0;
  const hookSlots = [];
  let isRerendering = false;
  let contextValue = null;
  const listeners = new Set();

  function areDepsEqual(prev, next) {
    if (!prev || !next) return false;
    if (prev.length !== next.length) return false;
    return prev.every((p, i) => Object.is(p, next[i]));
  }

  const dispatcher = {
    useState(initial) {
      const idx = hookIndex++;
      if (hookSlots[idx] === undefined) {
        hookSlots[idx] = typeof initial === 'function' ? initial() : initial;
      }
      const setState = (next) => {
        hookSlots[idx] = typeof next === 'function' ? next(hookSlots[idx]) : next;
        scheduleRerender();
      };
      return [hookSlots[idx], setState];
    },
    useRef(initial) {
      const idx = hookIndex++;
      if (hookSlots[idx] === undefined) {
        hookSlots[idx] = { current: initial };
      }
      return hookSlots[idx];
    },
    useCallback(fn, deps) {
      const idx = hookIndex++;
      const prev = hookSlots[idx];
      if (prev && areDepsEqual(prev.deps, deps)) {
        return prev.fn;
      }
      hookSlots[idx] = { fn, deps };
      return fn;
    },
    useEffect(effect, deps) {
      const idx = hookIndex++;
      const prev = hookSlots[idx];
      const shouldRun = !prev || !areDepsEqual(prev.deps, deps);
      hookSlots[idx] = { deps, effect, shouldRun };
    },
    useContext() {
      return contextValue;
    },
  };

  function scheduleRerender() {
    if (isRerendering) return;
    isRerendering = true;
    queueMicrotask(() => {
      isRerendering = false;
      rerender();
      for (const listener of listeners) {
        listener();
      }
    });
  }

  function rerender() {
    hookIndex = 0;
    React.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE.H = dispatcher;
    const vnode = AuthProvider({ ...props, children: null });
    contextValue = vnode.props.value;

    for (let i = 0; i < hookSlots.length; i++) {
      const slot = hookSlots[i];
      if (slot && typeof slot.effect === 'function' && slot.shouldRun) {
        slot.shouldRun = false;
        slot.effect();
      }
    }
  }

  rerender();

  return {
    getAuth: () => {
      React.__CLIENT_INTERNALS_DO_NOT_USE_OR_WARN_USERS_THEY_CANNOT_UPGRADE.H = dispatcher;
      return useAuth();
    },
    waitForStatus: (expectedStatus, timeoutMs = 1500) => {
      return new Promise((resolve, reject) => {
        if (contextValue?.status === expectedStatus) {
          return resolve(contextValue);
        }
        const timer = setTimeout(() => {
          listeners.delete(check);
          reject(
            new Error(
              `Timeout waiting for status "${expectedStatus}", current status is "${contextValue?.status}"`
            )
          );
        }, timeoutMs);

        function check() {
          if (contextValue?.status === expectedStatus) {
            clearTimeout(timer);
            listeners.delete(check);
            resolve(contextValue);
          }
        }
        listeners.add(check);
      });
    },
  };
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

test('secureStorage refuses silent memory fallback when not in headless test environment', async () => {
  resetStorageAdapters();
  const originalVersions = process.versions;

  try {
    // Simulate native production environment (no process.versions.node)
    Object.defineProperty(process, 'versions', {
      value: { ...originalVersions, node: undefined },
      configurable: true,
    });

    await assert.rejects(
      async () => {
        await getAuthToken();
      },
      (err) => {
        assert.match(err.message, /cannot be downgraded to memory in production/i);
        return true;
      }
    );
  } finally {
    Object.defineProperty(process, 'versions', {
      value: originalVersions,
      configurable: true,
    });
    resetStorageAdapters();
  }
});

test('production AuthProvider session restoration: empty storage transitions to unauthenticated', async () => {
  const storage = createMemoryStorageAdapter();
  setStorageAdapter(storage);

  try {
    const runner = renderProductionAuthProvider();
    assert.strictEqual(runner.getAuth().status, 'restoring');

    const auth = await runner.waitForStatus('unauthenticated');
    assert.strictEqual(auth.status, 'unauthenticated');
    assert.strictEqual(auth.user, null);
    assert.strictEqual(auth.token, null);
    assert.strictEqual(auth.restorationError, null);
  } finally {
    setStorageAdapter(null);
  }
});

test('production AuthProvider session restoration: valid token transitions to authenticated', async () => {
  const storage = createMemoryStorageAdapter();
  await storage.setItemAsync('lokal_access_token', 'valid-persisted-jwt');
  setStorageAdapter(storage);

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url, options) => {
    assert.strictEqual(url, 'http://localhost:8000/api/v1/auth/me');
    assert.strictEqual(options.headers.Authorization, 'Bearer valid-persisted-jwt');
    return {
      ok: true,
      status: 200,
      json: async () => ({
        id: 'user-restored',
        email: 'user@lokal.ph',
        user_metadata: { full_name: 'Restored User' },
      }),
    };
  };

  try {
    const runner = renderProductionAuthProvider();
    const auth = await runner.waitForStatus('authenticated');

    assert.strictEqual(auth.status, 'authenticated');
    assert.strictEqual(auth.token, 'valid-persisted-jwt');
    assert.strictEqual(auth.user?.id, 'user-restored');
    assert.strictEqual(auth.restorationError, null);
  } finally {
    globalThis.fetch = originalFetch;
    setStorageAdapter(null);
  }
});

test('production AuthProvider session restoration: 401 Unauthorized purges token and transitions to unauthenticated', async () => {
  const storage = createMemoryStorageAdapter();
  await storage.setItemAsync('lokal_access_token', 'expired-token');
  setStorageAdapter(storage);

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: 'Invalid or expired authentication token.' }),
  });

  try {
    const runner = renderProductionAuthProvider();
    const auth = await runner.waitForStatus('unauthenticated');

    assert.strictEqual(auth.status, 'unauthenticated');
    assert.strictEqual(auth.token, null);
    assert.strictEqual(auth.user, null);
    assert.strictEqual(await storage.getItemAsync('lokal_access_token'), null);
  } finally {
    globalThis.fetch = originalFetch;
    setStorageAdapter(null);
  }
});

test('production AuthProvider session restoration: network failure preserves token and exposes retry state', async () => {
  const storage = createMemoryStorageAdapter();
  await storage.setItemAsync('lokal_access_token', 'valid-token-offline');
  setStorageAdapter(storage);

  let fetchAttempt = 0;
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => {
    fetchAttempt++;
    if (fetchAttempt === 1) {
      return {
        ok: false,
        status: 503,
        json: async () => ({ detail: 'Service temporarily unavailable' }),
      };
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({
        id: 'user-recovered',
        email: 'recovered@lokal.ph',
      }),
    };
  };

  try {
    const runner = renderProductionAuthProvider();

    // Wait for initial failure
    await new Promise((resolve) => setTimeout(resolve, 50));

    const auth = runner.getAuth();
    assert.strictEqual(auth.status, 'restoring');
    assert.match(auth.restorationError || '', /unavailable/i);
    // Token was NOT deleted
    assert.strictEqual(await storage.getItemAsync('lokal_access_token'), 'valid-token-offline');

    // Trigger retry
    await auth.retryRestoration();
    const recoveredAuth = await runner.waitForStatus('authenticated');

    assert.strictEqual(recoveredAuth.status, 'authenticated');
    assert.strictEqual(recoveredAuth.user?.id, 'user-recovered');
    assert.strictEqual(recoveredAuth.restorationError, null);
  } finally {
    globalThis.fetch = originalFetch;
    setStorageAdapter(null);
  }
});

test('production AuthProvider restoration error: explicit sign out clears stored credentials and transitions to unauthenticated', async () => {
  const storage = createMemoryStorageAdapter();
  await storage.setItemAsync('lokal_access_token', 'token-offline-signout');
  setStorageAdapter(storage);

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url) => {
    if (url.includes('/api/v1/auth/me')) {
      return {
        ok: false,
        status: 503,
        json: async () => ({ detail: 'Service unavailable' }),
      };
    }
    if (url.includes('/api/v1/auth/logout')) {
      // Backend logout fails due to network outage
      throw new Error('Network error during logout');
    }
    throw new Error('Unexpected URL: ' + url);
  };

  try {
    const runner = renderProductionAuthProvider();

    // Wait for initial failure
    await new Promise((resolve) => setTimeout(resolve, 50));

    const auth = runner.getAuth();
    assert.strictEqual(auth.status, 'restoring');
    assert.match(auth.restorationError || '', /unavailable/i);
    assert.strictEqual(await storage.getItemAsync('lokal_access_token'), 'token-offline-signout');

    // User explicitly signs out from the restoration error screen
    await auth.logout();
    const unauth = await runner.waitForStatus('unauthenticated');

    assert.strictEqual(unauth.status, 'unauthenticated');
    assert.strictEqual(unauth.token, null);
    assert.strictEqual(unauth.user, null);
    assert.strictEqual(unauth.restorationError, null);
    assert.strictEqual(await storage.getItemAsync('lokal_access_token'), null);
  } finally {
    globalThis.fetch = originalFetch;
    setStorageAdapter(null);
  }
});

test('production AuthProvider login transition: persists token and sets authenticated state', async () => {
  const storage = createMemoryStorageAdapter();
  setStorageAdapter(storage);

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url) => {
    if (url.includes('/api/v1/auth/login')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          user: { id: 'login-user', email: 'login@lokal.ph' },
          session: { access_token: 'new-login-token' },
        }),
      };
    }
    throw new Error('Unexpected URL: ' + url);
  };

  try {
    const runner = renderProductionAuthProvider();
    await runner.waitForStatus('unauthenticated');

    await runner.getAuth().login({ email: 'login@lokal.ph', password: 'password123' });
    const auth = await runner.waitForStatus('authenticated');

    assert.strictEqual(auth.status, 'authenticated');
    assert.strictEqual(auth.token, 'new-login-token');
    assert.strictEqual(auth.user?.id, 'login-user');
    assert.strictEqual(await storage.getItemAsync('lokal_access_token'), 'new-login-token');
  } finally {
    globalThis.fetch = originalFetch;
    setStorageAdapter(null);
  }
});

test('production AuthProvider register transition: with session enters authenticated', async () => {
  const storage = createMemoryStorageAdapter();
  setStorageAdapter(storage);

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url) => {
    if (url.includes('/api/v1/auth/register')) {
      return {
        ok: true,
        status: 201,
        json: async () => ({
          user: { id: 'reg-user', email: 'reg@lokal.ph' },
          session: { access_token: 'new-reg-token' },
          message: 'Registration successful.',
        }),
      };
    }
    throw new Error('Unexpected URL: ' + url);
  };

  try {
    const runner = renderProductionAuthProvider();
    await runner.waitForStatus('unauthenticated');

    const res = await runner.getAuth().register({ email: 'reg@lokal.ph', password: 'password123' });
    assert.strictEqual(res.message, 'Registration successful.');

    const auth = await runner.waitForStatus('authenticated');
    assert.strictEqual(auth.status, 'authenticated');
    assert.strictEqual(auth.token, 'new-reg-token');
    assert.strictEqual(await storage.getItemAsync('lokal_access_token'), 'new-reg-token');
  } finally {
    globalThis.fetch = originalFetch;
    setStorageAdapter(null);
  }
});

test('production AuthProvider register transition: without session stays unauthenticated', async () => {
  const storage = createMemoryStorageAdapter();
  setStorageAdapter(storage);

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url) => {
    if (url.includes('/api/v1/auth/register')) {
      return {
        ok: true,
        status: 201,
        json: async () => ({
          user: { id: 'unconf-user', email: 'unconf@lokal.ph' },
          session: null,
          message: 'Please check your email.',
        }),
      };
    }
    throw new Error('Unexpected URL: ' + url);
  };

  try {
    const runner = renderProductionAuthProvider();
    await runner.waitForStatus('unauthenticated');

    const res = await runner.getAuth().register({ email: 'unconf@lokal.ph', password: 'password123' });
    assert.strictEqual(res.message, 'Please check your email.');

    const auth = runner.getAuth();
    assert.strictEqual(auth.status, 'unauthenticated');
    assert.strictEqual(auth.token, null);
    assert.strictEqual(await storage.getItemAsync('lokal_access_token'), null);
  } finally {
    globalThis.fetch = originalFetch;
    setStorageAdapter(null);
  }
});

test('production AuthProvider logout transition: purges token and returns to unauthenticated', async () => {
  const storage = createMemoryStorageAdapter();
  await storage.setItemAsync('lokal_access_token', 'token-to-signout');
  setStorageAdapter(storage);

  const originalFetch = globalThis.fetch;
  let logoutCalled = false;
  globalThis.fetch = async (url, options) => {
    if (url.includes('/api/v1/auth/me')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 'u1', email: 'u1@lokal.ph' }),
      };
    }
    if (url.includes('/api/v1/auth/logout')) {
      logoutCalled = true;
      assert.strictEqual(options.headers.Authorization, 'Bearer token-to-signout');
      return {
        ok: true,
        status: 200,
        json: async () => ({ message: 'Successfully signed out.' }),
      };
    }
    throw new Error('Unexpected URL: ' + url);
  };

  try {
    const runner = renderProductionAuthProvider();
    await runner.waitForStatus('authenticated');

    await runner.getAuth().logout();
    const auth = await runner.waitForStatus('unauthenticated');

    assert.strictEqual(logoutCalled, true);
    assert.strictEqual(auth.status, 'unauthenticated');
    assert.strictEqual(auth.token, null);
    assert.strictEqual(await storage.getItemAsync('lokal_access_token'), null);
  } finally {
    globalThis.fetch = originalFetch;
    setStorageAdapter(null);
  }
});

test('production AuthProvider logout transition on backend failure: still clears credentials', async () => {
  const storage = createMemoryStorageAdapter();
  await storage.setItemAsync('lokal_access_token', 'token-fail-logout');
  setStorageAdapter(storage);

  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (url) => {
    if (url.includes('/api/v1/auth/me')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({ id: 'u1', email: 'u1@lokal.ph' }),
      };
    }
    if (url.includes('/api/v1/auth/logout')) {
      return {
        ok: false,
        status: 500,
        json: async () => ({ detail: 'Backend crashed' }),
      };
    }
    throw new Error('Unexpected URL: ' + url);
  };

  try {
    const runner = renderProductionAuthProvider();
    await runner.waitForStatus('authenticated');

    await runner.getAuth().logout();
    const auth = await runner.waitForStatus('unauthenticated');

    assert.strictEqual(auth.status, 'unauthenticated');
    assert.strictEqual(auth.token, null);
    assert.strictEqual(await storage.getItemAsync('lokal_access_token'), null);
  } finally {
    globalThis.fetch = originalFetch;
    setStorageAdapter(null);
  }
});

test('stale restoration protection: login during restoration prevents 401 from deleting new token', async () => {
  const storage = createMemoryStorageAdapter();
  await storage.setItemAsync('lokal_access_token', 'stale-token-1');
  setStorageAdapter(storage);

  const originalFetch = globalThis.fetch;
  let resolveGetMe;
  const getMeGate = new Promise((resolve) => {
    resolveGetMe = resolve;
  });

  globalThis.fetch = async (url) => {
    if (url.includes('/api/v1/auth/me')) {
      await getMeGate;
      return {
        ok: false,
        status: 401,
        json: async () => ({ detail: 'Token expired' }),
      };
    }
    if (url.includes('/api/v1/auth/login')) {
      return {
        ok: true,
        status: 200,
        json: async () => ({
          user: { id: 'new-user', email: 'new@lokal.ph' },
          session: { access_token: 'newly-authenticated-token' },
        }),
      };
    }
    throw new Error('Unexpected URL: ' + url);
  };

  try {
    const runner = renderProductionAuthProvider();

    // While restoration is in flight, perform login
    await runner.getAuth().login({ email: 'new@lokal.ph', password: 'password123' });
    const authAfterLogin = runner.getAuth();
    assert.strictEqual(authAfterLogin.status, 'authenticated');
    assert.strictEqual(authAfterLogin.token, 'newly-authenticated-token');

    // Unblock the old restoration to return 401
    resolveGetMe();
    await new Promise((resolve) => setTimeout(resolve, 30));

    // Verify: new token must NOT be deleted, and state must remain authenticated
    assert.strictEqual(await storage.getItemAsync('lokal_access_token'), 'newly-authenticated-token');
    const authFinal = runner.getAuth();
    assert.strictEqual(authFinal.status, 'authenticated');
    assert.strictEqual(authFinal.token, 'newly-authenticated-token');
    assert.strictEqual(authFinal.user?.id, 'new-user');
  } finally {
    globalThis.fetch = originalFetch;
    setStorageAdapter(null);
  }
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

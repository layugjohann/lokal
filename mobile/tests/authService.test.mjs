import test from 'node:test';
import assert from 'node:assert';
import {
  login,
  register,
  logout,
  getMe,
} from '../src/services/authService.ts';

test('login sends credentials and returns AuthResponse on success', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedMethod = '';
  let requestedBody = null;

  globalThis.fetch = async (url, options) => {
    requestedUrl = url;
    requestedMethod = options.method;
    requestedBody = JSON.parse(options.body);

    return {
      ok: true,
      status: 200,
      json: async () => ({
        user: {
          id: 'user-123',
          email: 'test@lokal.ph',
          created_at: '2026-09-25T00:00:00Z',
          user_metadata: {},
          app_metadata: {},
        },
        session: {
          access_token: 'valid-jwt-token',
          refresh_token: null,
          token_type: 'bearer',
          expires_in: 3600,
          expires_at: 1727222400,
        },
        message: 'Authentication successful.',
      }),
    };
  };

  try {
    const res = await login({ email: 'test@lokal.ph', password: 'password123' });

    assert.strictEqual(requestedUrl, 'http://localhost:8000/api/v1/auth/login');
    assert.strictEqual(requestedMethod, 'POST');
    assert.strictEqual(requestedBody.email, 'test@lokal.ph');
    assert.strictEqual(requestedBody.password, 'password123');
    assert.strictEqual(res.user.id, 'user-123');
    assert.strictEqual(res.session?.access_token, 'valid-jwt-token');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('login throws descriptive error on 401 invalid credentials', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: 'Invalid email or password.' }),
  });

  try {
    await assert.rejects(
      async () => {
        await login({ email: 'wrong@lokal.ph', password: 'badpassword' });
      },
      (err) => {
        assert.strictEqual(err.message, 'Invalid email or password.');
        assert.strictEqual(err.status, 401);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('login throws generic error when backend returns non-JSON error', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 500,
    json: async () => {
      throw new Error('Non-JSON HTML response');
    },
  });

  try {
    await assert.rejects(
      async () => {
        await login({ email: 'test@lokal.ph', password: 'password123' });
      },
      (err) => {
        assert.strictEqual(err.message, 'Invalid email or password.');
        assert.strictEqual(err.status, 500);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('register sends payload and returns AuthResponse with session', async () => {
  const originalFetch = globalThis.fetch;
  let requestedUrl = '';
  let requestedBody = null;

  globalThis.fetch = async (url, options) => {
    requestedUrl = url;
    requestedBody = JSON.parse(options.body);

    return {
      ok: true,
      status: 201,
      json: async () => ({
        user: {
          id: 'new-user-1',
          email: 'newuser@lokal.ph',
          created_at: '2026-09-25T00:00:00Z',
        },
        session: {
          access_token: 'new-session-token',
          token_type: 'bearer',
        },
        message: 'Registration successful.',
      }),
    };
  };

  try {
    const res = await register({ email: 'newuser@lokal.ph', password: 'secretpassword' });
    assert.strictEqual(requestedUrl, 'http://localhost:8000/api/v1/auth/register');
    assert.strictEqual(requestedBody.email, 'newuser@lokal.ph');
    assert.strictEqual(res.user.id, 'new-user-1');
    assert.strictEqual(res.session?.access_token, 'new-session-token');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('register returns null session when email confirmation is required', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: true,
    status: 201,
    json: async () => ({
      user: {
        id: 'unconfirmed-user',
        email: 'unconfirmed@lokal.ph',
      },
      session: null,
      message: 'Registration successful. Please check your email to verify your account.',
    }),
  });

  try {
    const res = await register({ email: 'unconfirmed@lokal.ph', password: 'secretpassword' });
    assert.strictEqual(res.session, null);
    assert.match(res.message, /check your email/i);
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('register throws on 400 when user is already registered', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 400,
    json: async () => ({ detail: 'User already registered' }),
  });

  try {
    await assert.rejects(
      async () => {
        await register({ email: 'existing@lokal.ph', password: 'password123' });
      },
      (err) => {
        assert.strictEqual(err.message, 'User already registered');
        assert.strictEqual(err.status, 400);
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('logout sends Bearer token and succeeds', async () => {
  const originalFetch = globalThis.fetch;
  let requestedHeaders = {};

  globalThis.fetch = async (url, options) => {
    requestedHeaders = options.headers;
    return {
      ok: true,
      status: 200,
      json: async () => ({ message: 'Successfully signed out.' }),
    };
  };

  try {
    const res = await logout('active-session-jwt');
    assert.strictEqual(requestedHeaders.Authorization, 'Bearer active-session-jwt');
    assert.strictEqual(res.message, 'Successfully signed out.');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('logout throws when token is missing', async () => {
  await assert.rejects(
    async () => {
      await logout('');
    },
    (err) => {
      assert.strictEqual(err.status, 401);
      return true;
    }
  );
});

test('getMe retrieves profile with Bearer token', async () => {
  const originalFetch = globalThis.fetch;
  let requestedHeaders = {};

  globalThis.fetch = async (url, options) => {
    requestedHeaders = options.headers;
    return {
      ok: true,
      status: 200,
      json: async () => ({
        id: 'user-abc',
        email: 'user@lokal.ph',
        user_metadata: { full_name: 'Coffee Lover' },
      }),
    };
  };

  try {
    const profile = await getMe('my-jwt-token');
    assert.strictEqual(requestedHeaders.Authorization, 'Bearer my-jwt-token');
    assert.strictEqual(profile.id, 'user-abc');
    assert.strictEqual(profile.email, 'user@lokal.ph');
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test('getMe throws 401 when token is expired or rejected', async () => {
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: 'Invalid or expired authentication token.' }),
  });

  try {
    await assert.rejects(
      async () => {
        await getMe('expired-jwt-token');
      },
      (err) => {
        assert.strictEqual(err.status, 401);
        assert.strictEqual(err.message, 'Invalid or expired authentication token.');
        return true;
      }
    );
  } finally {
    globalThis.fetch = originalFetch;
  }
});

import type {
  AuthResponse,
  AuthUser,
  LoginInput,
  RegisterInput,
} from '../types/auth';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
export const DEFAULT_AUTH_TIMEOUT_MS = 10000;

export function getApiBaseUrl(): string {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL;
  }
  return DEFAULT_API_BASE_URL;
}

export interface AuthApiError extends Error {
  status?: number;
}

function createAuthError(message: string, status?: number): AuthApiError {
  const error = new Error(message) as AuthApiError;
  if (status !== undefined) {
    error.status = status;
  }
  return error;
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit = {},
  timeoutMs: number = DEFAULT_AUTH_TIMEOUT_MS
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => {
    controller.abort();
  }, timeoutMs);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
    });
    return response;
  } catch (err: any) {
    if (err?.name === 'AbortError' || controller.signal.aborted) {
      throw createAuthError('Authentication request timed out. Please try again.', 504);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

/**
 * Authenticates an existing user with email and password against FastAPI.
 */
export async function login(
  input: LoginInput,
  timeoutMs: number = DEFAULT_AUTH_TIMEOUT_MS
): Promise<AuthResponse> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/auth/login`;

  const response = await fetchWithTimeout(
    url,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        email: input.email.trim(),
        password: input.password,
      }),
    },
    timeoutMs
  );

  if (!response.ok) {
    let errorDetail = 'Invalid email or password.';
    try {
      const data = await response.json();
      if (data && typeof data.detail === 'string') {
        errorDetail = data.detail;
      }
    } catch {
      // Non-JSON fallback
    }
    throw createAuthError(errorDetail, response.status);
  }

  return response.json();
}

/**
 * Registers a new user account with email and password against FastAPI.
 */
export async function register(
  input: RegisterInput,
  timeoutMs: number = DEFAULT_AUTH_TIMEOUT_MS
): Promise<AuthResponse> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/auth/register`;

  const response = await fetchWithTimeout(
    url,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify({
        email: input.email.trim(),
        password: input.password,
      }),
    },
    timeoutMs
  );

  if (!response.ok) {
    let errorDetail = 'Registration failed.';
    try {
      const data = await response.json();
      if (data && typeof data.detail === 'string') {
        errorDetail = data.detail;
      }
    } catch {
      // Non-JSON fallback
    }
    throw createAuthError(errorDetail, response.status);
  }

  return response.json();
}

/**
 * Informs the backend to invalidate the user session.
 */
export async function logout(
  token: string,
  timeoutMs: number = DEFAULT_AUTH_TIMEOUT_MS
): Promise<{ message: string }> {
  if (!token || !token.trim()) {
    throw createAuthError('Authentication token is required to logout.', 401);
  }

  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/auth/logout`;

  const response = await fetchWithTimeout(
    url,
    {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${token.trim()}`,
      },
    },
    timeoutMs
  );

  if (!response.ok) {
    let errorDetail = 'Failed to logout.';
    try {
      const data = await response.json();
      if (data && typeof data.detail === 'string') {
        errorDetail = data.detail;
      }
    } catch {
      // Non-JSON fallback
    }
    throw createAuthError(errorDetail, response.status);
  }

  return response.json();
}

/**
 * Validates the current session token and returns the authenticated user profile.
 */
export async function getMe(
  token: string,
  timeoutMs: number = DEFAULT_AUTH_TIMEOUT_MS
): Promise<AuthUser> {
  if (!token || !token.trim()) {
    throw createAuthError('Authentication token is required.', 401);
  }

  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/auth/me`;

  const response = await fetchWithTimeout(
    url,
    {
      method: 'GET',
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${token.trim()}`,
      },
    },
    timeoutMs
  );

  if (!response.ok) {
    let errorDetail = 'Failed to fetch current user.';
    try {
      const data = await response.json();
      if (data && typeof data.detail === 'string') {
        errorDetail = data.detail;
      }
    } catch {
      // Non-JSON fallback
    }
    throw createAuthError(errorDetail, response.status);
  }

  return response.json();
}

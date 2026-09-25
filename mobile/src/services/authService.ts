import type {
  AuthResponse,
  AuthUser,
  LoginInput,
  RegisterInput,
} from '../types/auth';

const DEFAULT_API_BASE_URL = 'http://localhost:8000';

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

/**
 * Authenticates an existing user with email and password against FastAPI.
 */
export async function login(input: LoginInput): Promise<AuthResponse> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/auth/login`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      email: input.email.trim(),
      password: input.password,
    }),
  });

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
export async function register(input: RegisterInput): Promise<AuthResponse> {
  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/auth/register`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      email: input.email.trim(),
      password: input.password,
    }),
  });

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
export async function logout(token: string): Promise<{ message: string }> {
  if (!token || !token.trim()) {
    throw createAuthError('Authentication token is required to logout.', 401);
  }

  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/auth/logout`;

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${token.trim()}`,
    },
  });

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
export async function getMe(token: string): Promise<AuthUser> {
  if (!token || !token.trim()) {
    throw createAuthError('Authentication token is required.', 401);
  }

  const baseUrl = getApiBaseUrl();
  const url = `${baseUrl}/api/v1/auth/me`;

  const response = await fetch(url, {
    method: 'GET',
    headers: {
      Accept: 'application/json',
      Authorization: `Bearer ${token.trim()}`,
    },
  });

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

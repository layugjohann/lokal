import React, {
  createContext,
  useCallback,
  useEffect,
  useRef,
  useState,
} from 'react';
import type {
  AuthResponse,
  AuthState,
  AuthUser,
  LoginInput,
  RegisterInput,
} from '../types/auth.ts';
import * as authService from '../services/authService.ts';
import {
  deleteAuthToken,
  getAuthToken,
  saveAuthToken,
} from '../services/secureStorage.ts';

export interface AuthContextValue extends AuthState {
  login: (input: LoginInput) => Promise<void>;
  register: (input: RegisterInput) => Promise<{ message?: string | null }>;
  logout: () => Promise<void>;
  retryRestoration: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export interface AuthProviderProps {
  children: React.ReactNode;
  initialToken?: string | null;
  initialUser?: AuthUser | null;
}

export function AuthProvider({
  children,
  initialToken,
  initialUser,
}: AuthProviderProps) {
  // Provider-level operation generation counter guarding against stale/concurrent async updates
  const operationGenerationRef = useRef(0);

  const [state, setState] = useState<AuthState>(() => {
    if (initialToken !== undefined && initialToken !== null) {
      return {
        status: 'authenticated',
        token: initialToken,
        user: initialUser ?? { id: 'test-user-id', email: 'test@lokal.ph' },
        restorationError: null,
      };
    }
    if (initialToken === null) {
      return {
        status: 'unauthenticated',
        token: null,
        user: null,
        restorationError: null,
      };
    }
    return {
      status: 'restoring',
      token: null,
      user: null,
      restorationError: null,
    };
  });

  const restoreSession = useCallback(async () => {
    if (initialToken !== undefined) {
      return;
    }

    const currentGen = ++operationGenerationRef.current;

    setState((prev) => ({
      ...prev,
      status: 'restoring',
      restorationError: null,
    }));

    let storedToken: string | null = null;
    try {
      storedToken = await getAuthToken();
    } catch {
      if (operationGenerationRef.current !== currentGen) return;
      setState({
        status: 'unauthenticated',
        token: null,
        user: null,
        restorationError: null,
      });
      return;
    }

    if (operationGenerationRef.current !== currentGen) return;

    if (!storedToken) {
      setState({
        status: 'unauthenticated',
        token: null,
        user: null,
        restorationError: null,
      });
      return;
    }

    try {
      const user = await authService.getMe(storedToken);
      if (operationGenerationRef.current !== currentGen) return;

      setState({
        status: 'authenticated',
        token: storedToken,
        user,
        restorationError: null,
      });
    } catch (err: any) {
      if (operationGenerationRef.current !== currentGen) return;

      if (err?.status === 401) {
        // Token is invalid or expired: purge from secure storage ONLY if this restoration is still current
        try {
          await deleteAuthToken();
        } catch {
          // Ignore deletion error
        }

        if (operationGenerationRef.current !== currentGen) return;

        setState({
          status: 'unauthenticated',
          token: null,
          user: null,
          restorationError: null,
        });
      } else {
        // Network or 5xx server failure: preserve stored credentials and expose retry state
        setState({
          status: 'restoring',
          token: storedToken,
          user: null,
          restorationError:
            err?.message || 'Unable to connect to server. Please check your connection.',
        });
      }
    }
  }, [initialToken]);

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  const login = useCallback(async (input: LoginInput) => {
    // Invalidate any in-flight session restoration
    operationGenerationRef.current++;

    const response: AuthResponse = await authService.login(input);
    const accessToken = response.session?.access_token;
    if (!accessToken) {
      throw new Error('Authentication succeeded but no access token was returned.');
    }

    await saveAuthToken(accessToken);

    setState({
      status: 'authenticated',
      token: accessToken,
      user: response.user,
      restorationError: null,
    });
  }, []);

  const register = useCallback(
    async (input: RegisterInput): Promise<{ message?: string | null }> => {
      // Invalidate any in-flight session restoration
      operationGenerationRef.current++;

      const response: AuthResponse = await authService.register(input);
      const accessToken = response.session?.access_token;

      if (accessToken) {
        await saveAuthToken(accessToken);
        setState({
          status: 'authenticated',
          token: accessToken,
          user: response.user,
          restorationError: null,
        });
      } else {
        setState({
          status: 'unauthenticated',
          token: null,
          user: null,
          restorationError: null,
        });
      }

      return { message: response.message };
    },
    []
  );

  const logout = useCallback(async () => {
    // Invalidate any in-flight session restoration
    operationGenerationRef.current++;

    let activeToken = state.token;
    if (!activeToken) {
      try {
        activeToken = await getAuthToken();
      } catch {
        // Ignore storage read error
      }
    }

    try {
      if (activeToken) {
        await authService.logout(activeToken);
      }
    } catch {
      // Swallow backend/network errors so local cleanup is never prevented
    } finally {
      try {
        await deleteAuthToken();
      } catch {
        // Fallback cleanup
      }
      setState({
        status: 'unauthenticated',
        token: null,
        user: null,
        restorationError: null,
      });
    }
  }, [state.token]);

  const retryRestoration = useCallback(async () => {
    await restoreSession();
  }, [restoreSession]);

  const value: AuthContextValue = {
    ...state,
    login,
    register,
    logout,
    retryRestoration,
  };

  return React.createElement(AuthContext.Provider, { value }, children);
}

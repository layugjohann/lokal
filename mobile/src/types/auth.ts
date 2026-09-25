export interface AuthUser {
  id: string;
  email: string | null;
  created_at?: string | null;
  user_metadata?: Record<string, unknown>;
  app_metadata?: Record<string, unknown>;
}

export interface AuthSession {
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
  expires_in?: number | null;
  expires_at?: number | null;
}

export interface AuthResponse {
  user: AuthUser;
  session: AuthSession | null;
  message?: string | null;
}

export interface LoginInput {
  email: string;
  password: string;
}

export interface RegisterInput {
  email: string;
  password: string;
}

export type AuthStatus = 'restoring' | 'authenticated' | 'unauthenticated';

export interface AuthState {
  status: AuthStatus;
  user: AuthUser | null;
  token: string | null;
  restorationError: string | null;
}

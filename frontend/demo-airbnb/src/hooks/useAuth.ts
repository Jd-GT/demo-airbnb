"use client";

import {
  createContext,
  createElement,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useRouter } from 'next/navigation';
import {
  AUTH_UNAUTHORIZED_EVENT,
  getCurrentUser,
  type AuthUser,
  type SignUpInput,
} from '../lib/authService';
import * as authService from '../lib/authService';

type AuthContextValue = {
  user: AuthUser | null;
  isAuthenticated: boolean;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<AuthUser>;
  signup: (input: SignUpInput) => Promise<AuthUser>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<string>;
  clearError: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

function getStoredAuthenticatedUser() {
  const storedUser = getCurrentUser();
  return storedUser && authService.getAccessToken() ? storedUser : null;
}

function getErrorMessage(error: unknown) {
  if (error instanceof Error) {
    return error.message;
  }

  return 'Ocurrio un error inesperado.';
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setUser(getStoredAuthenticatedUser());
    setLoading(false);
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      setError('Tu sesion expiro. Inicia sesion de nuevo.');
      router.replace('/login');
    };

    window.addEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);

    return () => {
      window.removeEventListener(AUTH_UNAUTHORIZED_EVENT, handleUnauthorized);
    };
  }, [router]);

  useEffect(() => {
    const handleStorageChange = (event: StorageEvent) => {
      if (event.key === 'user' || event.key === 'access_token') {
        setUser(getStoredAuthenticatedUser());
      }
    };

    window.addEventListener('storage', handleStorageChange);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    setLoading(true);
    setError(null);

    try {
      const session = await authService.login(email, password);
      setUser(session.user);
      return session.user;
    } catch (loginError) {
      setError(getErrorMessage(loginError));
      throw loginError;
    } finally {
      setLoading(false);
    }
  }, []);

  const signup = useCallback(async (input: SignUpInput) => {
    setLoading(true);
    setError(null);

    try {
      const session = await authService.signup(input);
      setUser(session.user);
      return session.user;
    } catch (signupError) {
      setError(getErrorMessage(signupError));
      throw signupError;
    } finally {
      setLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      await authService.logout();
    } finally {
      setUser(null);
      setLoading(false);
      router.replace('/login');
    }
  }, [router]);

  const refreshToken = useCallback(async () => {
    setError(null);

    try {
      return await authService.refreshToken();
    } catch (refreshError) {
      setUser(null);
      setError(getErrorMessage(refreshError));
      throw refreshError;
    }
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isAuthenticated: Boolean(user && authService.getAccessToken()),
      loading,
      error,
      login,
      signup,
      logout,
      refreshToken,
      clearError,
    }),
    [clearError, error, loading, login, logout, refreshToken, signup, user],
  );

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider.');
  }

  return context;
}

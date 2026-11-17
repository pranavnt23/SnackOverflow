/**
 * Authentication Context & Provider for Snack Overflow.
 * Manages JWT tokens, authenticated user lifecycle, and role detection.
 */

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { User, LoginResponse } from '../api/types';
import { apiClient, TOKEN_STORAGE_KEY } from '../api/client';

/**
 * SECURITY TRADE-OFF NOTE (XSS vs CSRF):
 * Storing JWTs in localStorage allows simple client-side attachment in the Authorization
 * Bearer header, avoiding Cross-Site Request Forgery (CSRF) attacks since browsers do not
 * automatically append localStorage tokens to cross-origin requests.
 *
 * Trade-off: localStorage is accessible to any JavaScript running in the same origin.
 * Therefore, if an application suffers from a Cross-Site Scripting (XSS) vulnerability,
 * an attacker can exfiltrate the access token.
 *
 * Production alternatives: An HttpOnly, Secure, SameSite=Strict cookie prevents JavaScript
 * access (mitigating XSS exfiltration), but requires CSRF tokens (Double Submit Cookie or
 * synchronizer tokens) and strict origin verification.
 * In this single-page application, localStorage is used alongside React's automatic JSX
 * output escaping, with the server strictly re-validating the token and database user state
 * on every single incoming API request.
 */

interface AuthContextType {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(() => {
    return localStorage.getItem(TOKEN_STORAGE_KEY);
  });
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // Restore session via GET /auth/me when application initializes
  const restoreSession = useCallback(async () => {
    const existingToken = localStorage.getItem(TOKEN_STORAGE_KEY);
    if (!existingToken) {
      setUser(null);
      setIsLoading(false);
      return;
    }

    try {
      // Backend validates token and returns fresh user record from Postgres
      const currentUser = await apiClient.get<User>('/auth/me');
      setUser(currentUser);
      setToken(existingToken);
    } catch {
      // Token expired, malformed, or user deleted from DB
      localStorage.removeItem(TOKEN_STORAGE_KEY);
      setUser(null);
      setToken(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    restoreSession();
  }, [restoreSession]);

  const login = async (email: string, password: string): Promise<void> => {
    setIsLoading(true);
    try {
      const response = await apiClient.post<LoginResponse>('/auth/login', {
        email: email.trim(),
        password,
      });

      localStorage.setItem(TOKEN_STORAGE_KEY, response.access_token);
      setToken(response.access_token);
      setUser(response.user);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = useCallback(() => {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    setToken(null);
    setUser(null);
  }, []);

  const refreshUser = async () => {
    try {
      const updatedUser = await apiClient.get<User>('/auth/me');
      setUser(updatedUser);
    } catch {
      logout();
    }
  };

  const isAdmin = user?.role === 'admin';

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!user && !!token,
        isLoading,
        isAdmin,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

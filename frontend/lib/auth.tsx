'use client';

import { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { CurrentUser, clearToken, getCurrentUser, getStoredToken, login, storeToken } from './api';

type AuthContextValue = {
  user: CurrentUser | null;
  isLoading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      if (!getStoredToken()) {
        setIsLoading(false);
        return;
      }
      try {
        setUser(await getCurrentUser());
      } catch {
        clearToken();
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    }

    void loadUser();
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      isLoading,
      async signIn(email: string, password: string) {
        const token = await login(email, password);
        storeToken(token.access_token);
        setUser(await getCurrentUser());
      },
      signOut() {
        clearToken();
        setUser(null);
      },
    }),
    [isLoading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}

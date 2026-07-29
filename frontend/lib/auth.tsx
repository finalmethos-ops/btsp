"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  CurrentUser,
  clearToken,
  changePassword,
  getCurrentUser,
  getStoredToken,
  login,
  selectVendorContext,
  selectEventVendorContext,
  storeToken,
  storeRefreshToken,
} from "./api";
import {
  clearEventOfflineAssets,
  clearEventOfflineCache,
} from "./event-offline-cache";

type AuthContextValue = {
  user: CurrentUser | null;
  isLoading: boolean;
  signIn: (
    email: string,
    password: string,
    loginContext?: "standard" | "event",
  ) => Promise<void>;
  selectVendor: (vendorCode: string) => Promise<void>;
  selectEventVendor: (eventId: string, vendorCode: string) => Promise<void>;
  updatePassword: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<void>;
  signOut: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  // Keep protected routes behind a hydration barrier when a token already
  // exists. Without this, a hard navigation briefly renders the login page
  // before the session lookup completes.
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (
      typeof window !== "undefined" &&
      ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname) &&
      "serviceWorker" in navigator
    ) {
      void navigator.serviceWorker
        .getRegistrations()
        .then((registrations) =>
          Promise.all(
            registrations
              .filter((registration) =>
                registration.active?.scriptURL.endsWith("/event-sw.js"),
              )
              .map((registration) => registration.unregister()),
          ),
        );
    }

    async function loadUser() {
      try {
        if (!getStoredToken()) {
          return;
        }
        setIsLoading(true);
        setUser(await getCurrentUser());
      } catch {
        clearToken();
        clearEventOfflineCache();
        clearEventOfflineAssets();
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
      async signIn(email: string, password: string, loginContext = "standard") {
        const token = await login(email, password, loginContext);
        clearEventOfflineCache();
        clearEventOfflineAssets();
        storeToken(token.access_token);
        storeRefreshToken(token.refresh_token);
        try {
          setUser(await getCurrentUser());
        } catch (error) {
          clearToken();
          clearEventOfflineCache();
          clearEventOfflineAssets();
          setUser(null);
          throw error;
        }
      },
      async selectVendor(vendorCode: string) {
        const token = await selectVendorContext(vendorCode);
        storeToken(token.access_token);
        storeRefreshToken(token.refresh_token);
        try {
          setUser(await getCurrentUser());
        } catch (error) {
          clearToken();
          setUser(null);
          throw error;
        }
      },
      async selectEventVendor(eventId: string, vendorCode: string) {
        const token = await selectEventVendorContext(eventId, vendorCode);
        storeToken(token.access_token);
        storeRefreshToken(token.refresh_token);
        setUser(await getCurrentUser());
      },
      async updatePassword(currentPassword: string, newPassword: string) {
        await changePassword(currentPassword, newPassword);
        setUser(await getCurrentUser());
      },
      signOut() {
        clearToken();
        clearEventOfflineCache();
        clearEventOfflineAssets();
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
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}

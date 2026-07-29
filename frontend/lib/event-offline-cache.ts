const prefix = "btsp.event-offline.";
const maxEntries = 12;

type CachedValue<T> = {
  value: T;
  cached_at: string;
  expires_at: string;
};

export function cacheEventData<T>(key: string, value: T, expiresAt: string) {
  try {
    const keys = Array.from({ length: sessionStorage.length }, (_, index) =>
      sessionStorage.key(index),
    ).filter((item): item is string => Boolean(item?.startsWith(prefix)));
    keys.forEach((item) => {
      try {
        const cached = JSON.parse(sessionStorage.getItem(item) || "{}");
        if (
          cached.expires_at &&
          new Date(cached.expires_at).getTime() < Date.now()
        )
          sessionStorage.removeItem(item);
      } catch {
        sessionStorage.removeItem(item);
      }
    });
    sessionStorage.setItem(
      `${prefix}${key}`,
      JSON.stringify({
        value,
        cached_at: new Date().toISOString(),
        expires_at: expiresAt,
      } satisfies CachedValue<T>),
    );
    const remaining = Array.from(
      { length: sessionStorage.length },
      (_, index) => sessionStorage.key(index),
    ).filter((item): item is string => Boolean(item?.startsWith(prefix)));
    remaining
      .slice(0, Math.max(0, remaining.length - maxEntries))
      .forEach((item) => sessionStorage.removeItem(item));
  } catch {
    // Storage can be unavailable in private browsing; online behavior continues.
  }
}

export function readCachedEventData<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(`${prefix}${key}`);
    if (!raw) return null;
    const cached = JSON.parse(raw) as CachedValue<T>;
    if (new Date(cached.expires_at).getTime() < Date.now()) {
      sessionStorage.removeItem(`${prefix}${key}`);
      return null;
    }
    return cached.value;
  } catch {
    return null;
  }
}

export function clearEventOfflineCache() {
  try {
    const keys = Array.from({ length: sessionStorage.length }, (_, index) =>
      sessionStorage.key(index),
    ).filter((key): key is string => Boolean(key?.startsWith(prefix)));
    keys.forEach((key) => sessionStorage.removeItem(key));
  } catch {
    // There is nothing to clear when session storage is unavailable.
  }
}

export function clearEventOfflineAssets() {
  if (typeof navigator !== "undefined" && "serviceWorker" in navigator) {
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
  if (typeof caches !== "undefined") {
    void caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith("btsp-event-shell-"))
            .map((key) => caches.delete(key)),
        ),
      );
  }
}

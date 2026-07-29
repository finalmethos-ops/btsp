"use client";

import { useEffect } from "react";

export function EventOfflineRegistration() {
  useEffect(() => {
    if (!("serviceWorker" in navigator) || !window.isSecureContext) return;
    // Offline caching is useful in production, but stale service workers are
    // especially disruptive during local UI development. Remove any previous
    // event worker on localhost so Next.js always serves the current bundle.
    const localHost = ["localhost", "127.0.0.1", "::1"].includes(
      window.location.hostname,
    );
    if (localHost) {
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
      return;
    }
    void navigator.serviceWorker
      .register("/event-sw.js", { scope: "/", updateViaCache: "none" })
      .then(async (registration) => {
        const worker =
          registration.active ??
          registration.waiting ??
          registration.installing;
        if (!worker) return;
        const resources = performance
          .getEntriesByType("resource")
          .map((entry) => entry.name)
          .filter((url) => url.startsWith(window.location.origin));
        worker.postMessage({
          type: "CACHE_EVENT_SHELL",
          urls: [window.location.href, ...resources],
        });
      })
      .catch(() => undefined);
  }, []);

  return null;
}

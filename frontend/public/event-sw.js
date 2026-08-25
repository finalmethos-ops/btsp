// Bump this when shell/UI assets change so returning event users do not stay
// on a stale cached login or calendar bundle.
const cacheName = "btsp-event-shell-v3";
const maxCacheEntries = 100;
const shellUrls = [
  "/events/calendar",
  "/event-login",
  "/brand/buddys-logo-compact.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(cacheName)
      .then((cache) =>
        Promise.allSettled(shellUrls.map((url) => cache.add(url))),
      )
      .then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key.startsWith("btsp-event-shell-") && key !== cacheName)
            .map((key) => caches.delete(key)),
        ),
      )
      .then(() => self.clients.claim()),
  );
});

function cacheable(url) {
  return (
    url.origin === self.location.origin &&
    (url.pathname.startsWith("/brand/") ||
      url.pathname === "/events/calendar" ||
      url.pathname === "/event-login" ||
      url.pathname === "/messages")
  );
}

async function trimCache() {
  const cache = await caches.open(cacheName);
  const requests = await cache.keys();
  await Promise.all(requests.slice(0, Math.max(0, requests.length - maxCacheEntries)).map((request) => cache.delete(request)));
}

self.addEventListener("message", (event) => {
  if (event.data?.type !== "CACHE_EVENT_SHELL") return;
  const urls = (event.data.urls ?? []).filter((value) => {
    try {
      return cacheable(new URL(value, self.location.origin));
    } catch {
      return false;
    }
  });
  event.waitUntil(
    caches
      .open(cacheName)
      .then((cache) => Promise.allSettled(urls.map((url) => cache.add(url)))),
  );
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  const url = new URL(event.request.url);
  if (!cacheable(url)) return;

  if (url.pathname.startsWith("/brand/")) {
    event.respondWith(
      caches.match(event.request).then(
        (cached) =>
          cached ||
          fetch(event.request).then((response) => {
            if (response.ok) {
              const copy = response.clone();
              void caches.open(cacheName).then((cache) => cache.put(event.request, copy)).then(trimCache);
            }
            return response;
          }),
      ),
    );
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response.ok) {
          const copy = response.clone();
          void caches.open(cacheName).then((cache) => cache.put(event.request, copy)).then(trimCache);
        }
        return response;
      })
      .catch(async () =>
        (await caches.match(event.request)) ||
        (await caches.match("/events/calendar")) ||
        Response.error(),
      ),
  );
});

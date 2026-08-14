/**
 * public/sw.js
 * ==============
 * Minimal offline support: runtime, network-first caching for the app
 * shell and static assets, so the generator/passphrase/vault tabs keep
 * working after the first visit even with no connection. Deliberately
 * does NOT cache /api/breach-check responses -- breach data must always
 * be live, and failing offline (with a clear error in the UI) is the
 * correct behavior for that one network-dependent feature.
 */

const CACHE_NAME = "securepass-shell-v1";

self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);

  // Never cache API calls -- breach data must be live.
  if (url.pathname.startsWith("/api/")) return;

  // Only handle same-origin GET requests.
  if (event.request.method !== "GET" || url.origin !== self.location.origin) return;

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        const clone = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        return response;
      })
      .catch(() => caches.match(event.request))
  );
});

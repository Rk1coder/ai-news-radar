// shortcut: cache-first for a fixed static asset list; no versioned cache busting beyond CACHE_NAME —
// bump CACHE_NAME when any cached file's content changes meaningfully.
const CACHE_NAME = "radar-static-v1";
const ASSETS = [
  "/styles.css",
  "/app.js",
  "/chat-state.js",
  "/live-feed.js",
  "/settings.js",
  "/manifest.webmanifest",
  "/radar.svg",
  "/radar-favicon.svg",
  "/radar-logo.png",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)));
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
});

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  if (!ASSETS.includes(url.pathname)) return; // leave /, /refresh, /settings-api/*, etc. to the network

  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        const copy = response.clone();
        caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        return response;
      });
    })
  );
});

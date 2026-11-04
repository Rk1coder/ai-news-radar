// shortcut: cache-first for a fixed static asset list; no versioned cache busting beyond CACHE_NAME —
// bump CACHE_NAME when any cached file's content changes meaningfully.
const CACHE_NAME = "ai-news-static-v8";
const ASSETS = [
  "/styles.css",
  "/app.js",
  "/chat-state.js",
  "/live-feed.js",
  "/settings.js",
  "/settings-motion.js",
  "/scan-program.js",
  "/assistant-motion.js",
  "/vendor/gsap.min.js",
  "/manifest.webmanifest",
  "/fonts/inter-latin.woff2",
  "/fonts/inter-latin-ext.woff2",
  "/fonts/source-serif-4-latin.woff2",
  "/fonts/source-serif-4-latin-ext.woff2",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => cache.addAll(ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    ).then(() => self.clients.claim())
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

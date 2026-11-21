/**
 * sw.js — Basic Service Worker for Bolta Khata PWA.
 * Provides offline caching:
 * - Cache-first strategy for static UI assets (HTML, CSS, JS, manifest, icons)
 * - Network-first strategy for API calls and dynamic endpoints
 */

const CACHE_NAME = "bolta-khata-v1";

const STATIC_ASSETS = [
  "./",
  "./index.html",
  "./dashboard.html",
  "./customers.html",
  "./voice.html",
  "./history.html",
  "./css/style.css",
  "./js/storage.js",
  "./js/api.js",
  "./js/offline.js",
  "./js/app.js",
  "./js/lang.js",
  "./js/auth.js",
  "./js/customers.js",
  "./js/history.js",
  "./js/voice.js",
  "./manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png"
];

// Install Event: pre-cache static assets
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("[SW] Pre-caching static assets for offline access");
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn("[SW] Cache addAll warning:", err);
      });
    }).then(() => self.skipWaiting())
  );
});

// Activate Event: clean up any older cache versions
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            console.log("[SW] Removing old cache:", key);
            return caches.delete(key);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch Event: apply network-first for APIs, cache-first for static assets
self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);

  // Skip WebSocket connections and non-GET requests
  if (request.method !== "GET" || url.protocol.startsWith("ws")) {
    return;
  }

  // Network-first for API requests
  const isApiRequest = url.pathname.includes("/api/") ||
                       url.pathname.includes("/auth/") ||
                       url.pathname.includes("/customers") ||
                       url.pathname.includes("/summary/") ||
                       url.pathname.includes("/sync/");

  if (isApiRequest) {
    event.respondWith(
      fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return networkResponse;
        })
        .catch(() => {
          // Fallback to cache if network is offline
          return caches.match(request);
        })
    );
    return;
  }

  // Cache-first for static assets (HTML, JS, CSS, images)
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        // Return cached version immediately and update cache in background
        fetch(request)
          .then((networkResponse) => {
            if (networkResponse && networkResponse.status === 200) {
              caches.open(CACHE_NAME).then((cache) => cache.put(request, networkResponse));
            }
          })
          .catch(() => {
            // Network offline, cached version was already returned
          });
        return cachedResponse;
      }

      // If not in cache, fetch from network
      return fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(request, clone));
          }
          return networkResponse;
        })
        .catch(() => {
          // If HTML navigation fails offline, fallback to dashboard or index
          if (request.mode === "navigate") {
            return caches.match("./dashboard.html") || caches.match("./index.html");
          }
        });
    })
  );
});

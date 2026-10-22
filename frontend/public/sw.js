// Service Worker for HospitalIQ Frontend
// Provides offline support and caching for static assets

const CACHE_NAME = 'hospitaliq-v1';
const STATIC_CACHE = 'hospitaliq-static-v1';
const API_CACHE = 'hospitaliq-api-v1';

// Static assets to cache immediately
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/states.json',
  '/favicon.svg',
  '/icons.svg',
];

// API endpoints to cache
const CACHEABLE_API_PATTERNS = [
  '/api/v1/states',
  '/api/v1/districts',
  '/api/v1/stats',
];

// Install event - cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then((cache) => {
      return cache.addAll(STATIC_ASSETS);
    })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames
          .filter((cacheName) => {
            return (
              cacheName !== STATIC_CACHE &&
              cacheName !== API_CACHE &&
              cacheName !== CACHE_NAME
            );
          })
          .map((cacheName) => {
            return caches.delete(cacheName);
          })
      );
    })
  );
});

// Fetch event - serve from cache when offline
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Handle static assets
  if (STATIC_ASSETS.some(asset => url.pathname === asset || url.pathname.endsWith(asset))) {
    event.respondWith(
      caches.match(event.request).then((response) => {
        if (response) {
          return response;
        }
        return fetch(event.request).then((response) => {
          const responseClone = response.clone();
          caches.open(STATIC_CACHE).then((cache) => {
            cache.put(event.request, responseClone);
          });
          return response;
        });
      })
    );
    return;
  }

  // Handle API requests
  if (url.pathname.startsWith('/api/')) {
    const isCacheable = CACHEABLE_API_PATTERNS.some(pattern => 
      url.pathname.includes(pattern)
    );

    if (isCacheable && event.request.method === 'GET') {
      event.respondWith(
        caches.match(event.request).then((response) => {
          if (response) {
            // Serve from cache, but fetch in background
            fetch(event.request).then((networkResponse) => {
              const networkClone = networkResponse.clone();
              caches.open(API_CACHE).then((cache) => {
                cache.put(event.request, networkClone);
              });
            });
            return response;
          }

          return fetch(event.request).then((networkResponse) => {
            const networkClone = networkResponse.clone();
            caches.open(API_CACHE).then((cache) => {
              cache.put(event.request, networkClone);
            });
            return networkResponse;
          });
        })
      );
      return;
    }
  }

  // Default: network first, fallback to cache
  event.respondWith(
    fetch(event.request).catch(() => {
      return caches.match(event.request);
    })
  );
});

// Skip waiting for immediate activation
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }
});

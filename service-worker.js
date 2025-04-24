const CACHE_NAME = 'ove-cache-v1';
const urlsToCache = [
  '/',
  '/index.html',
  '/app.js',
  '/style.css',
  '/V192.png',
  '/V512.png'
];

// Installera service worker och cacha resurser
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('Öppnade cache');
        return cache.addAll(urlsToCache);
      })
  );
});

// Hämta resurser från cachen
self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Returnera cachen om resursen finns där, annars hämta från nätverket
        return response || fetch(event.request);
      })
  );
});

// Uppdatera service worker och rensa gammal cache
self.addEventListener('activate', event => {
  const cacheWhitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (!cacheWhitelist.includes(cacheName)) {
            return caches.delete(cacheName);
          }
        })
      );
    })
  );
});

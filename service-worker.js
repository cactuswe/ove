const CACHE_NAME = 'ove-cache-v2';
const urlsToCache = [
  '/',
  '/index.html',
  '/app.js',
  '/style.css',
  '/manifest.json',
  '/V.png',
  '/V192.png',
  '/V512.png',
  '/ove-face.svg'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(resp => resp || fetch(event.request))
  );
});

self.addEventListener('activate', event => {
  const whitelist = [CACHE_NAME];
  event.waitUntil(
    caches.keys().then(names =>
      Promise.all(
        names.map(n => !whitelist.includes(n) ? caches.delete(n) : null)
      )
    )
  );
});

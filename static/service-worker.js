const CACHE_NAME = "kasir-cache-v1";
const urlsToCache = [
  "/",
  "/static/css/style.css",
  "/static/icons/icon-192.png",
  "/static/icons/icon-512.png",
  "/static/js/app.js",
  "/static/js/nota-utils.js",
  "/static/js/ua-parser.min.js",
  "/static/js/esc-pos-encoder.min.js",
];

// Install Service Worker dan cache aset
self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log("📦 Caching app shell");
      return cache.addAll(urlsToCache);
    })
  );
});

// Activate: hapus cache lama kalau ada
self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) =>
      Promise.all(
        cacheNames.map((name) => {
          if (name !== CACHE_NAME) {
            console.log("🧹 Deleting old cache:", name);
            return caches.delete(name);
          }
        })
      )
    )
  );
});

// Fetch: coba dari network, kalau gagal fallback ke cache
self.addEventListener("fetch", (event) => {
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
}); 
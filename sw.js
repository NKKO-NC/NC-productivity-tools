const CACHE_NAME = "nc-productivity-tools-v1";
const APP_SHELL = [
  "./",
  "./index.html",
  "./README.md",
  "./manifest.webmanifest",
  "./assets/css/site.css",
  "./assets/js/home.js",
  "./assets/js/i18n.js",
  "./assets/js/pwa.js",
  "./assets/icons/app-icon.svg",
  "./tools/excel-column-helper/",
  "./tools/excel-column-helper/index.html",
  "./tools/excel-column-helper/app.js"
];

function toAbsoluteUrl(path) {
  return new URL(path, self.registration.scope).toString();
}

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL.map(toAbsoluteUrl)))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.map((key) => {
          if (key !== CACHE_NAME) {
            return caches.delete(key);
          }

          return Promise.resolve();
        })
      )
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") {
    return;
  }

  const requestUrl = new URL(event.request.url);
  if (requestUrl.origin !== self.location.origin) {
    return;
  }

  event.respondWith(
    fetch(event.request)
      .then((response) => {
        if (response && response.status === 200) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, responseClone));
        }

        return response;
      })
      .catch(async () => {
        const cached = await caches.match(event.request, { ignoreSearch: true });
        if (cached) {
          return cached;
        }

        if (event.request.mode === "navigate") {
          return caches.match(toAbsoluteUrl("./index.html"));
        }

        return new Response("Offline", {
          status: 503,
          statusText: "Offline",
          headers: { "Content-Type": "text/plain; charset=utf-8" }
        });
      })
  );
});

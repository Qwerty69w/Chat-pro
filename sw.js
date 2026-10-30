const MEDIA_CACHE_NAME = "chat-pro-media-v1";

function isCacheableMedia(request) {
  const url = new URL(request.url);
  return request.method === "GET" && url.origin === self.location.origin && url.pathname.startsWith("/media/messages/");
}

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
self.addEventListener("message", (event) => {
  if (event.data?.type === "clear-media-cache") event.waitUntil(caches.delete(MEDIA_CACHE_NAME));
});
self.addEventListener("fetch", (event) => {
  if (!isCacheableMedia(event.request)) return;
  event.respondWith((async () => {
    const cache = await caches.open(MEDIA_CACHE_NAME);
    const cached = await cache.match(event.request);
    if (cached) return cached;
    const response = await fetch(event.request);
    if (response.ok || response.type === "opaque") cache.put(event.request, response.clone());
    return response;
  })());
});

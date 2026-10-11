import { cleanupOutdatedCaches, matchPrecache, precacheAndRoute } from 'workbox-precaching'
import { registerRoute } from 'workbox-routing'

// Workbox injects an explicit build-time list of static assets only.
// There are no runtime caches and no API/OAuth fetch handlers.
precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

registerRoute(
  ({ request, url }) => request.mode === 'navigate'
    && url.origin === self.location.origin
    && !/^\/api(?:\/|$)/.test(url.pathname),
  async ({ request }) => {
    try {
      return await fetch(request, { cache: 'no-store' })
    } catch {
      return await matchPrecache('/offline.html')
        || new Response('Moniq needs an internet connection.', { status: 503 })
    }
  },
)

// Updates wait for all existing app windows to close; no forced reload while editing.
// Explicitly configured runtime financial functionality always requires the backend.

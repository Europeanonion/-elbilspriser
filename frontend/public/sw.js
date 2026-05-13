const CACHE = 'elbilspriser-v1'
const SHELL = ['/', '/map', '/beregner']

self.addEventListener('install', e => e.waitUntil(
  caches.open(CACHE).then(c => c.addAll(SHELL))
))

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url)
  if (url.pathname.startsWith('/api/v1/')) {
    e.respondWith(fetch(e.request).catch(() => caches.match(e.request) ?? new Response('{}', { headers: { 'Content-Type': 'application/json' } })))
  } else {
    e.respondWith(caches.match(e.request).then(r => r ?? fetch(e.request)))
  }
})

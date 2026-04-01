// Service Worker mínimo — solo para activar PWA (sin cache offline)
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (e) => e.waitUntil(self.clients.claim()))

/* service_worker.js — Monitor de Câmbio PWA */

const CACHE_NAME  = "cambio-monitor-v1";
const STATIC_URLS = ["/", "/static/css/", "/favicon.ico"];

// ── Instalação: pré-cache de recursos estáticos ──────────────────────────
self.addEventListener("install", (event) => {
    event.waitUntil(
        caches.open(CACHE_NAME).then((cache) => {
            console.log("[SW] Pré-cacheando recursos");
            return cache.addAll(STATIC_URLS).catch(() => {
                // Ignora erros de recursos não disponíveis offline
            });
        })
    );
    self.skipWaiting();
});

// ── Ativação: remove caches antigos ─────────────────────────────────────
self.addEventListener("activate", (event) => {
    event.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(
                keys
                    .filter((key) => key !== CACHE_NAME)
                    .map((key) => caches.delete(key))
            )
        )
    );
    self.clients.claim();
});

// ── Intercepta requisições ───────────────────────────────────────────────
self.addEventListener("fetch", (event) => {
    const url = new URL(event.request.url);

    // APIs de câmbio: sempre tenta rede, sem cache (dados em tempo real)
    if (
        url.hostname.includes("exchangerate-api") ||
        url.hostname.includes("awesomeapi") ||
        url.hostname.includes("newsapi") ||
        url.hostname.includes("googleapis") ||
        url.hostname.includes("api.telegram")
    ) {
        event.respondWith(fetch(event.request));
        return;
    }

    // Recursos estáticos: cache-first
    event.respondWith(
        caches.match(event.request).then((cached) => {
            if (cached) return cached;
            return fetch(event.request).then((response) => {
                // Cacheia apenas respostas válidas de recursos estáticos
                if (
                    response &&
                    response.status === 200 &&
                    response.type === "basic" &&
                    !url.pathname.startsWith("/api/")
                ) {
                    const clone = response.clone();
                    caches.open(CACHE_NAME).then((cache) =>
                        cache.put(event.request, clone)
                    );
                }
                return response;
            }).catch(() => {
                // Offline: retorna página de fallback se disponível
                return caches.match("/") || new Response(
                    "<h2>📵 Sem conexão</h2><p>Verifique sua internet para ver cotações atualizadas.</p>",
                    { headers: { "Content-Type": "text/html" } }
                );
            });
        })
    );
});

// ── Push Notifications (web push) ───────────────────────────────────────
self.addEventListener("push", (event) => {
    const data = event.data ? event.data.json() : {};
    const title = data.title || "🚨 Alerta de Câmbio";
    const options = {
        body:    data.body    || "Sua moeda atingiu o valor configurado!",
        icon:    data.icon    || "/favicon.ico",
        badge:   data.badge   || "/favicon.ico",
        tag:     data.tag     || "cambio-alert",
        vibrate: [200, 100, 200],
        data:    { url: data.url || "/" },
        actions: [
            { action: "open",    title: "Ver painel" },
            { action: "dismiss", title: "Dispensar"  },
        ],
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener("notificationclick", (event) => {
    event.notification.close();
    if (event.action === "open" || !event.action) {
        const url = event.notification.data?.url || "/";
        event.waitUntil(clients.openWindow(url));
    }
});

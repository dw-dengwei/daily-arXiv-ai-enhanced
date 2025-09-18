const CACHE_VERSION = "2.0.0";
const CACHE_NAME = `daily-arxiv-v${CACHE_VERSION}`;
const RUNTIME_CACHE = `runtime-${CACHE_VERSION}`;
const DATA_CACHE = `data-${CACHE_VERSION}`;

// 核心应用资源 - 优先缓存
const CORE_CACHE_URLS = [
  "/",
  "/index.html",
  "/settings.html",
  "/statistic.html",
  "/css/styles.css",
  "/css/settings.css",
  "/css/statistic.css",
  "/js/app.js",
  "/js/settings.js",
  "/js/statistic.js",
  "/manifest.json",
];

// 静态资源 - 可选缓存
const STATIC_CACHE_URLS = [
  "/assets/logo2-removebg-preview.png",
  "/assets/logo2-white.png",
  "/icons/icon-192.png",
  "/icons/icon-512.png",
  "/icons/maskable-192.png",
  "/icons/maskable-512.png",
];

// 数据文件模式 - 动态缓存
const DATA_PATTERNS = [
  /\/data\/.*\.jsonl$/,
  /\/data\/.*\.md$/,
  /\/assets\/file-list\.txt$/,
];

// 外部资源模式 - 网络优先
const EXTERNAL_PATTERNS = [
  /^https:\/\/fonts\.googleapis\.com/,
  /^https:\/\/cdn\.jsdelivr\.net/,
  /^https:\/\/arxiv\.org/,
];

// 安装事件 - 缓存核心资源
self.addEventListener("install", (event) => {
  console.log("[SW] Installing service worker");
  event.waitUntil(
    Promise.all([
      // 缓存核心应用资源
      caches.open(CACHE_NAME).then((cache) => {
        console.log("[SW] Caching core app resources");
        return cache.addAll(CORE_CACHE_URLS);
      }),
      // 预缓存静态资源（失败不影响安装）
      caches.open(CACHE_NAME).then((cache) => {
        console.log("[SW] Pre-caching static resources");
        return Promise.allSettled(
          STATIC_CACHE_URLS.map((url) =>
            cache
              .add(url)
              .catch((err) => console.warn("[SW] Failed to cache:", url, err)),
          ),
        );
      }),
    ]).then(() => {
      console.log("[SW] Installation complete");
      return self.skipWaiting();
    }),
  );
});

// 激活事件 - 清理旧缓存
self.addEventListener("activate", (event) => {
  console.log("[SW] Activating service worker");
  event.waitUntil(
    caches
      .keys()
      .then((cacheNames) => {
        return Promise.all([
          // 删除旧版本缓存
          ...cacheNames
            .filter(
              (cacheName) =>
                cacheName.startsWith("daily-arxiv-") &&
                cacheName !== CACHE_NAME &&
                !cacheName.includes(CACHE_VERSION),
            )
            .map((cacheName) => {
              console.log("[SW] Deleting old cache:", cacheName);
              return caches.delete(cacheName);
            }),
          // 清理运行时缓存
          ...cacheNames
            .filter(
              (cacheName) =>
                cacheName.startsWith("runtime-") && cacheName !== RUNTIME_CACHE,
            )
            .map((cacheName) => {
              console.log("[SW] Deleting old runtime cache:", cacheName);
              return caches.delete(cacheName);
            }),
          // 清理数据缓存
          ...cacheNames
            .filter(
              (cacheName) =>
                cacheName.startsWith("data-") && cacheName !== DATA_CACHE,
            )
            .map((cacheName) => {
              console.log("[SW] Deleting old data cache:", cacheName);
              return caches.delete(cacheName);
            }),
        ]);
      })
      .then(() => {
        console.log("[SW] Activation complete");
        return self.clients.claim();
      }),
  );
});

// 请求拦截 - 智能缓存策略
self.addEventListener("fetch", (event) => {
  const { request } = event;
  const { url, method } = request;

  // 只处理GET请求
  if (method !== "GET") return;

  // 跳过chrome扩展等非http(s)请求
  if (!url.startsWith("http")) return;

  event.respondWith(handleFetch(request));
});

// 智能请求处理函数
async function handleFetch(request) {
  const { url } = request;

  try {
    // 1. 导航请求 - 网络优先，缓存回退
    if (request.mode === "navigate") {
      return await handleNavigationRequest(request);
    }

    // 2. 数据文件 - 网络优先，缓存回退，智能更新
    if (isDataRequest(url)) {
      return await handleDataRequest(request);
    }

    // 3. 外部资源 - 网络优先，短期缓存
    if (isExternalRequest(url)) {
      return await handleExternalRequest(request);
    }

    // 4. 静态资源 - 缓存优先，网络更新
    return await handleStaticRequest(request);
  } catch (error) {
    console.error("[SW] Fetch error:", error);
    return await getFallbackResponse(request);
  }
}

// 处理导航请求
async function handleNavigationRequest(request) {
  try {
    // 网络优先
    const response = await fetchWithTimeout(request, 3000);

    // 缓存成功的导航响应
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    // 网络失败时使用缓存
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }

    // 返回默认页面
    const defaultResponse = await caches.match("/");
    if (defaultResponse) {
      return defaultResponse;
    }

    // 最后的离线页面
    return createOfflineResponse();
  }
}

// 处理数据请求
async function handleDataRequest(request) {
  const cache = await caches.open(DATA_CACHE);

  try {
    // 尝试网络请求
    const response = await fetchWithTimeout(request, 5000);

    if (response.ok) {
      // 缓存新数据
      cache.put(request, response.clone());
      return response;
    } else {
      throw new Error(`Network response not ok: ${response.status}`);
    }
  } catch (error) {
    console.log("[SW] Network failed for data, trying cache:", request.url);

    // 网络失败时使用缓存
    const cachedResponse = await cache.match(request);
    if (cachedResponse) {
      // 在后台尝试更新缓存
      updateCacheInBackground(request, cache);
      return cachedResponse;
    }

    throw error;
  }
}

// 处理外部资源请求
async function handleExternalRequest(request) {
  const cache = await caches.open(RUNTIME_CACHE);

  try {
    const response = await fetchWithTimeout(request, 8000);

    if (response.ok) {
      // 短期缓存外部资源（1小时）
      const responseToCache = response.clone();
      responseToCache.headers = new Headers(responseToCache.headers);
      responseToCache.headers.set("sw-cached-at", Date.now().toString());

      cache.put(request, responseToCache);
    }

    return response;
  } catch (error) {
    const cachedResponse = await cache.match(request);

    if (cachedResponse) {
      // 检查缓存是否过期（1小时）
      const cachedAt = cachedResponse.headers.get("sw-cached-at");
      const isExpired = cachedAt && Date.now() - parseInt(cachedAt) > 3600000;

      if (!isExpired) {
        return cachedResponse;
      }
    }

    throw error;
  }
}

// 处理静态资源请求
async function handleStaticRequest(request) {
  // 缓存优先
  const cachedResponse = await caches.match(request);

  if (cachedResponse) {
    // 在后台更新缓存
    updateCacheInBackground(request, await caches.open(CACHE_NAME));
    return cachedResponse;
  }

  // 缓存未命中时尝试网络
  try {
    const response = await fetchWithTimeout(request, 5000);

    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }

    return response;
  } catch (error) {
    console.error("[SW] Failed to fetch static resource:", request.url);
    throw error;
  }
}

// 后台更新缓存
async function updateCacheInBackground(request, cache) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      await cache.put(request, response.clone());
      console.log("[SW] Background cache update successful:", request.url);
    }
  } catch (error) {
    console.log("[SW] Background cache update failed:", request.url, error);
  }
}

// 带超时的fetch
function fetchWithTimeout(request, timeout = 5000) {
  return Promise.race([
    fetch(request),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error("Fetch timeout")), timeout),
    ),
  ]);
}

// 判断是否为数据请求
function isDataRequest(url) {
  return DATA_PATTERNS.some((pattern) => pattern.test(url));
}

// 判断是否为外部请求
function isExternalRequest(url) {
  const requestUrl = new URL(url);
  const isExternal = requestUrl.origin !== self.location.origin;
  const matchesPattern = EXTERNAL_PATTERNS.some((pattern) => pattern.test(url));
  return isExternal || matchesPattern;
}

// 获取回退响应
async function getFallbackResponse(request) {
  // 尝试从任何缓存中获取
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }

  // 如果是导航请求，返回主页
  if (request.mode === "navigate") {
    const homeResponse = await caches.match("/");
    if (homeResponse) {
      return homeResponse;
    }
  }

  // 创建离线响应
  return createOfflineResponse();
}

// 创建离线响应
function createOfflineResponse() {
  const html = `
    <!DOCTYPE html>
    <html>
    <head>
      <title>离线模式 - Daily arXiv AI Enhanced</title>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <style>
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          display: flex;
          justify-content: center;
          align-items: center;
          height: 100vh;
          margin: 0;
          background: #f5f5f5;
          color: #333;
        }
        .offline-container {
          text-align: center;
          max-width: 400px;
          padding: 2rem;
          background: white;
          border-radius: 12px;
          box-shadow: 0 2px 20px rgba(0,0,0,0.1);
        }
        .offline-icon {
          font-size: 4rem;
          margin-bottom: 1rem;
        }
        .offline-title {
          font-size: 1.5rem;
          margin-bottom: 1rem;
          color: #2196f3;
        }
        .offline-message {
          margin-bottom: 2rem;
          line-height: 1.6;
          color: #666;
        }
        .retry-button {
          background: #2196f3;
          color: white;
          border: none;
          padding: 12px 24px;
          border-radius: 6px;
          cursor: pointer;
          font-size: 1rem;
        }
        .retry-button:hover {
          background: #1976d2;
        }
      </style>
    </head>
    <body>
      <div class="offline-container">
        <div class="offline-icon">📱</div>
        <h1 class="offline-title">离线模式</h1>
        <p class="offline-message">
          您当前处于离线状态。请检查网络连接后重试。
          <br><br>
          已缓存的论文数据仍可正常浏览。
        </p>
        <button class="retry-button" onclick="window.location.reload()">
          重新加载
        </button>
      </div>
    </body>
    </html>
  `;

  return new Response(html, {
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Cache-Control": "no-cache",
    },
  });
}

// 消息处理 - 与主线程通信
self.addEventListener("message", (event) => {
  const { type, data } = event.data;

  switch (type) {
    case "SKIP_WAITING":
      self.skipWaiting();
      break;

    case "GET_VERSION":
      event.ports[0].postMessage({ version: CACHE_VERSION });
      break;

    case "CLEAR_CACHE":
      clearAllCaches().then(() => {
        event.ports[0].postMessage({ success: true });
      });
      break;

    case "PREFETCH_DATA":
      if (data && data.urls) {
        prefetchUrls(data.urls);
      }
      break;
  }
});

// 清理所有缓存
async function clearAllCaches() {
  const cacheNames = await caches.keys();
  const deletePromises = cacheNames
    .filter((name) => name.startsWith("daily-arxiv-"))
    .map((name) => caches.delete(name));

  return Promise.all(deletePromises);
}

// 预取URL
async function prefetchUrls(urls) {
  const cache = await caches.open(DATA_CACHE);
  const prefetchPromises = urls.map((url) => {
    return fetch(url)
      .then((response) => {
        if (response.ok) {
          return cache.put(url, response);
        }
      })
      .catch((error) => console.log("[SW] Prefetch failed:", url, error));
  });

  return Promise.allSettled(prefetchPromises);
}

// 推送通知处理
self.addEventListener("push", (event) => {
  if (!event.data) return;

  try {
    const data = event.data.json();
    const options = {
      body: data.body || "发现新的arXiv论文摘要",
      icon: "/icons/icon-192.png",
      badge: "/icons/icon-192.png",
      data: data.url || "/",
      actions: [
        {
          action: "view",
          title: "查看",
        },
        {
          action: "dismiss",
          title: "忽略",
        },
      ],
    };

    event.waitUntil(
      self.registration.showNotification(
        data.title || "Daily arXiv AI Enhanced",
        options,
      ),
    );
  } catch (error) {
    console.error("[SW] Push notification error:", error);
  }
});

// 通知点击处理
self.addEventListener("notificationclick", (event) => {
  event.notification.close();

  if (event.action === "view" || !event.action) {
    const url = event.notification.data || "/";
    event.waitUntil(
      clients.matchAll({ type: "window" }).then((clientList) => {
        // 如果已有窗口打开，则聚焦到该窗口
        for (const client of clientList) {
          if (client.url.includes(self.location.origin) && "focus" in client) {
            client.navigate(url);
            return client.focus();
          }
        }

        // 否则打开新窗口
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      }),
    );
  }
});

console.log(`[SW] Service Worker ${CACHE_VERSION} loaded`);

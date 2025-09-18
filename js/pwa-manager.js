/**
 * PWA Manager - 管理Progressive Web App的安装、更新和离线功能
 * 版本: 2.0.0
 */

class PWAManager {
  constructor() {
    this.version = '2.0.0';
    this.swRegistration = null;
    this.deferredPrompt = null;
    this.isOnline = navigator.onLine;
    this.updateAvailable = false;

    // 配置选项
    this.options = {
      enableNotifications: false,
      enableBackgroundSync: true,
      enablePrefetch: true,
      updateCheckInterval: 30 * 60 * 1000, // 30分钟
      offlineMessage: {
        title: '离线模式',
        message: '您当前处于离线状态，已缓存的内容仍可正常使用。'
      }
    };

    this.init();
  }

  /**
   * 初始化PWA管理器
   */
  async init() {
    console.log('[PWA Manager] Initializing...');

    try {
      await this.registerServiceWorker();
      this.setupEventListeners();
      this.checkForUpdates();
      this.loadSettings();

      console.log('[PWA Manager] Initialized successfully');
    } catch (error) {
      console.error('[PWA Manager] Initialization failed:', error);
    }
  }

  /**
   * 注册Service Worker
   */
  async registerServiceWorker() {
    if (!('serviceWorker' in navigator)) {
      console.warn('[PWA Manager] Service Worker not supported');
      return;
    }

    try {
      const registration = await navigator.serviceWorker.register('/service-worker.js');
      this.swRegistration = registration;

      console.log('[PWA Manager] Service Worker registered successfully');

      // 监听Service Worker状态变化
      registration.addEventListener('updatefound', () => {
        this.handleUpdateFound(registration.installing);
      });

      // 检查是否有等待的Service Worker
      if (registration.waiting) {
        this.showUpdateAvailable();
      }

    } catch (error) {
      console.error('[PWA Manager] Service Worker registration failed:', error);
    }
  }

  /**
   * 设置事件监听器
   */
  setupEventListeners() {
    // 监听安装提示
    window.addEventListener('beforeinstallprompt', (e) => {
      console.log('[PWA Manager] Install prompt available');
      e.preventDefault();
      this.deferredPrompt = e;
      this.showInstallPrompt();
    });

    // 监听应用安装
    window.addEventListener('appinstalled', () => {
      console.log('[PWA Manager] App installed successfully');
      this.hideInstallPrompt();
      this.showToast('应用安装成功！', 'success');
    });

    // 监听网络状态变化
    window.addEventListener('online', () => {
      console.log('[PWA Manager] Back online');
      this.isOnline = true;
      this.hideOfflineIndicator();
      this.showToast('网络连接已恢复', 'success');
      this.syncWhenOnline();
    });

    window.addEventListener('offline', () => {
      console.log('[PWA Manager] Gone offline');
      this.isOnline = false;
      this.showOfflineIndicator();
      this.showToast('网络连接已断开，进入离线模式', 'warning');
    });

    // 监听页面可见性变化
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden && this.swRegistration) {
        this.checkForUpdates();
      }
    });

    // Service Worker消息监听
    navigator.serviceWorker?.addEventListener('message', (event) => {
      this.handleServiceWorkerMessage(event);
    });
  }

  /**
   * 处理Service Worker更新
   */
  handleUpdateFound(installingWorker) {
    console.log('[PWA Manager] New service worker found');

    installingWorker.addEventListener('statechange', () => {
      if (installingWorker.state === 'installed') {
        if (navigator.serviceWorker.controller) {
          // 有新版本可用
          this.updateAvailable = true;
          this.showUpdateAvailable();
        } else {
          // 首次安装
          console.log('[PWA Manager] Service worker installed for the first time');
        }
      }
    });
  }

  /**
   * 显示更新可用通知
   */
  showUpdateAvailable() {
    const updateBanner = this.createUpdateBanner();
    document.body.appendChild(updateBanner);

    // 自动隐藏横幅（可选）
    setTimeout(() => {
      if (updateBanner.parentNode) {
        this.hideUpdateBanner();
      }
    }, 10000);
  }

  /**
   * 创建更新横幅
   */
  createUpdateBanner() {
    const banner = document.createElement('div');
    banner.id = 'pwa-update-banner';
    banner.className = 'pwa-update-banner';

    banner.innerHTML = `
      <div class="pwa-banner-content">
        <div class="pwa-banner-icon">🔄</div>
        <div class="pwa-banner-text">
          <strong>新版本可用</strong>
          <p>发现应用更新，立即更新以获得最佳体验？</p>
        </div>
        <div class="pwa-banner-actions">
          <button class="pwa-btn pwa-btn-secondary" onclick="pwaManager.hideUpdateBanner()">稍后</button>
          <button class="pwa-btn pwa-btn-primary" onclick="pwaManager.applyUpdate()">立即更新</button>
        </div>
      </div>
    `;

    return banner;
  }

  /**
   * 应用更新
   */
  async applyUpdate() {
    if (!this.swRegistration?.waiting) {
      console.warn('[PWA Manager] No waiting service worker found');
      return;
    }

    try {
      // 通知Service Worker跳过等待
      this.swRegistration.waiting.postMessage({ type: 'SKIP_WAITING' });

      // 等待控制权转移
      await new Promise((resolve) => {
        const listener = () => {
          navigator.serviceWorker.removeEventListener('controllerchange', listener);
          resolve();
        };
        navigator.serviceWorker.addEventListener('controllerchange', listener);
      });

      this.hideUpdateBanner();
      this.showToast('更新完成！页面即将重新加载', 'success');

      // 重新加载页面
      setTimeout(() => window.location.reload(), 1000);

    } catch (error) {
      console.error('[PWA Manager] Update failed:', error);
      this.showToast('更新失败，请稍后重试', 'error');
    }
  }

  /**
   * 隐藏更新横幅
   */
  hideUpdateBanner() {
    const banner = document.getElementById('pwa-update-banner');
    if (banner) {
      banner.remove();
    }
  }

  /**
   * 显示安装提示
   */
  showInstallPrompt() {
    // 检查是否已经安装或已经显示过提示
    if (this.isInstalled() || localStorage.getItem('pwa-install-dismissed')) {
      return;
    }

    const installBanner = this.createInstallBanner();
    document.body.appendChild(installBanner);
  }

  /**
   * 创建安装横幅
   */
  createInstallBanner() {
    const banner = document.createElement('div');
    banner.id = 'pwa-install-banner';
    banner.className = 'pwa-install-banner';

    banner.innerHTML = `
      <div class="pwa-banner-content">
        <div class="pwa-banner-icon">📱</div>
        <div class="pwa-banner-text">
          <strong>安装应用</strong>
          <p>安装到主屏幕，获得原生应用般的体验</p>
        </div>
        <div class="pwa-banner-actions">
          <button class="pwa-btn pwa-btn-secondary" onclick="pwaManager.dismissInstallPrompt()">不了，谢谢</button>
          <button class="pwa-btn pwa-btn-primary" onclick="pwaManager.installApp()">立即安装</button>
        </div>
      </div>
    `;

    return banner;
  }

  /**
   * 安装应用
   */
  async installApp() {
    if (!this.deferredPrompt) {
      console.warn('[PWA Manager] No install prompt available');
      return;
    }

    try {
      this.deferredPrompt.prompt();
      const { outcome } = await this.deferredPrompt.userChoice;

      if (outcome === 'accepted') {
        console.log('[PWA Manager] User accepted install prompt');
      } else {
        console.log('[PWA Manager] User dismissed install prompt');
        localStorage.setItem('pwa-install-dismissed', 'true');
      }

      this.deferredPrompt = null;
      this.hideInstallPrompt();

    } catch (error) {
      console.error('[PWA Manager] Install failed:', error);
    }
  }

  /**
   * 忽略安装提示
   */
  dismissInstallPrompt() {
    localStorage.setItem('pwa-install-dismissed', 'true');
    this.hideInstallPrompt();
  }

  /**
   * 隐藏安装提示
   */
  hideInstallPrompt() {
    const banner = document.getElementById('pwa-install-banner');
    if (banner) {
      banner.remove();
    }
  }

  /**
   * 检查应用是否已安装
   */
  isInstalled() {
    return window.matchMedia('(display-mode: standalone)').matches ||
           window.navigator.standalone ||
           document.referrer.includes('android-app://');
  }

  /**
   * 显示离线指示器
   */
  showOfflineIndicator() {
    let indicator = document.getElementById('pwa-offline-indicator');

    if (!indicator) {
      indicator = document.createElement('div');
      indicator.id = 'pwa-offline-indicator';
      indicator.className = 'pwa-offline-indicator';
      indicator.innerHTML = `
        <div class="pwa-offline-content">
          <span class="pwa-offline-icon">📡</span>
          <span class="pwa-offline-text">离线模式</span>
        </div>
      `;
      document.body.appendChild(indicator);
    }

    indicator.style.display = 'flex';
  }

  /**
   * 隐藏离线指示器
   */
  hideOfflineIndicator() {
    const indicator = document.getElementById('pwa-offline-indicator');
    if (indicator) {
      indicator.style.display = 'none';
    }
  }

  /**
   * 显示Toast通知
   */
  showToast(message, type = 'info', duration = 3000) {
    const toast = document.createElement('div');
    toast.className = `pwa-toast pwa-toast-${type}`;
    toast.textContent = message;

    document.body.appendChild(toast);

    // 触发显示动画
    setTimeout(() => toast.classList.add('pwa-toast-show'), 100);

    // 自动隐藏
    setTimeout(() => {
      toast.classList.remove('pwa-toast-show');
      setTimeout(() => toast.remove(), 300);
    }, duration);
  }

  /**
   * 检查更新
   */
  async checkForUpdates() {
    if (!this.swRegistration) return;

    try {
      await this.swRegistration.update();
      console.log('[PWA Manager] Update check completed');
    } catch (error) {
      console.error('[PWA Manager] Update check failed:', error);
    }
  }

  /**
   * 联网时同步
   */
  async syncWhenOnline() {
    if (!this.isOnline) return;

    try {
      // 预取重要数据
      if (this.options.enablePrefetch) {
        await this.prefetchImportantData();
      }

      // 触发后台同步（如果支持）
      if ('sync' in window.ServiceWorkerRegistration.prototype) {
        await this.swRegistration.sync.register('background-sync');
      }

    } catch (error) {
      console.error('[PWA Manager] Sync failed:', error);
    }
  }

  /**
   * 预取重要数据
   */
  async prefetchImportantData() {
    try {
      // 获取文件列表
      const response = await fetch('/assets/file-list.txt');
      if (response.ok) {
        const fileList = await response.text();
        const files = fileList.split('\n').filter(line => line.trim());

        // 预取最新的几个数据文件
        const latestFiles = files
          .filter(file => file.includes('.jsonl'))
          .slice(-3)
          .map(file => `/data/${file}`);

        if (latestFiles.length > 0) {
          this.sendMessageToSW('PREFETCH_DATA', { urls: latestFiles });
        }
      }
    } catch (error) {
      console.error('[PWA Manager] Prefetch failed:', error);
    }
  }

  /**
   * 处理Service Worker消息
   */
  handleServiceWorkerMessage(event) {
    const { type, data } = event.data;

    switch (type) {
      case 'UPDATE_AVAILABLE':
        this.showUpdateAvailable();
        break;

      case 'CACHE_UPDATED':
        this.showToast('内容已更新', 'info', 2000);
        break;

      case 'SYNC_COMPLETE':
        console.log('[PWA Manager] Background sync completed');
        break;

      default:
        console.log('[PWA Manager] Unknown message type:', type);
    }
  }

  /**
   * 向Service Worker发送消息
   */
  sendMessageToSW(type, data = {}) {
    if (!navigator.serviceWorker.controller) {
      console.warn('[PWA Manager] No service worker controller');
      return;
    }

    navigator.serviceWorker.controller.postMessage({ type, data });
  }

  /**
   * 获取缓存信息
   */
  async getCacheInfo() {
    return new Promise((resolve) => {
      const channel = new MessageChannel();
      channel.port1.onmessage = (event) => resolve(event.data);
      this.sendMessageToSW('GET_CACHE_INFO', {}, [channel.port2]);
    });
  }

  /**
   * 清理缓存
   */
  async clearCache() {
    return new Promise((resolve) => {
      const channel = new MessageChannel();
      channel.port1.onmessage = (event) => {
        this.showToast('缓存已清理', 'success');
        resolve(event.data);
      };
      this.sendMessageToSW('CLEAR_CACHE', {}, [channel.port2]);
    });
  }

  /**
   * 加载设置
   */
  loadSettings() {
    const settings = JSON.parse(localStorage.getItem('pwa-settings') || '{}');
    this.options = { ...this.options, ...settings };
  }

  /**
   * 保存设置
   */
  saveSettings() {
    localStorage.setItem('pwa-settings', JSON.stringify(this.options));
  }

  /**
   * 获取应用状态
   */
  getAppStatus() {
    return {
      version: this.version,
      isOnline: this.isOnline,
      isInstalled: this.isInstalled(),
      updateAvailable: this.updateAvailable,
      swRegistered: !!this.swRegistration,
      settings: this.options
    };
  }

  /**
   * 启用通知
   */
  async enableNotifications() {
    if (!('Notification' in window)) {
      console.warn('[PWA Manager] Notifications not supported');
      return false;
    }

    try {
      const permission = await Notification.requestPermission();
      this.options.enableNotifications = permission === 'granted';
      this.saveSettings();
      return this.options.enableNotifications;
    } catch (error) {
      console.error('[PWA Manager] Notification permission failed:', error);
      return false;
    }
  }

  /**
   * 销毁PWA管理器
   */
  destroy() {
    // 清理事件监听器和定时器
    if (this.updateCheckTimer) {
      clearInterval(this.updateCheckTimer);
    }

    this.hideUpdateBanner();
    this.hideInstallPrompt();
    this.hideOfflineIndicator();
  }
}

// 创建全局PWA管理器实例
let pwaManager = null;

// 在DOM加载完成后初始化
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    pwaManager = new PWAManager();
    window.pwaManager = pwaManager;
  });
} else {
  pwaManager = new PWAManager();
  window.pwaManager = pwaManager;
}

// CSS样式
const pwaStyles = `
<style>
/* PWA横幅样式 */
.pwa-update-banner,
.pwa-install-banner {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  background: linear-gradient(135deg, #2196f3, #21cbf3);
  color: white;
  z-index: 10000;
  box-shadow: 0 2px 10px rgba(0,0,0,0.2);
  animation: pwaSlideDown 0.3s ease-out;
}

.pwa-banner-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.pwa-banner-icon {
  font-size: 24px;
  margin-right: 15px;
  flex-shrink: 0;
}

.pwa-banner-text {
  flex: 1;
  min-width: 0;
}

.pwa-banner-text strong {
  display: block;
  font-size: 16px;
  margin-bottom: 4px;
}

.pwa-banner-text p {
  margin: 0;
  font-size: 14px;
  opacity: 0.9;
}

.pwa-banner-actions {
  display: flex;
  gap: 10px;
  flex-shrink: 0;
}

.pwa-btn {
  padding: 8px 16px;
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 4px;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  background: transparent;
  color: white;
}

.pwa-btn-primary {
  background: rgba(255,255,255,0.2);
}

.pwa-btn:hover {
  background: rgba(255,255,255,0.3);
  transform: translateY(-1px);
}

/* 离线指示器样式 */
.pwa-offline-indicator {
  position: fixed;
  top: 20px;
  right: 20px;
  background: #ff9800;
  color: white;
  padding: 8px 16px;
  border-radius: 20px;
  font-size: 14px;
  z-index: 9999;
  box-shadow: 0 2px 10px rgba(0,0,0,0.2);
  animation: pwaFadeIn 0.3s ease-out;
}

.pwa-offline-content {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pwa-offline-icon {
  font-size: 16px;
}

/* Toast通知样式 */
.pwa-toast {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%) translateY(100px);
  background: #333;
  color: white;
  padding: 12px 20px;
  border-radius: 8px;
  font-size: 14px;
  z-index: 10001;
  opacity: 0;
  transition: all 0.3s ease-out;
  max-width: 90%;
  text-align: center;
}

.pwa-toast-show {
  opacity: 1;
  transform: translateX(-50%) translateY(0);
}

.pwa-toast-success {
  background: #4caf50;
}

.pwa-toast-warning {
  background: #ff9800;
}

.pwa-toast-error {
  background: #f44336;
}

.pwa-toast-info {
  background: #2196f3;
}

/* 动画 */
@keyframes pwaSlideDown {
  from {
    transform: translateY(-100%);
  }
  to {
    transform: translateY(0);
  }
}

@keyframes pwaFadeIn {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .pwa-banner-content {
    flex-direction: column;
    align-items: stretch;
    gap: 15px;
    padding: 15px;
  }

  .pwa-banner-text {
    text-align: center;
  }

  .pwa-banner-actions {
    justify-content: center;
  }

  .pwa-offline-indicator {
    top: 10px;
    right: 10px;
    left: 10px;
    text-align: center;
  }
}
</style>
`;

// 插入样式
if (document.head) {
  document.head.insertAdjacentHTML('beforeend', pwaStyles);
} else {
  document.addEventListener('DOMContentLoaded', () => {
    document.head.insertAdjacentHTML('beforeend', pwaStyles);
  });
}

export { PWAManager, pwaManager };

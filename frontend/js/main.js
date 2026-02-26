/**
 * main.js - 主入口文件
 */

/**
 * 应用初始化
 */
const App = {
  /**
   * 初始化应用
   */
  init() {
    this.initNavigation();
    this.initGlobalErrorHandler();
    this.checkHealth();
  },

  /**
   * 初始化导航
   */
  initNavigation() {
    const appLayout = document.querySelector('.app-layout');
    if (appLayout && typeof Nav !== 'undefined') {
      Nav.render(appLayout);

      // 移动端菜单按钮
      const pageHeader = document.querySelector('.page-header');
      if (pageHeader) {
        Nav.renderMobileMenuBtn(pageHeader);
      }
    }
  },

  /**
   * 初始化全局错误处理
   */
  initGlobalErrorHandler() {
    window.addEventListener('error', (event) => {
      console.error('Global error:', event.error);
      if (typeof Toast !== 'undefined') {
        Toast.error('发生错误，请刷新页面重试');
      }
    });

    window.addEventListener('unhandledrejection', (event) => {
      console.error('Unhandled rejection:', event.reason);
      if (typeof Toast !== 'undefined') {
        const message = event.reason?.message || '请求失败，请重试';
        Toast.error(message);
      }
    });
  },

  /**
   * 检查后端健康状态
   */
  async checkHealth() {
    try {
      const response = await fetch('/health');
      if (!response.ok) {
        console.warn('Backend health check failed');
      }
    } catch (e) {
      console.warn('Backend is not reachable:', e.message);
    }
  },

  /**
   * 页面跳转
   * @param {string} path - 路径
   */
  navigate(path) {
    window.location.href = path;
  },

  /**
   * 获取当前页面名称
   * @returns {string} 页面名称
   */
  getCurrentPage() {
    const path = window.location.pathname;
    if (path === '/' || path === '/index.html') return 'dashboard';
    const match = path.match(/\/(\w+)/);
    return match ? match[1] : 'unknown';
  },
};

// DOM 加载完成后初始化
document.addEventListener('DOMContentLoaded', () => {
  App.init();
});

window.App = App;

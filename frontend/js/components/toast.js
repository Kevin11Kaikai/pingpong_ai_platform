/**
 * toast.js - 消息提示组件
 */

const Toast = {
  /**
   * 容器元素
   */
  container: null,

  /**
   * 默认配置
   */
  defaultOptions: {
    duration: 3000,
    position: 'top-right',
  },

  /**
   * 图标 SVG
   */
  icons: {
    success: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
    error: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`,
    warning: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`,
    info: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`,
  },

  /**
   * 初始化
   */
  init() {
    if (this.container) return;

    this.container = document.createElement('div');
    this.container.className = 'toast-container';
    this.container.style.cssText = `
      position: fixed;
      top: 20px;
      right: 20px;
      z-index: var(--z-toast, 800);
      display: flex;
      flex-direction: column;
      gap: 8px;
      pointer-events: none;
    `;
    document.body.appendChild(this.container);
  },

  /**
   * 显示提示
   * @param {string} message - 消息内容
   * @param {string} type - 类型 (success/error/warning/info)
   * @param {Object} options - 配置选项
   */
  show(message, type = 'info', options = {}) {
    this.init();

    const { duration } = { ...this.defaultOptions, ...options };

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.style.cssText = `
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      background-color: var(--card-bg, #fff);
      border-radius: var(--radius, 8px);
      box-shadow: var(--shadow-lg, 0 4px 16px rgba(0,0,0,0.12));
      pointer-events: auto;
      animation: toastIn 0.3s ease;
      max-width: 400px;
    `;

    const iconColor = {
      success: 'var(--success, #52c41a)',
      error: 'var(--error, #ff4d4f)',
      warning: 'var(--warning, #faad14)',
      info: 'var(--primary, #1890ff)',
    }[type];

    toast.innerHTML = `
      <span style="width: 20px; height: 20px; color: ${iconColor}; flex-shrink: 0;">
        ${this.icons[type]}
      </span>
      <span style="flex: 1; font-size: 14px; color: var(--text, #333);">${message}</span>
      <button style="
        padding: 4px;
        background: none;
        border: none;
        cursor: pointer;
        color: var(--text-tertiary, #999);
        opacity: 0.6;
      " onclick="this.parentElement.remove()">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
    `;

    this.container.appendChild(toast);

    // 自动关闭
    if (duration > 0) {
      setTimeout(() => {
        toast.style.animation = 'toastOut 0.3s ease forwards';
        setTimeout(() => toast.remove(), 300);
      }, duration);
    }

    // 添加动画样式
    if (!document.getElementById('toast-styles')) {
      const style = document.createElement('style');
      style.id = 'toast-styles';
      style.textContent = `
        @keyframes toastIn {
          from { opacity: 0; transform: translateX(100%); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes toastOut {
          from { opacity: 1; transform: translateX(0); }
          to { opacity: 0; transform: translateX(100%); }
        }
      `;
      document.head.appendChild(style);
    }

    return toast;
  },

  /**
   * 成功提示
   * @param {string} message - 消息内容
   * @param {Object} options - 配置选项
   */
  success(message, options) {
    return this.show(message, 'success', options);
  },

  /**
   * 错误提示
   * @param {string} message - 消息内容
   * @param {Object} options - 配置选项
   */
  error(message, options) {
    return this.show(message, 'error', options);
  },

  /**
   * 警告提示
   * @param {string} message - 消息内容
   * @param {Object} options - 配置选项
   */
  warning(message, options) {
    return this.show(message, 'warning', options);
  },

  /**
   * 信息提示
   * @param {string} message - 消息内容
   * @param {Object} options - 配置选项
   */
  info(message, options) {
    return this.show(message, 'info', options);
  },

  /**
   * 清除所有提示
   */
  clear() {
    if (this.container) {
      this.container.innerHTML = '';
    }
  },
};

window.Toast = Toast;

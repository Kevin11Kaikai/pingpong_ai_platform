/**
 * loading.js - 加载状态组件
 */

const Loading = {
  /**
   * 全屏加载遮罩
   */
  overlay: null,

  /**
   * 显示全屏加载
   * @param {string} message - 加载提示文本
   */
  show(message = '加载中...') {
    if (this.overlay) {
      this.updateMessage(message);
      return;
    }

    this.overlay = document.createElement('div');
    this.overlay.className = 'loading-overlay';
    this.overlay.style.cssText = `
      position: fixed;
      inset: 0;
      background-color: rgba(255, 255, 255, 0.8);
      z-index: var(--z-modal, 500);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 16px;
    `;

    this.overlay.innerHTML = `
      <div class="loading-spinner" style="
        width: 40px;
        height: 40px;
        border: 3px solid var(--border-light, #e8e8e8);
        border-top-color: var(--primary, #1890ff);
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      "></div>
      <div class="loading-message" style="
        font-size: 14px;
        color: var(--text-secondary, #666);
      ">${message}</div>
    `;

    // 添加动画样式
    if (!document.getElementById('loading-styles')) {
      const style = document.createElement('style');
      style.id = 'loading-styles';
      style.textContent = `
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `;
      document.head.appendChild(style);
    }

    document.body.appendChild(this.overlay);
  },

  /**
   * 隐藏全屏加载
   */
  hide() {
    if (this.overlay) {
      this.overlay.remove();
      this.overlay = null;
    }
  },

  /**
   * 更新加载提示文本
   * @param {string} message - 新的提示文本
   */
  updateMessage(message) {
    if (this.overlay) {
      const msgEl = this.overlay.querySelector('.loading-message');
      if (msgEl) msgEl.textContent = message;
    }
  },

  /**
   * 创建行内加载指示器
   * @param {string} size - 尺寸 (sm/md/lg)
   * @returns {HTMLElement} 加载指示器元素
   */
  createSpinner(size = 'md') {
    const sizeMap = { sm: 16, md: 24, lg: 32 };
    const sizePx = sizeMap[size] || sizeMap.md;

    const spinner = document.createElement('div');
    spinner.className = `loading-spinner loading-spinner-${size}`;
    spinner.style.cssText = `
      width: ${sizePx}px;
      height: ${sizePx}px;
      border: 2px solid var(--border-light, #e8e8e8);
      border-top-color: var(--primary, #1890ff);
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      display: inline-block;
    `;

    return spinner;
  },

  /**
   * 在元素内显示加载状态
   * @param {HTMLElement} element - 目标元素
   * @param {boolean} show - 显示/隐藏
   * @param {string} message - 加载提示
   */
  toggleInElement(element, show, message = '加载中...') {
    const existingLoader = element.querySelector('.element-loader');

    if (show) {
      if (existingLoader) return;

      const loader = document.createElement('div');
      loader.className = 'element-loader';
      loader.style.cssText = `
        position: absolute;
        inset: 0;
        background-color: rgba(255, 255, 255, 0.8);
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        gap: 8px;
        z-index: 10;
      `;

      loader.innerHTML = `
        <div style="
          width: 24px;
          height: 24px;
          border: 2px solid var(--border-light, #e8e8e8);
          border-top-color: var(--primary, #1890ff);
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
        "></div>
        <span style="font-size: 12px; color: var(--text-secondary, #666);">${message}</span>
      `;

      // 确保父元素有定位
      const position = window.getComputedStyle(element).position;
      if (position === 'static') {
        element.style.position = 'relative';
      }

      element.appendChild(loader);
    } else {
      if (existingLoader) {
        existingLoader.remove();
      }
    }
  },

  /**
   * 按钮加载状态
   * @param {HTMLElement} button - 按钮元素
   * @param {boolean} loading - 加载状态
   */
  toggleButton(button, loading) {
    if (loading) {
      button.disabled = true;
      button.dataset.originalText = button.innerHTML;
      button.innerHTML = `
        <span style="
          width: 14px;
          height: 14px;
          border: 2px solid currentColor;
          border-top-color: transparent;
          border-radius: 50%;
          animation: spin 0.8s linear infinite;
          display: inline-block;
          vertical-align: middle;
          margin-right: 6px;
        "></span>
        处理中...
      `;
    } else {
      button.disabled = false;
      if (button.dataset.originalText) {
        button.innerHTML = button.dataset.originalText;
        delete button.dataset.originalText;
      }
    }
  },

  /**
   * 骨架屏
   * @param {string} type - 骨架类型 (text/card/list)
   * @param {number} count - 数量
   * @returns {string} 骨架屏 HTML
   */
  skeleton(type = 'text', count = 1) {
    const templates = {
      text: `
        <div class="skeleton skeleton-title"></div>
        <div class="skeleton skeleton-text" style="width: 90%;"></div>
        <div class="skeleton skeleton-text" style="width: 80%;"></div>
        <div class="skeleton skeleton-text" style="width: 85%;"></div>
      `,
      card: `
        <div class="card" style="overflow: hidden;">
          <div class="skeleton skeleton-image"></div>
          <div style="padding: 16px;">
            <div class="skeleton skeleton-title" style="width: 60%;"></div>
            <div class="skeleton skeleton-text"></div>
            <div class="skeleton skeleton-text" style="width: 70%;"></div>
          </div>
        </div>
      `,
      list: `
        <div class="list-item" style="display: flex; gap: 12px; padding: 12px;">
          <div class="skeleton skeleton-avatar"></div>
          <div style="flex: 1;">
            <div class="skeleton skeleton-text" style="width: 30%; height: 14px;"></div>
            <div class="skeleton skeleton-text" style="margin-top: 8px;"></div>
          </div>
        </div>
      `,
    };

    const template = templates[type] || templates.text;
    return Array(count).fill(template).join('');
  },
};

window.Loading = Loading;

/**
 * modal.js - 弹窗组件
 */

const Modal = {
  /**
   * 当前打开的弹窗
   */
  currentModal: null,

  /**
   * 打开弹窗
   * @param {Object} options - 弹窗配置
   * @param {string} options.title - 标题
   * @param {string} options.content - 内容 HTML
   * @param {string} options.size - 尺寸 (sm/md/lg/xl)
   * @param {boolean} options.closable - 是否可关闭
   * @param {Array} options.actions - 操作按钮
   * @param {Function} options.onClose - 关闭回调
   * @returns {HTMLElement} 弹窗元素
   */
  open(options = {}) {
    const {
      title = '',
      content = '',
      size = 'md',
      closable = true,
      actions = [],
      onClose = null,
    } = options;

    // 关闭已有弹窗
    this.close();

    // 尺寸映射
    const sizeMap = {
      sm: '400px',
      md: '560px',
      lg: '720px',
      xl: '960px',
    };

    // 创建遮罩层
    const backdrop = document.createElement('div');
    backdrop.className = 'modal-backdrop';
    backdrop.style.cssText = `
      position: fixed;
      inset: 0;
      background-color: rgba(0, 0, 0, 0.5);
      z-index: var(--z-modal-backdrop, 400);
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
      animation: fadeIn 0.2s ease;
    `;

    // 创建弹窗
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.style.cssText = `
      background-color: var(--card-bg, #fff);
      border-radius: var(--radius-lg, 12px);
      box-shadow: var(--shadow-lg, 0 4px 16px rgba(0,0,0,0.12));
      width: 100%;
      max-width: ${sizeMap[size] || sizeMap.md};
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      animation: slideIn 0.3s ease;
    `;

    modal.innerHTML = `
      ${title ? `
        <div class="modal-header" style="
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 16px 24px;
          border-bottom: 1px solid var(--border-light, #e8e8e8);
        ">
          <h3 style="margin: 0; font-size: 18px; font-weight: 600;">${title}</h3>
          ${closable ? `
            <button class="modal-close" style="
              padding: 8px;
              background: none;
              border: none;
              cursor: pointer;
              color: var(--text-tertiary, #999);
              border-radius: 4px;
              transition: background-color 0.2s;
            ">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          ` : ''}
        </div>
      ` : ''}
      <div class="modal-body" style="
        padding: 24px;
        overflow-y: auto;
        flex: 1;
      ">${content}</div>
      ${actions.length > 0 ? `
        <div class="modal-footer" style="
          display: flex;
          justify-content: flex-end;
          gap: 12px;
          padding: 16px 24px;
          border-top: 1px solid var(--border-light, #e8e8e8);
        ">
          ${actions.map((action, index) => `
            <button class="btn ${action.type ? `btn-${action.type}` : 'btn-secondary'}" data-action-index="${index}">
              ${action.label}
            </button>
          `).join('')}
        </div>
      ` : ''}
    `;

    backdrop.appendChild(modal);
    document.body.appendChild(backdrop);

    // 添加动画样式
    if (!document.getElementById('modal-styles')) {
      const style = document.createElement('style');
      style.id = 'modal-styles';
      style.textContent = `
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        @keyframes fadeOut {
          from { opacity: 1; }
          to { opacity: 0; }
        }
        @keyframes slideIn {
          from { opacity: 0; transform: translateY(-20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes slideOut {
          from { opacity: 1; transform: translateY(0); }
          to { opacity: 0; transform: translateY(-20px); }
        }
        .modal-close:hover {
          background-color: var(--bg-light, #f5f5f5) !important;
        }
      `;
      document.head.appendChild(style);
    }

    // 绑定事件
    if (closable) {
      const closeBtn = modal.querySelector('.modal-close');
      if (closeBtn) {
        closeBtn.addEventListener('click', () => this.close());
      }
      backdrop.addEventListener('click', (e) => {
        if (e.target === backdrop) {
          this.close();
        }
      });
    }

    // 绑定按钮事件
    actions.forEach((action, index) => {
      const btn = modal.querySelector(`[data-action-index="${index}"]`);
      if (btn && action.onClick) {
        btn.addEventListener('click', () => {
          const result = action.onClick();
          if (result !== false) {
            this.close();
          }
        });
      }
    });

    // ESC 关闭
    const handleEsc = (e) => {
      if (e.key === 'Escape' && closable) {
        this.close();
        document.removeEventListener('keydown', handleEsc);
      }
    };
    document.addEventListener('keydown', handleEsc);

    // 保存引用和回调
    this.currentModal = { backdrop, modal, onClose };

    // 禁止背景滚动
    document.body.style.overflow = 'hidden';

    return modal;
  },

  /**
   * 关闭弹窗
   */
  close() {
    if (!this.currentModal) return;

    const { backdrop, modal, onClose } = this.currentModal;

    // 执行关闭动画
    backdrop.style.animation = 'fadeOut 0.2s ease forwards';
    modal.style.animation = 'slideOut 0.2s ease forwards';

    setTimeout(() => {
      backdrop.remove();
      document.body.style.overflow = '';
      if (onClose) onClose();
    }, 200);

    this.currentModal = null;
  },

  /**
   * 确认弹窗
   * @param {string} message - 确认消息
   * @param {Object} options - 配置选项
   * @returns {Promise<boolean>} 用户选择
   */
  confirm(message, options = {}) {
    return new Promise((resolve) => {
      this.open({
        title: options.title || '确认',
        content: `<p style="margin: 0; font-size: 14px; color: var(--text-secondary);">${message}</p>`,
        size: 'sm',
        actions: [
          {
            label: options.cancelText || '取消',
            onClick: () => {
              resolve(false);
            },
          },
          {
            label: options.confirmText || '确认',
            type: options.danger ? 'danger' : 'primary',
            onClick: () => {
              resolve(true);
            },
          },
        ],
        onClose: () => resolve(false),
      });
    });
  },

  /**
   * 警告弹窗
   * @param {string} message - 警告消息
   * @param {Object} options - 配置选项
   * @returns {Promise<void>}
   */
  alert(message, options = {}) {
    return new Promise((resolve) => {
      this.open({
        title: options.title || '提示',
        content: `<p style="margin: 0; font-size: 14px; color: var(--text-secondary);">${message}</p>`,
        size: 'sm',
        actions: [
          {
            label: options.confirmText || '确定',
            type: 'primary',
            onClick: () => {
              resolve();
            },
          },
        ],
        onClose: () => resolve(),
      });
    });
  },

  /**
   * 输入弹窗
   * @param {string} message - 提示消息
   * @param {Object} options - 配置选项
   * @returns {Promise<string|null>} 用户输入
   */
  prompt(message, options = {}) {
    return new Promise((resolve) => {
      const inputId = 'modal-prompt-input';

      this.open({
        title: options.title || '输入',
        content: `
          <p style="margin: 0 0 12px; font-size: 14px; color: var(--text-secondary);">${message}</p>
          <input type="text" id="${inputId}" class="form-input" value="${options.defaultValue || ''}"
                 placeholder="${options.placeholder || ''}" style="width: 100%;">
        `,
        size: 'sm',
        actions: [
          {
            label: options.cancelText || '取消',
            onClick: () => {
              resolve(null);
            },
          },
          {
            label: options.confirmText || '确认',
            type: 'primary',
            onClick: () => {
              const input = document.getElementById(inputId);
              resolve(input ? input.value : null);
            },
          },
        ],
        onClose: () => resolve(null),
      });

      // 聚焦输入框
      setTimeout(() => {
        const input = document.getElementById(inputId);
        if (input) input.focus();
      }, 100);
    });
  },
};

window.Modal = Modal;

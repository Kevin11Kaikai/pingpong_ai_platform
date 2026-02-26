/**
 * pagination.js - 分页组件
 */

const Pagination = {
  /**
   * 默认配置
   */
  defaultOptions: {
    page: 1,
    pageSize: 20,
    total: 0,
    maxVisible: 7,
    showInfo: true,
    showSizeChanger: true,
    pageSizes: [10, 20, 50, 100],
    onChange: null,
    onPageSizeChange: null,
  },

  /**
   * 创建分页组件
   * @param {HTMLElement} container - 容器元素
   * @param {Object} options - 配置选项
   * @returns {Object} 分页实例
   */
  create(container, options = {}) {
    const config = { ...this.defaultOptions, ...options };
    const instance = { container, config };

    this.render(instance);
    return instance;
  },

  /**
   * 渲染分页
   * @param {Object} instance - 分页实例
   */
  render(instance) {
    const { container, config } = instance;
    const { page, pageSize, total, maxVisible, showInfo, showSizeChanger, pageSizes } = config;

    const totalPages = Math.ceil(total / pageSize);
    const pages = this.getPageNumbers(page, totalPages, maxVisible);

    const startItem = (page - 1) * pageSize + 1;
    const endItem = Math.min(page * pageSize, total);

    container.innerHTML = `
      <div class="pagination" style="
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 16px;
        flex-wrap: wrap;
      ">
        ${showInfo ? `
          <div class="pagination-info" style="font-size: 14px; color: var(--text-secondary, #666);">
            显示 ${total > 0 ? startItem : 0}-${endItem} 条，共 ${total} 条
          </div>
        ` : ''}

        <div class="pagination-controls" style="display: flex; align-items: center; gap: 8px;">
          ${showSizeChanger ? `
            <select class="pagination-size form-select" style="
              padding: 6px 32px 6px 12px;
              font-size: 14px;
              border: 1px solid var(--border, #d9d9d9);
              border-radius: 4px;
              background-color: var(--card-bg, #fff);
            ">
              ${pageSizes.map(size => `
                <option value="${size}" ${size === pageSize ? 'selected' : ''}>${size} 条/页</option>
              `).join('')}
            </select>
          ` : ''}

          <div class="pagination-pages" style="display: flex; align-items: center; gap: 4px;">
            <button class="pagination-btn pagination-prev" ${page <= 1 ? 'disabled' : ''} style="
              padding: 6px 10px;
              border: 1px solid var(--border, #d9d9d9);
              border-radius: 4px;
              background-color: var(--card-bg, #fff);
              cursor: pointer;
              font-size: 14px;
            ">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15 18 9 12 15 6"/>
              </svg>
            </button>

            ${pages.map(p => {
              if (p === '...') {
                return `<span class="pagination-ellipsis" style="padding: 6px 8px; color: var(--text-tertiary, #999);">...</span>`;
              }
              return `
                <button class="pagination-btn pagination-page ${p === page ? 'active' : ''}" data-page="${p}" style="
                  min-width: 32px;
                  padding: 6px 10px;
                  border: 1px solid ${p === page ? 'var(--primary, #1890ff)' : 'var(--border, #d9d9d9)'};
                  border-radius: 4px;
                  background-color: ${p === page ? 'var(--primary, #1890ff)' : 'var(--card-bg, #fff)'};
                  color: ${p === page ? '#fff' : 'var(--text, #333)'};
                  cursor: pointer;
                  font-size: 14px;
                ">
                  ${p}
                </button>
              `;
            }).join('')}

            <button class="pagination-btn pagination-next" ${page >= totalPages ? 'disabled' : ''} style="
              padding: 6px 10px;
              border: 1px solid var(--border, #d9d9d9);
              border-radius: 4px;
              background-color: var(--card-bg, #fff);
              cursor: pointer;
              font-size: 14px;
            ">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 18 15 12 9 6"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    `;

    // 添加禁用样式
    if (!document.getElementById('pagination-styles')) {
      const style = document.createElement('style');
      style.id = 'pagination-styles';
      style.textContent = `
        .pagination-btn:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
        .pagination-btn:not(:disabled):hover {
          border-color: var(--primary, #1890ff);
          color: var(--primary, #1890ff);
        }
        .pagination-btn.active:hover {
          color: #fff;
        }
      `;
      document.head.appendChild(style);
    }

    this.bindEvents(instance);
  },

  /**
   * 获取页码数组
   * @param {number} current - 当前页
   * @param {number} total - 总页数
   * @param {number} max - 最大显示数
   * @returns {Array} 页码数组
   */
  getPageNumbers(current, total, max) {
    if (total <= max) {
      return Array.from({ length: total }, (_, i) => i + 1);
    }

    const pages = [];
    const half = Math.floor((max - 3) / 2);

    pages.push(1);

    if (current > half + 2) {
      pages.push('...');
    }

    const start = Math.max(2, current - half);
    const end = Math.min(total - 1, current + half);

    for (let i = start; i <= end; i++) {
      pages.push(i);
    }

    if (current < total - half - 1) {
      pages.push('...');
    }

    if (total > 1) {
      pages.push(total);
    }

    return pages;
  },

  /**
   * 绑定事件
   * @param {Object} instance - 分页实例
   */
  bindEvents(instance) {
    const { container, config } = instance;

    // 页码点击
    container.querySelectorAll('.pagination-page').forEach(btn => {
      btn.addEventListener('click', () => {
        const page = parseInt(btn.dataset.page);
        if (page !== config.page) {
          config.page = page;
          this.render(instance);
          if (config.onChange) {
            config.onChange(page, config.pageSize);
          }
        }
      });
    });

    // 上一页
    const prevBtn = container.querySelector('.pagination-prev');
    if (prevBtn) {
      prevBtn.addEventListener('click', () => {
        if (config.page > 1) {
          config.page--;
          this.render(instance);
          if (config.onChange) {
            config.onChange(config.page, config.pageSize);
          }
        }
      });
    }

    // 下一页
    const nextBtn = container.querySelector('.pagination-next');
    if (nextBtn) {
      nextBtn.addEventListener('click', () => {
        const totalPages = Math.ceil(config.total / config.pageSize);
        if (config.page < totalPages) {
          config.page++;
          this.render(instance);
          if (config.onChange) {
            config.onChange(config.page, config.pageSize);
          }
        }
      });
    }

    // 每页条数
    const sizeSelect = container.querySelector('.pagination-size');
    if (sizeSelect) {
      sizeSelect.addEventListener('change', () => {
        const newSize = parseInt(sizeSelect.value);
        if (newSize !== config.pageSize) {
          config.pageSize = newSize;
          config.page = 1; // 重置到第一页
          this.render(instance);
          if (config.onPageSizeChange) {
            config.onPageSizeChange(config.page, newSize);
          }
          if (config.onChange) {
            config.onChange(config.page, newSize);
          }
        }
      });
    }
  },

  /**
   * 更新分页
   * @param {Object} instance - 分页实例
   * @param {Object} options - 更新选项
   */
  update(instance, options) {
    Object.assign(instance.config, options);
    this.render(instance);
  },
};

window.Pagination = Pagination;

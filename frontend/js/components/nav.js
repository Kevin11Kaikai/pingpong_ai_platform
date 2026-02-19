/**
 * nav.js - 导航组件
 */

const Nav = {
  /**
   * 导航菜单配置
   */
  menuItems: [
    {
      section: '概览',
      items: [
        { id: 'dashboard', label: '仪表盘', icon: 'home', path: '/' },
      ],
    },
    {
      section: '核心功能',
      items: [
        { id: 'chat', label: 'AI 助手', icon: 'chat', path: '/chat' },
        { id: 'video', label: '视频分析', icon: 'video', path: '/video' },
        { id: 'equipment', label: '装备推荐', icon: 'equipment', path: '/equipment' },
      ],
    },
    {
      section: '学习与训练',
      items: [
        { id: 'learning', label: '学习资源', icon: 'book', path: '/learning' },
        { id: 'training', label: '训练分析', icon: 'chart', path: '/training' },
      ],
    },
    {
      section: '社区',
      items: [
        { id: 'social', label: '社交媒体', icon: 'social', path: '/social' },
      ],
    },
  ],

  /**
   * 图标 SVG 映射
   */
  icons: {
    home: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>`,
    chat: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>`,
    video: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>`,
    equipment: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>`,
    book: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>`,
    chart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
    social: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>`,
    menu: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="18" x2="21" y2="18"/></svg>`,
    close: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
    pingpong: `<svg viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="6"/><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z"/></svg>`,
  },

  /**
   * 获取图标 SVG
   * @param {string} name - 图标名称
   * @returns {string} SVG HTML
   */
  getIcon(name) {
    return this.icons[name] || '';
  },

  /**
   * 获取当前页面 ID
   * @returns {string} 页面 ID
   */
  getCurrentPageId() {
    const path = window.location.pathname;
    if (path === '/' || path === '/index.html') return 'dashboard';
    const match = path.match(/\/(\w+)/);
    return match ? match[1] : 'dashboard';
  },

  /**
   * 渲染侧边栏
   * @param {HTMLElement} container - 容器元素
   */
  render(container) {
    const currentPage = this.getCurrentPageId();

    const html = `
      <div class="sidebar" id="sidebar">
        <div class="sidebar-header">
          <div class="sidebar-logo">
            ${this.getIcon('pingpong')}
            <span>乒乓 AI</span>
          </div>
        </div>
        <nav class="sidebar-nav">
          ${this.menuItems.map(section => `
            <div class="nav-section">
              <div class="nav-section-title">${section.section}</div>
              ${section.items.map(item => `
                <a href="${item.path}" class="nav-item ${item.id === currentPage ? 'active' : ''}" data-page="${item.id}">
                  ${this.getIcon(item.icon)}
                  <span>${item.label}</span>
                </a>
              `).join('')}
            </div>
          `).join('')}
        </nav>
        <div class="sidebar-footer">
          <div class="text-sm text-secondary">v1.0.0</div>
        </div>
      </div>
      <div class="sidebar-overlay" id="sidebarOverlay"></div>
    `;

    container.insertAdjacentHTML('afterbegin', html);
    this.bindEvents();
  },

  /**
   * 渲染移动端菜单按钮
   * @param {HTMLElement} header - 页面头部元素
   */
  renderMobileMenuBtn(header) {
    const btn = document.createElement('button');
    btn.className = 'mobile-menu-btn';
    btn.innerHTML = this.getIcon('menu');
    btn.addEventListener('click', () => this.toggleSidebar());
    header.insertBefore(btn, header.firstChild);
  },

  /**
   * 绑定事件
   */
  bindEvents() {
    const overlay = document.getElementById('sidebarOverlay');
    if (overlay) {
      overlay.addEventListener('click', () => this.closeSidebar());
    }

    // 监听窗口大小变化
    window.addEventListener('resize', () => {
      if (window.innerWidth > 768) {
        this.closeSidebar();
      }
    });
  },

  /**
   * 切换侧边栏
   */
  toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar && overlay) {
      sidebar.classList.toggle('open');
      overlay.classList.toggle('open');
    }
  },

  /**
   * 关闭侧边栏
   */
  closeSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (sidebar && overlay) {
      sidebar.classList.remove('open');
      overlay.classList.remove('open');
    }
  },

  /**
   * 设置当前活动项
   * @param {string} pageId - 页面 ID
   */
  setActive(pageId) {
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.toggle('active', item.dataset.page === pageId);
    });
  },
};

window.Nav = Nav;

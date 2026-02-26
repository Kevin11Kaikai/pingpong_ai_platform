/**
 * dashboard.js - 仪表盘页面逻辑
 */

const Dashboard = {
  /**
   * 模块配置
   */
  modules: [
    { id: 'llm', name: 'AI 助手', icon: 'chat', api: llmApi },
    { id: 'ball-tracking', name: '视频分析', icon: 'video', api: ballTrackingApi },
    { id: 'equipment', name: '装备推荐', icon: 'equipment', api: equipmentApi },
    { id: 'learning', name: '学习资源', icon: 'book', api: learningApi },
    { id: 'training', name: '训练分析', icon: 'chart', api: trainingApi },
    { id: 'social', name: '社交媒体', icon: 'social', api: socialApi },
  ],

  /**
   * 模块状态
   */
  moduleStatus: {},

  /**
   * 初始化
   */
  async init() {
    this.renderStats();
    this.renderModuleStatus();
    this.renderRecentActivity();
    await this.checkAllModulesHealth();
  },

  /**
   * 刷新数据
   */
  async refresh() {
    Toast.info('正在刷新数据...');
    await this.checkAllModulesHealth();
    this.renderStats();
    this.renderRecentActivity();
    Toast.success('数据已刷新');
  },

  /**
   * 渲染统计数据
   */
  renderStats() {
    const statsGrid = document.getElementById('statsGrid');
    if (!statsGrid) return;

    // 从本地存储获取统计数据（实际应用中应从API获取）
    const stats = Storage.get('dashboard_stats', {
      totalChats: 0,
      videosAnalyzed: 0,
      trainingDays: 0,
      learningProgress: 0,
    });

    statsGrid.innerHTML = `
      <div class="card stat-card">
        <div class="stat-card-icon primary">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
          </svg>
        </div>
        <div class="stat-card-value">${Format.number(stats.totalChats)}</div>
        <div class="stat-card-label">对话次数</div>
      </div>

      <div class="card stat-card">
        <div class="stat-card-icon success">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="23 7 16 12 23 17 23 7"/>
            <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
          </svg>
        </div>
        <div class="stat-card-value">${Format.number(stats.videosAnalyzed)}</div>
        <div class="stat-card-label">视频分析</div>
      </div>

      <div class="card stat-card">
        <div class="stat-card-icon warning">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="20" x2="18" y2="10"/>
            <line x1="12" y1="20" x2="12" y2="4"/>
            <line x1="6" y1="20" x2="6" y2="14"/>
          </svg>
        </div>
        <div class="stat-card-value">${Format.number(stats.trainingDays)}</div>
        <div class="stat-card-label">训练天数</div>
      </div>

      <div class="card stat-card">
        <div class="stat-card-icon error">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
          </svg>
        </div>
        <div class="stat-card-value">${Format.percent(stats.learningProgress / 100)}</div>
        <div class="stat-card-label">学习进度</div>
      </div>
    `;
  },

  /**
   * 渲染模块状态
   */
  renderModuleStatus() {
    const grid = document.getElementById('moduleStatusGrid');
    if (!grid) return;

    const icons = {
      chat: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/></svg>`,
      video: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>`,
      equipment: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="3"/></svg>`,
      book: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>`,
      chart: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>`,
      social: `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 00-3-3.87"/><path d="M16 3.13a4 4 0 010 7.75"/></svg>`,
    };

    grid.innerHTML = this.modules.map(module => {
      const status = this.moduleStatus[module.id] || 'loading';
      const statusText = {
        online: '运行中',
        offline: '离线',
        loading: '检测中...',
      }[status];

      return `
        <div class="card module-status-card">
          <div class="module-status-icon" style="background-color: var(--primary-bg); color: var(--primary);">
            ${icons[module.icon]}
          </div>
          <div class="module-status-info">
            <h4>${module.name}</h4>
            <div class="module-status-badge">
              <span class="status-dot ${status}"></span>
              <span>${statusText}</span>
            </div>
          </div>
        </div>
      `;
    }).join('');
  },

  /**
   * 检查所有模块健康状态
   */
  async checkAllModulesHealth() {
    const checks = this.modules.map(async (module) => {
      try {
        await module.api.health();
        this.moduleStatus[module.id] = 'online';
      } catch (e) {
        this.moduleStatus[module.id] = 'offline';
      }
    });

    await Promise.allSettled(checks);
    this.renderModuleStatus();
  },

  /**
   * 渲染最近活动
   */
  renderRecentActivity() {
    const container = document.getElementById('recentActivity');
    if (!container) return;

    // 从本地存储获取活动记录
    const activities = Storage.get('recent_activities', []);

    if (activities.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <div class="empty-state-title">暂无活动记录</div>
          <div class="empty-state-desc">开始使用各个功能模块，活动记录将显示在这里</div>
        </div>
      `;
      return;
    }

    container.innerHTML = `
      <div class="list">
        ${activities.slice(0, 10).map(activity => `
          <div class="list-item">
            <div class="avatar avatar-sm" style="background-color: var(--${activity.color || 'primary'}-bg); color: var(--${activity.color || 'primary'});">
              ${activity.icon || '?'}
            </div>
            <div class="list-item-content">
              <div class="list-item-title">${activity.title}</div>
              <div class="list-item-desc">${activity.description || ''}</div>
            </div>
            <div class="text-tertiary text-sm">${Format.relativeTime(activity.timestamp)}</div>
          </div>
        `).join('')}
      </div>
    `;
  },

  /**
   * 添加活动记录
   * @param {Object} activity - 活动数据
   */
  addActivity(activity) {
    const activities = Storage.get('recent_activities', []);
    activities.unshift({
      ...activity,
      timestamp: new Date().toISOString(),
    });
    // 只保留最近50条
    Storage.set('recent_activities', activities.slice(0, 50));
    this.renderRecentActivity();
  },

  /**
   * 更新统计数据
   * @param {string} key - 统计键
   * @param {number} value - 值或增量
   * @param {boolean} increment - 是否增量
   */
  updateStats(key, value, increment = true) {
    const stats = Storage.get('dashboard_stats', {
      totalChats: 0,
      videosAnalyzed: 0,
      trainingDays: 0,
      learningProgress: 0,
    });

    if (increment) {
      stats[key] = (stats[key] || 0) + value;
    } else {
      stats[key] = value;
    }

    Storage.set('dashboard_stats', stats);
    this.renderStats();
  },
};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
  Dashboard.init();
});

window.Dashboard = Dashboard;

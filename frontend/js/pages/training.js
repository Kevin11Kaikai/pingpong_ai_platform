/**
 * training.js - 训练分析页面逻辑
 */

const TrainingPage = {
  /**
   * 用户 ID (模拟)
   */
  userId: 'default_user',

  /**
   * 趋势图表
   */
  trendsChart: null,

  /**
   * 初始化
   */
  async init() {
    await Promise.all([
      this.loadStats(),
      this.loadTrends(),
      this.loadSessions(),
      this.loadStreak(),
      this.loadGoals(),
      this.loadInsights(),
    ]);
  },

  /**
   * 加载统计数据
   */
  async loadStats() {
    const container = document.getElementById('statsOverview');
    if (!container) return;

    try {
      const stats = await trainingApi.getStats(this.userId, 'month');

      container.innerHTML = `
        <div class="card stat-card">
          <div class="stat-card-icon primary">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
            </svg>
          </div>
          <div class="stat-card-value">${stats.total_sessions || 0}</div>
          <div class="stat-card-label">本月训练次数</div>
        </div>
        <div class="card stat-card">
          <div class="stat-card-icon success">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/>
              <line x1="6" y1="20" x2="6" y2="14"/>
            </svg>
          </div>
          <div class="stat-card-value">${Format.durationMinutes(stats.total_duration || 0)}</div>
          <div class="stat-card-label">总训练时长</div>
        </div>
        <div class="card stat-card">
          <div class="stat-card-icon warning">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
            </svg>
          </div>
          <div class="stat-card-value">${(stats.avg_performance || 0).toFixed(1)}</div>
          <div class="stat-card-label">平均表现</div>
        </div>
        <div class="card stat-card">
          <div class="stat-card-icon error">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
          </div>
          <div class="stat-card-value">${(stats.improvement || 0).toFixed(1)}%</div>
          <div class="stat-card-label">进步幅度</div>
        </div>
      `;
    } catch (e) {
      console.error('Failed to load stats:', e);
    }
  },

  /**
   * 加载趋势数据
   */
  async loadTrends() {
    const metric = document.getElementById('metricSelect')?.value || 'duration';
    const period = document.getElementById('periodSelect')?.value || 'month';

    try {
      const trends = await trainingApi.getTrends(this.userId, metric, period);
      this.renderTrendsChart(trends, metric);
    } catch (e) {
      console.error('Failed to load trends:', e);
    }
  },

  /**
   * 渲染趋势图表
   * @param {Array} data - 趋势数据
   * @param {string} metric - 指标
   */
  renderTrendsChart(data, metric) {
    const canvas = document.getElementById('trendsChart');
    if (!canvas || typeof Chart === 'undefined') return;

    if (this.trendsChart) {
      this.trendsChart.destroy();
    }

    const labels = {
      duration: '训练时长 (分钟)',
      intensity: '训练强度',
      performance: '表现评分',
    };

    this.trendsChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: data.map(d => d.date),
        datasets: [{
          label: labels[metric] || metric,
          data: data.map(d => d.value),
          borderColor: '#1890ff',
          backgroundColor: 'rgba(24, 144, 255, 0.1)',
          fill: true,
          tension: 0.3,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
        },
        scales: {
          x: {
            grid: { display: false },
          },
          y: {
            beginAtZero: true,
            grid: { color: '#f0f0f0' },
          },
        },
      },
    });
  },

  /**
   * 加载训练会话
   */
  async loadSessions() {
    const container = document.getElementById('sessionList');
    if (!container) return;

    try {
      const result = await trainingApi.getSessions({ user_id: this.userId }, 0, 5);
      this.renderSessions(result.items || []);
    } catch (e) {
      console.error('Failed to load sessions:', e);
      container.innerHTML = '<div class="text-secondary">加载失败</div>';
    }
  },

  /**
   * 渲染会话列表
   * @param {Array} sessions - 会话列表
   */
  renderSessions(sessions) {
    const container = document.getElementById('sessionList');
    if (!container) return;

    if (sessions.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-title">暂无训练记录</div>
          <div class="empty-state-desc">点击"记录训练"开始记录</div>
        </div>
      `;
      return;
    }

    const typeLabels = {
      practice: '练习',
      match: '比赛',
      physical: '体能',
      technical: '技术',
    };

    container.innerHTML = sessions.map(session => `
      <div class="session-item" onclick="TrainingPage.showSession('${session.id}')">
        <div class="session-item-header">
          <div class="session-item-date">${Format.date(session.date, 'MM-DD')} ${typeLabels[session.type] || session.type}</div>
          <div class="session-item-duration">${Format.durationMinutes(session.duration)}</div>
        </div>
        <div class="session-item-stats">
          ${session.metrics ? Object.entries(session.metrics).slice(0, 3).map(([key, value]) => `
            <span>${key}: ${value}</span>
          `).join('') : ''}
        </div>
        ${session.notes ? `<div class="text-xs text-secondary mt-xs truncate">${session.notes}</div>` : ''}
      </div>
    `).join('');
  },

  /**
   * 加载连续天数
   */
  async loadStreak() {
    try {
      const streak = await trainingApi.getStreak(this.userId);

      document.getElementById('streakDays').textContent = streak.days || 0;

      const info = streak.days > 0
        ? `最后训练: ${Format.relativeTime(streak.last_training)}`
        : '今天开始新的记录！';
      document.getElementById('streakInfo').textContent = info;
    } catch (e) {
      console.error('Failed to load streak:', e);
    }
  },

  /**
   * 加载目标
   */
  async loadGoals() {
    const container = document.getElementById('goalsList');
    if (!container) return;

    try {
      const goals = await trainingApi.getGoals(this.userId, 'active');

      if (!goals || goals.length === 0) {
        container.innerHTML = '<div class="text-sm text-secondary">暂无目标</div>';
        return;
      }

      container.innerHTML = goals.map(goal => `
        <div class="goal-card">
          <div class="goal-header">
            <div class="goal-title">${goal.title}</div>
            <div class="goal-deadline">${Format.date(goal.target_date, 'MM-DD')}</div>
          </div>
          <div class="progress-labeled">
            <div class="progress">
              <div class="progress-bar ${goal.progress >= 100 ? 'success' : ''}" style="width: ${Math.min(goal.progress, 100)}%;"></div>
            </div>
            <span class="progress-text">${goal.progress || 0}%</span>
          </div>
        </div>
      `).join('');
    } catch (e) {
      console.error('Failed to load goals:', e);
    }
  },

  /**
   * 加载 AI 洞察
   */
  async loadInsights() {
    const container = document.getElementById('insightsList');
    if (!container) return;

    try {
      const insights = await trainingApi.getInsights(this.userId);

      if (!insights || !insights.suggestions || insights.suggestions.length === 0) {
        container.innerHTML = '<div class="insight-item">暂无建议，继续训练获取更多数据</div>';
        return;
      }

      container.innerHTML = insights.suggestions.map(item => `
        <div class="insight-item">${item}</div>
      `).join('');
    } catch (e) {
      console.error('Failed to load insights:', e);
      container.innerHTML = '<div class="insight-item">加载建议失败</div>';
    }
  },

  /**
   * 显示新建会话弹窗
   */
  showNewSessionModal() {
    const content = `
      <form id="sessionForm" onsubmit="TrainingPage.createSession(event)">
        <div class="form-group">
          <label class="form-label required">训练日期</label>
          <input type="date" id="sessionDate" class="form-input" value="${Format.date(new Date(), 'YYYY-MM-DD')}" required>
        </div>

        <div class="grid grid-cols-2 gap-md">
          <div class="form-group">
            <label class="form-label required">训练类型</label>
            <select id="sessionType" class="form-input form-select" required>
              <option value="practice">练习</option>
              <option value="match">比赛</option>
              <option value="physical">体能</option>
              <option value="technical">技术</option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label required">时长 (分钟)</label>
            <input type="number" id="sessionDuration" class="form-input" min="1" max="480" required>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-md">
          <div class="form-group">
            <label class="form-label">强度 (1-10)</label>
            <input type="number" id="sessionIntensity" class="form-input" min="1" max="10">
          </div>

          <div class="form-group">
            <label class="form-label">表现评分 (1-10)</label>
            <input type="number" id="sessionPerformance" class="form-input" min="1" max="10">
          </div>
        </div>

        <div class="form-group">
          <label class="form-label">训练内容</label>
          <textarea id="sessionContent" class="form-input" rows="2" placeholder="例如：正手拉球 200 个，反手推挡 150 个..."></textarea>
        </div>

        <div class="form-group">
          <label class="form-label">备注</label>
          <textarea id="sessionNotes" class="form-input" rows="2" placeholder="训练感受、问题记录..."></textarea>
        </div>

        <button type="submit" class="btn btn-primary btn-block">保存记录</button>
      </form>
    `;

    Modal.open({
      title: '记录训练',
      content,
      size: 'md',
    });
  },

  /**
   * 创建会话
   * @param {Event} event - 表单事件
   */
  async createSession(event) {
    event.preventDefault();

    const session = {
      user_id: this.userId,
      date: document.getElementById('sessionDate').value,
      type: document.getElementById('sessionType').value,
      duration: parseInt(document.getElementById('sessionDuration').value),
      metrics: {
        intensity: parseInt(document.getElementById('sessionIntensity').value) || null,
        performance: parseInt(document.getElementById('sessionPerformance').value) || null,
      },
      content: document.getElementById('sessionContent').value,
      notes: document.getElementById('sessionNotes').value,
    };

    try {
      await trainingApi.createSession(session);
      Toast.success('训练记录已保存');
      Modal.close();

      // 刷新数据
      await Promise.all([
        this.loadStats(),
        this.loadTrends(),
        this.loadSessions(),
        this.loadStreak(),
        this.loadInsights(),
      ]);
    } catch (e) {
      Toast.error('保存失败: ' + e.message);
    }
  },

  /**
   * 显示会话详情
   * @param {string} sessionId - 会话 ID
   */
  async showSession(sessionId) {
    try {
      Loading.show('加载详情...');
      const session = await trainingApi.getSession(sessionId);
      Loading.hide();

      const typeLabels = {
        practice: '练习',
        match: '比赛',
        physical: '体能',
        technical: '技术',
      };

      const content = `
        <div class="grid grid-cols-2 gap-md mb-lg">
          <div>
            <div class="text-sm text-secondary">日期</div>
            <div class="font-medium">${Format.date(session.date, 'YYYY-MM-DD')}</div>
          </div>
          <div>
            <div class="text-sm text-secondary">类型</div>
            <div class="font-medium">${typeLabels[session.type] || session.type}</div>
          </div>
          <div>
            <div class="text-sm text-secondary">时长</div>
            <div class="font-medium">${Format.durationMinutes(session.duration)}</div>
          </div>
          <div>
            <div class="text-sm text-secondary">强度</div>
            <div class="font-medium">${session.metrics?.intensity || '-'} / 10</div>
          </div>
        </div>

        ${session.content ? `
          <div class="mb-md">
            <div class="text-sm text-secondary mb-xs">训练内容</div>
            <div>${session.content}</div>
          </div>
        ` : ''}

        ${session.notes ? `
          <div class="mb-md">
            <div class="text-sm text-secondary mb-xs">备注</div>
            <div>${session.notes}</div>
          </div>
        ` : ''}

        <div class="flex gap-sm">
          <button class="btn btn-danger" onclick="TrainingPage.deleteSession('${session.id}')">删除</button>
          <button class="btn btn-secondary" onclick="Modal.close()">关闭</button>
        </div>
      `;

      Modal.open({
        title: '训练详情',
        content,
        size: 'md',
      });
    } catch (e) {
      Loading.hide();
      Toast.error('加载失败');
    }
  },

  /**
   * 删除会话
   * @param {string} sessionId - 会话 ID
   */
  async deleteSession(sessionId) {
    const confirmed = await Modal.confirm('确定要删除这条训练记录吗？');
    if (!confirmed) return;

    try {
      await trainingApi.deleteSession(sessionId);
      Toast.success('已删除');
      Modal.close();
      this.loadSessions();
      this.loadStats();
    } catch (e) {
      Toast.error('删除失败');
    }
  },

  /**
   * 显示新建目标弹窗
   */
  showNewGoalModal() {
    const content = `
      <form id="goalForm" onsubmit="TrainingPage.createGoal(event)">
        <div class="form-group">
          <label class="form-label required">目标标题</label>
          <input type="text" id="goalTitle" class="form-input" placeholder="例如：每周训练 3 次" required>
        </div>

        <div class="form-group">
          <label class="form-label">目标描述</label>
          <textarea id="goalDescription" class="form-input" rows="2"></textarea>
        </div>

        <div class="form-group">
          <label class="form-label required">目标日期</label>
          <input type="date" id="goalDate" class="form-input" required>
        </div>

        <button type="submit" class="btn btn-primary btn-block">创建目标</button>
      </form>
    `;

    Modal.open({
      title: '新建目标',
      content,
      size: 'sm',
    });
  },

  /**
   * 创建目标
   * @param {Event} event - 表单事件
   */
  async createGoal(event) {
    event.preventDefault();

    const goal = {
      user_id: this.userId,
      title: document.getElementById('goalTitle').value,
      description: document.getElementById('goalDescription').value,
      target_date: document.getElementById('goalDate').value,
    };

    try {
      await trainingApi.createGoal(goal);
      Toast.success('目标已创建');
      Modal.close();
      this.loadGoals();
    } catch (e) {
      Toast.error('创建失败');
    }
  },

  /**
   * 显示所有会话
   */
  async showAllSessions() {
    try {
      Loading.show('加载会话...');
      const result = await trainingApi.getSessions({ user_id: this.userId }, 0, 50);
      Loading.hide();

      const sessions = result.items || [];

      if (sessions.length === 0) {
        Modal.alert('暂无训练记录');
        return;
      }

      const typeLabels = {
        practice: '练习',
        match: '比赛',
        physical: '体能',
        technical: '技术',
      };

      const content = `
        <div class="list" style="max-height: 400px; overflow-y: auto;">
          ${sessions.map(session => `
            <div class="list-item" style="cursor: pointer;" onclick="TrainingPage.showSession('${session.id}')">
              <div class="list-item-content">
                <div class="list-item-title">${Format.date(session.date, 'MM-DD')} ${typeLabels[session.type] || session.type}</div>
                <div class="list-item-desc">${Format.durationMinutes(session.duration)}</div>
              </div>
              ${session.metrics?.performance ? `
                <div class="badge badge-primary">${session.metrics.performance}/10</div>
              ` : ''}
            </div>
          `).join('')}
        </div>
      `;

      Modal.open({
        title: '所有训练记录',
        content,
        size: 'md',
      });
    } catch (e) {
      Loading.hide();
      Toast.error('加载失败');
    }
  },
};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
  TrainingPage.init();
});

window.TrainingPage = TrainingPage;

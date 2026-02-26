/**
 * learning.js - 学习资源页面逻辑
 */

const LearningPage = {
  /**
   * 用户 ID (模拟)
   */
  userId: 'default_user',

  /**
   * 筛选条件
   */
  filters: {
    search: '',
    category: '',
    difficulty: '',
  },

  /**
   * 分页
   */
  page: 1,
  pageSize: 10,
  total: 0,

  /**
   * 进度图表
   */
  progressChart: null,

  /**
   * 搜索防抖
   */
  searchTimer: null,

  /**
   * 初始化
   */
  async init() {
    await Promise.all([
      this.loadPaths(),
      this.loadResources(),
      this.loadProgress(),
      this.loadRecommendations(),
      this.loadRecentLearning(),
    ]);
  },

  /**
   * 加载学习路径
   */
  async loadPaths() {
    const container = document.getElementById('pathsGrid');
    if (!container) return;

    try {
      const paths = await learningApi.getPaths();
      this.renderPaths(paths);
    } catch (e) {
      console.error('Failed to load paths:', e);
      container.innerHTML = '<div class="text-secondary">加载失败</div>';
    }
  },

  /**
   * 渲染学习路径
   * @param {Array} paths - 路径列表
   */
  renderPaths(paths) {
    const container = document.getElementById('pathsGrid');
    if (!container) return;

    if (!paths || paths.length === 0) {
      container.innerHTML = '<div class="col-span-2 text-secondary">暂无学习路径</div>';
      return;
    }

    container.innerHTML = paths.slice(0, 4).map(path => `
      <div class="card learning-path-card card-clickable" onclick="LearningPage.showPath('${path.id}')">
        <div class="flex items-center gap-sm mb-sm">
          <div class="avatar" style="background-color: var(--primary-bg); color: var(--primary);">
            ${path.name.charAt(0)}
          </div>
          <div>
            <h4 class="font-medium">${path.name}</h4>
            <div class="text-xs text-secondary">${path.resource_count || 0} 个资源</div>
          </div>
        </div>
        <div class="path-progress">
          <div class="progress-labeled">
            <div class="progress">
              <div class="progress-bar success" style="width: ${path.progress || 0}%;"></div>
            </div>
            <span class="progress-text">${path.progress || 0}%</span>
          </div>
        </div>
        <div class="text-sm text-secondary line-clamp-2">${path.description || ''}</div>
      </div>
    `).join('');
  },

  /**
   * 显示路径详情
   * @param {string} pathId - 路径 ID
   */
  async showPath(pathId) {
    try {
      Loading.show('加载路径详情...');
      const path = await learningApi.getPath(pathId);
      Loading.hide();

      const content = `
        <div class="mb-lg">
          <p class="text-secondary">${path.description || ''}</p>
        </div>
        <h4 class="font-medium mb-md">学习步骤</h4>
        <div class="path-steps">
          ${(path.steps || []).map((step, index) => `
            <div class="path-step ${step.completed ? 'completed' : step.current ? 'current' : ''}">
              <div class="path-step-indicator">
                ${step.completed ? '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3"><polyline points="20 6 9 17 4 12"/></svg>' : index + 1}
              </div>
              <div class="flex-1">
                <div class="font-medium">${step.title}</div>
                <div class="text-xs text-secondary">${step.description || ''}</div>
              </div>
              ${!step.completed ? `
                <button class="btn btn-sm btn-primary" onclick="LearningPage.startStep('${path.id}', ${index})">
                  ${step.current ? '继续' : '开始'}
                </button>
              ` : ''}
            </div>
          `).join('')}
        </div>
      `;

      Modal.open({
        title: path.name,
        content,
        size: 'md',
      });
    } catch (e) {
      Loading.hide();
      Toast.error('加载失败');
    }
  },

  /**
   * 加载资源列表
   */
  async loadResources() {
    const container = document.getElementById('resourcesList');
    if (!container) return;

    container.innerHTML = Loading.skeleton('list', 5);

    try {
      const result = await learningApi.getResources({
        search: this.filters.search,
        category: this.filters.category,
        difficulty: this.filters.difficulty,
      }, (this.page - 1) * this.pageSize, this.pageSize);

      this.total = result.total || 0;
      this.renderResources(result.items || []);
      this.renderPagination();
    } catch (e) {
      console.error('Failed to load resources:', e);
      container.innerHTML = '<div class="text-secondary">加载失败</div>';
    }
  },

  /**
   * 渲染资源列表
   * @param {Array} resources - 资源列表
   */
  renderResources(resources) {
    const container = document.getElementById('resourcesList');
    if (!container) return;

    if (resources.length === 0) {
      container.innerHTML = `
        <div class="empty-state">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
          </svg>
          <div class="empty-state-title">未找到资源</div>
        </div>
      `;
      return;
    }

    const difficultyLabels = {
      beginner: '入门',
      intermediate: '进阶',
      advanced: '高级',
    };

    const typeIcons = {
      video: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>',
      article: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>',
      exercise: '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>',
    };

    container.innerHTML = resources.map(resource => `
      <div class="card resource-card card-clickable" onclick="LearningPage.showResource('${resource.id}')">
        <div class="resource-thumbnail">
          ${resource.thumbnail ? `<img src="${resource.thumbnail}" alt="${resource.title}">` : `
            <div style="display: flex; align-items: center; justify-content: center; height: 100%; color: var(--text-tertiary);">
              ${typeIcons[resource.type] || typeIcons.article}
            </div>
          `}
        </div>
        <div class="resource-info">
          <div class="resource-title">${resource.title}</div>
          <div class="resource-meta">
            <span>${resource.category || '未分类'}</span>
            <span>${difficultyLabels[resource.difficulty] || resource.difficulty}</span>
            <span>${resource.duration ? Format.durationMinutes(resource.duration) : ''}</span>
          </div>
          <div class="resource-tags">
            ${(resource.tags || []).slice(0, 3).map(tag => `<span class="tag">${tag}</span>`).join('')}
          </div>
        </div>
        <div class="flex flex-col items-end gap-sm">
          ${resource.progress !== undefined ? `
            <div class="text-sm text-primary">${resource.progress}%</div>
          ` : ''}
          <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); LearningPage.toggleBookmark('${resource.id}')">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="${resource.bookmarked ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
              <path d="M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z"/>
            </svg>
          </button>
        </div>
      </div>
    `).join('');
  },

  /**
   * 渲染分页
   */
  renderPagination() {
    const container = document.getElementById('pagination');
    if (!container) return;

    Pagination.create(container, {
      page: this.page,
      pageSize: this.pageSize,
      total: this.total,
      onChange: (page) => {
        this.page = page;
        this.loadResources();
      },
    });
  },

  /**
   * 加载学习进度
   */
  async loadProgress() {
    try {
      const progress = await learningApi.getProgress(this.userId);
      this.renderProgressChart(progress);

      document.getElementById('completedCount').textContent = progress.completed || 0;
      document.getElementById('inProgressCount').textContent = progress.in_progress || 0;
      document.getElementById('notStartedCount').textContent = progress.not_started || 0;
    } catch (e) {
      console.error('Failed to load progress:', e);
    }
  },

  /**
   * 渲染进度图表
   * @param {Object} progress - 进度数据
   */
  renderProgressChart(progress) {
    const canvas = document.getElementById('progressChart');
    if (!canvas || typeof Chart === 'undefined') return;

    if (this.progressChart) {
      this.progressChart.destroy();
    }

    const data = {
      labels: ['已完成', '进行中', '未开始'],
      datasets: [{
        data: [progress.completed || 0, progress.in_progress || 0, progress.not_started || 0],
        backgroundColor: ['#52c41a', '#faad14', '#d9d9d9'],
        borderWidth: 0,
      }],
    };

    this.progressChart = new Chart(canvas, {
      type: 'doughnut',
      data,
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: { display: false },
        },
        cutout: '70%',
      },
    });
  },

  /**
   * 加载推荐资源
   */
  async loadRecommendations() {
    const container = document.getElementById('recommendedResources');
    if (!container) return;

    try {
      const recommendations = await learningApi.getRecommendations({
        user_id: this.userId,
      });

      if (!recommendations || recommendations.length === 0) {
        container.innerHTML = '<div class="text-sm text-secondary">暂无推荐</div>';
        return;
      }

      container.innerHTML = `
        <div class="list">
          ${recommendations.slice(0, 3).map(item => `
            <div class="list-item" style="cursor: pointer; padding: 8px 0;" onclick="LearningPage.showResource('${item.id}')">
              <div class="list-item-content">
                <div class="list-item-title text-sm">${item.title}</div>
                <div class="text-xs text-secondary">${item.category || ''}</div>
              </div>
            </div>
          `).join('')}
        </div>
      `;
    } catch (e) {
      console.error('Failed to load recommendations:', e);
    }
  },

  /**
   * 加载最近学习
   */
  async loadRecentLearning() {
    const container = document.getElementById('recentLearning');
    if (!container) return;

    const recent = Storage.get('recent_learning', []);

    if (recent.length === 0) {
      container.innerHTML = '<div class="text-sm text-secondary">暂无学习记录</div>';
      return;
    }

    container.innerHTML = `
      <div class="list">
        ${recent.slice(0, 3).map(item => `
          <div class="list-item" style="cursor: pointer; padding: 8px 0;" onclick="LearningPage.showResource('${item.id}')">
            <div class="list-item-content">
              <div class="list-item-title text-sm">${item.title}</div>
              <div class="text-xs text-secondary">${Format.relativeTime(item.timestamp)}</div>
            </div>
          </div>
        `).join('')}
      </div>
    `;
  },

  /**
   * 显示资源详情
   * @param {string} resourceId - 资源 ID
   */
  async showResource(resourceId) {
    try {
      Loading.show('加载资源...');
      const resource = await learningApi.getResource(resourceId);
      Loading.hide();

      // 记录最近学习
      this.addRecentLearning(resource);

      const content = `
        <div class="mb-lg">
          ${resource.thumbnail ? `<img src="${resource.thumbnail}" alt="${resource.title}" style="width: 100%; border-radius: var(--radius); margin-bottom: 16px;">` : ''}
          <p class="text-secondary">${resource.description || ''}</p>
        </div>

        ${resource.content ? `
          <div class="mb-lg">
            <h4 class="font-medium mb-sm">内容</h4>
            <div class="text-sm">${resource.content}</div>
          </div>
        ` : ''}

        ${resource.video_url ? `
          <div class="mb-lg">
            <video src="${resource.video_url}" controls style="width: 100%; border-radius: var(--radius);"></video>
          </div>
        ` : ''}

        <div class="flex gap-sm">
          <button class="btn btn-primary" onclick="LearningPage.markComplete('${resource.id}')">
            标记为已学习
          </button>
          <button class="btn btn-secondary" onclick="LearningPage.toggleBookmark('${resource.id}')">
            ${resource.bookmarked ? '取消书签' : '添加书签'}
          </button>
        </div>
      `;

      Modal.open({
        title: resource.title,
        content,
        size: 'lg',
      });
    } catch (e) {
      Loading.hide();
      Toast.error('加载失败');
    }
  },

  /**
   * 添加最近学习记录
   * @param {Object} resource - 资源
   */
  addRecentLearning(resource) {
    const recent = Storage.get('recent_learning', []);
    const filtered = recent.filter(r => r.id !== resource.id);
    filtered.unshift({
      id: resource.id,
      title: resource.title,
      timestamp: new Date().toISOString(),
    });
    Storage.set('recent_learning', filtered.slice(0, 10));
    this.loadRecentLearning();
  },

  /**
   * 标记完成
   * @param {string} resourceId - 资源 ID
   */
  async markComplete(resourceId) {
    try {
      await learningApi.updateProgress(this.userId, resourceId, { completed: true });
      Toast.success('已标记为完成');
      Modal.close();
      this.loadProgress();
      this.loadResources();
    } catch (e) {
      Toast.error('操作失败');
    }
  },

  /**
   * 切换书签
   * @param {string} resourceId - 资源 ID
   */
  async toggleBookmark(resourceId) {
    try {
      // 检查是否已收藏
      const bookmarks = await learningApi.getBookmarks(this.userId);
      const isBookmarked = bookmarks.some(b => b.resource_id === resourceId);

      if (isBookmarked) {
        await learningApi.removeBookmark(this.userId, resourceId);
        Toast.success('已取消书签');
      } else {
        await learningApi.addBookmark(this.userId, resourceId);
        Toast.success('已添加书签');
      }

      this.loadResources();
    } catch (e) {
      Toast.error('操作失败');
    }
  },

  /**
   * 显示书签
   */
  async showBookmarks() {
    try {
      Loading.show('加载书签...');
      const bookmarks = await learningApi.getBookmarks(this.userId);
      Loading.hide();

      if (!bookmarks || bookmarks.length === 0) {
        Modal.alert('暂无书签');
        return;
      }

      const content = `
        <div class="list" style="max-height: 400px; overflow-y: auto;">
          ${bookmarks.map(item => `
            <div class="list-item" style="cursor: pointer;" onclick="LearningPage.showResource('${item.resource_id}')">
              <div class="list-item-content">
                <div class="list-item-title">${item.title}</div>
                <div class="list-item-desc">${Format.relativeTime(item.created_at)}</div>
              </div>
              <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); LearningPage.toggleBookmark('${item.resource_id}')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
          `).join('')}
        </div>
      `;

      Modal.open({
        title: '我的书签',
        content,
        size: 'md',
      });
    } catch (e) {
      Loading.hide();
      Toast.error('加载失败');
    }
  },

  /**
   * 处理搜索
   */
  handleSearch() {
    clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => {
      this.filters.search = document.getElementById('searchInput').value.trim();
      this.page = 1;
      this.loadResources();
    }, 300);
  },

  /**
   * 处理筛选变化
   */
  handleFilterChange() {
    this.filters.category = document.getElementById('categoryFilter').value;
    this.filters.difficulty = document.getElementById('difficultyFilter').value;
    this.page = 1;
    this.loadResources();
  },

  /**
   * 开始学习步骤
   * @param {string} pathId - 路径 ID
   * @param {number} stepIndex - 步骤索引
   */
  startStep(pathId, stepIndex) {
    Modal.close();
    Toast.info('开始学习...');
    // 实际实现中跳转到对应资源
  },
};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
  LearningPage.init();
});

window.LearningPage = LearningPage;

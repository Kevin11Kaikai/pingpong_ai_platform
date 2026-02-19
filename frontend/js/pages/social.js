/**
 * social.js - 社交媒体页面逻辑
 */

const SocialPage = {
  /**
   * 筛选条件
   */
  filters: {
    query: '',
    platform: '',
    content_type: '',
  },

  /**
   * 分页
   */
  page: 1,
  pageSize: 10,
  total: 0,

  /**
   * 当前选中的内容
   */
  selectedContent: null,

  /**
   * 搜索防抖
   */
  searchTimer: null,

  /**
   * 初始化
   */
  async init() {
    await Promise.all([
      this.loadContents(),
      this.loadStats(),
    ]);
  },

  /**
   * 加载内容列表
   */
  async loadContents() {
    const container = document.getElementById('contentList');
    if (!container) return;

    container.innerHTML = Loading.skeleton('card', 3);

    try {
      const result = await socialApi.searchContents({
        query: this.filters.query,
        platform: this.filters.platform,
        content_type: this.filters.content_type,
      }, (this.page - 1) * this.pageSize, this.pageSize);

      this.total = result.total || 0;
      this.renderContents(result.items || []);
      this.renderPagination();
    } catch (e) {
      console.error('Failed to load contents:', e);
      container.innerHTML = '<div class="text-secondary">加载失败</div>';
    }
  },

  /**
   * 渲染内容列表
   * @param {Array} contents - 内容列表
   */
  renderContents(contents) {
    const container = document.getElementById('contentList');
    if (!container) return;

    if (contents.length === 0) {
      container.innerHTML = `
        <div class="card">
          <div class="card-body empty-state">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
              <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
            </svg>
            <div class="empty-state-title">未找到内容</div>
            <div class="empty-state-desc">尝试调整筛选条件或创建抓取任务</div>
          </div>
        </div>
      `;
      return;
    }

    const platformIcons = {
      weibo: '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>',
      zhihu: '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>',
      douyin: '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>',
      bilibili: '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>',
      xiaohongshu: '<svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="10"/></svg>',
    };

    const platformNames = {
      weibo: '微博',
      zhihu: '知乎',
      douyin: '抖音',
      bilibili: 'B站',
      xiaohongshu: '小红书',
    };

    const typeLabels = {
      question: '问答',
      post: '帖子',
      comment: '评论',
    };

    container.innerHTML = contents.map(content => `
      <div class="card content-card ${this.selectedContent?.id === content.id ? 'active' : ''}" onclick="SocialPage.selectContent('${content.id}')">
        <div class="content-header">
          <div class="avatar avatar-sm">${content.author?.charAt(0) || '?'}</div>
          <div class="flex-1">
            <div class="font-medium">${content.author || '匿名用户'}</div>
            <div class="content-source">
              <span style="color: var(--primary);">${platformNames[content.platform] || content.platform}</span>
              <span>·</span>
              <span>${typeLabels[content.content_type] || content.content_type}</span>
              <span>·</span>
              <span>${Format.relativeTime(content.created_at)}</span>
            </div>
          </div>
        </div>
        <div class="content-body">
          ${content.title ? `<div class="font-medium mb-sm">${content.title}</div>` : ''}
          <div class="line-clamp-3">${content.content}</div>
        </div>
        <div class="content-actions">
          <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); SocialPage.analyzeContent('${content.id}')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
            </svg>
            分析
          </button>
          <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); SocialPage.selectContent('${content.id}')">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 15a2 2 0 01-2 2H7l-4 4V5a2 2 0 012-2h14a2 2 0 012 2z"/>
            </svg>
            回复
          </button>
          <a href="${content.url}" target="_blank" class="btn btn-ghost btn-sm" onclick="event.stopPropagation();">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M18 13v6a2 2 0 01-2 2H5a2 2 0 01-2-2V8a2 2 0 012-2h6"/>
              <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
            </svg>
            原文
          </a>
        </div>
        ${content.analysis ? `
          <div class="analysis-result">
            <h5>分析结果</h5>
            <div class="sentiment-indicator mb-sm">
              <span class="text-xs">情感</span>
              <div class="sentiment-bar">
                <div class="sentiment-positive" style="width: ${content.analysis.sentiment?.positive || 0}%;"></div>
                <div class="sentiment-neutral" style="width: ${content.analysis.sentiment?.neutral || 0}%;"></div>
                <div class="sentiment-negative" style="width: ${content.analysis.sentiment?.negative || 0}%;"></div>
              </div>
            </div>
            ${content.analysis.topics ? `
              <div class="flex gap-xs flex-wrap">
                ${content.analysis.topics.map(topic => `<span class="tag">${topic}</span>`).join('')}
              </div>
            ` : ''}
          </div>
        ` : ''}
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
        this.loadContents();
      },
    });
  },

  /**
   * 加载统计数据
   */
  async loadStats() {
    const container = document.getElementById('statsCard');
    if (!container) return;

    try {
      const stats = await socialApi.getStats('day');

      container.innerHTML = `
        <div class="grid grid-cols-2 gap-md">
          <div class="text-center">
            <div class="text-xl font-bold text-primary">${stats.total_contents || 0}</div>
            <div class="text-xs text-secondary">抓取内容</div>
          </div>
          <div class="text-center">
            <div class="text-xl font-bold text-success">${stats.analyzed || 0}</div>
            <div class="text-xs text-secondary">已分析</div>
          </div>
          <div class="text-center">
            <div class="text-xl font-bold text-warning">${stats.questions || 0}</div>
            <div class="text-xs text-secondary">问答内容</div>
          </div>
          <div class="text-center">
            <div class="text-xl font-bold text-error">${stats.replies_generated || 0}</div>
            <div class="text-xs text-secondary">生成回复</div>
          </div>
        </div>
      `;
    } catch (e) {
      console.error('Failed to load stats:', e);
    }
  },

  /**
   * 选择内容
   * @param {string} contentId - 内容 ID
   */
  async selectContent(contentId) {
    try {
      const content = await socialApi.getContent(contentId);
      this.selectedContent = content;

      // 更新选中状态
      document.querySelectorAll('.content-card').forEach(card => {
        card.classList.remove('active');
      });
      event?.target?.closest?.('.content-card')?.classList.add('active');

      // 显示选中内容
      const container = document.getElementById('selectedContent');
      container.innerHTML = `
        <div class="text-sm text-secondary mb-xs">选中内容</div>
        <div class="font-medium line-clamp-2">${content.title || content.content.substring(0, 50)}...</div>
      `;

      // 显示回复区域
      document.getElementById('replySection').style.display = 'block';
      document.getElementById('generatedReply').style.display = 'none';

    } catch (e) {
      Toast.error('加载内容失败');
    }
  },

  /**
   * 分析内容
   * @param {string} contentId - 内容 ID
   */
  async analyzeContent(contentId) {
    try {
      Loading.show('分析中...');
      const result = await socialApi.analyzeContent({
        content_id: contentId,
        analysis_types: ['sentiment', 'topics', 'intent'],
      });
      Loading.hide();

      // 显示分析结果
      const card = document.getElementById('analysisCard');
      const container = document.getElementById('analysisResult');

      card.style.display = 'block';

      container.innerHTML = `
        <div class="mb-md">
          <div class="text-sm text-secondary mb-xs">情感分析</div>
          <div class="sentiment-indicator">
            <div class="sentiment-bar">
              <div class="sentiment-positive" style="width: ${result.sentiment?.positive || 0}%;"></div>
              <div class="sentiment-neutral" style="width: ${result.sentiment?.neutral || 0}%;"></div>
              <div class="sentiment-negative" style="width: ${result.sentiment?.negative || 0}%;"></div>
            </div>
          </div>
          <div class="flex justify-between text-xs mt-xs">
            <span class="text-success">正面 ${result.sentiment?.positive || 0}%</span>
            <span class="text-warning">中性 ${result.sentiment?.neutral || 0}%</span>
            <span class="text-error">负面 ${result.sentiment?.negative || 0}%</span>
          </div>
        </div>

        ${result.topics ? `
          <div class="mb-md">
            <div class="text-sm text-secondary mb-xs">主题标签</div>
            <div class="flex gap-xs flex-wrap">
              ${result.topics.map(topic => `<span class="tag">${topic}</span>`).join('')}
            </div>
          </div>
        ` : ''}

        ${result.intent ? `
          <div>
            <div class="text-sm text-secondary mb-xs">用户意图</div>
            <div class="badge badge-primary">${result.intent}</div>
          </div>
        ` : ''}
      `;

      // 刷新内容列表以显示分析结果
      this.loadContents();

      Toast.success('分析完成');
    } catch (e) {
      Loading.hide();
      Toast.error('分析失败');
    }
  },

  /**
   * 生成回复
   */
  async generateReply() {
    if (!this.selectedContent) {
      Toast.warning('请先选择内容');
      return;
    }

    const tone = document.getElementById('replyTone').value;

    try {
      Loading.show('生成回复中...');
      const result = await socialApi.generateReply({
        content_id: this.selectedContent.id,
        tone,
      });
      Loading.hide();

      // 显示生成的回复
      const container = document.getElementById('generatedReply');
      const content = document.getElementById('replyContent');

      container.style.display = 'block';
      content.textContent = result.reply;

      Toast.success('回复已生成');
    } catch (e) {
      Loading.hide();
      Toast.error('生成失败');
    }
  },

  /**
   * 重新生成回复
   */
  regenerateReply() {
    this.generateReply();
  },

  /**
   * 复制回复
   */
  copyReply() {
    const content = document.getElementById('replyContent').textContent;
    navigator.clipboard.writeText(content).then(() => {
      Toast.success('已复制到剪贴板');
    }).catch(() => {
      Toast.error('复制失败');
    });
  },

  /**
   * 处理搜索
   */
  handleSearch() {
    clearTimeout(this.searchTimer);
    this.searchTimer = setTimeout(() => {
      this.filters.query = document.getElementById('searchInput').value.trim();
      this.page = 1;
      this.loadContents();
    }, 300);
  },

  /**
   * 处理筛选变化
   */
  handleFilterChange() {
    this.filters.platform = document.getElementById('platformFilter').value;
    this.filters.content_type = document.getElementById('typeFilter').value;
    this.page = 1;
    this.loadContents();
  },

  /**
   * 清除筛选
   */
  clearFilters() {
    document.getElementById('searchInput').value = '';
    document.getElementById('platformFilter').value = '';
    document.getElementById('typeFilter').value = '';

    this.filters = { query: '', platform: '', content_type: '' };
    this.page = 1;
    this.loadContents();
  },

  /**
   * 显示抓取任务列表
   */
  async showTasks() {
    try {
      Loading.show('加载任务...');
      const tasks = await socialApi.getScrapeTasks();
      Loading.hide();

      const statusLabels = {
        pending: { text: '等待中', color: 'warning' },
        running: { text: '运行中', color: 'primary' },
        completed: { text: '已完成', color: 'success' },
        failed: { text: '失败', color: 'error' },
      };

      const content = `
        <div class="scrape-task-list">
          ${(!tasks || tasks.length === 0) ? '<div class="text-secondary p-md">暂无任务</div>' : tasks.map(task => `
            <div class="scrape-task-item">
              <div>
                <div class="font-medium">${task.query || '未命名任务'}</div>
                <div class="text-xs text-secondary">${task.platform} · ${Format.relativeTime(task.created_at)}</div>
              </div>
              <div class="task-status">
                <span class="badge badge-${statusLabels[task.status]?.color || 'default'}">
                  ${statusLabels[task.status]?.text || task.status}
                </span>
                ${task.status === 'running' ? `
                  <button class="btn btn-ghost btn-sm ml-sm" onclick="SocialPage.cancelTask('${task.id}')">取消</button>
                ` : ''}
              </div>
            </div>
          `).join('')}
        </div>
      `;

      Modal.open({
        title: '抓取任务',
        content,
        size: 'md',
      });
    } catch (e) {
      Loading.hide();
      Toast.error('加载失败');
    }
  },

  /**
   * 显示新建任务弹窗
   */
  showNewTaskModal() {
    const content = `
      <form id="taskForm" onsubmit="SocialPage.createTask(event)">
        <div class="form-group">
          <label class="form-label required">平台</label>
          <select id="taskPlatform" class="form-input form-select" required>
            <option value="">选择平台</option>
            <option value="weibo">微博</option>
            <option value="zhihu">知乎</option>
            <option value="douyin">抖音</option>
            <option value="bilibili">B站</option>
            <option value="xiaohongshu">小红书</option>
          </select>
        </div>

        <div class="form-group">
          <label class="form-label required">搜索关键词</label>
          <input type="text" id="taskQuery" class="form-input" placeholder="例如：乒乓球技术" required>
        </div>

        <div class="form-group">
          <label class="form-label">抓取数量</label>
          <input type="number" id="taskLimit" class="form-input" value="50" min="1" max="200">
        </div>

        <button type="submit" class="btn btn-primary btn-block">创建任务</button>
      </form>
    `;

    Modal.open({
      title: '新建抓取任务',
      content,
      size: 'sm',
    });
  },

  /**
   * 创建任务
   * @param {Event} event - 表单事件
   */
  async createTask(event) {
    event.preventDefault();

    const task = {
      platform: document.getElementById('taskPlatform').value,
      query: document.getElementById('taskQuery').value,
      limit: parseInt(document.getElementById('taskLimit').value) || 50,
    };

    try {
      await socialApi.createScrapeTask(task);
      Toast.success('任务已创建');
      Modal.close();
    } catch (e) {
      Toast.error('创建失败');
    }
  },

  /**
   * 取消任务
   * @param {string} taskId - 任务 ID
   */
  async cancelTask(taskId) {
    try {
      await socialApi.cancelScrapeTask(taskId);
      Toast.success('任务已取消');
      this.showTasks(); // 刷新列表
    } catch (e) {
      Toast.error('取消失败');
    }
  },
};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
  SocialPage.init();
});

window.SocialPage = SocialPage;

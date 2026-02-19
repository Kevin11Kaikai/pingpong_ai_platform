/**
 * video.js - 视频分析页面逻辑
 */

const VideoPage = {
  /**
   * 当前任务 ID
   */
  currentJobId: null,

  /**
   * 轨迹数据
   */
  tracks: [],

  /**
   * Canvas 控制器
   */
  canvasController: null,

  /**
   * 是否显示轨迹
   */
  showTrajectory: true,

  /**
   * 状态轮询定时器
   */
  pollTimer: null,

  /**
   * 初始化
   */
  init() {
    // 检查是否有正在进行的任务
    const pendingJob = Storage.get('pending_video_job');
    if (pendingJob) {
      this.currentJobId = pendingJob;
      this.showAnalysisSection();
      this.pollJobStatus();
    }
  },

  /**
   * 处理文件选择
   * @param {Event} event - 文件选择事件
   */
  handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
      this.uploadVideo(file);
    }
  },

  /**
   * 处理拖放
   * @param {DragEvent} event - 拖放事件
   */
  handleDrop(event) {
    event.preventDefault();
    const uploadArea = document.getElementById('uploadArea');
    uploadArea.classList.remove('dragover');

    const file = event.dataTransfer.files[0];
    if (file && file.type.startsWith('video/')) {
      this.uploadVideo(file);
    } else {
      Toast.error('请上传视频文件');
    }
  },

  /**
   * 处理拖拽经过
   * @param {DragEvent} event - 拖放事件
   */
  handleDragOver(event) {
    event.preventDefault();
    const uploadArea = document.getElementById('uploadArea');
    uploadArea.classList.add('dragover');
  },

  /**
   * 处理拖拽离开
   * @param {DragEvent} event - 拖放事件
   */
  handleDragLeave(event) {
    event.preventDefault();
    const uploadArea = document.getElementById('uploadArea');
    uploadArea.classList.remove('dragover');
  },

  /**
   * 上传视频
   * @param {File} file - 视频文件
   */
  async uploadVideo(file) {
    // 检查文件大小
    if (file.size > 500 * 1024 * 1024) {
      Toast.error('文件大小不能超过 500MB');
      return;
    }

    // 显示进度
    document.getElementById('uploadProgress').style.display = 'block';

    try {
      const result = await ballTrackingApi.uploadVideo(file, (percent) => {
        document.getElementById('progressBar').style.width = `${percent}%`;
        document.getElementById('progressText').textContent = `${percent}%`;
      });

      this.currentJobId = result.job_id;
      Storage.set('pending_video_job', this.currentJobId);

      // 显示分析区域
      this.showAnalysisSection();

      // 设置视频名称
      document.getElementById('videoName').textContent = file.name;

      // 开始轮询状态
      this.pollJobStatus();

      Toast.success('视频上传成功，开始分析');
    } catch (e) {
      Toast.error('上传失败: ' + e.message);
      document.getElementById('uploadProgress').style.display = 'none';
    }
  },

  /**
   * 显示分析区域
   */
  showAnalysisSection() {
    document.getElementById('uploadSection').style.display = 'none';
    document.getElementById('analysisSection').style.display = 'grid';
  },

  /**
   * 轮询任务状态
   */
  async pollJobStatus() {
    if (!this.currentJobId) return;

    try {
      const status = await ballTrackingApi.getJobStatus(this.currentJobId);

      this.updateTaskStatus(status);

      if (status.status === 'completed') {
        this.onAnalysisComplete();
      } else if (status.status === 'failed') {
        this.onAnalysisFailed(status.error);
      } else {
        // 继续轮询
        this.pollTimer = setTimeout(() => this.pollJobStatus(), 2000);
      }
    } catch (e) {
      console.error('Failed to get job status:', e);
      this.pollTimer = setTimeout(() => this.pollJobStatus(), 5000);
    }
  },

  /**
   * 更新任务状态 UI
   * @param {Object} status - 任务状态
   */
  updateTaskStatus(status) {
    const badge = document.getElementById('taskStatusBadge');
    const progress = document.getElementById('taskProgress');
    const progressText = document.getElementById('taskProgressText');
    const message = document.getElementById('taskMessage');

    const statusMap = {
      pending: { text: '等待中', color: 'warning' },
      processing: { text: '处理中', color: 'primary' },
      completed: { text: '已完成', color: 'success' },
      failed: { text: '失败', color: 'error' },
    };

    const statusInfo = statusMap[status.status] || statusMap.pending;

    badge.textContent = statusInfo.text;
    badge.className = `badge badge-${statusInfo.color}`;

    const percent = status.progress || 0;
    progress.style.width = `${percent}%`;
    progressText.textContent = `${percent}%`;

    message.textContent = status.message || '正在分析视频...';
  },

  /**
   * 分析完成
   */
  async onAnalysisComplete() {
    Storage.remove('pending_video_job');

    // 加载视频和结果
    const video = document.getElementById('videoPlayer');
    video.src = ballTrackingApi.getVideoUrl(this.currentJobId, 'original');

    // 加载轨迹数据
    await this.loadTracks();

    // 初始化 Canvas 叠加层
    const canvas = document.getElementById('overlayCanvas');
    this.canvasController = CanvasUtils.initOverlay(video, canvas);
    this.canvasController.setTracks(this.tracks);

    video.addEventListener('play', () => {
      this.canvasController.startAnimation();
    });

    video.addEventListener('pause', () => {
      this.canvasController.stopAnimation();
    });

    // 加载分析结果
    await this.loadResults();

    // 显示统计卡片
    document.getElementById('statsCard').style.display = 'block';
    document.getElementById('detailsCard').style.display = 'block';

    Toast.success('分析完成！');
  },

  /**
   * 分析失败
   * @param {string} error - 错误信息
   */
  onAnalysisFailed(error) {
    Storage.remove('pending_video_job');
    Toast.error('分析失败: ' + (error || '未知错误'));

    // 允许重新上传
    document.getElementById('uploadSection').style.display = 'block';
    document.getElementById('analysisSection').style.display = 'none';
  },

  /**
   * 加载轨迹数据
   */
  async loadTracks() {
    try {
      this.tracks = await ballTrackingApi.getTracks(this.currentJobId);
    } catch (e) {
      console.error('Failed to load tracks:', e);
      this.tracks = [];
    }
  },

  /**
   * 加载分析结果
   */
  async loadResults() {
    try {
      const result = await ballTrackingApi.getJobResult(this.currentJobId);
      this.renderStats(result);
      this.renderSpeedData(result);
      this.renderLandingData(result);
      this.renderRallyData(result);
    } catch (e) {
      console.error('Failed to load results:', e);
    }
  },

  /**
   * 渲染统计数据
   * @param {Object} result - 分析结果
   */
  renderStats(result) {
    const container = document.getElementById('analysisStats');
    if (!container) return;

    const stats = result.statistics || {};

    container.innerHTML = `
      <div class="analysis-stat-item">
        <div class="analysis-stat-value">${stats.total_frames || 0}</div>
        <div class="analysis-stat-label">总帧数</div>
      </div>
      <div class="analysis-stat-item">
        <div class="analysis-stat-value">${stats.ball_detected_frames || 0}</div>
        <div class="analysis-stat-label">检测到球</div>
      </div>
      <div class="analysis-stat-item">
        <div class="analysis-stat-value">${(stats.avg_speed || 0).toFixed(1)}</div>
        <div class="analysis-stat-label">平均球速 (km/h)</div>
      </div>
      <div class="analysis-stat-item">
        <div class="analysis-stat-value">${(stats.max_speed || 0).toFixed(1)}</div>
        <div class="analysis-stat-label">最高球速 (km/h)</div>
      </div>
      <div class="analysis-stat-item">
        <div class="analysis-stat-value">${stats.total_hits || 0}</div>
        <div class="analysis-stat-label">击球次数</div>
      </div>
      <div class="analysis-stat-item">
        <div class="analysis-stat-value">${stats.rally_count || 0}</div>
        <div class="analysis-stat-label">回合数</div>
      </div>
    `;
  },

  /**
   * 渲染球速数据
   * @param {Object} result - 分析结果
   */
  renderSpeedData(result) {
    const container = document.getElementById('speedData');
    if (!container) return;

    const speeds = result.speed_analysis || [];

    if (speeds.length === 0) {
      container.innerHTML = '<div class="text-secondary text-sm">暂无球速数据</div>';
      return;
    }

    container.innerHTML = `
      <div class="list" style="max-height: 200px; overflow-y: auto;">
        ${speeds.slice(0, 20).map((item, index) => `
          <div class="list-item" style="padding: 8px 0;">
            <span class="text-sm">#${index + 1}</span>
            <div class="flex-1 px-md">
              <div class="progress" style="height: 6px;">
                <div class="progress-bar" style="width: ${Math.min(item.speed / 150 * 100, 100)}%;"></div>
              </div>
            </div>
            <span class="text-sm font-medium">${item.speed.toFixed(1)} km/h</span>
          </div>
        `).join('')}
      </div>
    `;
  },

  /**
   * 渲染落点数据
   * @param {Object} result - 分析结果
   */
  renderLandingData(result) {
    const container = document.getElementById('landingData');
    if (!container) return;

    const landings = result.landing_points || {};

    container.innerHTML = `
      <div class="grid grid-cols-2 gap-md">
        <div class="p-md" style="background: var(--success-bg); border-radius: var(--radius);">
          <div class="text-2xl font-bold text-success">${landings.left || 0}</div>
          <div class="text-sm text-secondary">左侧落点</div>
        </div>
        <div class="p-md" style="background: var(--warning-bg); border-radius: var(--radius);">
          <div class="text-2xl font-bold text-warning">${landings.right || 0}</div>
          <div class="text-sm text-secondary">右侧落点</div>
        </div>
      </div>
      <div class="mt-md text-sm text-secondary">
        落点分布比例：左 ${landings.left_percent || 0}% / 右 ${landings.right_percent || 0}%
      </div>
    `;
  },

  /**
   * 渲染回合数据
   * @param {Object} result - 分析结果
   */
  renderRallyData(result) {
    const container = document.getElementById('rallyData');
    if (!container) return;

    const rallies = result.rallies || [];

    if (rallies.length === 0) {
      container.innerHTML = '<div class="text-secondary text-sm">暂无回合数据</div>';
      return;
    }

    container.innerHTML = `
      <div class="list" style="max-height: 200px; overflow-y: auto;">
        ${rallies.map((rally, index) => `
          <div class="list-item" style="padding: 8px 0;">
            <span class="badge badge-primary">回合 ${index + 1}</span>
            <div class="flex-1 px-md">
              <span class="text-sm">${rally.hits} 次击球</span>
            </div>
            <span class="text-sm text-secondary">${Format.duration(rally.duration)}</span>
          </div>
        `).join('')}
      </div>
    `;
  },

  /**
   * 切换标签页
   * @param {string} tabId - 标签 ID
   */
  switchTab(tabId) {
    // 更新标签
    document.querySelectorAll('.tab-item').forEach(tab => {
      tab.classList.toggle('active', tab.dataset.tab === tabId);
    });

    // 更新内容
    document.querySelectorAll('.tab-pane').forEach(pane => {
      pane.classList.toggle('active', pane.id === `${tabId}Tab`);
    });
  },

  /**
   * 切换轨迹显示
   */
  toggleTrajectory() {
    this.showTrajectory = !this.showTrajectory;

    if (this.canvasController) {
      if (this.showTrajectory) {
        this.canvasController.startAnimation();
      } else {
        this.canvasController.stopAnimation();
        this.canvasController.clear();
      }
    }

    Toast.info(this.showTrajectory ? '轨迹叠加已开启' : '轨迹叠加已关闭');
  },

  /**
   * 下载可视化视频
   */
  async downloadVisualization() {
    if (!this.currentJobId) return;

    Toast.info('正在生成可视化视频...');

    try {
      const result = await ballTrackingApi.generateVisualization(this.currentJobId);

      // 打开下载链接
      const url = ballTrackingApi.getVideoUrl(this.currentJobId, 'visualized');
      const link = document.createElement('a');
      link.href = url;
      link.download = 'visualization.mp4';
      link.click();

      Toast.success('可视化视频已生成');
    } catch (e) {
      Toast.error('生成失败: ' + e.message);
    }
  },

  /**
   * 显示历史记录
   */
  async showHistory() {
    try {
      const jobs = await ballTrackingApi.getJobs(0, 20);

      if (!jobs || jobs.length === 0) {
        Modal.alert('暂无分析历史记录');
        return;
      }

      const content = `
        <div class="list" style="max-height: 400px; overflow-y: auto;">
          ${jobs.map(job => `
            <div class="list-item" style="cursor: pointer;" onclick="VideoPage.loadJob('${job.id}')">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--primary);">
                <polygon points="23 7 16 12 23 17 23 7"/>
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
              </svg>
              <div class="list-item-content">
                <div class="list-item-title">${job.filename || '未命名视频'}</div>
                <div class="list-item-desc">
                  ${Format.status(job.status).label} · ${Format.relativeTime(job.created_at)}
                </div>
              </div>
              <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation(); VideoPage.deleteJob('${job.id}')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"/>
                  <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                </svg>
              </button>
            </div>
          `).join('')}
        </div>
      `;

      Modal.open({
        title: '分析历史',
        content,
        size: 'md',
      });
    } catch (e) {
      Toast.error('加载历史失败');
    }
  },

  /**
   * 加载历史任务
   * @param {string} jobId - 任务 ID
   */
  async loadJob(jobId) {
    Modal.close();

    this.currentJobId = jobId;
    this.showAnalysisSection();

    try {
      const status = await ballTrackingApi.getJobStatus(jobId);

      if (status.status === 'completed') {
        this.updateTaskStatus(status);
        await this.onAnalysisComplete();
      } else {
        this.pollJobStatus();
      }
    } catch (e) {
      Toast.error('加载失败');
    }
  },

  /**
   * 删除任务
   * @param {string} jobId - 任务 ID
   */
  async deleteJob(jobId) {
    const confirmed = await Modal.confirm('确定要删除这个分析记录吗？');
    if (!confirmed) return;

    try {
      await ballTrackingApi.deleteJob(jobId);
      Toast.success('已删除');
      this.showHistory(); // 刷新列表
    } catch (e) {
      Toast.error('删除失败');
    }
  },

  /**
   * 销毁
   */
  destroy() {
    if (this.pollTimer) {
      clearTimeout(this.pollTimer);
    }
    if (this.canvasController) {
      this.canvasController.destroy();
    }
  },
};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
  VideoPage.init();
});

// 页面卸载时清理
window.addEventListener('beforeunload', () => {
  VideoPage.destroy();
});

window.VideoPage = VideoPage;

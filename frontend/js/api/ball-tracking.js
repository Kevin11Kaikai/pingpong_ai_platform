/**
 * ball-tracking.js - 视频分析 API
 */

const ballTrackingApi = {
  /**
   * 上传视频
   * @param {File} file - 视频文件
   * @param {Function} onProgress - 进度回调
   * @returns {Promise<Object>} 上传结果（包含 job_id）
   */
  async uploadVideo(file, onProgress) {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.upload('/ball-tracking/upload', formData, onProgress);
  },

  /**
   * 获取任务状态
   * @param {string} jobId - 任务 ID
   * @returns {Promise<Object>} 任务状态
   */
  async getJobStatus(jobId) {
    return apiClient.get(`/ball-tracking/jobs/${jobId}/status`);
  },

  /**
   * 获取分析结果
   * @param {string} jobId - 任务 ID
   * @returns {Promise<Object>} 分析结果
   */
  async getJobResult(jobId) {
    return apiClient.get(`/ball-tracking/jobs/${jobId}/result`);
  },

  /**
   * 获取轨迹数据
   * @param {string} jobId - 任务 ID
   * @returns {Promise<Array>} 轨迹数据
   */
  async getTracks(jobId) {
    return apiClient.get(`/ball-tracking/jobs/${jobId}/tracks`);
  },

  /**
   * 生成可视化视频
   * @param {string} jobId - 任务 ID
   * @param {Object} options - 可视化选项
   * @returns {Promise<Object>} 可视化结果
   */
  async generateVisualization(jobId, options = {}) {
    return apiClient.post(`/ball-tracking/jobs/${jobId}/visualize`, options);
  },

  /**
   * 获取任务列表
   * @param {number} skip - 跳过数量
   * @param {number} limit - 限制数量
   * @returns {Promise<Array>} 任务列表
   */
  async getJobs(skip = 0, limit = 20) {
    return apiClient.get('/ball-tracking/jobs', { skip, limit });
  },

  /**
   * 删除任务
   * @param {string} jobId - 任务 ID
   * @returns {Promise<void>}
   */
  async deleteJob(jobId) {
    return apiClient.delete(`/ball-tracking/jobs/${jobId}`);
  },

  /**
   * 获取视频 URL
   * @param {string} jobId - 任务 ID
   * @param {string} type - 视频类型 (original/visualized)
   * @returns {string} 视频 URL
   */
  getVideoUrl(jobId, type = 'original') {
    return `/api/ball-tracking/jobs/${jobId}/video/${type}`;
  },

  /**
   * 健康检查
   * @returns {Promise<Object>} 健康状态
   */
  async health() {
    return apiClient.get('/ball-tracking/health');
  },
};

window.ballTrackingApi = ballTrackingApi;

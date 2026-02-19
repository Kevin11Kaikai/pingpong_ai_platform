/**
 * social.js - 社交媒体 API
 */

const socialApi = {
  /**
   * 搜索内容
   * @param {Object} params - 搜索参数
   * @param {string} params.query - 搜索关键词
   * @param {string} params.platform - 平台
   * @param {string} params.content_type - 内容类型
   * @param {string} params.start_date - 开始日期
   * @param {string} params.end_date - 结束日期
   * @param {number} skip - 跳过数量
   * @param {number} limit - 限制数量
   * @returns {Promise<Object>} 搜索结果
   */
  async searchContents(params = {}, skip = 0, limit = 20) {
    return apiClient.post('/social-media/contents/search', {
      ...params,
      skip,
      limit,
    });
  },

  /**
   * 获取内容详情
   * @param {string} id - 内容 ID
   * @returns {Promise<Object>} 内容详情
   */
  async getContent(id) {
    return apiClient.get(`/social-media/contents/${id}`);
  },

  /**
   * 分析内容
   * @param {Object} params - 分析参数
   * @param {string} params.content_id - 内容 ID
   * @param {string} params.text - 或直接提供文本
   * @param {Array<string>} params.analysis_types - 分析类型
   * @returns {Promise<Object>} 分析结果
   */
  async analyzeContent(params) {
    return apiClient.post('/social-media/analysis/analyze', params);
  },

  /**
   * 批量分析
   * @param {Array<string>} contentIds - 内容 ID 列表
   * @param {Array<string>} analysisTypes - 分析类型
   * @returns {Promise<Array>} 分析结果列表
   */
  async batchAnalyze(contentIds, analysisTypes = ['sentiment', 'topics']) {
    return apiClient.post('/social-media/analysis/batch', {
      content_ids: contentIds,
      analysis_types: analysisTypes,
    });
  },

  /**
   * 生成回复
   * @param {Object} params - 生成参数
   * @param {string} params.content_id - 内容 ID
   * @param {string} params.tone - 语气风格
   * @param {number} params.max_length - 最大长度
   * @returns {Promise<Object>} 生成的回复
   */
  async generateReply(params) {
    return apiClient.post('/social-media/replies/generate', params);
  },

  /**
   * 获取回复建议
   * @param {string} contentId - 内容 ID
   * @param {number} count - 建议数量
   * @returns {Promise<Array>} 回复建议列表
   */
  async getReplySuggestions(contentId, count = 3) {
    return apiClient.get(`/social-media/replies/suggestions/${contentId}`, { count });
  },

  /**
   * 创建抓取任务
   * @param {Object} task - 任务配置
   * @param {string} task.platform - 平台
   * @param {string} task.query - 搜索查询
   * @param {number} task.limit - 抓取数量
   * @returns {Promise<Object>} 创建的任务
   */
  async createScrapeTask(task) {
    return apiClient.post('/social-media/scrape/tasks', task);
  },

  /**
   * 获取抓取任务列表
   * @param {string} status - 任务状态
   * @param {number} skip - 跳过数量
   * @param {number} limit - 限制数量
   * @returns {Promise<Array>} 任务列表
   */
  async getScrapeTasks(status = null, skip = 0, limit = 20) {
    const params = { skip, limit };
    if (status) params.status = status;
    return apiClient.get('/social-media/scrape/tasks', params);
  },

  /**
   * 获取任务详情
   * @param {string} taskId - 任务 ID
   * @returns {Promise<Object>} 任务详情
   */
  async getScrapeTask(taskId) {
    return apiClient.get(`/social-media/scrape/tasks/${taskId}`);
  },

  /**
   * 取消抓取任务
   * @param {string} taskId - 任务 ID
   * @returns {Promise<void>}
   */
  async cancelScrapeTask(taskId) {
    return apiClient.post(`/social-media/scrape/tasks/${taskId}/cancel`);
  },

  /**
   * 获取平台配置
   * @returns {Promise<Array>} 平台配置列表
   */
  async getPlatformConfigs() {
    return apiClient.get('/social-media/platforms');
  },

  /**
   * 更新平台配置
   * @param {string} platform - 平台名称
   * @param {Object} config - 配置数据
   * @returns {Promise<Object>} 更新后的配置
   */
  async updatePlatformConfig(platform, config) {
    return apiClient.put(`/social-media/platforms/${platform}`, config);
  },

  /**
   * 获取统计数据
   * @param {string} period - 统计周期
   * @returns {Promise<Object>} 统计数据
   */
  async getStats(period = 'week') {
    return apiClient.get('/social-media/stats', { period });
  },

  /**
   * 健康检查
   * @returns {Promise<Object>} 健康状态
   */
  async health() {
    return apiClient.get('/social-media/health');
  },
};

window.socialApi = socialApi;

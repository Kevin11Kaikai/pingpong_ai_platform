/**
 * learning.js - 学习资源 API
 */

const learningApi = {
  /**
   * 获取资源列表
   * @param {Object} params - 查询参数
   * @param {string} params.category - 分类
   * @param {string} params.difficulty - 难度
   * @param {string} params.type - 类型
   * @param {string} params.search - 搜索关键词
   * @param {number} skip - 跳过数量
   * @param {number} limit - 限制数量
   * @returns {Promise<Object>} 资源列表
   */
  async getResources(params = {}, skip = 0, limit = 20) {
    return apiClient.get('/learning/resources', { ...params, skip, limit });
  },

  /**
   * 获取资源详情
   * @param {string} id - 资源 ID
   * @returns {Promise<Object>} 资源详情
   */
  async getResource(id) {
    return apiClient.get(`/learning/resources/${id}`);
  },

  /**
   * 搜索资源
   * @param {string} query - 搜索关键词
   * @param {number} limit - 限制数量
   * @returns {Promise<Array>} 搜索结果
   */
  async searchResources(query, limit = 10) {
    return apiClient.get('/learning/resources/search', { query, limit });
  },

  /**
   * 获取学习路径列表
   * @param {number} skip - 跳过数量
   * @param {number} limit - 限制数量
   * @returns {Promise<Array>} 学习路径列表
   */
  async getPaths(skip = 0, limit = 20) {
    return apiClient.get('/learning/paths', { skip, limit });
  },

  /**
   * 获取学习路径详情
   * @param {string} id - 路径 ID
   * @returns {Promise<Object>} 路径详情
   */
  async getPath(id) {
    return apiClient.get(`/learning/paths/${id}`);
  },

  /**
   * 获取用户学习进度
   * @param {string} userId - 用户 ID
   * @returns {Promise<Object>} 学习进度
   */
  async getProgress(userId) {
    return apiClient.get(`/learning/progress/${userId}`);
  },

  /**
   * 更新学习进度
   * @param {string} userId - 用户 ID
   * @param {string} resourceId - 资源 ID
   * @param {Object} progress - 进度数据
   * @returns {Promise<Object>} 更新后的进度
   */
  async updateProgress(userId, resourceId, progress) {
    return apiClient.post(`/learning/progress/${userId}/resources/${resourceId}`, progress);
  },

  /**
   * 获取知识图谱
   * @param {string} topic - 主题（可选）
   * @returns {Promise<Object>} 知识图谱数据
   */
  async getKnowledgeGraph(topic = null) {
    const params = topic ? { topic } : {};
    return apiClient.get('/learning/knowledge/graph', params);
  },

  /**
   * 获取推荐资源
   * @param {Object} params - 推荐参数
   * @param {string} params.user_id - 用户 ID
   * @param {string} params.level - 当前水平
   * @param {Array<string>} params.interests - 兴趣标签
   * @returns {Promise<Array>} 推荐资源列表
   */
  async getRecommendations(params) {
    return apiClient.post('/learning/recommendations', params);
  },

  /**
   * 获取书签列表
   * @param {string} userId - 用户 ID
   * @returns {Promise<Array>} 书签列表
   */
  async getBookmarks(userId) {
    return apiClient.get(`/learning/bookmarks/${userId}`);
  },

  /**
   * 添加书签
   * @param {string} userId - 用户 ID
   * @param {string} resourceId - 资源 ID
   * @returns {Promise<Object>} 书签对象
   */
  async addBookmark(userId, resourceId) {
    return apiClient.post(`/learning/bookmarks/${userId}`, { resource_id: resourceId });
  },

  /**
   * 删除书签
   * @param {string} userId - 用户 ID
   * @param {string} resourceId - 资源 ID
   * @returns {Promise<void>}
   */
  async removeBookmark(userId, resourceId) {
    return apiClient.delete(`/learning/bookmarks/${userId}/${resourceId}`);
  },

  /**
   * 获取分类列表
   * @returns {Promise<Array>} 分类列表
   */
  async getCategories() {
    return apiClient.get('/learning/categories');
  },

  /**
   * 健康检查
   * @returns {Promise<Object>} 健康状态
   */
  async health() {
    return apiClient.get('/learning/health');
  },
};

window.learningApi = learningApi;

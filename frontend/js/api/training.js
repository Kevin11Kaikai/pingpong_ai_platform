/**
 * training.js - 训练分析 API
 */

const trainingApi = {
  /**
   * 获取训练会话列表
   * @param {Object} params - 查询参数
   * @param {string} params.user_id - 用户 ID
   * @param {string} params.start_date - 开始日期
   * @param {string} params.end_date - 结束日期
   * @param {number} skip - 跳过数量
   * @param {number} limit - 限制数量
   * @returns {Promise<Object>} 会话列表
   */
  async getSessions(params = {}, skip = 0, limit = 20) {
    return apiClient.get('/training/sessions', { ...params, skip, limit });
  },

  /**
   * 创建训练会话
   * @param {Object} session - 会话数据
   * @param {string} session.date - 日期
   * @param {number} session.duration - 时长（分钟）
   * @param {string} session.type - 训练类型
   * @param {Object} session.metrics - 训练指标
   * @param {string} session.notes - 备注
   * @returns {Promise<Object>} 创建的会话
   */
  async createSession(session) {
    return apiClient.post('/training/sessions', session);
  },

  /**
   * 获取会话详情
   * @param {string} id - 会话 ID
   * @returns {Promise<Object>} 会话详情
   */
  async getSession(id) {
    return apiClient.get(`/training/sessions/${id}`);
  },

  /**
   * 更新会话
   * @param {string} id - 会话 ID
   * @param {Object} data - 更新数据
   * @returns {Promise<Object>} 更新后的会话
   */
  async updateSession(id, data) {
    return apiClient.put(`/training/sessions/${id}`, data);
  },

  /**
   * 删除会话
   * @param {string} id - 会话 ID
   * @returns {Promise<void>}
   */
  async deleteSession(id) {
    return apiClient.delete(`/training/sessions/${id}`);
  },

  /**
   * 获取用户统计数据
   * @param {string} userId - 用户 ID
   * @param {string} period - 统计周期 (week/month/year)
   * @returns {Promise<Object>} 统计数据
   */
  async getStats(userId, period = 'month') {
    return apiClient.get(`/training/analysis/user/${userId}/stats`, { period });
  },

  /**
   * 获取趋势分析
   * @param {string} userId - 用户 ID
   * @param {string} metric - 指标名称
   * @param {string} period - 时间周期
   * @returns {Promise<Array>} 趋势数据
   */
  async getTrends(userId, metric = 'duration', period = 'month') {
    return apiClient.get(`/training/analysis/user/${userId}/trends`, { metric, period });
  },

  /**
   * 获取 AI 洞察
   * @param {string} userId - 用户 ID
   * @returns {Promise<Object>} AI 洞察
   */
  async getInsights(userId) {
    return apiClient.get(`/training/insights/user/${userId}`);
  },

  /**
   * 获取目标列表
   * @param {string} userId - 用户 ID
   * @param {string} status - 目标状态 (active/completed/all)
   * @returns {Promise<Array>} 目标列表
   */
  async getGoals(userId, status = 'active') {
    return apiClient.get('/training/goals', { user_id: userId, status });
  },

  /**
   * 创建目标
   * @param {Object} goal - 目标数据
   * @param {string} goal.title - 标题
   * @param {string} goal.description - 描述
   * @param {string} goal.target_date - 目标日期
   * @param {Object} goal.metrics - 目标指标
   * @returns {Promise<Object>} 创建的目标
   */
  async createGoal(goal) {
    return apiClient.post('/training/goals', goal);
  },

  /**
   * 更新目标
   * @param {string} id - 目标 ID
   * @param {Object} data - 更新数据
   * @returns {Promise<Object>} 更新后的目标
   */
  async updateGoal(id, data) {
    return apiClient.put(`/training/goals/${id}`, data);
  },

  /**
   * 删除目标
   * @param {string} id - 目标 ID
   * @returns {Promise<void>}
   */
  async deleteGoal(id) {
    return apiClient.delete(`/training/goals/${id}`);
  },

  /**
   * 获取连续训练天数
   * @param {string} userId - 用户 ID
   * @returns {Promise<Object>} 连续天数数据
   */
  async getStreak(userId) {
    return apiClient.get(`/training/streak/${userId}`);
  },

  /**
   * 健康检查
   * @returns {Promise<Object>} 健康状态
   */
  async health() {
    return apiClient.get('/training/health');
  },
};

window.trainingApi = trainingApi;

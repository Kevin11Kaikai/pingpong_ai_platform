/**
 * equipment.js - 装备推荐 API
 */

const equipmentApi = {
  /**
   * 搜索装备
   * @param {Object} params - 搜索参数
   * @param {string} params.query - 搜索关键词
   * @param {string} params.category - 分类
   * @param {string} params.brand - 品牌
   * @param {number} params.min_price - 最低价格
   * @param {number} params.max_price - 最高价格
   * @param {number} skip - 跳过数量
   * @param {number} limit - 限制数量
   * @returns {Promise<Object>} 搜索结果
   */
  async search(params, skip = 0, limit = 20) {
    return apiClient.post('/equipment/equipment/search', {
      ...params,
      skip,
      limit,
    });
  },

  /**
   * 获取装备列表
   * @param {Object} params - 查询参数
   * @returns {Promise<Array>} 装备列表
   */
  async getEquipments(params = {}) {
    return apiClient.get('/equipment/equipment', params);
  },

  /**
   * 获取装备详情
   * @param {string} id - 装备 ID
   * @returns {Promise<Object>} 装备详情
   */
  async getEquipment(id) {
    return apiClient.get(`/equipment/equipment/${id}`);
  },

  /**
   * 对比装备
   * @param {Array<string>} ids - 装备 ID 列表
   * @returns {Promise<Object>} 对比结果
   */
  async compare(ids) {
    return apiClient.post('/equipment/equipment/compare', { equipment_ids: ids });
  },

  /**
   * 获取推荐
   * @param {Object} profile - 用户偏好
   * @param {string} profile.play_style - 打法风格
   * @param {string} profile.level - 水平等级
   * @param {number} profile.budget - 预算
   * @param {Array<string>} profile.preferences - 偏好标签
   * @returns {Promise<Array>} 推荐列表
   */
  async getRecommendations(profile) {
    return apiClient.post('/equipment/recommendations', profile);
  },

  /**
   * 获取分类列表
   * @returns {Promise<Array>} 分类列表
   */
  async getCategories() {
    return apiClient.get('/equipment/categories');
  },

  /**
   * 获取品牌列表
   * @returns {Promise<Array>} 品牌列表
   */
  async getBrands() {
    return apiClient.get('/equipment/brands');
  },

  /**
   * 获取装备评价
   * @param {string} equipmentId - 装备 ID
   * @param {number} skip - 跳过数量
   * @param {number} limit - 限制数量
   * @returns {Promise<Array>} 评价列表
   */
  async getReviews(equipmentId, skip = 0, limit = 10) {
    return apiClient.get(`/equipment/reviews/equipment/${equipmentId}`, { skip, limit });
  },

  /**
   * 添加评价
   * @param {string} equipmentId - 装备 ID
   * @param {Object} review - 评价内容
   * @param {number} review.rating - 评分 (1-5)
   * @param {string} review.content - 评价内容
   * @returns {Promise<Object>} 创建的评价
   */
  async addReview(equipmentId, review) {
    return apiClient.post(`/equipment/reviews/equipment/${equipmentId}`, review);
  },

  /**
   * 健康检查
   * @returns {Promise<Object>} 健康状态
   */
  async health() {
    return apiClient.get('/equipment/health');
  },
};

window.equipmentApi = equipmentApi;

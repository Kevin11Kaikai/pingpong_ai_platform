/**
 * llm.js - LLM 模块 API
 */

const llmApi = {
  /**
   * 流式聊天
   * @param {Object} params - 聊天参数
   * @param {string} params.message - 用户消息
   * @param {string} params.conversation_id - 对话 ID
   * @param {Object} handlers - 事件处理器
   * @returns {Function} 关闭连接的函数
   */
  chatStream(params, handlers) {
    return apiClient.stream('/llm/chat/stream', params, handlers);
  },

  /**
   * 非流式聊天
   * @param {Object} params - 聊天参数
   * @returns {Promise<Object>} 聊天响应
   */
  async chat(params) {
    return apiClient.post('/llm/chat', params);
  },

  /**
   * 获取对话列表
   * @param {number} skip - 跳过数量
   * @param {number} limit - 限制数量
   * @returns {Promise<Array>} 对话列表
   */
  async getConversations(skip = 0, limit = 20) {
    return apiClient.get('/llm/conversations', { skip, limit });
  },

  /**
   * 创建对话
   * @param {string} title - 对话标题
   * @returns {Promise<Object>} 新对话
   */
  async createConversation(title = '') {
    return apiClient.post('/llm/conversations', { title });
  },

  /**
   * 获取对话详情
   * @param {string} id - 对话 ID
   * @returns {Promise<Object>} 对话详情
   */
  async getConversation(id) {
    return apiClient.get(`/llm/conversations/${id}`);
  },

  /**
   * 删除对话
   * @param {string} id - 对话 ID
   * @returns {Promise<void>}
   */
  async deleteConversation(id) {
    return apiClient.delete(`/llm/conversations/${id}`);
  },

  /**
   * 获取对话消息
   * @param {string} conversationId - 对话 ID
   * @param {number} skip - 跳过数量
   * @param {number} limit - 限制数量
   * @returns {Promise<Array>} 消息列表
   */
  async getMessages(conversationId, skip = 0, limit = 50) {
    return apiClient.get(`/llm/conversations/${conversationId}/messages`, { skip, limit });
  },

  /**
   * 上传文档
   * @param {File} file - 文件对象
   * @param {Function} onProgress - 进度回调
   * @returns {Promise<Object>} 上传结果
   */
  async uploadDocument(file, onProgress) {
    const formData = new FormData();
    formData.append('file', file);
    return apiClient.upload('/llm/documents', formData, onProgress);
  },

  /**
   * 获取文档列表
   * @param {number} skip - 跳过数量
   * @param {number} limit - 限制数量
   * @returns {Promise<Array>} 文档列表
   */
  async getDocuments(skip = 0, limit = 20) {
    return apiClient.get('/llm/documents', { skip, limit });
  },

  /**
   * 删除文档
   * @param {string} id - 文档 ID
   * @returns {Promise<void>}
   */
  async deleteDocument(id) {
    return apiClient.delete(`/llm/documents/${id}`);
  },

  /**
   * 搜索知识库
   * @param {string} query - 搜索查询
   * @param {number} topK - 返回数量
   * @returns {Promise<Array>} 搜索结果
   */
  async searchKnowledge(query, topK = 5) {
    return apiClient.post('/llm/search', { query, top_k: topK });
  },

  /**
   * 健康检查
   * @returns {Promise<Object>} 健康状态
   */
  async health() {
    return apiClient.get('/llm/health');
  },
};

window.llmApi = llmApi;

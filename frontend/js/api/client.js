/**
 * client.js - API 基础客户端
 * 封装 HTTP 请求、错误处理、认证等
 */

const API_BASE_URL = '/api';

/**
 * API 客户端类
 */
class ApiClient {
  constructor(baseUrl = API_BASE_URL) {
    this.baseUrl = baseUrl;
    this.token = localStorage.getItem('auth_token');
  }

  /**
   * 设置认证 Token
   * @param {string} token - JWT token
   */
  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('auth_token', token);
    } else {
      localStorage.removeItem('auth_token');
    }
  }

  /**
   * 获取请求头
   * @returns {Object} 请求头对象
   */
  getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    };
    if (this.token) {
      headers['Authorization'] = `Bearer ${this.token}`;
    }
    return headers;
  }

  /**
   * 处理响应
   * @param {Response} response - fetch 响应对象
   * @returns {Promise<any>} 响应数据
   */
  async handleResponse(response) {
    if (!response.ok) {
      const error = await this.parseError(response);
      throw error;
    }

    // 处理空响应
    const contentType = response.headers.get('content-type');
    if (!contentType || !contentType.includes('application/json')) {
      return null;
    }

    return response.json();
  }

  /**
   * 解析错误响应
   * @param {Response} response - fetch 响应对象
   * @returns {Error} 错误对象
   */
  async parseError(response) {
    let message = `请求失败: ${response.status}`;
    let detail = null;

    try {
      const data = await response.json();
      message = data.detail || data.message || message;
      detail = data;
    } catch (e) {
      // 非 JSON 响应
    }

    const error = new Error(message);
    error.status = response.status;
    error.detail = detail;
    return error;
  }

  /**
   * GET 请求
   * @param {string} endpoint - API 端点
   * @param {Object} params - 查询参数
   * @returns {Promise<any>} 响应数据
   */
  async get(endpoint, params = {}) {
    const url = new URL(`${this.baseUrl}${endpoint}`, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) {
        url.searchParams.append(key, value);
      }
    });

    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: this.getHeaders(),
    });

    return this.handleResponse(response);
  }

  /**
   * POST 请求
   * @param {string} endpoint - API 端点
   * @param {Object} data - 请求数据
   * @returns {Promise<any>} 响应数据
   */
  async post(endpoint, data = {}) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });

    return this.handleResponse(response);
  }

  /**
   * PUT 请求
   * @param {string} endpoint - API 端点
   * @param {Object} data - 请求数据
   * @returns {Promise<any>} 响应数据
   */
  async put(endpoint, data = {}) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'PUT',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });

    return this.handleResponse(response);
  }

  /**
   * PATCH 请求
   * @param {string} endpoint - API 端点
   * @param {Object} data - 请求数据
   * @returns {Promise<any>} 响应数据
   */
  async patch(endpoint, data = {}) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
    });

    return this.handleResponse(response);
  }

  /**
   * DELETE 请求
   * @param {string} endpoint - API 端点
   * @returns {Promise<any>} 响应数据
   */
  async delete(endpoint) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    });

    return this.handleResponse(response);
  }

  /**
   * 上传文件
   * @param {string} endpoint - API 端点
   * @param {FormData} formData - 表单数据
   * @param {Function} onProgress - 进度回调
   * @returns {Promise<any>} 响应数据
   */
  async upload(endpoint, formData, onProgress = null) {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', `${this.baseUrl}${endpoint}`);

      // 设置认证头
      if (this.token) {
        xhr.setRequestHeader('Authorization', `Bearer ${this.token}`);
      }

      // 进度监听
      if (onProgress) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percent = Math.round((event.loaded / event.total) * 100);
            onProgress(percent);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            resolve(data);
          } catch (e) {
            resolve(null);
          }
        } else {
          const error = new Error(`上传失败: ${xhr.status}`);
          error.status = xhr.status;
          reject(error);
        }
      };

      xhr.onerror = () => {
        reject(new Error('网络错误'));
      };

      xhr.send(formData);
    });
  }

  /**
   * SSE 流式请求
   * @param {string} endpoint - API 端点
   * @param {Object} data - 请求数据
   * @param {Object} handlers - 事件处理器
   * @returns {Function} 关闭连接的函数
   */
  stream(endpoint, data, handlers = {}) {
    const { onMessage, onError, onComplete } = handlers;

    // 使用 POST 请求创建 SSE 连接
    const controller = new AbortController();

    fetch(`${this.baseUrl}${endpoint}`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(data),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw await this.parseError(response);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            if (onComplete) onComplete();
            break;
          }

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') {
                if (onComplete) onComplete();
                return;
              }
              try {
                const parsed = JSON.parse(data);
                if (onMessage) onMessage(parsed);
              } catch (e) {
                // 非 JSON 数据，直接传递文本
                if (onMessage) onMessage({ content: data });
              }
            }
          }
        }
      })
      .catch((error) => {
        if (error.name === 'AbortError') return;
        if (onError) onError(error);
      });

    // 返回关闭函数
    return () => controller.abort();
  }
}

// 创建单例实例
const apiClient = new ApiClient();

// 导出
window.ApiClient = ApiClient;
window.apiClient = apiClient;

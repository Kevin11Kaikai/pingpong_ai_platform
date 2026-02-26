/**
 * storage.js - 本地存储工具
 */

const Storage = {
  /**
   * 存储前缀
   */
  prefix: 'pingpong_',

  /**
   * 获取完整的键名
   * @param {string} key - 键名
   * @returns {string} 完整键名
   */
  getKey(key) {
    return this.prefix + key;
  },

  /**
   * 设置值
   * @param {string} key - 键名
   * @param {any} value - 值
   * @param {number} expire - 过期时间（毫秒），可选
   */
  set(key, value, expire = null) {
    const data = {
      value,
      timestamp: Date.now(),
      expire: expire ? Date.now() + expire : null,
    };
    try {
      localStorage.setItem(this.getKey(key), JSON.stringify(data));
    } catch (e) {
      console.warn('Storage.set failed:', e);
      // 存储满了，清理过期数据
      this.cleanup();
    }
  },

  /**
   * 获取值
   * @param {string} key - 键名
   * @param {any} defaultValue - 默认值
   * @returns {any} 存储的值
   */
  get(key, defaultValue = null) {
    try {
      const raw = localStorage.getItem(this.getKey(key));
      if (!raw) return defaultValue;

      const data = JSON.parse(raw);

      // 检查是否过期
      if (data.expire && Date.now() > data.expire) {
        this.remove(key);
        return defaultValue;
      }

      return data.value;
    } catch (e) {
      console.warn('Storage.get failed:', e);
      return defaultValue;
    }
  },

  /**
   * 移除值
   * @param {string} key - 键名
   */
  remove(key) {
    localStorage.removeItem(this.getKey(key));
  },

  /**
   * 检查键是否存在
   * @param {string} key - 键名
   * @returns {boolean} 是否存在
   */
  has(key) {
    return this.get(key) !== null;
  },

  /**
   * 清除所有应用数据
   */
  clear() {
    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      if (key.startsWith(this.prefix)) {
        localStorage.removeItem(key);
      }
    });
  },

  /**
   * 清理过期数据
   */
  cleanup() {
    const keys = Object.keys(localStorage);
    const now = Date.now();

    keys.forEach(key => {
      if (key.startsWith(this.prefix)) {
        try {
          const raw = localStorage.getItem(key);
          if (raw) {
            const data = JSON.parse(raw);
            if (data.expire && now > data.expire) {
              localStorage.removeItem(key);
            }
          }
        } catch (e) {
          // 无效数据，直接删除
          localStorage.removeItem(key);
        }
      }
    });
  },

  /**
   * 获取所有应用数据
   * @returns {Object} 所有数据
   */
  getAll() {
    const result = {};
    const keys = Object.keys(localStorage);

    keys.forEach(key => {
      if (key.startsWith(this.prefix)) {
        const shortKey = key.slice(this.prefix.length);
        result[shortKey] = this.get(shortKey);
      }
    });

    return result;
  },

  /**
   * 获取存储大小
   * @returns {Object} 大小信息
   */
  getSize() {
    let total = 0;
    let app = 0;

    const keys = Object.keys(localStorage);
    keys.forEach(key => {
      const size = (localStorage.getItem(key) || '').length * 2; // UTF-16
      total += size;
      if (key.startsWith(this.prefix)) {
        app += size;
      }
    });

    return {
      total: total,
      app: app,
      totalFormatted: Format.fileSize(total),
      appFormatted: Format.fileSize(app),
    };
  },
};

/**
 * Session Storage 工具
 */
const SessionStorage = {
  /**
   * 存储前缀
   */
  prefix: 'pingpong_',

  /**
   * 获取完整的键名
   * @param {string} key - 键名
   * @returns {string} 完整键名
   */
  getKey(key) {
    return this.prefix + key;
  },

  /**
   * 设置值
   * @param {string} key - 键名
   * @param {any} value - 值
   */
  set(key, value) {
    try {
      sessionStorage.setItem(this.getKey(key), JSON.stringify(value));
    } catch (e) {
      console.warn('SessionStorage.set failed:', e);
    }
  },

  /**
   * 获取值
   * @param {string} key - 键名
   * @param {any} defaultValue - 默认值
   * @returns {any} 存储的值
   */
  get(key, defaultValue = null) {
    try {
      const raw = sessionStorage.getItem(this.getKey(key));
      if (!raw) return defaultValue;
      return JSON.parse(raw);
    } catch (e) {
      console.warn('SessionStorage.get failed:', e);
      return defaultValue;
    }
  },

  /**
   * 移除值
   * @param {string} key - 键名
   */
  remove(key) {
    sessionStorage.removeItem(this.getKey(key));
  },

  /**
   * 清除所有应用数据
   */
  clear() {
    const keys = Object.keys(sessionStorage);
    keys.forEach(key => {
      if (key.startsWith(this.prefix)) {
        sessionStorage.removeItem(key);
      }
    });
  },
};

window.Storage = Storage;
window.SessionStorage = SessionStorage;

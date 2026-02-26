/**
 * format.js - 格式化工具
 */

const Format = {
  /**
   * 格式化日期
   * @param {string|Date} date - 日期
   * @param {string} pattern - 格式模式
   * @returns {string} 格式化后的日期
   */
  date(date, pattern = 'YYYY-MM-DD') {
    if (!date) return '';

    const d = date instanceof Date ? date : new Date(date);
    if (isNaN(d.getTime())) return '';

    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const seconds = String(d.getSeconds()).padStart(2, '0');

    return pattern
      .replace('YYYY', year)
      .replace('MM', month)
      .replace('DD', day)
      .replace('HH', hours)
      .replace('mm', minutes)
      .replace('ss', seconds);
  },

  /**
   * 格式化相对时间
   * @param {string|Date} date - 日期
   * @returns {string} 相对时间描述
   */
  relativeTime(date) {
    if (!date) return '';

    const d = date instanceof Date ? date : new Date(date);
    const now = new Date();
    const diff = now.getTime() - d.getTime();

    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    const months = Math.floor(days / 30);
    const years = Math.floor(days / 365);

    if (seconds < 60) return '刚刚';
    if (minutes < 60) return `${minutes} 分钟前`;
    if (hours < 24) return `${hours} 小时前`;
    if (days < 30) return `${days} 天前`;
    if (months < 12) return `${months} 个月前`;
    return `${years} 年前`;
  },

  /**
   * 格式化数字
   * @param {number} num - 数字
   * @param {number} decimals - 小数位数
   * @returns {string} 格式化后的数字
   */
  number(num, decimals = 0) {
    if (num === null || num === undefined || isNaN(num)) return '0';
    return Number(num).toLocaleString('zh-CN', {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  },

  /**
   * 格式化百分比
   * @param {number} value - 数值 (0-1 或 0-100)
   * @param {number} decimals - 小数位数
   * @returns {string} 百分比字符串
   */
  percent(value, decimals = 1) {
    if (value === null || value === undefined || isNaN(value)) return '0%';
    // 如果值小于等于1，认为是小数形式
    const num = value <= 1 ? value * 100 : value;
    return `${num.toFixed(decimals)}%`;
  },

  /**
   * 格式化文件大小
   * @param {number} bytes - 字节数
   * @param {number} decimals - 小数位数
   * @returns {string} 格式化后的大小
   */
  fileSize(bytes, decimals = 2) {
    if (bytes === 0) return '0 B';

    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));

    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(decimals))} ${sizes[i]}`;
  },

  /**
   * 格式化时长
   * @param {number} seconds - 秒数
   * @returns {string} 格式化后的时长
   */
  duration(seconds) {
    if (!seconds || seconds < 0) return '0:00';

    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);

    if (h > 0) {
      return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
    }
    return `${m}:${String(s).padStart(2, '0')}`;
  },

  /**
   * 格式化时长（带单位）
   * @param {number} minutes - 分钟数
   * @returns {string} 格式化后的时长
   */
  durationMinutes(minutes) {
    if (!minutes || minutes < 0) return '0 分钟';

    const h = Math.floor(minutes / 60);
    const m = minutes % 60;

    if (h > 0 && m > 0) {
      return `${h} 小时 ${m} 分钟`;
    }
    if (h > 0) {
      return `${h} 小时`;
    }
    return `${m} 分钟`;
  },

  /**
   * 截断文本
   * @param {string} text - 文本
   * @param {number} maxLength - 最大长度
   * @param {string} suffix - 后缀
   * @returns {string} 截断后的文本
   */
  truncate(text, maxLength, suffix = '...') {
    if (!text) return '';
    if (text.length <= maxLength) return text;
    return text.slice(0, maxLength - suffix.length) + suffix;
  },

  /**
   * 格式化价格
   * @param {number} price - 价格
   * @param {string} currency - 货币符号
   * @returns {string} 格式化后的价格
   */
  price(price, currency = '¥') {
    if (price === null || price === undefined || isNaN(price)) return `${currency}0`;
    return `${currency}${Number(price).toFixed(2)}`;
  },

  /**
   * 高亮关键词
   * @param {string} text - 文本
   * @param {string} keyword - 关键词
   * @returns {string} 高亮后的 HTML
   */
  highlight(text, keyword) {
    if (!text || !keyword) return text || '';
    const regex = new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    return text.replace(regex, '<mark>$1</mark>');
  },

  /**
   * 首字母大写
   * @param {string} text - 文本
   * @returns {string} 首字母大写的文本
   */
  capitalize(text) {
    if (!text) return '';
    return text.charAt(0).toUpperCase() + text.slice(1);
  },

  /**
   * 驼峰转短横线
   * @param {string} str - 驼峰字符串
   * @returns {string} 短横线字符串
   */
  kebabCase(str) {
    if (!str) return '';
    return str.replace(/([a-z])([A-Z])/g, '$1-$2').toLowerCase();
  },

  /**
   * 格式化评分
   * @param {number} rating - 评分 (1-5)
   * @returns {string} 星星 HTML
   */
  rating(rating) {
    const stars = [];
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;

    for (let i = 0; i < 5; i++) {
      if (i < fullStars) {
        stars.push('<span style="color: #faad14;">★</span>');
      } else if (i === fullStars && hasHalfStar) {
        stars.push('<span style="color: #faad14;">☆</span>');
      } else {
        stars.push('<span style="color: #d9d9d9;">☆</span>');
      }
    }

    return stars.join('');
  },

  /**
   * 格式化状态
   * @param {string} status - 状态码
   * @param {Object} statusMap - 状态映射
   * @returns {Object} 状态对象 {label, color}
   */
  status(status, statusMap = {}) {
    const defaultMap = {
      queued: { label: '队列中', color: 'warning' },
      pending: { label: '待处理', color: 'warning' },
      processing: { label: '处理中', color: 'primary' },
      completed: { label: '已完成', color: 'success' },
      failed: { label: '失败', color: 'error' },
      cancelled: { label: '已取消', color: 'default' },
      active: { label: '活跃', color: 'success' },
      inactive: { label: '未激活', color: 'default' },
    };

    const map = { ...defaultMap, ...statusMap };
    return map[status] || { label: status, color: 'default' };
  },
};

window.Format = Format;

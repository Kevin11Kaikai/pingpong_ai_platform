/**
 * chat.js - LLM 聊天页面逻辑
 */

const ChatPage = {
  /**
   * 当前对话 ID
   */
  currentConversationId: null,

  /**
   * 消息列表
   */
  messages: [],

  /**
   * 是否正在发送
   */
  isSending: false,

  /**
   * 流式响应关闭函数
   */
  closeStream: null,

  /**
   * 初始化
   */
  async init() {
    await this.loadConversations();

    // 恢复上次对话
    const lastConversationId = Storage.get('last_conversation_id');
    if (lastConversationId) {
      await this.selectConversation(lastConversationId);
    }
  },

  /**
   * 加载对话列表
   */
  async loadConversations() {
    const container = document.getElementById('conversationList');
    if (!container) return;

    try {
      const conversations = await llmApi.getConversations();
      this.renderConversationList(conversations);
    } catch (e) {
      console.error('Failed to load conversations:', e);
      container.innerHTML = `
        <div class="empty-state" style="padding: 20px;">
          <div class="text-sm text-secondary">加载失败</div>
        </div>
      `;
    }
  },

  /**
   * 渲染对话列表
   * @param {Array} conversations - 对话列表
   */
  renderConversationList(conversations) {
    const container = document.getElementById('conversationList');
    if (!container) return;

    if (!conversations || conversations.length === 0) {
      container.innerHTML = `
        <div class="empty-state" style="padding: 20px;">
          <div class="text-sm text-secondary">暂无对话</div>
        </div>
      `;
      return;
    }

    container.innerHTML = conversations.map(conv => `
      <div class="chat-list-item ${conv.id === this.currentConversationId ? 'active' : ''}"
           data-id="${conv.id}"
           onclick="ChatPage.selectConversation('${conv.id}')">
        <div class="chat-list-item-title truncate">${conv.title || '新对话'}</div>
        <div class="chat-list-item-preview truncate">${conv.last_message || '暂无消息'}</div>
        <div class="chat-list-item-time">${Format.relativeTime(conv.updated_at)}</div>
      </div>
    `).join('');
  },

  /**
   * 创建新对话
   */
  async createConversation() {
    try {
      const conversation = await llmApi.createConversation();
      await this.loadConversations();
      await this.selectConversation(conversation.id);
      Toast.success('已创建新对话');
    } catch (e) {
      Toast.error('创建对话失败');
    }
  },

  /**
   * 选择对话
   * @param {string} conversationId - 对话 ID
   */
  async selectConversation(conversationId) {
    this.currentConversationId = conversationId;
    Storage.set('last_conversation_id', conversationId);

    // 更新 UI
    document.querySelectorAll('.chat-list-item').forEach(item => {
      item.classList.toggle('active', item.dataset.id === conversationId);
    });

    // 显示删除按钮
    const deleteBtn = document.getElementById('btnDeleteConversation');
    if (deleteBtn) deleteBtn.style.display = 'block';

    // 加载消息
    await this.loadMessages(conversationId);

    // 隐藏空状态
    const emptyState = document.getElementById('emptyState');
    if (emptyState) emptyState.style.display = 'none';

    // 关闭移动端侧边栏
    this.closeSidebar();
  },

  /**
   * 加载消息
   * @param {string} conversationId - 对话 ID
   */
  async loadMessages(conversationId) {
    const container = document.getElementById('messageList');
    if (!container) return;

    try {
      const messages = await llmApi.getMessages(conversationId);
      this.messages = messages;
      this.renderMessages();
    } catch (e) {
      console.error('Failed to load messages:', e);
      this.messages = [];
      this.renderMessages();
    }
  },

  /**
   * 渲染消息列表
   */
  renderMessages() {
    const container = document.getElementById('messageList');
    if (!container) return;

    if (!this.messages || this.messages.length === 0) {
      const emptyState = document.getElementById('emptyState');
      if (emptyState) emptyState.style.display = 'flex';
      return;
    }

    const emptyState = document.getElementById('emptyState');
    if (emptyState) emptyState.style.display = 'none';

    container.innerHTML = this.messages.map(msg => this.renderMessage(msg)).join('');
    this.scrollToBottom();
  },

  /**
   * 渲染单条消息
   * @param {Object} message - 消息对象
   * @returns {string} HTML 字符串
   */
  renderMessage(message) {
    const isUser = message.role === 'user';
    const content = this.renderMarkdown(message.content);

    return `
      <div class="message ${isUser ? 'user' : 'assistant'}">
        <div class="message-avatar">
          <div class="avatar" style="${isUser ? 'background-color: var(--primary-bg); color: var(--primary);' : 'background-color: var(--success-bg); color: var(--success);'}">
            ${isUser ? '我' : 'AI'}
          </div>
        </div>
        <div class="message-content">
          <div class="message-text">${content}</div>
          <div class="message-time">${Format.relativeTime(message.created_at)}</div>
        </div>
      </div>
    `;
  },

  /**
   * 渲染 Markdown
   * @param {string} text - Markdown 文本
   * @returns {string} HTML 字符串
   */
  renderMarkdown(text) {
    if (!text) return '';
    if (typeof marked !== 'undefined') {
      return marked.parse(text);
    }
    return text.replace(/\n/g, '<br>');
  },

  /**
   * 发送消息
   */
  async sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();

    if (!message || this.isSending) return;

    // 如果没有当前对话，创建一个
    if (!this.currentConversationId) {
      try {
        const conversation = await llmApi.createConversation();
        this.currentConversationId = conversation.id;
        await this.loadConversations();
      } catch (e) {
        Toast.error('创建对话失败');
        return;
      }
    }

    // 清空输入框
    input.value = '';
    this.autoResize(input);

    // 添加用户消息
    const userMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };
    this.messages.push(userMessage);
    this.renderMessages();

    // 添加 AI 消息占位
    const aiMessage = {
      id: (Date.now() + 1).toString(),
      role: 'assistant',
      content: '',
      created_at: new Date().toISOString(),
    };
    this.messages.push(aiMessage);

    // 开始发送
    this.isSending = true;
    this.updateSendButton(true);

    // 隐藏空状态
    const emptyState = document.getElementById('emptyState');
    if (emptyState) emptyState.style.display = 'none';

    try {
      // 流式响应
      this.closeStream = llmApi.chatStream(
        {
          message,
          conversation_id: this.currentConversationId,
        },
        {
          onMessage: (data) => {
            if (data.content) {
              aiMessage.content += data.content;
              this.updateLastMessage(aiMessage.content);
            }
          },
          onError: (error) => {
            Toast.error(error.message || '发送失败');
            this.isSending = false;
            this.updateSendButton(false);
          },
          onComplete: () => {
            this.isSending = false;
            this.updateSendButton(false);
            this.loadConversations(); // 刷新列表以更新预览
          },
        }
      );
    } catch (e) {
      Toast.error('发送失败');
      this.isSending = false;
      this.updateSendButton(false);
    }
  },

  /**
   * 更新最后一条消息
   * @param {string} content - 消息内容
   */
  updateLastMessage(content) {
    const container = document.getElementById('messageList');
    if (!container) return;

    const messages = container.querySelectorAll('.message');
    const lastMessage = messages[messages.length - 1];
    if (lastMessage) {
      const textEl = lastMessage.querySelector('.message-text');
      if (textEl) {
        textEl.innerHTML = this.renderMarkdown(content);
      }
    }
    this.scrollToBottom();
  },

  /**
   * 更新发送按钮状态
   * @param {boolean} sending - 是否正在发送
   */
  updateSendButton(sending) {
    const btn = document.getElementById('sendBtn');
    if (!btn) return;

    if (sending) {
      btn.disabled = true;
      btn.innerHTML = `
        <span style="width: 16px; height: 16px; border: 2px solid currentColor; border-top-color: transparent;
                     border-radius: 50%; animation: spin 0.8s linear infinite; display: inline-block;"></span>
      `;
    } else {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
        </svg>
      `;
    }
  },

  /**
   * 滚动到底部
   */
  scrollToBottom() {
    const container = document.getElementById('messageList');
    if (container) {
      container.scrollTop = container.scrollHeight;
    }
  },

  /**
   * 处理输入框键盘事件
   * @param {KeyboardEvent} event - 键盘事件
   */
  handleInputKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      this.sendMessage();
    }
  },

  /**
   * 自动调整输入框高度
   * @param {HTMLTextAreaElement} element - 输入框元素
   */
  autoResize(element) {
    element.style.height = 'auto';
    element.style.height = Math.min(element.scrollHeight, 150) + 'px';
  },

  /**
   * 删除当前对话
   */
  async deleteCurrentConversation() {
    if (!this.currentConversationId) return;

    const confirmed = await Modal.confirm('确定要删除这个对话吗？此操作不可恢复。', {
      danger: true,
      confirmText: '删除',
    });

    if (!confirmed) return;

    try {
      await llmApi.deleteConversation(this.currentConversationId);
      this.currentConversationId = null;
      this.messages = [];
      Storage.remove('last_conversation_id');

      await this.loadConversations();

      // 重置 UI
      const emptyState = document.getElementById('emptyState');
      if (emptyState) emptyState.style.display = 'flex';

      const deleteBtn = document.getElementById('btnDeleteConversation');
      if (deleteBtn) deleteBtn.style.display = 'none';

      const messageList = document.getElementById('messageList');
      if (messageList) {
        messageList.innerHTML = emptyState ? emptyState.outerHTML : '';
      }

      Toast.success('对话已删除');
    } catch (e) {
      Toast.error('删除失败');
    }
  },

  /**
   * 打开知识库管理
   */
  async openDocuments() {
    const content = document.getElementById('documentsModal');
    if (!content) return;

    // 加载文档列表
    await this.loadDocuments();

    Modal.open({
      title: '知识库管理',
      content: content.innerHTML,
      size: 'md',
    });
  },

  /**
   * 加载文档列表
   */
  async loadDocuments() {
    const container = document.getElementById('documentList');
    if (!container) return;

    try {
      const documents = await llmApi.getDocuments();

      if (!documents || documents.length === 0) {
        container.innerHTML = `
          <div class="empty-state">
            <div class="text-sm text-secondary">暂无文档</div>
            <div class="text-xs text-tertiary mt-sm">上传文档以增强 AI 的知识</div>
          </div>
        `;
        return;
      }

      container.innerHTML = `
        <div class="list">
          ${documents.map(doc => `
            <div class="list-item">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color: var(--primary);">
                <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
                <polyline points="14 2 14 8 20 8"/>
              </svg>
              <div class="list-item-content">
                <div class="list-item-title">${doc.filename}</div>
                <div class="list-item-desc">${Format.fileSize(doc.size)} · ${Format.relativeTime(doc.created_at)}</div>
              </div>
              <button class="btn btn-ghost btn-sm" onclick="ChatPage.deleteDocument('${doc.id}')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                </svg>
              </button>
            </div>
          `).join('')}
        </div>
      `;
    } catch (e) {
      container.innerHTML = `<div class="text-sm text-error">加载失败</div>`;
    }
  },

  /**
   * 上传文档
   * @param {Event} event - 文件选择事件
   */
  async uploadDocument(event) {
    const file = event.target.files[0];
    if (!file) return;

    Toast.info('正在上传...');

    try {
      await llmApi.uploadDocument(file);
      Toast.success('文档上传成功');
      await this.loadDocuments();
      Modal.close();
      this.openDocuments(); // 重新打开以刷新
    } catch (e) {
      Toast.error('上传失败: ' + e.message);
    }

    event.target.value = '';
  },

  /**
   * 删除文档
   * @param {string} documentId - 文档 ID
   */
  async deleteDocument(documentId) {
    const confirmed = await Modal.confirm('确定要删除这个文档吗？');
    if (!confirmed) return;

    try {
      await llmApi.deleteDocument(documentId);
      Toast.success('文档已删除');
      Modal.close();
      this.openDocuments();
    } catch (e) {
      Toast.error('删除失败');
    }
  },

  /**
   * 切换侧边栏（移动端）
   */
  toggleSidebar() {
    const sidebar = document.getElementById('chatSidebar');
    if (sidebar) {
      sidebar.classList.toggle('open');
    }
  },

  /**
   * 关闭侧边栏（移动端）
   */
  closeSidebar() {
    const sidebar = document.getElementById('chatSidebar');
    if (sidebar) {
      sidebar.classList.remove('open');
    }
  },
};

// 页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
  ChatPage.init();
});

window.ChatPage = ChatPage;

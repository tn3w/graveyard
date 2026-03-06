import * as api from './api.js';
import * as crypto from './crypto.js';

export class UIManager {
  constructor(application) {
    this.application = application;
    this.currentView = null;
    this.activeChat = null;
    this.chats = new Map();
    this.messages = new Map();
  }

  render() {
    const appElement = document.getElementById('app');
    
    if (!this.application.isAuthenticated()) {
      this.renderAuthView(appElement);
      return;
    }

    this.renderMainView(appElement);
  }

  renderAuthView(container) {
    this.currentView = 'auth';
    
    container.innerHTML = `
      <div class="auth-container">
        <div class="auth-box">
          <h1 id="auth-title">Login</h1>
          <div id="auth-error" class="error-message hidden"></div>
          <form id="auth-form" class="auth-form">
            <div class="form-group">
              <label for="username">Username</label>
              <input 
                type="text" 
                id="username" 
                required 
                autocomplete="username"
              />
            </div>
            <div class="form-group">
              <label for="password">Password</label>
              <input 
                type="password" 
                id="password" 
                required 
                autocomplete="current-password"
                minlength="8"
              />
            </div>
            <button type="submit" class="btn btn-primary" id="auth-submit">
              Login
            </button>
          </form>
          <div class="auth-toggle">
            <span id="auth-toggle-text">Don't have an account?</span>
            <button type="button" id="auth-toggle-btn">Register</button>
          </div>
        </div>
      </div>
    `;

    this.attachAuthListeners();
  }

  attachAuthListeners() {
    const form = document.getElementById('auth-form');
    const toggleBtn = document.getElementById('auth-toggle-btn');
    let isLoginMode = true;

    toggleBtn.addEventListener('click', () => {
      isLoginMode = !isLoginMode;
      const title = document.getElementById('auth-title');
      const submitBtn = document.getElementById('auth-submit');
      const toggleText = document.getElementById('auth-toggle-text');
      
      if (isLoginMode) {
        title.textContent = 'Login';
        submitBtn.textContent = 'Login';
        toggleText.textContent = "Don't have an account?";
        toggleBtn.textContent = 'Register';
      } else {
        title.textContent = 'Register';
        submitBtn.textContent = 'Register';
        toggleText.textContent = 'Already have an account?';
        toggleBtn.textContent = 'Login';
      }
      
      this.hideError();
    });

    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      
      const username = document.getElementById('username').value;
      const password = document.getElementById('password').value;
      const submitBtn = document.getElementById('auth-submit');
      
      submitBtn.disabled = true;
      this.hideError();

      try {
        if (isLoginMode) {
          await this.application.login(username, password);
        } else {
          await this.application.register(username, password);
          await this.application.login(username, password);
        }
        
        this.render();
      } catch (error) {
        this.showError(error.message);
      } finally {
        submitBtn.disabled = false;
      }
    });
  }

  renderMainView(container) {
    this.currentView = 'main';
    
    container.innerHTML = `
      <div class="main-container">
        <div class="sidebar">
          <div class="sidebar-header">
            <h2>Chats</h2>
            <div class="header-actions">
              <button class="icon-btn" id="devices-btn" title="Devices">
                📱
              </button>
              <button class="icon-btn" id="new-chat-btn" title="New Chat">
                ➕
              </button>
              <button class="icon-btn" id="logout-btn" title="Logout">
                🚪
              </button>
            </div>
          </div>
          <div class="search-box">
            <input 
              type="text" 
              id="user-search" 
              placeholder="Search users..."
            />
          </div>
          <div id="chat-list" class="chat-list"></div>
        </div>
        <div class="chat-panel">
          <div id="chat-content"></div>
        </div>
      </div>
    `;

    this.attachMainListeners();
    this.renderEmptyState();
    this.loadChats();
  }

  attachMainListeners() {
    const logoutBtn = document.getElementById('logout-btn');
    const searchInput = document.getElementById('user-search');
    const newChatBtn = document.getElementById('new-chat-btn');
    const devicesBtn = document.getElementById('devices-btn');

    devicesBtn.addEventListener('click', () => {
      this.showDeviceManagement();
    });

    logoutBtn.addEventListener('click', async () => {
      await this.application.logout();
      this.render();
    });

    let searchTimeout;
    searchInput.addEventListener('input', (event) => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(() => {
        this.searchUsers(event.target.value);
      }, 300);
    });

    newChatBtn.addEventListener('click', () => {
      searchInput.focus();
    });

    this.setupWebSocketListeners();
  }

  setupWebSocketListeners() {
    const websocket = this.application.getWebSocket();
    if (!websocket) {
      return;
    }

    websocket.on('message', (event) => this.handleIncomingMessage(event));
    websocket.on('message_edited', (event) => {
      this.handleMessageEdited(event);
    });
    websocket.on('reaction', (event) => this.handleReaction(event));
    websocket.on('typing', (event) => this.handleTypingIndicator(event));
    websocket.on('presence', (event) => this.handlePresenceUpdate(event));
  }

  async loadChats() {
    const session = this.application.getSession();
    
    try {
      const messages = await api.getMessagesCursor(session.accessToken, 50);
      
      const chatMap = new Map();
      
      for (const message of messages.messages) {
        let senderUserId = 'unknown';
        let lastMessagePreview = '[Encrypted]';

        try {
          const conversationId = message.conversation_id;

          if (conversationId) {
            const messageJson = JSON.parse(
              new TextDecoder().decode(
                new Uint8Array(message.encrypted_content)
              )
            );

            const decrypted = await crypto.decryptWithSealedSender(
              conversationId,
              messageJson
            );

            senderUserId = decrypted.senderUserId;
            lastMessagePreview = decrypted.plaintext.substring(0, 50);
          }
        } catch (error) {
          console.error('Failed to decrypt message preview:', error);
        }

        const isOutgoing = senderUserId === session.userId;
        const chatUserId = isOutgoing 
          ? message.recipient_user_id 
          : senderUserId;
        
        if (!chatMap.has(chatUserId) || 
            message.created_at > chatMap.get(chatUserId).created_at) {
          chatMap.set(chatUserId, {
            userId: chatUserId,
            username: isOutgoing 
              ? message.recipient_username 
              : message.sender_username || chatUserId,
            lastMessage: lastMessagePreview,
            timestamp: message.created_at,
          });
        }
      }

      this.chats = chatMap;
      this.renderChatList();
    } catch (error) {
      console.error('Failed to load chats:', error);
    }
  }

  async searchUsers(query) {
    if (!query.trim()) {
      this.renderChatList();
      return;
    }

    const session = this.application.getSession();
    
    try {
      const result = await api.searchUsers(session.accessToken, query, 20);
      this.renderUserSearchResults(result.users);
    } catch (error) {
      console.error('Failed to search users:', error);
    }
  }

  renderUserSearchResults(users) {
    const chatList = document.getElementById('chat-list');
    
    if (users.length === 0) {
      chatList.innerHTML = '<div class="loading">No users found</div>';
      return;
    }

    chatList.innerHTML = users.map(user => `
      <div class="chat-item" data-user-id="${user.id}">
        <div class="chat-avatar">${user.username[0].toUpperCase()}</div>
        <div class="chat-info">
          <div class="chat-name">${this.escapeHtml(user.username)}</div>
          <div class="chat-preview">Click to start chatting</div>
        </div>
      </div>
    `).join('');

    chatList.querySelectorAll('.chat-item').forEach(item => {
      item.addEventListener('click', () => {
        const userId = item.dataset.userId;
        const username = item.querySelector('.chat-name').textContent;
        this.openChat(userId, username);
      });
    });
  }

  renderChatList() {
    const chatList = document.getElementById('chat-list');
    
    if (this.chats.size === 0) {
      chatList.innerHTML = `
        <div class="loading">No chats yet. Search for users to start.</div>
      `;
      return;
    }

    const sortedChats = Array.from(this.chats.values())
      .sort((a, b) => b.timestamp - a.timestamp);

    chatList.innerHTML = sortedChats.map(chat => `
      <div 
        class="chat-item ${this.activeChat?.userId === chat.userId ? 'active' : ''}" 
        data-user-id="${chat.userId}"
      >
        <div class="chat-avatar">${chat.username[0].toUpperCase()}</div>
        <div class="chat-info">
          <div class="chat-name">${this.escapeHtml(chat.username)}</div>
          <div class="chat-preview">${this.escapeHtml(chat.lastMessage)}</div>
        </div>
      </div>
    `).join('');

    chatList.querySelectorAll('.chat-item').forEach(item => {
      item.addEventListener('click', () => {
        const userId = item.dataset.userId;
        const chat = this.chats.get(userId);
        this.openChat(userId, chat.username);
      });
    });
  }

  async openChat(userId, username) {
    const session = this.application.getSession();
    
    try {
      const users = await api.searchUsers(session.accessToken, username);
      const recipientUser = users.users.find(user => user.id === userId);
      
      const recipientDeviceId = recipientUser?.devices?.[0]?.id || null;
      
      const conversations = await api.listConversations(session.accessToken);
      const existingConversation = conversations.find(conv => 
        conv.participant_user_id_1 === userId || 
        conv.participant_user_id_2 === userId
      );
      
      this.activeChat = { 
        userId, 
        username, 
        recipientDeviceId,
        conversationId: existingConversation?.id || null,
        isOnline: false,
      };
    } catch (error) {
      console.error('Failed to fetch recipient info:', error);
      this.activeChat = { 
        userId, 
        username, 
        recipientDeviceId: null,
        conversationId: null,
      };
    }
    
    document.querySelectorAll('.chat-item').forEach(item => {
      item.classList.toggle('active', item.dataset.userId === userId);
    });

    await this.renderChatPanel();
  }

  async renderChatPanel() {
    const chatContent = document.getElementById('chat-content');
    const statusText = this.activeChat.isOnline ? 'Online' : 'Offline';
    const statusClass = this.activeChat.isOnline ? 'online' : 'offline';
    
    chatContent.innerHTML = `
      <div class="chat-header">
        <div class="chat-avatar">
          ${this.activeChat.username[0].toUpperCase()}
        </div>
        <div class="chat-header-info">
          <div class="chat-header-name">
            ${this.escapeHtml(this.activeChat.username)}
          </div>
          <div class="chat-header-status ${statusClass}" id="status-indicator">
            ${statusText}
          </div>
        </div>
        <div id="typing-indicator" class="typing-indicator hidden">
          typing...
        </div>
      </div>
      <div id="message-list" class="message-list"></div>
      <div class="message-input-container">
        <div class="message-input-wrapper">
          <textarea 
            id="message-input" 
            class="message-input" 
            placeholder="Type a message..."
            rows="1"
          ></textarea>
          <button id="send-btn" class="send-btn" title="Send">
            ➤
          </button>
        </div>
      </div>
    `;

    this.attachChatListeners();
    await this.loadMessages();
  }

  attachChatListeners() {
    const messageInput = document.getElementById('message-input');
    const sendBtn = document.getElementById('send-btn');

    messageInput.addEventListener('input', () => {
      messageInput.style.height = 'auto';
      messageInput.style.height = messageInput.scrollHeight + 'px';
      this.sendTypingIndicator();
    });

    messageInput.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendBtn.click();
      }
    });

    sendBtn.addEventListener('click', () => this.sendMessage());
  }

  sendTypingIndicator() {
    const websocket = this.application.getWebSocket();
    if (!websocket || !this.activeChat) {
      return;
    }

    if (this.typingTimeout) {
      clearTimeout(this.typingTimeout);
    }

    if (!this.activeChat.recipientDeviceId) {
      return;
    }

    websocket.send({
      type: 'typing',
      recipient_device_id: this.activeChat.recipientDeviceId,
    });

    this.typingTimeout = setTimeout(() => {
      this.typingTimeout = null;
    }, 3000);
  }

  async loadMessages() {
    const session = this.application.getSession();
    const messageList = document.getElementById('message-list');
    
    messageList.innerHTML = '<div class="loading">Loading messages...</div>';

    try {
      const result = await api.getMessagesCursor(session.accessToken, 50);
      
      const conversationId = this.activeChat.conversationId;

      const chatMessages = conversationId
        ? result.messages.filter(m => m.conversation_id === conversationId)
        : [];

      if (chatMessages.length === 0) {
        messageList.innerHTML = `
          <div class="empty-state">
            <div class="empty-state-icon">💬</div>
            <div class="empty-state-text">No messages yet</div>
            <div class="empty-state-subtext">
              Send a message to start the conversation
            </div>
          </div>
        `;
        return;
      }

      const conversationManager = this.application.getConversationManager();

      const decryptedMessages = [];

      for (const message of chatMessages) {
        try {
          if (message.initialization_data) {
            await conversationManager.handleInitialMessage(
              conversationId,
              message.initialization_data.sender_identity,
              message.initialization_data.associated_data
            );
          }

          const messageJson = JSON.parse(
            new TextDecoder().decode(new Uint8Array(message.encrypted_content))
          );

          const decrypted = await crypto.decryptWithSealedSender(
            conversationId,
            messageJson
          );

          decryptedMessages.push({
            ...message,
            encrypted_content: decrypted.plaintext,
            sender_user_id: decrypted.senderUserId,
          });
        } catch (error) {
          console.error('Failed to decrypt message:', error);
          decryptedMessages.push({
            ...message,
            encrypted_content: '[Decryption failed]',
            sender_user_id: 'unknown',
          });
        }
      }

      this.renderMessages(decryptedMessages);
    } catch (error) {
      console.error('Failed to load messages:', error);
      messageList.innerHTML = `
        <div class="loading">Failed to load messages</div>
      `;
    }
  }

  renderMessages(messages) {
    const session = this.application.getSession();
    const messageList = document.getElementById('message-list');
    
    messageList.innerHTML = messages.map(message => {
      const isOutgoing = message.sender_user_id === session.userId;
      const timestamp = new Date(message.created_at * 1000);
      const timeString = timestamp.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
      });

      const deliveryStatus = this.getDeliveryStatus(message);

      return `
        <div class="message ${isOutgoing ? 'sent' : 'received'}" 
             data-message-id="${message.id}">
          <div class="message-bubble">
            <div class="message-content">
              ${this.escapeHtml(message.encrypted_content)}
            </div>
            <div class="message-footer">
              <span class="message-time">${timeString}</span>
              ${isOutgoing ? `<span class="delivery-status">${deliveryStatus}</span>` : ''}
            </div>
          </div>
        </div>
      `;
    }).join('');

    messageList.scrollTop = messageList.scrollHeight;
  }

  getDeliveryStatus(message) {
    if (message.read_at) {
      return '✓✓';
    }
    if (message.delivered_at) {
      return '✓✓';
    }
    return '✓';
  }

  async sendMessage() {
    const messageInput = document.getElementById('message-input');
    const content = messageInput.value.trim();
    
    if (!content) {
      return;
    }

    const session = this.application.getSession();
    const sendBtn = document.getElementById('send-btn');
    
    sendBtn.disabled = true;

    try {
      const recipientUserId = this.activeChat.userId;
      const recipientDeviceId = this.activeChat.recipientDeviceId;
      
      if (!recipientDeviceId) {
        throw new Error('Recipient device not found');
      }

      let conversationId = this.activeChat.conversationId;

      if (!conversationId) {
        const conversation = await api.createConversation(
          session.accessToken,
          recipientUserId
        );
        conversationId = conversation.id;
        this.activeChat.conversationId = conversationId;
      }

      const conversationManager = this.application.getConversationManager();
      await conversationManager.initializeConversation(
        conversationId,
        recipientDeviceId
      );

      const encryptedMessage = await crypto.encryptWithSealedSender(
        conversationId,
        content,
        session.userId
      );

      const encryptedContent = Array.from(
        new TextEncoder().encode(JSON.stringify(encryptedMessage))
      );

      await api.sendMessage(
        session.accessToken,
        conversationId,
        encryptedContent
      );

      messageInput.value = '';
      messageInput.style.height = 'auto';
      
      await this.loadMessages();
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('Failed to send message: ' + error.message);
    } finally {
      sendBtn.disabled = false;
    }
  }

  getConversationId(userId1, userId2) {
    const sorted = [userId1, userId2].sort();
    return `conv_${sorted[0]}_${sorted[1]}`;
  }

  async handleIncomingMessage(event) {
    const session = this.application.getSession();
    const conversationManager = this.application.getConversationManager();
    
    try {
      const conversationId = event.conversation_id;

      if (event.initialization_data) {
        await conversationManager.handleInitialMessage(
          conversationId,
          event.initialization_data.sender_identity,
          event.initialization_data.associated_data
        );
      }

      const messageJson = JSON.parse(
        new TextDecoder().decode(new Uint8Array(event.encrypted_content))
      );

      const decrypted = await crypto.decryptWithSealedSender(
        conversationId,
        messageJson
      );

      event.encrypted_content = decrypted.plaintext;
      event.sender_user_id = decrypted.senderUserId;
    } catch (error) {
      console.error('Failed to decrypt incoming message:', error);
      event.encrypted_content = '[Decryption failed]';
      event.sender_user_id = 'unknown';
    }
    
    const isRelevant = event.sender_user_id === this.activeChat?.userId ||
                       event.recipient_user_id === this.activeChat?.userId;
    
    if (isRelevant && this.activeChat) {
      this.addMessageToUI(event);
    }
    
    this.loadChats();
    
    if (event.recipient_device_id === session.deviceId) {
      this.sendDeliveryReceipt(event.id);
    }
  }

  addMessageToUI(messageEvent) {
    const messageList = document.getElementById('message-list');
    if (!messageList) {
      return;
    }

    const emptyState = messageList.querySelector('.empty-state');
    const loadingState = messageList.querySelector('.loading');
    if (emptyState || loadingState) {
      messageList.innerHTML = '';
    }

    const session = this.application.getSession();
    const isOutgoing = messageEvent.sender_user_id === session.userId;
    const timestamp = new Date(messageEvent.created_at * 1000);
    const timeString = timestamp.toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });

    const messageElement = document.createElement('div');
    messageElement.className = `message ${isOutgoing ? 'sent' : 'received'} message-appear`;
    messageElement.dataset.messageId = messageEvent.id;
    messageElement.innerHTML = `
      <div class="message-bubble">
        <div class="message-content">
          ${this.escapeHtml(messageEvent.encrypted_content)}
        </div>
        <div class="message-footer">
          <span class="message-time">${timeString}</span>
          ${isOutgoing ? '<span class="delivery-status">✓</span>' : ''}
        </div>
      </div>
    `;

    messageList.appendChild(messageElement);
    messageList.scrollTop = messageList.scrollHeight;
  }

  sendDeliveryReceipt(messageId) {
    const websocket = this.application.getWebSocket();
    if (!websocket) {
      return;
    }

    websocket.send({
      type: 'delivery_receipt',
      message_id: messageId,
    });
  }

  handleMessageEdited(event) {
    if (!this.activeChat) {
      return;
    }

    const messageElement = document.querySelector(
      `[data-message-id="${event.message_id}"]`
    );
    
    if (messageElement) {
      const contentElement = messageElement.querySelector('.message-content');
      if (contentElement) {
        contentElement.textContent = event.new_content;
        contentElement.classList.add('edited');
      }
    }
  }

  handleReaction(event) {
    if (!this.activeChat) {
      return;
    }

    const messageElement = document.querySelector(
      `[data-message-id="${event.message_id}"]`
    );
    
    if (messageElement) {
      let reactionsContainer = messageElement.querySelector('.reactions');
      
      if (!reactionsContainer) {
        reactionsContainer = document.createElement('div');
        reactionsContainer.className = 'reactions';
        messageElement.querySelector('.message-bubble').appendChild(reactionsContainer);
      }
      
      const reactionElement = document.createElement('span');
      reactionElement.className = 'reaction';
      reactionElement.textContent = event.emoji;
      reactionsContainer.appendChild(reactionElement);
    }
  }

  handleTypingIndicator(event) {
    if (!this.activeChat) {
      return;
    }

    const session = this.application.getSession();
    if (event.sender_user_id !== this.activeChat.userId) {
      return;
    }

    const typingIndicator = document.getElementById('typing-indicator');
    if (!typingIndicator) {
      return;
    }

    typingIndicator.classList.remove('hidden');

    if (this.typingIndicatorTimeout) {
      clearTimeout(this.typingIndicatorTimeout);
    }

    this.typingIndicatorTimeout = setTimeout(() => {
      typingIndicator.classList.add('hidden');
    }, 3000);
  }

  handlePresenceUpdate(event) {
    if (!this.activeChat) {
      return;
    }

    if (event.user_id !== this.activeChat.userId) {
      return;
    }

    this.activeChat.isOnline = event.status === 'online';
    
    const statusIndicator = document.getElementById('status-indicator');
    if (statusIndicator) {
      statusIndicator.textContent = this.activeChat.isOnline ? 'Online' : 'Offline';
      statusIndicator.className = `chat-header-status ${this.activeChat.isOnline ? 'online' : 'offline'}`;
    }
  }

  renderEmptyState() {
    const chatContent = document.getElementById('chat-content');
    
    chatContent.innerHTML = `
      <div class="empty-state">
        <div class="empty-state-icon">💬</div>
        <div class="empty-state-text">Select a chat to start messaging</div>
        <div class="empty-state-subtext">
          Search for users to begin a conversation
        </div>
      </div>
    `;
  }

  showError(message) {
    const errorElement = document.getElementById('auth-error');
    
    if (errorElement) {
      errorElement.textContent = message;
      errorElement.classList.remove('hidden');
    }
  }

  hideError() {
    const errorElement = document.getElementById('auth-error');
    
    if (errorElement) {
      errorElement.classList.add('hidden');
    }
  }

  escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  async showDeviceManagement() {
    const session = this.application.getSession();
    
    if (!session) {
      return;
    }

    try {
      const devices = await api.listDevices(session.accessToken);
      
      const modal = document.createElement('div');
      modal.className = 'modal-overlay';
      modal.innerHTML = `
        <div class="modal-content">
          <div class="modal-header">
            <h2>Device Management</h2>
            <button class="modal-close" id="close-devices">&times;</button>
          </div>
          <div class="modal-body">
            <div class="sync-section">
              <h3>History Sync</h3>
              <p>Request message history from your other devices</p>
              <button class="btn btn-primary" id="request-sync-btn">
                Request History Sync
              </button>
            </div>
            <div class="devices-list">
              ${devices.map(device => `
                <div class="device-item" data-device-id="${device.id}">
                  <div class="device-info">
                    <div class="device-name">
                      ${device.id === session.deviceId ? '📱 This Device' : '💻 Device'}
                    </div>
                    <div class="device-details">
                      ID: ${this.escapeHtml(device.id.substring(0, 8))}...
                    </div>
                    <div class="device-details">
                      Last seen: ${new Date(device.last_seen * 1000).toLocaleString()}
                    </div>
                  </div>
                  ${device.id !== session.deviceId ? `
                    <button class="btn btn-danger device-delete" data-device-id="${device.id}">
                      Remove
                    </button>
                  ` : ''}
                </div>
              `).join('')}
            </div>
          </div>
        </div>
      `;
      
      document.body.appendChild(modal);
      
      document.getElementById('close-devices').addEventListener('click', () => {
        modal.remove();
      });
      
      document.getElementById('request-sync-btn').addEventListener('click', async () => {
        try {
          await this.application.requestHistorySync();
          alert('History sync requested. Your other devices will be notified.');
        } catch (error) {
          console.error('Failed to request sync:', error);
          alert('Failed to request history sync: ' + error.message);
        }
      });
      
      modal.addEventListener('click', (event) => {
        if (event.target === modal) {
          modal.remove();
        }
      });
      
      modal.querySelectorAll('.device-delete').forEach(button => {
        button.addEventListener('click', async (event) => {
          const deviceId = event.target.dataset.deviceId;
          
          if (confirm('Are you sure you want to remove this device?')) {
            try {
              await api.deleteDevice(session.accessToken, deviceId);
              modal.remove();
              this.showDeviceManagement();
            } catch (error) {
              console.error('Failed to delete device:', error);
              alert('Failed to remove device: ' + error.message);
            }
          }
        });
      });
    } catch (error) {
      console.error('Failed to load devices:', error);
      alert('Failed to load devices: ' + error.message);
    }
  }
}

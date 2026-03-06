import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { UIManager } from './ui.js';

vi.mock('./crypto.js', () => ({
  initializeCrypto: vi.fn().mockResolvedValue(undefined),
  generateKeyPair: vi.fn().mockResolvedValue({
    publicKey: 'mock-public-key',
    secretKey: 'mock-secret-key',
  }),
  decryptMessage: vi.fn((context, encrypted) => {
    if (typeof encrypted === 'string') {
      return encrypted;
    }
    return 'Decrypted message';
  }),
  decryptWithSealedSender: vi.fn((conversationId, messageJson) => {
    return Promise.resolve({
      plaintext: messageJson.plaintext || 'Decrypted message',
      senderUserId: messageJson.senderUserId || 'user1',
    });
  }),
}));

vi.mock('./api.js', () => ({
  registerUser: vi.fn(),
  loginUser: vi.fn(),
  getCurrentUser: vi.fn(),
  searchUsers: vi.fn().mockResolvedValue({ users: [] }),
  sendMessage: vi.fn(),
  getMessages: vi.fn(),
  getMessagesCursor: vi.fn().mockResolvedValue({ messages: [] }),
  editMessage: vi.fn(),
  createGroup: vi.fn(),
  getGroups: vi.fn(),
  getGroupMembers: vi.fn(),
  addGroupMember: vi.fn(),
  removeGroupMember: vi.fn(),
  sendGroupMessage: vi.fn(),
  addReaction: vi.fn(),
  getReactions: vi.fn(),
  removeReaction: vi.fn(),
  listDevices: vi.fn(),
  deleteDevice: vi.fn(),
}));

describe('UIManager', () => {
  let uiManager;
  let mockApplication;
  let container;

  beforeEach(() => {
    container = document.createElement('div');
    container.id = 'app';
    document.body.innerHTML = '';
    document.body.appendChild(container);

    mockApplication = {
      isAuthenticated: vi.fn(() => false),
      getSession: vi.fn(() => null),
      getCryptoContext: vi.fn(() => ({})),
      getWebSocket: vi.fn(() => null),
      getDatabase: vi.fn(() => null),
      getConversationManager: vi.fn(() => null),
      login: vi.fn(),
      register: vi.fn(),
      logout: vi.fn(),
    };

    uiManager = new UIManager(mockApplication);
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  describe('Authentication View', () => {
    it('should render login form when not authenticated', () => {
      uiManager.render();

      expect(container.querySelector('.auth-container')).toBeTruthy();
      expect(container.querySelector('#auth-title').textContent).toBe('Login');
      expect(container.querySelector('#auth-submit').textContent.trim()).toBe('Login');
    });

    it('should toggle between login and register modes', () => {
      uiManager.render();

      const toggleBtn = container.querySelector('#auth-toggle-btn');
      const title = container.querySelector('#auth-title');
      const submitBtn = container.querySelector('#auth-submit');

      toggleBtn.click();

      expect(title.textContent).toBe('Register');
      expect(submitBtn.textContent).toBe('Register');

      toggleBtn.click();

      expect(title.textContent).toBe('Login');
      expect(submitBtn.textContent).toBe('Login');
    });

    it('should call login on form submit in login mode', async () => {
      mockApplication.login.mockResolvedValue({});
      uiManager.render();

      const form = container.querySelector('#auth-form');
      const usernameInput = container.querySelector('#username');
      const passwordInput = container.querySelector('#password');

      usernameInput.value = 'testuser';
      passwordInput.value = 'password123';

      form.dispatchEvent(new Event('submit'));

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(mockApplication.login).toHaveBeenCalledWith('testuser', 'password123');
    });

    it('should show error message on login failure', async () => {
      mockApplication.login.mockRejectedValue(new Error('Invalid credentials'));
      uiManager.render();

      const form = container.querySelector('#auth-form');
      const usernameInput = container.querySelector('#username');
      const passwordInput = container.querySelector('#password');

      usernameInput.value = 'testuser';
      passwordInput.value = 'wrongpassword';

      form.dispatchEvent(new Event('submit'));

      await new Promise(resolve => setTimeout(resolve, 0));

      const errorElement = container.querySelector('#auth-error');
      expect(errorElement.classList.contains('hidden')).toBe(false);
      expect(errorElement.textContent).toBe('Invalid credentials');
    });
  });

  describe('Main View', () => {
    beforeEach(() => {
      mockApplication.isAuthenticated.mockReturnValue(true);
      mockApplication.getSession.mockReturnValue({
        token: 'test-token',
        username: 'testuser',
        deviceId: 'device-123',
      });
    });

    it('should render main view when authenticated', () => {
      uiManager.render();

      expect(container.querySelector('.main-container')).toBeTruthy();
      expect(container.querySelector('.sidebar')).toBeTruthy();
      expect(container.querySelector('.chat-panel')).toBeTruthy();
    });

    it('should render empty state initially', () => {
      uiManager.render();

      const emptyState = container.querySelector('.empty-state');
      expect(emptyState).toBeTruthy();
      expect(emptyState.textContent).toContain('Select a chat');
    });

    it('should call logout on logout button click', async () => {
      uiManager.render();

      const logoutBtn = container.querySelector('#logout-btn');
      logoutBtn.click();

      await new Promise(resolve => setTimeout(resolve, 0));

      expect(mockApplication.logout).toHaveBeenCalled();
    });
  });

  describe('Chat List', () => {
    beforeEach(() => {
      mockApplication.isAuthenticated.mockReturnValue(true);
      mockApplication.getSession.mockReturnValue({
        token: 'test-token',
        username: 'testuser',
        deviceId: 'device-123',
      });
    });

    it('should render chat items', () => {
      uiManager.render();

      uiManager.chats.set('user1', {
        userId: 'user1',
        username: 'alice',
        lastMessage: 'Hello there',
        timestamp: Date.now() / 1000,
      });

      uiManager.renderChatList();

      const chatItems = container.querySelectorAll('.chat-item');
      expect(chatItems.length).toBe(1);
      expect(chatItems[0].querySelector('.chat-name').textContent).toBe('alice');
    });

    it('should escape HTML in chat names', () => {
      uiManager.render();

      uiManager.chats.set('user1', {
        userId: 'user1',
        username: '<script>alert("xss")</script>',
        lastMessage: 'Hello',
        timestamp: Date.now() / 1000,
      });

      uiManager.renderChatList();

      const chatName = container.querySelector('.chat-name');
      expect(chatName.innerHTML).not.toContain('<script>');
      expect(chatName.textContent).toContain('<script>');
    });
  });

  describe('Message Rendering', () => {
    beforeEach(() => {
      mockApplication.isAuthenticated.mockReturnValue(true);
      mockApplication.getSession.mockReturnValue({
        token: 'test-token',
        username: 'testuser',
        deviceId: 'device-123',
      });
    });

    it('should render messages correctly', () => {
      mockApplication.isAuthenticated.mockReturnValue(true);
      mockApplication.getSession.mockReturnValue({
        userId: 'current-user',
        accessToken: 'token',
      });

      uiManager.render();

      const messages = [
        {
          id: 'msg1',
          sender_user_id: 'current-user',
          encrypted_content: 'Hello',
          created_at: Date.now() / 1000,
        },
        {
          id: 'msg2',
          sender_user_id: 'user1',
          encrypted_content: 'Hi there',
          created_at: Date.now() / 1000,
        },
      ];

      uiManager.activeChat = { userId: 'user1', username: 'alice' };
      uiManager.renderChatPanel();
      
      const messageList = container.querySelector('#message-list');
      messageList.innerHTML = '';
      
      uiManager.renderMessages(messages);

      const messageElements = container.querySelectorAll('.message');
      expect(messageElements.length).toBe(2);
      expect(messageElements[0].classList.contains('sent')).toBe(true);
      expect(messageElements[1].classList.contains('received')).toBe(true);
    });

    it('should escape HTML in message content', () => {
      uiManager.render();

      const messages = [
        {
          id: 'msg1',
          sender_device_id: 'device-123',
          encrypted_content: '<img src=x onerror=alert(1)>',
          created_at: Date.now() / 1000,
        },
      ];

      uiManager.activeChat = { userId: 'user1', username: 'alice' };
      uiManager.renderChatPanel();
      
      const messageList = container.querySelector('#message-list');
      messageList.innerHTML = '';
      
      uiManager.renderMessages(messages);

      const messageContent = container.querySelector('.message-content');
      expect(messageContent.innerHTML).not.toContain('<img');
      expect(messageContent.textContent).toContain('<img');
    });
  });

  describe('Utility Functions', () => {
    it('should escape HTML correctly', () => {
      const escaped = uiManager.escapeHtml('<script>alert("xss")</script>');
      expect(escaped).not.toContain('<script>');
      expect(escaped).toContain('&lt;script&gt;');
    });

    it('should handle special characters', () => {
      const escaped = uiManager.escapeHtml('Test & "quotes" <tags>');
      expect(escaped).toContain('&amp;');
      expect(escaped).toContain('&lt;');
      expect(escaped).toContain('&gt;');
    });
  });

  describe('Real-time Features', () => {
    beforeEach(() => {
      mockApplication.isAuthenticated.mockReturnValue(true);
      mockApplication.getSession.mockReturnValue({
        token: 'test-token',
        username: 'testuser',
        deviceId: 'device-123',
      });
    });

    it('should handle incoming messages in real-time', async () => {
      const mockConversationManager = {
        handleInitialMessage: vi.fn(),
      };
      mockApplication.getConversationManager.mockReturnValue(
        mockConversationManager
      );
      mockApplication.isAuthenticated.mockReturnValue(true);
      mockApplication.getSession.mockReturnValue({
        userId: 'current-user',
        deviceId: 'device-123',
        accessToken: 'token',
      });

      uiManager.render();
      uiManager.activeChat = { 
        userId: 'user1', 
        username: 'alice',
        conversationId: 'conv-123',
      };
      uiManager.renderChatPanel();

      const encryptedContent = new TextEncoder().encode(
        JSON.stringify({
          plaintext: 'Hello in real-time',
          senderUserId: 'user1',
        })
      );

      const messageEvent = {
        id: 'msg1',
        conversation_id: 'conv-123',
        sender_user_id: 'user1',
        sender_device_id: 'device-456',
        recipient_user_id: 'current-user',
        recipient_device_id: 'device-123',
        encrypted_content: Array.from(encryptedContent),
        created_at: Date.now() / 1000,
      };

      await uiManager.handleIncomingMessage(messageEvent);

      const messageList = container.querySelector('#message-list');
      expect(messageList.textContent).toContain('Hello in real-time');
    });

    it('should display typing indicator', () => {
      uiManager.render();
      uiManager.activeChat = { userId: 'user1', username: 'alice' };
      uiManager.renderChatPanel();

      const typingEvent = {
        sender_user_id: 'user1',
        sender_device_id: 'device-456',
      };

      uiManager.handleTypingIndicator(typingEvent);

      const typingIndicator = container.querySelector('#typing-indicator');
      expect(typingIndicator.classList.contains('hidden')).toBe(false);
    });

    it('should hide typing indicator after timeout', async () => {
      vi.useFakeTimers();
      uiManager.render();
      uiManager.activeChat = { userId: 'user1', username: 'alice' };
      uiManager.renderChatPanel();

      const typingEvent = {
        sender_user_id: 'user1',
        sender_device_id: 'device-456',
      };

      uiManager.handleTypingIndicator(typingEvent);

      vi.advanceTimersByTime(3000);

      const typingIndicator = container.querySelector('#typing-indicator');
      expect(typingIndicator.classList.contains('hidden')).toBe(true);

      vi.useRealTimers();
    });

    it('should update presence status to online', () => {
      uiManager.render();
      uiManager.activeChat = { userId: 'user1', username: 'alice', isOnline: false };
      uiManager.renderChatPanel();

      const presenceEvent = {
        user_id: 'user1',
        status: 'online',
      };

      uiManager.handlePresenceUpdate(presenceEvent);

      const statusIndicator = container.querySelector('#status-indicator');
      expect(statusIndicator.textContent).toBe('Online');
      expect(statusIndicator.classList.contains('online')).toBe(true);
    });

    it('should update presence status to offline', () => {
      uiManager.render();
      uiManager.activeChat = { userId: 'user1', username: 'alice', isOnline: true };
      uiManager.renderChatPanel();

      const presenceEvent = {
        user_id: 'user1',
        status: 'offline',
      };

      uiManager.handlePresenceUpdate(presenceEvent);

      const statusIndicator = container.querySelector('#status-indicator');
      expect(statusIndicator.textContent).toBe('Offline');
      expect(statusIndicator.classList.contains('offline')).toBe(true);
    });

    it('should handle message edits in real-time', () => {
      uiManager.render();
      uiManager.activeChat = { userId: 'user1', username: 'alice' };
      uiManager.renderChatPanel();

      const messageList = container.querySelector('#message-list');
      messageList.innerHTML = `
        <div class="message" data-message-id="msg1">
          <div class="message-bubble">
            <div class="message-content">Original message</div>
          </div>
        </div>
      `;

      const editEvent = {
        message_id: 'msg1',
        new_content: 'Edited message',
      };

      uiManager.handleMessageEdited(editEvent);

      const messageContent = container.querySelector('.message-content');
      expect(messageContent.textContent).toBe('Edited message');
      expect(messageContent.classList.contains('edited')).toBe(true);
    });

    it('should handle reactions in real-time', () => {
      uiManager.render();
      uiManager.activeChat = { userId: 'user1', username: 'alice' };
      uiManager.renderChatPanel();

      const messageList = container.querySelector('#message-list');
      messageList.innerHTML = `
        <div class="message" data-message-id="msg1">
          <div class="message-bubble">
            <div class="message-content">Test message</div>
          </div>
        </div>
      `;

      const reactionEvent = {
        message_id: 'msg1',
        emoji: '👍',
      };

      uiManager.handleReaction(reactionEvent);

      const reactions = container.querySelector('.reactions');
      expect(reactions).toBeTruthy();
      expect(reactions.textContent).toContain('👍');
    });

    it('should display delivery status for sent messages', () => {
      uiManager.render();
      uiManager.activeChat = { userId: 'user1', username: 'alice' };
      uiManager.renderChatPanel();

      const messages = [
        {
          id: 'msg1',
          sender_device_id: 'device-123',
          encrypted_content: 'Test message',
          created_at: Date.now() / 1000,
        },
      ];

      uiManager.renderMessages(messages);

      const deliveryStatus = container.querySelector('.delivery-status');
      expect(deliveryStatus).toBeTruthy();
      expect(deliveryStatus.textContent).toBe('✓');
    });

    it('should send typing indicator on input', () => {
      const mockWebSocket = {
        send: vi.fn(),
        on: vi.fn(),
      };
      mockApplication.getWebSocket.mockReturnValue(mockWebSocket);

      uiManager.render();
      uiManager.activeChat = { 
        userId: 'user1', 
        username: 'alice',
        recipientDeviceId: 'device-456',
      };
      uiManager.renderChatPanel();

      const messageInput = container.querySelector('#message-input');
      messageInput.value = 'Hello';
      messageInput.dispatchEvent(new Event('input'));

      expect(mockWebSocket.send).toHaveBeenCalledWith({
        type: 'typing',
        recipient_device_id: 'device-456',
      });
    });
  });
});

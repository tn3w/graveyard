import * as storage from './storage.js';
import * as crypto from './crypto.js';
import * as auth from './auth.js';
import { WebSocketManager } from './websocket.js';
import { UIManager } from './ui.js';
import { ConversationManager } from './conversation-manager.js';

class Application {
  constructor() {
    this.database = null;
    this.session = null;
    this.cryptoContext = null;
    this.websocket = null;
    this.ui = null;
    this.conversationManager = null;
  }

  async initialize() {
    try {
      await crypto.initializeCrypto();
      this.database = await storage.initializeDatabase();
      this.session = await auth.restoreSession(this.database);

      if (this.session) {
        this.cryptoContext = this.session.context;
        this.conversationManager = new ConversationManager(
          this.session,
          this.database
        );
        await this.conversationManager.initialize();
        this.connectWebSocket();
      }

      return true;
    } catch (error) {
      console.error('Failed to initialize application:', error);
      throw error;
    }
  }

  async login(username, password) {
    this.session = await auth.login(this.database, username, password);
    this.cryptoContext = this.session.context;
    this.conversationManager = new ConversationManager(
      this.session,
      this.database
    );
    await this.conversationManager.initialize();
    this.connectWebSocket();
    return this.session;
  }

  async register(username, password) {
    await auth.register(this.database, username, password);
  }

  async logout() {
    const refreshToken = this.session?.refreshToken;

    if (this.websocket) {
      this.websocket.disconnect();
      this.websocket = null;
    }

    if (this.session?.tokenManager) {
      this.session.tokenManager.clear();
    }

    await auth.logout(this.database, refreshToken);
    this.session = null;
    this.cryptoContext = null;
    this.conversationManager = null;
  }

  connectWebSocket() {
    if (!this.session) {
      return;
    }

    this.websocket = new WebSocketManager(
      this.session.accessToken,
      this.session.tokenManager
    );
    this.websocket.connect();

    this.websocket.on('connected', () => {
      console.log('WebSocket connected');
    });

    this.websocket.on('disconnected', () => {
      console.log('WebSocket disconnected');
    });

    this.websocket.on('error', (error) => {
      console.error('WebSocket error:', error);
    });
  }

  isAuthenticated() {
    return this.session !== null;
  }

  getSession() {
    return this.session;
  }

  getCryptoContext() {
    return this.cryptoContext;
  }

  getWebSocket() {
    return this.websocket;
  }

  getDatabase() {
    return this.database;
  }

  getConversationManager() {
    return this.conversationManager;
  }
}

const application = new Application();

async function initializeApplication() {
  const appElement = document.getElementById('app');
  appElement.textContent = 'Initializing application...';

  try {
    await application.initialize();
    
    application.ui = new UIManager(application);
    application.ui.render();
  } catch (error) {
    appElement.textContent = `Error: ${error.message}`;
    console.error('Initialization error:', error);
  }
}

initializeApplication();

export { application };

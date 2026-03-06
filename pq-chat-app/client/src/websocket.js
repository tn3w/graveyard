const WEBSOCKET_URL = '/ws';
const RECONNECT_DELAY = 3000;
const MAX_RECONNECT_ATTEMPTS = 10;
const AUTH_RESPONSE_TIMEOUT = 11000;

export class WebSocketManager {
  constructor(token, tokenManager = null) {
    this.token = token;
    this.tokenManager = tokenManager;
    this.socket = null;
    this.reconnectAttempts = 0;
    this.reconnectTimer = null;
    this.listeners = new Map();
    this.isIntentionallyClosed = false;
    this.authTimer = null;
    this.isAuthenticated = false;
  }

  async updateToken() {
    if (this.tokenManager) {
      try {
        this.token = await this.tokenManager.ensureValidToken();
      } catch (error) {
        console.error('Failed to update token:', error);
        throw error;
      }
    }
  }

  connect() {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return;
    }

    this.isIntentionallyClosed = false;
    this.isAuthenticated = false;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const url = `${protocol}//${host}${WEBSOCKET_URL}`;

    this.socket = new WebSocket(url);
    this.socket.onopen = () => this.handleOpen();
    this.socket.onmessage = (event) => this.handleMessage(event);
    this.socket.onerror = (error) => this.handleError(error);
    this.socket.onclose = () => this.handleClose();
  }

  disconnect() {
    this.isIntentionallyClosed = true;
    
    this.clearAuthTimer();
    this.clearReconnectTimer();

    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }

  send(event) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(event));
    }
  }

  on(eventType, callback) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, []);
    }
    this.listeners.get(eventType).push(callback);
  }

  off(eventType, callback) {
    const callbacks = this.listeners.get(eventType);
    if (!callbacks) {
      return;
    }

    const index = callbacks.indexOf(callback);
    if (index !== -1) {
      callbacks.splice(index, 1);
    }
  }

  async handleOpen() {
    this.reconnectAttempts = 0;
    await this.sendAuth();
    this.startAuthTimer();
  }

  async sendAuth() {
    await this.updateToken();
    this.send({ type: 'auth', token: this.token });
  }

  startAuthTimer() {
    this.clearAuthTimer();
    this.authTimer = setTimeout(() => {
      if (!this.isAuthenticated) {
        this.sendAuth();
        this.startAuthTimer();
      }
    }, AUTH_RESPONSE_TIMEOUT);
  }

  clearAuthTimer() {
    if (this.authTimer) {
      clearTimeout(this.authTimer);
      this.authTimer = null;
    }
  }

  clearReconnectTimer() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  handleMessage(event) {
    try {
      const data = JSON.parse(event.data);
      
      if (Array.isArray(data)) {
        for (const item of data) {
          this.processEvent(item);
        }
      } else {
        this.processEvent(data);
      }
    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  processEvent(event) {
    const eventType = event.type || event.event_type;
    if (!eventType) {
      return;
    }

    if (this.shouldReauthenticate(eventType, event)) {
      this.handleReauthentication(event);
      return;
    }

    if (this.isAuthSuccess(eventType, event)) {
      this.handleAuthSuccess();
    }

    this.emit(eventType, event);
  }

  shouldReauthenticate(eventType, event) {
    if (eventType !== 'error') {
      return false;
    }

    const authErrors = [
      'Authentication timeout',
      'Invalid token',
      'Auth required'
    ];

    return authErrors.includes(event.message);
  }

  handleReauthentication(event) {
    this.isAuthenticated = false;
    this.sendAuth();
    this.startAuthTimer();
  }

  isAuthSuccess(eventType, event) {
    return eventType === 'presence' && event.is_online === true;
  }

  handleAuthSuccess() {
    if (!this.isAuthenticated) {
      this.isAuthenticated = true;
      this.clearAuthTimer();
      this.emit('connected');
    }
  }

  handleError(error) {
    console.error('WebSocket error:', error);
    this.emit('error', error);
  }

  handleClose() {
    this.clearAuthTimer();
    this.isAuthenticated = false;
    this.emit('disconnected');

    if (this.isIntentionallyClosed) {
      return;
    }

    if (this.reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
      this.reconnectAttempts++;
      this.reconnectTimer = setTimeout(() => {
        this.connect();
      }, RECONNECT_DELAY);
    } else {
      this.emit('reconnect_failed');
    }
  }

  emit(eventType, data = null) {
    const callbacks = this.listeners.get(eventType);
    if (!callbacks) {
      return;
    }

    for (const callback of callbacks) {
      try {
        callback(data);
      } catch (error) {
        console.error(`Error in ${eventType} listener:`, error);
      }
    }
  }
}

export function sendTypingIndicator(manager, recipientDeviceId) {
  manager.send({
    type: 'typing',
    recipient_device_id: recipientDeviceId,
  });
}

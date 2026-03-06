import * as api from './api.js';
import * as storage from './storage.js';

const TOKEN_REFRESH_THRESHOLD = 60 * 1000;
const TOKEN_EXPIRY_TIME = 15 * 60 * 1000;

class TokenManager {
  constructor(database) {
    this.database = database;
    this.accessToken = null;
    this.refreshToken = null;
    this.tokenExpiresAt = null;
    this.refreshTimer = null;
    this.isRefreshing = false;
    this.refreshPromise = null;
  }

  setTokens(accessToken, refreshToken) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    this.tokenExpiresAt = Date.now() + TOKEN_EXPIRY_TIME;
    this.scheduleRefresh();
  }

  getAccessToken() {
    return this.accessToken;
  }

  getRefreshToken() {
    return this.refreshToken;
  }

  scheduleRefresh() {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
    }

    if (!this.tokenExpiresAt) {
      return;
    }

    const timeUntilRefresh = this.tokenExpiresAt - Date.now() - TOKEN_REFRESH_THRESHOLD;

    if (timeUntilRefresh > 0) {
      this.refreshTimer = setTimeout(() => {
        this.refresh().catch(error => {
          console.error('Scheduled token refresh failed:', error);
        });
      }, timeUntilRefresh);
    }
  }

  async refresh() {
    if (this.isRefreshing) {
      return this.refreshPromise;
    }

    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    this.isRefreshing = true;
    this.refreshPromise = this.performRefresh();

    try {
      const result = await this.refreshPromise;
      return result;
    } finally {
      this.isRefreshing = false;
      this.refreshPromise = null;
    }
  }

  async performRefresh() {
    try {
      const response = await api.refreshToken(this.refreshToken);

      this.setTokens(response.access_token, response.refresh_token);

      await storage.saveSession(
        this.database,
        response.access_token,
        response.refresh_token,
        response.user_id,
        response.device_id
      );

      return response.access_token;
    } catch (error) {
      console.error('Token refresh failed:', error);
      this.clear();
      throw error;
    }
  }

  async ensureValidToken() {
    if (!this.accessToken) {
      throw new Error('No access token available');
    }

    const timeUntilExpiry = this.tokenExpiresAt - Date.now();

    if (timeUntilExpiry < TOKEN_REFRESH_THRESHOLD) {
      await this.refresh();
    }

    return this.accessToken;
  }

  clear() {
    if (this.refreshTimer) {
      clearTimeout(this.refreshTimer);
      this.refreshTimer = null;
    }

    this.accessToken = null;
    this.refreshToken = null;
    this.tokenExpiresAt = null;
    this.isRefreshing = false;
    this.refreshPromise = null;
  }
}

export { TokenManager };

import * as api from './api.js';
import * as storage from './storage.js';
import * as crypto from './crypto.js';
import { TokenManager } from './token-manager.js';

export async function register(database, username, password) {
  if (!username || username.length === 0) {
    throw new Error('Username is required');
  }

  if (!password || password.length < 8) {
    throw new Error('Password must be at least 8 characters');
  }

  await api.registerUser(username, password);
}

export async function login(database, username, password) {
  if (!username || username.length === 0) {
    throw new Error('Username is required');
  }

  if (!password || password.length === 0) {
    throw new Error('Password is required');
  }

  const context = crypto.createCryptoContext();
  const publicKeys = crypto.getPublicKeys(context);

  const response = await api.loginUser(username, password, publicKeys);

  const tokenManager = new TokenManager(database);
  tokenManager.setTokens(response.access_token, response.refresh_token);

  await storage.saveSession(
    database,
    response.access_token,
    response.refresh_token,
    response.user_id,
    response.device_id
  );

  await storage.saveKeys(
    database,
    response.user_id,
    response.device_id,
    publicKeys
  );

  api.setTokenManager(tokenManager);

  return {
    accessToken: response.access_token,
    refreshToken: response.refresh_token,
    userId: response.user_id,
    deviceId: response.device_id,
    username: response.username,
    context,
    tokenManager,
  };
}

export async function restoreSession(database) {
  const session = await storage.loadSession(database);
  
  if (!session) {
    return null;
  }

  const tokenManager = new TokenManager(database);
  tokenManager.setTokens(session.accessToken, session.refreshToken);

  api.setTokenManager(tokenManager);

  try {
    const token = await tokenManager.ensureValidToken();
    const user = await api.getCurrentUser(token);
    const context = crypto.createCryptoContext();

    return {
      accessToken: session.accessToken,
      refreshToken: session.refreshToken,
      userId: session.userId,
      deviceId: session.deviceId,
      username: user.username,
      context,
      tokenManager,
    };
  } catch (error) {
    console.error('Session restoration failed:', error);
    await storage.clearSession(database);
    tokenManager.clear();
    api.setTokenManager(null);
    return null;
  }
}

export async function logout(database, refreshToken) {
  try {
    if (refreshToken) {
      await api.logoutUser(refreshToken);
    }
  } catch (error) {
    console.error('Logout API call failed:', error);
  }

  await storage.clearSession(database);
  api.setTokenManager(null);
}

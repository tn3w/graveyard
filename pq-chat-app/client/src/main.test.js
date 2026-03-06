import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('./crypto.js', () => ({
  initializeCrypto: vi.fn().mockResolvedValue({}),
  createCryptoContext: vi.fn().mockReturnValue({ mock: 'context' }),
  getPublicKeys: vi.fn().mockReturnValue({ x25519: 'key1', kyber: 'key2' }),
  encryptMessage: vi.fn(),
  decryptMessage: vi.fn(),
}));

vi.mock('./api.js', () => ({
  registerUser: vi.fn(),
  loginUser: vi.fn(),
  getCurrentUser: vi.fn(),
  searchUsers: vi.fn(),
  sendMessage: vi.fn(),
  getMessages: vi.fn(),
  getMessagesCursor: vi.fn(),
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
  refreshToken: vi.fn(),
  logoutUser: vi.fn(),
  setTokenManager: vi.fn(),
}));

import * as storage from './storage.js';
import * as auth from './auth.js';
import * as api from './api.js';
import * as crypto from './crypto.js';
import { WebSocketManager } from './websocket.js';

describe('Storage', () => {
  let database;

  beforeEach(async () => {
    const dbName = `test-db-${Date.now()}-${Math.random()}`;
    database = await storage.initializeDatabase();
  });

  it('should save and load session', async () => {
    await storage.saveSession(database, 'access123', 'refresh456', 'user1', 'device1');
    const session = await storage.loadSession(database);

    expect(session).toEqual({
      accessToken: 'access123',
      refreshToken: 'refresh456',
      userId: 'user1',
      deviceId: 'device1',
    });
  });

  it('should clear session', async () => {
    await storage.saveSession(database, 'access123', 'refresh456', 'user1', 'device1');
    await storage.clearSession(database);
    const session = await storage.loadSession(database);

    expect(session).toBeNull();
  });

  it('should save and load keys', async () => {
    const keys = { x25519: 'key1', kyber: 'key2' };
    await storage.saveKeys(database, 'user1', 'device1', keys);
    const loaded = await storage.loadKeys(database, 'user1', 'device1');

    expect(loaded).toEqual(keys);
  });

  it('should return null for non-existent keys', async () => {
    const loaded = await storage.loadKeys(database, 'nonexistent', 'device');
    expect(loaded).toBeNull();
  });
});

describe('Authentication', () => {
  let database;

  beforeEach(async () => {
    database = await storage.initializeDatabase();
    vi.clearAllMocks();
  });

  it('should register user', async () => {
    api.registerUser.mockResolvedValue({ success: true });

    await auth.register(database, 'testuser', 'password123');

    expect(api.registerUser).toHaveBeenCalledWith('testuser', 'password123');
  });

  it('should reject registration with empty username', async () => {
    await expect(
      auth.register(database, '', 'password123')
    ).rejects.toThrow('Username is required');
  });

  it('should reject registration with short password', async () => {
    await expect(
      auth.register(database, 'testuser', 'short')
    ).rejects.toThrow('Password must be at least 8 characters');
  });

  it('should login and save session', async () => {
    const mockContext = { mock: 'context' };
    const mockKeys = { x25519: 'key1', kyber: 'key2' };

    crypto.createCryptoContext.mockReturnValue(mockContext);
    crypto.getPublicKeys.mockReturnValue(mockKeys);
    api.loginUser.mockResolvedValue({
      access_token: 'access123',
      refresh_token: 'refresh456',
      user_id: 'user1',
      device_id: 'device1',
      username: 'testuser',
    });

    const result = await auth.login(database, 'testuser', 'password123');

    expect(result.accessToken).toBe('access123');
    expect(result.refreshToken).toBe('refresh456');
    expect(result.userId).toBe('user1');
    expect(result.deviceId).toBe('device1');
    expect(result.username).toBe('testuser');
    expect(result.context).toBe(mockContext);
    expect(result.tokenManager).toBeDefined();

    const session = await storage.loadSession(database);
    expect(session.accessToken).toBe('access123');
    expect(session.refreshToken).toBe('refresh456');
  });

  it('should restore session', async () => {
    const mockContext = { mock: 'context' };

    await storage.saveSession(database, 'access123', 'refresh456', 'user1', 'device1');
    crypto.createCryptoContext.mockReturnValue(mockContext);
    api.getCurrentUser.mockResolvedValue({ username: 'testuser' });

    const result = await auth.restoreSession(database);

    expect(result.accessToken).toBe('access123');
    expect(result.refreshToken).toBe('refresh456');
    expect(result.userId).toBe('user1');
    expect(result.deviceId).toBe('device1');
    expect(result.username).toBe('testuser');
    expect(result.context).toBe(mockContext);
    expect(result.tokenManager).toBeDefined();
  });

  it('should return null when no session exists', async () => {
    await storage.clearSession(database);
    const result = await auth.restoreSession(database);
    expect(result).toBeNull();
  });

  it('should clear invalid session', async () => {
    await storage.saveSession(database, 'invalid', 'refresh456', 'user1', 'device1');
    api.getCurrentUser.mockRejectedValue(new Error('Unauthorized'));

    const result = await auth.restoreSession(database);

    expect(result).toBeNull();
    const session = await storage.loadSession(database);
    expect(session).toBeNull();
  });

  it('should logout and clear session', async () => {
    await storage.saveSession(database, 'access123', 'refresh456', 'user1', 'device1');
    await auth.logout(database, 'refresh456');

    const session = await storage.loadSession(database);
    expect(session).toBeNull();
  });
});

describe('WebSocket Manager', () => {
  let manager;

  beforeEach(() => {
    manager = new WebSocketManager('token123');
  });

  it('should register event listeners', () => {
    const callback = vi.fn();
    manager.on('message', callback);

    expect(manager.listeners.get('message')).toContain(callback);
  });

  it('should remove event listeners', () => {
    const callback = vi.fn();
    manager.on('message', callback);
    manager.off('message', callback);

    expect(manager.listeners.get('message')).not.toContain(callback);
  });

  it('should emit events to listeners', () => {
    const callback = vi.fn();
    manager.on('test', callback);
    manager.emit('test', { data: 'value' });

    expect(callback).toHaveBeenCalledWith({ data: 'value' });
  });

  it('should handle multiple listeners', () => {
    const callback1 = vi.fn();
    const callback2 = vi.fn();
    
    manager.on('test', callback1);
    manager.on('test', callback2);
    manager.emit('test', { data: 'value' });

    expect(callback1).toHaveBeenCalledWith({ data: 'value' });
    expect(callback2).toHaveBeenCalledWith({ data: 'value' });
  });

  it('should process batched events', () => {
    const callback = vi.fn();
    manager.on('message', callback);

    const events = [
      { type: 'message', content: 'msg1' },
      { type: 'message', content: 'msg2' },
    ];

    manager.handleMessage({ data: JSON.stringify(events) });

    expect(callback).toHaveBeenCalledTimes(2);
    expect(callback).toHaveBeenCalledWith({ type: 'message', content: 'msg1' });
    expect(callback).toHaveBeenCalledWith({ type: 'message', content: 'msg2' });
  });
});


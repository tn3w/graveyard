const API_BASE = '/api';

let tokenManager = null;

export function setTokenManager(manager) {
  tokenManager = manager;
}

class ApiError extends Error {
  constructor(status, message, details) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.details = details;
  }
}

async function request(method, path, body = null, token = null, retryOnAuth = true) {
  const headers = { 'Content-Type': 'application/json' };
  
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const options = { method, headers };
  
  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${path}`, options);
  
  if (!response.ok) {
    if (response.status === 401 && retryOnAuth && tokenManager) {
      try {
        const newToken = await tokenManager.refresh();
        return await request(method, path, body, newToken, false);
      } catch (refreshError) {
        console.error('Token refresh failed during request retry:', refreshError);
      }
    }

    const errorText = await response.text();
    let errorMessage = errorText;
    let errorDetails = null;
    
    try {
      const errorJson = JSON.parse(errorText);
      errorMessage = errorJson.error || errorText;
      errorDetails = errorJson;
    } catch {
      // Keep errorText as message
    }
    
    throw new ApiError(response.status, errorMessage, errorDetails);
  }

  if (response.status === 204 || response.status === 201) {
    const text = await response.text();
    if (!text) {
      return null;
    }
    return JSON.parse(text);
  }

  return await response.json();
}

export async function registerUser(username, password) {
  return await request('POST', '/auth/register', { username, password });
}

export async function loginUser(username, password, publicKeys) {
  const payload = { username, password, public_key: publicKeys.public_key };
  return await request('POST', '/auth/login', payload);
}

export async function refreshToken(refreshToken) {
  return await request('POST', '/auth/refresh', { refresh_token: refreshToken });
}

export async function logoutUser(refreshToken) {
  return await request('POST', '/auth/logout', { refresh_token: refreshToken });
}

export async function getCurrentUser(token) {
  return await request('GET', '/users/me', null, token);
}

export async function searchUsers(token, searchQuery, limit = 50) {
  const params = new URLSearchParams({ limit: limit.toString() });
  
  if (searchQuery) {
    params.append('search', searchQuery);
  }
  
  return await request('GET', `/users?${params}`, null, token);
}

export async function createChatSession(token, responderDeviceId) {
  const payload = { responder_device_id: responderDeviceId };
  return await request('POST', '/chat-sessions', payload, token);
}

export async function createConversation(token, participantUserId) {
  const payload = { participant_user_id: participantUserId };
  return await request('POST', '/conversations', payload, token);
}

export async function listConversations(token) {
  return await request('GET', '/conversations', null, token);
}

export async function getConversation(token, conversationId) {
  return await request('GET', `/conversations/${conversationId}`, null, token);
}

export async function listChatSessions(token) {
  return await request('GET', '/chat-sessions', null, token);
}

export async function getChatSession(token, sessionId) {
  return await request('GET', `/chat-sessions/${sessionId}`, null, token);
}

export async function sendMessage(token, conversationId, encryptedContent) {
  const payload = {
    conversation_id: conversationId,
    encrypted_content: encryptedContent,
  };
  return await request('POST', '/messages', payload, token);
}

export async function sendMultiDeviceMessage(token, recipientUserId, encryptedContents) {
  const payload = {
    recipient_user_id: recipientUserId,
    encrypted_contents: encryptedContents,
  };
  return await request('POST', '/messages/multi-device', payload, token);
}

export async function getUserDevices(token, userId) {
  return await request('GET', `/users/${userId}/devices`, null, token);
}

export async function getMessages(token, limit = 50, offset = 0) {
  const params = new URLSearchParams({
    limit: limit.toString(),
    offset: offset.toString(),
  });
  return await request('GET', `/messages?${params}`, null, token);
}

export async function getMessagesCursor(token, limit = 50, cursor = null) {
  const params = new URLSearchParams({ limit: limit.toString() });
  
  if (cursor) {
    params.append('cursor', cursor);
  }
  
  return await request('GET', `/messages/cursor?${params}`, null, token);
}

export async function editMessage(token, messageId, encryptedContent) {
  const payload = { encrypted_content: encryptedContent };
  return await request('POST', `/messages/${messageId}`, payload, token);
}

export async function createGroup(token, name, memberUserIds) {
  const payload = { name, member_user_ids: memberUserIds };
  return await request('POST', '/groups', payload, token);
}

export async function getGroups(token) {
  return await request('GET', '/groups', null, token);
}

export async function getGroupMembers(token, groupId) {
  return await request('GET', `/groups/${groupId}/members`, null, token);
}

export async function addGroupMember(token, groupId, userId) {
  return await request('POST', `/groups/${groupId}/members/${userId}`, null, token);
}

export async function removeGroupMember(token, groupId, userId) {
  return await request('DELETE', `/groups/${groupId}/members/${userId}`, null, token);
}

export async function sendGroupMessage(token, groupId, encryptedMessages) {
  const payload = { group_id: groupId, encrypted_messages: encryptedMessages };
  return await request('POST', '/groups/messages', payload, token);
}

export async function addReaction(token, messageId, emoji) {
  const payload = { emoji };
  return await request('POST', `/messages/${messageId}/reactions`, payload, token);
}

export async function getReactions(token, messageId) {
  return await request('GET', `/messages/${messageId}/reactions`, null, token);
}

export async function removeReaction(token, reactionId) {
  return await request('DELETE', `/reactions/${reactionId}`, null, token);
}

export async function listDevices(token) {
  return await request('GET', '/devices', null, token);
}

export async function deleteDevice(token, deviceId) {
  return await request('DELETE', `/devices/${deviceId}`, null, token);
}

export async function uploadPrekeyBundle(token, deviceId, bundle) {
  return await request('POST', `/prekeys/${deviceId}`, bundle, token);
}

export async function fetchPrekeyBundle(token, deviceId) {
  return await request('GET', `/prekeys/${deviceId}`, null, token);
}

export { ApiError };

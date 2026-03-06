const DATABASE_NAME = 'encrypted-chat';
const DATABASE_VERSION = 4;
const STORE_KEYS = 'keys';
const STORE_SESSION = 'session';
const STORE_CHAT_SESSIONS = 'chat_sessions';
const STORE_IDENTITY_KEYS = 'identity_keys';
const STORE_SIGNED_PREKEY = 'signed_prekey';
const STORE_ONE_TIME_PREKEY_SECRETS = 'one_time_prekey_secrets';
const STORE_PREKEY_ROTATION = 'prekey_rotation';
const STORE_CONVERSATION_INIT = 'conversation_init';

function promisifyRequest(request) {
  return new Promise((resolve, reject) => {
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

export async function initializeDatabase() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);

    request.onerror = () => reject(request.error);
    request.onsuccess = () => resolve(request.result);

    request.onupgradeneeded = (event) => {
      const database = event.target.result;
      const oldVersion = event.oldVersion;

      if (!database.objectStoreNames.contains(STORE_KEYS)) {
        database.createObjectStore(STORE_KEYS);
      }
      if (!database.objectStoreNames.contains(STORE_SESSION)) {
        database.createObjectStore(STORE_SESSION);
      }
      if (oldVersion < 3) {
        if (database.objectStoreNames.contains('sync_requests')) {
          database.deleteObjectStore('sync_requests');
        }
        if (database.objectStoreNames.contains('synced_history')) {
          database.deleteObjectStore('synced_history');
        }
        if (!database.objectStoreNames.contains(STORE_CHAT_SESSIONS)) {
          database.createObjectStore(STORE_CHAT_SESSIONS);
        }
      }
      if (oldVersion < 4) {
        if (!database.objectStoreNames.contains(STORE_IDENTITY_KEYS)) {
          database.createObjectStore(STORE_IDENTITY_KEYS);
        }
        if (!database.objectStoreNames.contains(STORE_SIGNED_PREKEY)) {
          database.createObjectStore(STORE_SIGNED_PREKEY);
        }
        if (!database.objectStoreNames.contains(STORE_ONE_TIME_PREKEY_SECRETS)) {
          database.createObjectStore(STORE_ONE_TIME_PREKEY_SECRETS);
        }
        if (!database.objectStoreNames.contains(STORE_PREKEY_ROTATION)) {
          database.createObjectStore(STORE_PREKEY_ROTATION);
        }
        if (!database.objectStoreNames.contains(STORE_CONVERSATION_INIT)) {
          database.createObjectStore(STORE_CONVERSATION_INIT);
        }
      }
    };
  });
}

export async function saveKeys(database, userId, deviceId, publicKeys) {
  const key = `${userId}:${deviceId}`;
  const transaction = database.transaction(STORE_KEYS, 'readwrite');
  const store = transaction.objectStore(STORE_KEYS);
  await promisifyRequest(store.put({ publicKeys }, key));
}

export async function loadKeys(database, userId, deviceId) {
  const key = `${userId}:${deviceId}`;
  const transaction = database.transaction(STORE_KEYS, 'readonly');
  const store = transaction.objectStore(STORE_KEYS);
  const record = await promisifyRequest(store.get(key));
  return record?.publicKeys || null;
}

export async function saveSession(database, accessToken, refreshToken, userId, deviceId) {
  const transaction = database.transaction(STORE_SESSION, 'readwrite');
  const store = transaction.objectStore(STORE_SESSION);
  await promisifyRequest(store.put({ 
    accessToken, 
    refreshToken, 
    userId, 
    deviceId 
  }, 'current'));
}

export async function loadSession(database) {
  const transaction = database.transaction(STORE_SESSION, 'readonly');
  const store = transaction.objectStore(STORE_SESSION);
  const result = await promisifyRequest(store.get('current'));
  return result || null;
}

export async function clearSession(database) {
  const transaction = database.transaction(STORE_SESSION, 'readwrite');
  const store = transaction.objectStore(STORE_SESSION);
  await promisifyRequest(store.delete('current'));
}

export async function saveChatSession(database, sessionId, sessionData) {
  const transaction = database.transaction(STORE_CHAT_SESSIONS, 'readwrite');
  const store = transaction.objectStore(STORE_CHAT_SESSIONS);
  await promisifyRequest(store.put(sessionData, sessionId));
}

export async function getChatSession(database, sessionId) {
  const transaction = database.transaction(STORE_CHAT_SESSIONS, 'readonly');
  const store = transaction.objectStore(STORE_CHAT_SESSIONS);
  const result = await promisifyRequest(store.get(sessionId));
  return result || null;
}

export async function getAllChatSessions(database) {
  const transaction = database.transaction(STORE_CHAT_SESSIONS, 'readonly');
  const store = transaction.objectStore(STORE_CHAT_SESSIONS);
  const keys = await promisifyRequest(store.getAllKeys());
  const sessions = [];

  for (const key of keys) {
    const session = await promisifyRequest(store.get(key));
    if (session) {
      sessions.push(session);
    }
  }

  return sessions;
}

export async function setItem(database, storeName, key, value) {
  const transaction = database.transaction(storeName, 'readwrite');
  const store = transaction.objectStore(storeName);
  await promisifyRequest(store.put(value, key));
}

export async function getItem(database, storeName, key) {
  const transaction = database.transaction(storeName, 'readonly');
  const store = transaction.objectStore(storeName);
  const result = await promisifyRequest(store.get(key));
  return result || null;
}


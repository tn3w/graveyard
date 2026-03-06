const DATABASE_NAME = 'chat_ratchet_state';
const DATABASE_VERSION = 1;
const STORE_NAME = 'ratchet_states';

class RatchetStorage {
  constructor() {
    this.database = null;
  }

  async initialize() {
    if (this.database) {
      return;
    }

    return new Promise((resolve, reject) => {
      const request = indexedDB.open(DATABASE_NAME, DATABASE_VERSION);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        this.database = request.result;
        resolve();
      };

      request.onupgradeneeded = (event) => {
        const database = event.target.result;

        if (!database.objectStoreNames.contains(STORE_NAME)) {
          const store = database.createObjectStore(STORE_NAME, {
            keyPath: 'conversationId'
          });
          store.createIndex('updatedAt', 'updatedAt', { unique: false });
        }
      };
    });
  }

  async saveState(conversationId, stateJson) {
    await this.initialize();

    return new Promise((resolve, reject) => {
      const transaction = this.database.transaction(
        [STORE_NAME],
        'readwrite'
      );
      const store = transaction.objectStore(STORE_NAME);

      const record = {
        conversationId,
        stateJson,
        updatedAt: Date.now()
      };

      const request = store.put(record);
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  async loadState(conversationId) {
    await this.initialize();

    return new Promise((resolve, reject) => {
      const transaction = this.database.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.get(conversationId);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => {
        const record = request.result;
        resolve(record ? record.stateJson : null);
      };
    });
  }

  async deleteState(conversationId) {
    await this.initialize();

    return new Promise((resolve, reject) => {
      const transaction = this.database.transaction(
        [STORE_NAME],
        'readwrite'
      );
      const store = transaction.objectStore(STORE_NAME);
      const request = store.delete(conversationId);

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }

  async getAllConversationIds() {
    await this.initialize();

    return new Promise((resolve, reject) => {
      const transaction = this.database.transaction([STORE_NAME], 'readonly');
      const store = transaction.objectStore(STORE_NAME);
      const request = store.getAllKeys();

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
    });
  }

  async clearAll() {
    await this.initialize();

    return new Promise((resolve, reject) => {
      const transaction = this.database.transaction(
        [STORE_NAME],
        'readwrite'
      );
      const store = transaction.objectStore(STORE_NAME);
      const request = store.clear();

      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve();
    });
  }
}

export const ratchetStorage = new RatchetStorage();

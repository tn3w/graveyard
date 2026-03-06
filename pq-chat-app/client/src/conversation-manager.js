import * as crypto from './crypto.js';
import * as api from './api.js';
import * as storage from './storage.js';

const PREKEY_ROTATION_INTERVAL = 7 * 24 * 60 * 60 * 1000;
const PREKEY_REPLENISH_THRESHOLD = 20;
const PREKEY_BATCH_SIZE = 100;

export class ConversationManager {
  constructor(session, database) {
    this.session = session;
    this.database = database;
    this.identityKeys = null;
    this.signedPrekeyKeys = null;
    this.oneTimePrekeySecrets = new Map();
  }

  async initialize() {
    await this.loadOrGenerateIdentityKeys();
    await this.ensurePrekeyBundle();
  }

  async loadOrGenerateIdentityKeys() {
    const stored = await storage.getItem(
      this.database,
      'identity_keys',
      this.session.deviceId
    );

    if (stored) {
      this.identityKeys = stored;
      return;
    }

    this.identityKeys = crypto.generateIdentityKeys();

    await storage.setItem(
      this.database,
      'identity_keys',
      this.session.deviceId,
      this.identityKeys
    );
  }

  async ensurePrekeyBundle() {
    const lastRotation = await storage.getItem(
      this.database,
      'prekey_rotation',
      'last_rotation'
    );

    const now = Date.now();
    const shouldRotate = !lastRotation ||
      now - lastRotation > PREKEY_ROTATION_INTERVAL;

    if (shouldRotate) {
      await this.rotatePrekeyBundle();
    }
  }

  async rotatePrekeyBundle() {
    const signedPrekeyResult = crypto.generateSignedPrekeyPair(
      new Uint8Array(this.identityKeys.secret)
    );

    this.signedPrekeyKeys = signedPrekeyResult;

    const oneTimePrekeyResult = crypto.generateOneTimePrekeyBatch(
      PREKEY_BATCH_SIZE
    );

    this.oneTimePrekeySecrets.clear();

    for (let i = 0; i < oneTimePrekeyResult.publics.length; i++) {
      const publicKey = oneTimePrekeyResult.publics[i];
      const secretKey = oneTimePrekeyResult.secrets[i];
      const keyId = this.hashKey(publicKey);
      this.oneTimePrekeySecrets.set(keyId, secretKey);
    }

    const bundle = crypto.buildPrekeyBundle(
      new Uint8Array(this.identityKeys.public),
      new Uint8Array(signedPrekeyResult.public),
      new Uint8Array(signedPrekeyResult.signature),
      Math.floor(Date.now() / 1000),
      oneTimePrekeyResult.publics.map(p => new Uint8Array(p))
    );

    await api.uploadPrekeyBundle(
      this.session.accessToken,
      this.session.deviceId,
      bundle
    );

    await storage.setItem(
      this.database,
      'signed_prekey',
      this.session.deviceId,
      signedPrekeyResult
    );

    await storage.setItem(
      this.database,
      'one_time_prekey_secrets',
      this.session.deviceId,
      Array.from(this.oneTimePrekeySecrets.entries())
    );

    await storage.setItem(
      this.database,
      'prekey_rotation',
      'last_rotation',
      Date.now()
    );
  }

  async initializeConversation(conversationId, recipientDeviceId) {
    const existingState = await crypto.loadRatchetState(conversationId);

    if (existingState) {
      return { isInitiator: false, needsInitialization: false };
    }

    const bundle = await api.fetchPrekeyBundle(
      this.session.accessToken,
      recipientDeviceId
    );

    const result = await crypto.initializeConversationAsInitiator(
      conversationId,
      new Uint8Array(this.identityKeys.secret),
      bundle
    );

    await storage.setItem(
      this.database,
      'conversation_init',
      conversationId,
      {
        isInitiator: true,
        associatedData: Array.from(result.associatedData),
        recipientDeviceId,
        timestamp: Date.now(),
      }
    );

    return {
      isInitiator: true,
      needsInitialization: true,
      associatedData: result.associatedData,
    };
  }

  async handleInitialMessage(conversationId, initiatorIdentity, data) {
    const existingState = await crypto.loadRatchetState(conversationId);

    if (existingState) {
      return;
    }

    const associatedData = new Uint8Array(data);
    const oneTimePrekeyId = this.extractOneTimePrekeyId(associatedData);
    const oneTimePrekeySecret = oneTimePrekeyId
      ? this.oneTimePrekeySecrets.get(oneTimePrekeyId)
      : null;

    await crypto.initializeConversationAsResponder(
      conversationId,
      new Uint8Array(this.identityKeys.secret),
      new Uint8Array(this.signedPrekeyKeys.secret),
      oneTimePrekeySecret ? new Uint8Array(oneTimePrekeySecret) : null,
      new Uint8Array(initiatorIdentity),
      associatedData
    );

    if (oneTimePrekeyId) {
      this.oneTimePrekeySecrets.delete(oneTimePrekeyId);
      await this.checkPrekeyReplenishment();
    }
  }

  async checkPrekeyReplenishment() {
    if (this.oneTimePrekeySecrets.size < PREKEY_REPLENISH_THRESHOLD) {
      await this.rotatePrekeyBundle();
    }
  }

  extractOneTimePrekeyId(associatedData) {
    if (associatedData.length < 32 + 1568 * 3) {
      return null;
    }

    const oneTimePrekeyPublic = associatedData.slice(
      32 + 1568 * 2,
      32 + 1568 * 3
    );

    return this.hashKey(oneTimePrekeyPublic);
  }

  hashKey(keyBytes) {
    let hash = 0;

    for (let i = 0; i < Math.min(keyBytes.length, 32); i++) {
      hash = (hash << 5) - hash + keyBytes[i];
      hash = hash & hash;
    }

    return hash.toString(36);
  }

  getIdentityPublic() {
    return new Uint8Array(this.identityKeys.public);
  }
}

import { describe, it, expect, beforeEach } from 'vitest';
import {
  initializeCrypto,
  initializeRatchetForSender,
  initializeRatchetForReceiver,
  encryptWithSealedSender,
  decryptWithSealedSender,
  clearAllRatchetStates,
} from './crypto.js';

describe('Sealed Sender', () => {
  beforeEach(async () => {
    await initializeCrypto();
    await clearAllRatchetStates();
  });

  it('encrypts message with sender identity', async () => {
    const conversationId = 'test-conversation-1';
    const sharedSecret = new Uint8Array(32).fill(1);
    const receiverPublicKey = new Uint8Array(32).fill(2);

    await initializeRatchetForSender(
      conversationId,
      sharedSecret,
      receiverPublicKey
    );

    const plaintext = 'Hello, World!';
    const senderUserId = 'user-alice-123';

    const encrypted = await encryptWithSealedSender(
      conversationId,
      plaintext,
      senderUserId
    );

    expect(encrypted).toBeDefined();
    expect(encrypted.ciphertext).toBeDefined();
    expect(encrypted.header).toBeDefined();
  });

  it('decrypts message and extracts sender identity', async () => {
    const conversationId = 'test-conversation-2';
    const sharedSecret = new Uint8Array(32).fill(1);
    const senderPublicKey = new Uint8Array(32).fill(2);
    const receiverPublicKey = new Uint8Array(32).fill(2);

    await initializeRatchetForSender(
      conversationId,
      sharedSecret,
      receiverPublicKey
    );

    const plaintext = 'Secret message';
    const senderUserId = 'user-bob-456';

    const encrypted = await encryptWithSealedSender(
      conversationId,
      plaintext,
      senderUserId
    );

    await clearAllRatchetStates();

    await initializeRatchetForReceiver(
      conversationId,
      sharedSecret,
      senderPublicKey
    );

    const messageJson = JSON.stringify(encrypted);
    const decrypted = await decryptWithSealedSender(
      conversationId,
      messageJson
    );

    expect(decrypted.senderUserId).toBe(senderUserId);
    expect(decrypted.plaintext).toBe(plaintext);
  });

  it('handles multiple messages with different senders', async () => {
    const conversationId = 'test-conversation-3';
    const sharedSecret = new Uint8Array(32).fill(1);
    const publicKey = new Uint8Array(32).fill(2);

    await initializeRatchetForSender(conversationId, sharedSecret, publicKey);

    const message1 = await encryptWithSealedSender(
      conversationId,
      'First message',
      'user-alice'
    );

    const message2 = await encryptWithSealedSender(
      conversationId,
      'Second message',
      'user-alice'
    );

    await clearAllRatchetStates();
    await initializeRatchetForReceiver(conversationId, sharedSecret, publicKey);

    const decrypted1 = await decryptWithSealedSender(
      conversationId,
      JSON.stringify(message1)
    );
    const decrypted2 = await decryptWithSealedSender(
      conversationId,
      JSON.stringify(message2)
    );

    expect(decrypted1.senderUserId).toBe('user-alice');
    expect(decrypted1.plaintext).toBe('First message');
    expect(decrypted2.senderUserId).toBe('user-alice');
    expect(decrypted2.plaintext).toBe('Second message');
  });

  it('throws error for invalid message format', async () => {
    const conversationId = 'test-conversation-4';
    const sharedSecret = new Uint8Array(32).fill(1);
    const publicKey = new Uint8Array(32).fill(2);

    await initializeRatchetForReceiver(conversationId, sharedSecret, publicKey);

    const invalidMessage = JSON.stringify({
      header: {},
      ciphertext: new Array(10).fill(0),
    });

    await expect(
      decryptWithSealedSender(conversationId, invalidMessage)
    ).rejects.toThrow();
  });

  it('preserves sender identity through encryption', async () => {
    const conversationId = 'test-conversation-5';
    const sharedSecret = new Uint8Array(32).fill(1);
    const publicKey = new Uint8Array(32).fill(2);

    await initializeRatchetForSender(conversationId, sharedSecret, publicKey);

    const longSenderId = 'user-with-very-long-identifier-12345678';
    const plaintext = 'Test message';

    const encrypted = await encryptWithSealedSender(
      conversationId,
      plaintext,
      longSenderId
    );

    await clearAllRatchetStates();
    await initializeRatchetForReceiver(conversationId, sharedSecret, publicKey);

    const decrypted = await decryptWithSealedSender(
      conversationId,
      JSON.stringify(encrypted)
    );

    expect(decrypted.senderUserId).toBe(longSenderId);
    expect(decrypted.plaintext).toBe(plaintext);
  });
});

import { describe, it, expect, beforeAll, beforeEach } from 'vitest';
import {
  initializeCrypto,
  initializeRatchetForSender,
  initializeRatchetForReceiver,
  encryptWithRatchet,
  decryptWithRatchet,
  clearAllRatchetStates,
} from './crypto.js';

describe('Crypto Ratchet Integration', () => {
  beforeAll(async () => {
    await initializeCrypto();
  });

  beforeEach(async () => {
    await clearAllRatchetStates();
  });

  it('initializes sender and receiver ratchets', async () => {
    const sharedSecret = new Uint8Array(32).fill(1);
    const senderPublicKey = new Uint8Array(32).fill(2);
    const receiverPublicKey = new Uint8Array(32).fill(3);

    const senderState = await initializeRatchetForSender(
      'conv-1',
      sharedSecret,
      receiverPublicKey
    );

    const receiverState = await initializeRatchetForReceiver(
      'conv-2',
      sharedSecret,
      senderPublicKey
    );

    expect(senderState).toBeTruthy();
    expect(receiverState).toBeTruthy();
    expect(typeof senderState).toBe('string');
    expect(typeof receiverState).toBe('string');
  });

  it('encrypts and decrypts messages with ratchet', async () => {
    const sharedSecret = new Uint8Array(32).fill(42);
    const alicePrivate = new Uint8Array(32).fill(1);
    const alicePublic = new Uint8Array(32).fill(2);
    const bobPrivate = new Uint8Array(32).fill(3);
    const bobPublic = new Uint8Array(32).fill(4);

    await initializeRatchetForSender('alice', sharedSecret, bobPublic);
    await initializeRatchetForReceiver('bob', sharedSecret, alicePublic);

    const plaintext = new TextEncoder().encode('Hello, Bob!');
    const encryptedMessage = await encryptWithRatchet('alice', plaintext);

    expect(encryptedMessage).toBeTruthy();
    expect(encryptedMessage.header).toBeTruthy();
    expect(encryptedMessage.ciphertext).toBeTruthy();

    const messageJson = JSON.stringify(encryptedMessage);
    const decrypted = await decryptWithRatchet('bob', messageJson);

    expect(decrypted).toEqual(Array.from(plaintext));
  });

  it('handles multiple messages in sequence', async () => {
    const sharedSecret = new Uint8Array(32).fill(99);
    const alicePublic = new Uint8Array(32).fill(10);
    const bobPublic = new Uint8Array(32).fill(20);

    await initializeRatchetForSender('alice', sharedSecret, bobPublic);
    await initializeRatchetForReceiver('bob', sharedSecret, alicePublic);

    const messages = ['First', 'Second', 'Third'];

    for (const text of messages) {
      const plaintext = new TextEncoder().encode(text);
      const encrypted = await encryptWithRatchet('alice', plaintext);
      const messageJson = JSON.stringify(encrypted);
      const decrypted = await decryptWithRatchet('bob', messageJson);
      const decryptedText = new TextDecoder().decode(
        new Uint8Array(decrypted)
      );

      expect(decryptedText).toBe(text);
    }
  });

  it('persists state across operations', async () => {
    const sharedSecret = new Uint8Array(32).fill(77);
    const alicePublic = new Uint8Array(32).fill(11);
    const bobPublic = new Uint8Array(32).fill(22);

    await initializeRatchetForSender('alice', sharedSecret, bobPublic);

    const plaintext1 = new TextEncoder().encode('Message 1');
    const encrypted1 = await encryptWithRatchet('alice', plaintext1);

    const plaintext2 = new TextEncoder().encode('Message 2');
    const encrypted2 = await encryptWithRatchet('alice', plaintext2);

    expect(encrypted1.header.message_number).toBe(0);
    expect(encrypted2.header.message_number).toBe(1);
  });

  it('throws error for missing ratchet state', async () => {
    const plaintext = new TextEncoder().encode('Test');

    await expect(
      encryptWithRatchet('nonexistent', plaintext)
    ).rejects.toThrow('No ratchet state');
  });
});

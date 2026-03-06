import { describe, it, expect, beforeAll } from 'vitest';
import {
  initializeCrypto,
  performX3DHInitiator,
  performX3DHResponder,
  initializeConversationAsInitiator,
  initializeConversationAsResponder,
  encryptWithRatchet,
  decryptWithRatchet,
} from './crypto.js';

describe('X3DH Key Agreement', () => {
  beforeAll(async () => {
    await initializeCrypto();
  });

  it('performs X3DH with one-time prekey', async () => {
    const aliceIdentity = new Uint8Array(1632);
    const bobIdentity = new Uint8Array(1632);
    const bobSignedPrekey = new Uint8Array(1600);
    const bobOneTimePrekey = new Uint8Array(1600);

    for (let i = 0; i < aliceIdentity.length; i++) {
      aliceIdentity[i] = i % 256;
    }
    for (let i = 0; i < bobIdentity.length; i++) {
      bobIdentity[i] = (i + 100) % 256;
    }
    for (let i = 0; i < bobSignedPrekey.length; i++) {
      bobSignedPrekey[i] = (i + 50) % 256;
    }
    for (let i = 0; i < bobOneTimePrekey.length; i++) {
      bobOneTimePrekey[i] = (i + 150) % 256;
    }

    const initiatorResult = await performX3DHInitiator(
      aliceIdentity,
      bobIdentity,
      bobSignedPrekey,
      bobOneTimePrekey
    );

    expect(initiatorResult.shared_secret).toBeDefined();
    expect(initiatorResult.shared_secret.length).toBe(32);
    expect(initiatorResult.associated_data).toBeDefined();
    expect(initiatorResult.associated_data.length).toBeGreaterThan(0);
  });

  it('performs X3DH without one-time prekey', async () => {
    const aliceIdentity = new Uint8Array(1632);
    const bobIdentity = new Uint8Array(1632);
    const bobSignedPrekey = new Uint8Array(1600);

    for (let i = 0; i < aliceIdentity.length; i++) {
      aliceIdentity[i] = i % 256;
    }
    for (let i = 0; i < bobIdentity.length; i++) {
      bobIdentity[i] = (i + 100) % 256;
    }
    for (let i = 0; i < bobSignedPrekey.length; i++) {
      bobSignedPrekey[i] = (i + 50) % 256;
    }

    const initiatorResult = await performX3DHInitiator(
      aliceIdentity,
      bobIdentity,
      bobSignedPrekey,
      null
    );

    expect(initiatorResult.shared_secret).toBeDefined();
    expect(initiatorResult.shared_secret.length).toBe(32);
  });

  it('produces matching shared secrets', async () => {
    const aliceIdentity = new Uint8Array(1632);
    const bobIdentity = new Uint8Array(1632);
    const bobSignedPrekey = new Uint8Array(1600);
    const bobSignedPrekeySecret = new Uint8Array(1600);

    for (let i = 0; i < aliceIdentity.length; i++) {
      aliceIdentity[i] = i % 256;
    }
    for (let i = 0; i < bobIdentity.length; i++) {
      bobIdentity[i] = (i + 100) % 256;
    }
    for (let i = 0; i < bobSignedPrekey.length; i++) {
      bobSignedPrekey[i] = (i + 50) % 256;
    }
    for (let i = 0; i < bobSignedPrekeySecret.length; i++) {
      bobSignedPrekeySecret[i] = (i + 50) % 256;
    }

    const initiatorResult = await performX3DHInitiator(
      aliceIdentity,
      bobIdentity,
      bobSignedPrekey,
      null
    );

    const ephemeralPublic = initiatorResult.associated_data.slice(0, 32);
    const kyberCiphertextsStart = 32;
    const ciphertextSize = 1568;

    const kyberCiphertexts = [
      Array.from(
        initiatorResult.associated_data.slice(
          kyberCiphertextsStart,
          kyberCiphertextsStart + ciphertextSize
        )
      ),
      Array.from(
        initiatorResult.associated_data.slice(
          kyberCiphertextsStart + ciphertextSize,
          kyberCiphertextsStart + 2 * ciphertextSize
        )
      ),
    ];

    const responderSecret = await performX3DHResponder(
      bobIdentity,
      bobSignedPrekeySecret,
      null,
      aliceIdentity,
      ephemeralPublic,
      kyberCiphertexts
    );

    expect(responderSecret).toEqual(initiatorResult.shared_secret);
  });

  it('initializes conversation as initiator', async () => {
    const identitySecret = new Uint8Array(1632);
    for (let i = 0; i < identitySecret.length; i++) {
      identitySecret[i] = i % 256;
    }

    const prekeyBundle = {
      identity_key: Array.from(new Uint8Array(1632).fill(1)),
      signed_prekey: Array.from(new Uint8Array(1600).fill(2)),
      one_time_prekey: Array.from(new Uint8Array(1600).fill(3)),
    };

    const result = await initializeConversationAsInitiator(
      'test-conversation',
      identitySecret,
      prekeyBundle
    );

    expect(result.ratchetState).toBeDefined();
    expect(result.associatedData).toBeDefined();
    expect(result.associatedData.length).toBeGreaterThan(0);
  });

  it('initializes conversation as responder', async () => {
    const identitySecret = new Uint8Array(1632);
    const signedPrekeySecret = new Uint8Array(1600);
    const oneTimePrekeySecret = new Uint8Array(1600);
    const initiatorIdentityPublic = new Uint8Array(1632);

    for (let i = 0; i < identitySecret.length; i++) {
      identitySecret[i] = i % 256;
    }
    for (let i = 0; i < signedPrekeySecret.length; i++) {
      signedPrekeySecret[i] = (i + 50) % 256;
    }
    for (let i = 0; i < oneTimePrekeySecret.length; i++) {
      oneTimePrekeySecret[i] = (i + 100) % 256;
    }
    for (let i = 0; i < initiatorIdentityPublic.length; i++) {
      initiatorIdentityPublic[i] = (i + 150) % 256;
    }

    const associatedData = new Uint8Array(32 + 2 * 1568);
    for (let i = 0; i < associatedData.length; i++) {
      associatedData[i] = i % 256;
    }

    const result = await initializeConversationAsResponder(
      'test-conversation-2',
      identitySecret,
      signedPrekeySecret,
      oneTimePrekeySecret,
      initiatorIdentityPublic,
      associatedData
    );

    expect(result).toBeDefined();
  });

  it('enables end-to-end encrypted conversation', async () => {
    const aliceIdentity = new Uint8Array(1632);
    const bobIdentity = new Uint8Array(1632);
    const bobSignedPrekey = new Uint8Array(1600);
    const bobSignedPrekeySecret = new Uint8Array(1600);

    for (let i = 0; i < aliceIdentity.length; i++) {
      aliceIdentity[i] = i % 256;
    }
    for (let i = 0; i < bobIdentity.length; i++) {
      bobIdentity[i] = (i + 100) % 256;
    }
    for (let i = 0; i < bobSignedPrekey.length; i++) {
      bobSignedPrekey[i] = (i + 50) % 256;
    }
    for (let i = 0; i < bobSignedPrekeySecret.length; i++) {
      bobSignedPrekeySecret[i] = (i + 50) % 256;
    }

    const prekeyBundle = {
      identity_key: Array.from(bobIdentity),
      signed_prekey: Array.from(bobSignedPrekey),
      one_time_prekey: null,
    };

    const aliceResult = await initializeConversationAsInitiator(
      'alice-conversation',
      aliceIdentity,
      prekeyBundle
    );

    const bobResult = await initializeConversationAsResponder(
      'bob-conversation',
      bobIdentity,
      bobSignedPrekeySecret,
      null,
      aliceIdentity,
      aliceResult.associatedData
    );

    const plaintext = new TextEncoder().encode('Hello from Alice!');
    const encrypted = await encryptWithRatchet(
      'alice-conversation',
      plaintext
    );

    const messageJson = JSON.stringify(encrypted);
    const decrypted = await decryptWithRatchet(
      'bob-conversation',
      messageJson
    );

    const decryptedText = new TextDecoder().decode(
      new Uint8Array(decrypted)
    );
    expect(decryptedText).toBe('Hello from Alice!');
  });
});

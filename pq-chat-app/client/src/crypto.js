import { ratchetStorage } from './ratchet-storage.js';

let wasmModule = null;
const ratchetStates = new Map();

export async function initializeCrypto() {
  if (wasmModule) {
    return wasmModule;
  }

  const wasm = await import('./wasm/chat_client_wasm.js');
  await wasm.default();
  wasmModule = wasm;
  return wasmModule;
}

export function createCryptoContext() {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }
  return new wasmModule.CryptoContext();
}

export function getPublicKeys(context) {
  const keysJson = context.get_public_keys();
  return JSON.parse(keysJson);
}

export function encryptMessage(context, plaintext, recipientPublicKeys) {
  const recipientJson = JSON.stringify(recipientPublicKeys);
  const encryptedJson = context.encrypt_message(plaintext, recipientJson);
  const encryptedMessage = JSON.parse(encryptedJson);
  
  const serialized = JSON.stringify(encryptedMessage);
  const bytes = new TextEncoder().encode(serialized);
  return Array.from(bytes);
}

export function decryptMessage(context, encryptedBytes) {
  const bytes = new Uint8Array(encryptedBytes);
  const serialized = new TextDecoder().decode(bytes);
  const encryptedMessage = JSON.parse(serialized);
  const encryptedJson = JSON.stringify(encryptedMessage);
  return context.decrypt_message(encryptedJson);
}

export function encryptForMultipleDevices(
  context,
  plaintext,
  devicesPublicKeys
) {
  return devicesPublicKeys.map(deviceKeys => {
    const keyPair = {
      public_key: deviceKeys.public_key,
      secret_key: [],
    };
    
    const encryptedBytes = encryptMessage(context, plaintext, keyPair);
    
    return {
      recipient_device_id: deviceKeys.id,
      encrypted_content: encryptedBytes,
    };
  });
}

export async function initializeRatchetForSender(
  conversationId,
  sharedSecret,
  receiverPublicKey
) {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }

  const stateJson = wasmModule.initialize_ratchet_sender(
    sharedSecret,
    receiverPublicKey
  );

  await ratchetStorage.saveState(conversationId, stateJson);
  ratchetStates.set(conversationId, stateJson);

  return stateJson;
}

export async function initializeRatchetForReceiver(
  conversationId,
  sharedSecret,
  senderPublicKey
) {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }

  const stateJson = wasmModule.initialize_ratchet_receiver(
    sharedSecret,
    senderPublicKey
  );

  await ratchetStorage.saveState(conversationId, stateJson);
  ratchetStates.set(conversationId, stateJson);

  return stateJson;
}

export async function loadRatchetState(conversationId) {
  if (ratchetStates.has(conversationId)) {
    return ratchetStates.get(conversationId);
  }

  const stateJson = await ratchetStorage.loadState(conversationId);

  if (stateJson) {
    ratchetStates.set(conversationId, stateJson);
  }

  return stateJson;
}

export async function encryptWithRatchet(conversationId, plaintext) {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }

  let stateJson = await loadRatchetState(conversationId);

  if (!stateJson) {
    throw new Error(`No ratchet state for conversation ${conversationId}`);
  }

  const resultJson = wasmModule.ratchet_encrypt(stateJson, plaintext);
  const result = JSON.parse(resultJson);

  await ratchetStorage.saveState(conversationId, result.state);
  ratchetStates.set(conversationId, result.state);

  return result.message;
}

export async function decryptWithRatchet(conversationId, messageJson) {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }

  let stateJson = await loadRatchetState(conversationId);

  if (!stateJson) {
    throw new Error(`No ratchet state for conversation ${conversationId}`);
  }

  const resultJson = wasmModule.ratchet_decrypt(stateJson, messageJson);
  const result = JSON.parse(resultJson);

  await ratchetStorage.saveState(conversationId, result.state);
  ratchetStates.set(conversationId, result.state);

  return result.plaintext;
}

export async function deleteRatchetState(conversationId) {
  await ratchetStorage.deleteState(conversationId);
  ratchetStates.delete(conversationId);
}

export async function clearAllRatchetStates() {
  await ratchetStorage.clearAll();
  ratchetStates.clear();
}

export async function performX3DHInitiator(
  identitySecret,
  recipientIdentityPublic,
  recipientSignedPrekey,
  recipientOneTimePrekey = null
) {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }

  const resultJson = wasmModule.x3dh_initiator(
    identitySecret,
    recipientIdentityPublic,
    recipientSignedPrekey,
    recipientOneTimePrekey
  );

  return JSON.parse(resultJson);
}

export async function performX3DHResponder(
  identitySecret,
  signedPrekeySecret,
  oneTimePrekeySecret,
  initiatorIdentityPublic,
  initiatorEphemeralPublic,
  kyberCiphertexts
) {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }

  const kyberCiphertextsJson = JSON.stringify(kyberCiphertexts);

  const resultJson = wasmModule.x3dh_responder(
    identitySecret,
    signedPrekeySecret,
    oneTimePrekeySecret,
    initiatorIdentityPublic,
    initiatorEphemeralPublic,
    kyberCiphertextsJson
  );

  const result = JSON.parse(resultJson);
  return result.shared_secret;
}

export async function initializeConversationAsInitiator(
  conversationId,
  identitySecret,
  recipientPrekeyBundle
) {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }

  const identityPublicBytes = new Uint8Array(
    recipientPrekeyBundle.identity_key
  );
  const signedPrekeyBytes = new Uint8Array(
    recipientPrekeyBundle.signed_prekey
  );
  const oneTimePrekeyBytes = recipientPrekeyBundle.one_time_prekey
    ? new Uint8Array(recipientPrekeyBundle.one_time_prekey)
    : null;

  const x3dhResult = await performX3DHInitiator(
    identitySecret,
    identityPublicBytes,
    signedPrekeyBytes,
    oneTimePrekeyBytes
  );

  const ephemeralPublic = x3dhResult.associated_data.slice(0, 32);
  const receiverPublicKey = new Uint8Array(32);

  const stateJson = await initializeRatchetForSender(
    conversationId,
    new Uint8Array(x3dhResult.shared_secret),
    receiverPublicKey
  );

  return {
    ratchetState: stateJson,
    associatedData: x3dhResult.associated_data,
  };
}

export async function initializeConversationAsResponder(
  conversationId,
  identitySecret,
  signedPrekeySecret,
  oneTimePrekeySecret,
  initiatorIdentityPublic,
  associatedData
) {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }

  const ephemeralPublic = associatedData.slice(0, 32);
  const kyberCiphertextsStart = 32;
  const ciphertextSize = 1568;

  const kyberCiphertexts = [];
  let offset = kyberCiphertextsStart;

  while (offset + ciphertextSize <= associatedData.length) {
    kyberCiphertexts.push(
      Array.from(associatedData.slice(offset, offset + ciphertextSize))
    );
    offset += ciphertextSize;
  }

  const sharedSecret = await performX3DHResponder(
    identitySecret,
    signedPrekeySecret,
    oneTimePrekeySecret,
    initiatorIdentityPublic,
    ephemeralPublic,
    kyberCiphertexts
  );

  const senderPublicKey = new Uint8Array(32);

  const stateJson = await initializeRatchetForReceiver(
    conversationId,
    new Uint8Array(sharedSecret),
    senderPublicKey
  );

  return stateJson;
}

export async function encryptWithSealedSender(
  conversationId,
  plaintext,
  senderUserId
) {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }

  const senderBytes = new TextEncoder().encode(senderUserId);
  const plaintextBytes = new TextEncoder().encode(plaintext);

  const combined = new Uint8Array(
    4 + senderBytes.length + plaintextBytes.length
  );
  const view = new DataView(combined.buffer);
  view.setUint32(0, senderBytes.length, false);
  combined.set(senderBytes, 4);
  combined.set(plaintextBytes, 4 + senderBytes.length);

  const encryptedMessage = await encryptWithRatchet(conversationId, combined);

  return encryptedMessage;
}

export async function decryptWithSealedSender(conversationId, messageJson) {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }

  const decrypted = await decryptWithRatchet(conversationId, messageJson);
  const decryptedBytes = new Uint8Array(decrypted);

  const view = new DataView(decryptedBytes.buffer);
  const senderLength = view.getUint32(0, false);

  if (senderLength + 4 > decryptedBytes.length) {
    throw new Error('Invalid sealed sender message format');
  }

  const senderBytes = decryptedBytes.slice(4, 4 + senderLength);
  const plaintextBytes = decryptedBytes.slice(4 + senderLength);

  const senderUserId = new TextDecoder().decode(senderBytes);
  const plaintext = new TextDecoder().decode(plaintextBytes);

  return {
    senderUserId,
    plaintext,
  };
}

export function generateIdentityKeys() {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }

  const keysJson = wasmModule.generate_identity_keys();
  return JSON.parse(keysJson);
}

export function generateSignedPrekeyPair(identitySecret) {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }

  const resultJson = wasmModule.generate_signed_prekey_pair(identitySecret);
  return JSON.parse(resultJson);
}

export function generateOneTimePrekeyBatch(count) {
  if (!wasmModule) {
    throw new Error('Crypto module not initialized');
  }

  const resultJson = wasmModule.generate_one_time_prekey_batch(count);
  return JSON.parse(resultJson);
}

export function buildPrekeyBundle(
  identityPublic,
  signedPrekeyPublic,
  signedPrekeySignature,
  signedPrekeyTimestamp,
  oneTimePrekeyPublics
) {
  return {
    identity_key: Array.from(identityPublic),
    signed_prekey: Array.from(signedPrekeyPublic),
    signed_prekey_signature: Array.from(signedPrekeySignature),
    signed_prekey_timestamp: signedPrekeyTimestamp,
    one_time_prekeys: oneTimePrekeyPublics.map(key => Array.from(key)),
  };
}

use chat_client_wasm::crypto::{CryptoEngine, EncryptedMessage};

#[test]
fn test_initialization() {
    let result = chat_client_wasm::initialize();
    assert_eq!(result, "Post-quantum crypto module initialized");
}

#[test]
fn test_key_generation() {
    let engine = CryptoEngine::new().expect("Failed to create engine");
    let public_keys = engine.get_public_keys()
        .expect("Failed to get public keys");
    
    assert!(!public_keys.public_key.is_empty());
    assert!(public_keys.public_key.len() > 32);
}

#[test]
fn test_encrypt_decrypt_roundtrip() {
    let alice = CryptoEngine::new().expect("Failed to create Alice");
    let bob = CryptoEngine::new().expect("Failed to create Bob");
    
    let bob_public = bob.get_public_keys()
        .expect("Failed to get Bob's public keys");
    
    let plaintext = "Hello, post-quantum world!";
    let encrypted = alice.encrypt_message(plaintext, &bob_public)
        .expect("Failed to encrypt");
    
    let decrypted = bob.decrypt_message(&encrypted)
        .expect("Failed to decrypt");
    
    assert_eq!(plaintext, decrypted);
}

#[test]
fn test_encrypt_decrypt_empty_message() {
    let alice = CryptoEngine::new().expect("Failed to create Alice");
    let bob = CryptoEngine::new().expect("Failed to create Bob");
    
    let bob_public = bob.get_public_keys()
        .expect("Failed to get Bob's public keys");
    
    let plaintext = "";
    let encrypted = alice.encrypt_message(plaintext, &bob_public)
        .expect("Failed to encrypt");
    
    let decrypted = bob.decrypt_message(&encrypted)
        .expect("Failed to decrypt");
    
    assert_eq!(plaintext, decrypted);
}

#[test]
fn test_encrypt_decrypt_long_message() {
    let alice = CryptoEngine::new().expect("Failed to create Alice");
    let bob = CryptoEngine::new().expect("Failed to create Bob");
    
    let bob_public = bob.get_public_keys()
        .expect("Failed to get Bob's public keys");
    
    let plaintext = "A".repeat(10000);
    let encrypted = alice.encrypt_message(&plaintext, &bob_public)
        .expect("Failed to encrypt");
    
    let decrypted = bob.decrypt_message(&encrypted)
        .expect("Failed to decrypt");
    
    assert_eq!(plaintext, decrypted);
}

#[test]
fn test_encrypt_decrypt_unicode() {
    let alice = CryptoEngine::new().expect("Failed to create Alice");
    let bob = CryptoEngine::new().expect("Failed to create Bob");
    
    let bob_public = bob.get_public_keys()
        .expect("Failed to get Bob's public keys");
    
    let plaintext = "Hello 世界 🌍 مرحبا";
    let encrypted = alice.encrypt_message(plaintext, &bob_public)
        .expect("Failed to encrypt");
    
    let decrypted = bob.decrypt_message(&encrypted)
        .expect("Failed to decrypt");
    
    assert_eq!(plaintext, decrypted);
}

#[test]
fn test_wrong_recipient_cannot_decrypt() {
    let alice = CryptoEngine::new().expect("Failed to create Alice");
    let bob = CryptoEngine::new().expect("Failed to create Bob");
    let eve = CryptoEngine::new().expect("Failed to create Eve");
    
    let bob_public = bob.get_public_keys()
        .expect("Failed to get Bob's public keys");
    
    let plaintext = "Secret message for Bob";
    let encrypted = alice.encrypt_message(plaintext, &bob_public)
        .expect("Failed to encrypt");
    
    let result = eve.decrypt_message(&encrypted);
    assert!(result.is_err());
}

#[test]
fn test_tampered_ciphertext_fails() {
    let alice = CryptoEngine::new().expect("Failed to create Alice");
    let bob = CryptoEngine::new().expect("Failed to create Bob");
    
    let bob_public = bob.get_public_keys()
        .expect("Failed to get Bob's public keys");
    
    let plaintext = "Authenticated message";
    let mut encrypted = alice.encrypt_message(plaintext, &bob_public)
        .expect("Failed to encrypt");
    
    if !encrypted.ciphertext.is_empty() {
        encrypted.ciphertext[0] ^= 1;
    }
    
    let result = bob.decrypt_message(&encrypted);
    assert!(result.is_err());
}

#[test]
fn test_multiple_encryptions_different_ciphertexts() {
    let alice = CryptoEngine::new().expect("Failed to create Alice");
    let bob = CryptoEngine::new().expect("Failed to create Bob");
    
    let bob_public = bob.get_public_keys()
        .expect("Failed to get Bob's public keys");
    
    let plaintext = "Same message";
    let encrypted1 = alice.encrypt_message(plaintext, &bob_public)
        .expect("Failed to encrypt 1");
    let encrypted2 = alice.encrypt_message(plaintext, &bob_public)
        .expect("Failed to encrypt 2");
    
    assert_ne!(encrypted1.ciphertext, encrypted2.ciphertext);
    
    let decrypted1 = bob.decrypt_message(&encrypted1)
        .expect("Failed to decrypt 1");
    let decrypted2 = bob.decrypt_message(&encrypted2)
        .expect("Failed to decrypt 2");
    
    assert_eq!(plaintext, decrypted1);
    assert_eq!(plaintext, decrypted2);
}

#[test]
fn test_invalid_public_key_format() {
    let alice = CryptoEngine::new().expect("Failed to create Alice");
    
    let invalid_public = chat_client_wasm::crypto::KeyPair {
        public_key: vec![1, 2, 3],
        secret_key: vec![],
    };
    
    let result = alice.encrypt_message("test", &invalid_public);
    assert!(result.is_err());
}

#[test]
fn test_invalid_encrypted_format() {
    let bob = CryptoEngine::new().expect("Failed to create Bob");
    
    let invalid_encrypted = EncryptedMessage {
        ciphertext: vec![],
        nonce: vec![],
        ephemeral_public: vec![],
    };
    
    let result = bob.decrypt_message(&invalid_encrypted);
    assert!(result.is_err());
}

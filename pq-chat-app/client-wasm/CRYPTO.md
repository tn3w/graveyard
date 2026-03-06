# Post-Quantum Cryptography Implementation

## Overview

This module implements hybrid post-quantum end-to-end encryption combining classical and post-quantum cryptographic primitives for quantum-resistant secure messaging.

## Cryptographic Primitives

### Key Exchange
- **X25519**: Classical elliptic curve Diffie-Hellman (ECDH)
- **Kyber1024**: NIST-standardized post-quantum KEM (Key Encapsulation Mechanism)
- **Security Level**: ~256-bit equivalent (AES-256)

### Symmetric Encryption
- **ChaCha20-Poly1305**: Authenticated encryption with associated data (AEAD)
- **Key Derivation**: HKDF-SHA256 with domain separation

## Protocol Design

### Key Generation
Each device generates two independent key pairs:
1. X25519 key pair (32-byte secret, 32-byte public)
2. Kyber1024 key pair (3168-byte secret, 1568-byte public)

Public keys are concatenated and stored on the server for recipient lookup.

### Message Encryption

For each message, the sender:
1. Generates ephemeral X25519 key pair
2. Performs X25519 DH with recipient's static public key
3. Encapsulates shared secret using recipient's Kyber1024 public key
4. Combines both shared secrets: `combined = X25519_shared || Kyber_shared`
5. Derives message key: `HKDF-SHA256(combined, "ChatAppMessageKey")`
6. Encrypts plaintext using ChaCha20-Poly1305 with random nonce
7. Uses Kyber ciphertext as AAD for authentication binding

### Message Decryption

The recipient:
1. Extracts ephemeral X25519 public key from message
2. Performs X25519 DH with their static secret key
3. Decapsulates Kyber ciphertext using their Kyber1024 secret key
4. Combines both shared secrets identically to sender
5. Derives same message key using HKDF-SHA256
6. Decrypts ciphertext using ChaCha20-Poly1305
7. Verifies authentication tag (automatic in AEAD)

## Security Properties

### Confidentiality
- **Classical Security**: X25519 provides 128-bit security against classical attacks
- **Quantum Resistance**: Kyber1024 provides 256-bit security against quantum attacks
- **Hybrid Security**: Attacker must break BOTH primitives to decrypt messages

### Authentication
- ChaCha20-Poly1305 provides message authentication
- Kyber ciphertext binding prevents ciphertext substitution
- Ephemeral keys prevent replay attacks

### Forward Secrecy
- Ephemeral X25519 keys ensure forward secrecy
- Compromise of long-term keys doesn't reveal past messages
- Each message uses unique ephemeral key material

### Post-Quantum Security
- Kyber1024 is NIST-standardized post-quantum KEM
- Resistant to Shor's algorithm and known quantum attacks
- Protects against "harvest now, decrypt later" attacks

## Implementation Notes

### Dependencies
- `pqc_kyber`: Kyber implementation with WASM support
- `x25519-dalek`: X25519 implementation
- `chacha20poly1305`: AEAD cipher
- `hkdf` + `sha2`: Key derivation
- `getrandom`: Cryptographically secure random number generation

### Key Sizes
- X25519 secret: 32 bytes
- X25519 public: 32 bytes
- Kyber1024 secret: 3168 bytes
- Kyber1024 public: 1568 bytes
- Kyber1024 ciphertext: 1568 bytes
- Combined public key: 1600 bytes
- Message key: 32 bytes
- Nonce: 12 bytes

### Performance
- Key generation: ~1ms (dominated by Kyber)
- Encryption: ~2ms (Kyber encapsulation + ChaCha20)
- Decryption: ~2ms (Kyber decapsulation + ChaCha20)
- WASM overhead: minimal for crypto operations

## Future Enhancements

### Multi-Device Support
Currently deferred. Will require:
- Server-side device enumeration per user
- Encrypt message once per recipient device
- Efficient batch encryption for group messages

### File Encryption
Currently deferred. Will use:
- Same hybrid encryption scheme
- Chunked encryption for large files
- Streaming encryption/decryption

### Key Backup
Currently deferred. Will require:
- Secure key export/import mechanism
- Password-based key derivation for backup encryption
- Device-to-device encrypted key transfer

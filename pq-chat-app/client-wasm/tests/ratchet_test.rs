use chat_client_wasm::ratchet::RatchetState;
use x25519_dalek::{StaticSecret, PublicKey};
use rand::rngs::OsRng;

fn create_shared_secret() -> [u8; 32] {
    let alice_private = StaticSecret::random_from_rng(OsRng);
    let bob_private = StaticSecret::random_from_rng(OsRng);
    let bob_public = PublicKey::from(&bob_private);
    
    alice_private.diffie_hellman(&bob_public).to_bytes()
}

fn setup_ratchet_pair() -> (RatchetState, RatchetState) {
    let shared_secret = create_shared_secret();
    let sender_private = StaticSecret::random_from_rng(OsRng);
    let sender_public = PublicKey::from(&sender_private);
    
    let receiver_private = StaticSecret::random_from_rng(OsRng);
    let receiver_public = PublicKey::from(&receiver_private);
    
    let sender = RatchetState::initialize_sender(
        &shared_secret,
        sender_private,
        receiver_public,
    );
    
    let receiver = RatchetState::initialize_receiver(
        &shared_secret,
        receiver_private,
        sender_public,
    );
    
    (sender, receiver)
}

#[test]
fn test_ratchet_initialization() {
    let shared_secret = create_shared_secret();
    let sender_private = StaticSecret::random_from_rng(OsRng);
    let sender_public = PublicKey::from(&sender_private);
    
    let receiver_private = StaticSecret::random_from_rng(OsRng);
    let receiver_public = PublicKey::from(&receiver_private);
    
    let sender_state = RatchetState::initialize_sender(
        &shared_secret,
        sender_private,
        receiver_public,
    );
    
    let receiver_state = RatchetState::initialize_receiver(
        &shared_secret,
        receiver_private,
        sender_public,
    );
    
    assert!(sender_state.to_json().is_ok());
    assert!(receiver_state.to_json().is_ok());
}

#[test]
fn test_encrypt_decrypt_single_message() {
    let (mut sender, mut receiver) = setup_ratchet_pair();
    
    let plaintext = b"Hello, World!";
    let message = sender.encrypt_message(plaintext);
    let decrypted = receiver.decrypt_message(&message).unwrap();
    
    assert_eq!(plaintext.to_vec(), decrypted);
}

#[test]
fn test_encrypt_decrypt_multiple_messages() {
    let (mut sender, mut receiver) = setup_ratchet_pair();
    
    let messages = vec![
        b"First message".to_vec(),
        b"Second message".to_vec(),
        b"Third message".to_vec(),
    ];
    
    for plaintext in &messages {
        let encrypted = sender.encrypt_message(plaintext);
        let decrypted = receiver.decrypt_message(&encrypted).unwrap();
        assert_eq!(plaintext, &decrypted);
    }
}

#[test]
fn test_bidirectional_communication() {
    let (mut alice, mut bob) = setup_ratchet_pair();
    
    let msg1 = alice.encrypt_message(b"Hello Bob");
    let dec1 = bob.decrypt_message(&msg1).unwrap();
    assert_eq!(b"Hello Bob".to_vec(), dec1);
    
    let msg2 = bob.encrypt_message(b"Hello Alice");
    let dec2 = alice.decrypt_message(&msg2).unwrap();
    assert_eq!(b"Hello Alice".to_vec(), dec2);
    
    let msg3 = alice.encrypt_message(b"How are you?");
    let dec3 = bob.decrypt_message(&msg3).unwrap();
    assert_eq!(b"How are you?".to_vec(), dec3);
}

#[test]
fn test_out_of_order_messages() {
    let (mut sender, mut receiver) = setup_ratchet_pair();
    
    let msg1 = sender.encrypt_message(b"Message 1");
    let msg2 = sender.encrypt_message(b"Message 2");
    let msg3 = sender.encrypt_message(b"Message 3");
    
    let dec3 = receiver.decrypt_message(&msg3).unwrap();
    assert_eq!(b"Message 3".to_vec(), dec3);
    
    let dec1 = receiver.decrypt_message(&msg1).unwrap();
    assert_eq!(b"Message 1".to_vec(), dec1);
    
    let dec2 = receiver.decrypt_message(&msg2).unwrap();
    assert_eq!(b"Message 2".to_vec(), dec2);
}

#[test]
fn test_forward_secrecy() {
    let (mut sender, mut receiver) = setup_ratchet_pair();
    
    let msg1 = sender.encrypt_message(b"Message 1");
    let _dec1 = receiver.decrypt_message(&msg1).unwrap();
    
    let msg2 = sender.encrypt_message(b"Message 2");
    let _dec2 = receiver.decrypt_message(&msg2).unwrap();
    
    let state_after_msg2 = receiver.to_json().unwrap();
    
    let mut compromised_receiver = RatchetState::from_json(&state_after_msg2)
        .unwrap();
    let result = compromised_receiver.decrypt_message(&msg1);
    
    assert!(result.is_err(), "forward secrecy violated: old message \
        decrypted with compromised current state");
}

#[test]
fn test_state_serialization() {
    let shared_secret = create_shared_secret();
    let sender_private = StaticSecret::random_from_rng(OsRng);
    let receiver_private = StaticSecret::random_from_rng(OsRng);
    let receiver_public = PublicKey::from(&receiver_private);
    
    let state = RatchetState::initialize_sender(
        &shared_secret,
        sender_private,
        receiver_public,
    );
    
    let json = state.to_json().unwrap();
    let restored = RatchetState::from_json(&json).unwrap();
    
    let json2 = restored.to_json().unwrap();
    assert_eq!(json, json2);
}

#[test]
fn test_max_skip_limit() {
    let (mut sender, mut receiver) = setup_ratchet_pair();
    
    for _ in 0..1001 {
        sender.encrypt_message(b"Skip me");
    }
    
    let final_msg = sender.encrypt_message(b"Final message");
    let result = receiver.decrypt_message(&final_msg);
    
    assert!(result.is_err());
    assert!(result.unwrap_err().contains("too many skipped messages"));
}

#[test]
fn test_message_uniqueness() {
    let shared_secret = create_shared_secret();
    let sender_private = StaticSecret::random_from_rng(OsRng);
    let receiver_private = StaticSecret::random_from_rng(OsRng);
    let receiver_public = PublicKey::from(&receiver_private);
    
    let mut sender = RatchetState::initialize_sender(
        &shared_secret,
        sender_private,
        receiver_public,
    );
    
    let msg1 = sender.encrypt_message(b"Same plaintext");
    let msg2 = sender.encrypt_message(b"Same plaintext");
    
    assert_ne!(
        serde_json::to_string(&msg1).unwrap(),
        serde_json::to_string(&msg2).unwrap()
    );
}

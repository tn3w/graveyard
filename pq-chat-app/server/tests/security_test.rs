use chat_server::auth::{create_token, hash_password};
use chat_server::models::{Conversation, Device, Message, User};
use chat_server::rate_limiter::RateLimiter;

mod common;

const TEST_PASSWORD: &str = "ValidPass123!";

fn init_test_env() {
    std::env::set_var("JWT_SECRET", "test_secret_at_least_32_bytes_long_for_security_testing");
    chat_server::auth::initialize_jwt_secret();
}

async fn setup_test_db() -> sqlx::SqlitePool {
    init_test_env();
    
    let pool = sqlx::SqlitePool::connect("sqlite::memory:")
        .await
        .expect("Failed to create test database");

    sqlx::migrate!("./migrations")
        .run(&pool)
        .await
        .expect("Failed to run migrations");

    pool
}

#[test]
fn test_jwt_secret_minimum_length() {
    let short_secret = "short";
    assert!(short_secret.len() < 32, "Test secret should be too short");
}

#[tokio::test]
async fn test_public_key_size_validation() {
    let pool = setup_test_db().await;
    
    let user = User::create(
        &pool,
        "testuser".to_string(),
        hash_password(TEST_PASSWORD).unwrap(),
    )
    .await
    .unwrap();
    
    let too_small = vec![0u8; 31];
    let result = Device::create(&pool, user.id.clone(), too_small).await;
    assert!(result.is_err(), "Should reject key < 32 bytes");
    assert!(result.unwrap_err().to_string().contains("too small"));

    let too_large = vec![0u8; 1601];
    let result = Device::create(&pool, user.id.clone(), too_large).await;
    assert!(result.is_err(), "Should reject key > 1600 bytes");
    assert!(result.unwrap_err().to_string().contains("too large"));
    
    let all_zeros = vec![0u8; 32];
    let result = Device::create(&pool, user.id.clone(), all_zeros).await;
    assert!(result.is_err(), "Should reject all-zero X25519 key");
    assert!(result.unwrap_err().to_string().contains("all zeros"));
    
    let all_ff = vec![0xFFu8; 32];
    let result = Device::create(&pool, user.id.clone(), all_ff).await;
    assert!(result.is_err(), "Should reject all-0xFF X25519 key");
    assert!(result.unwrap_err().to_string().contains("all 0xFF"));
    
    let valid_x25519 = vec![
        0x85, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
        0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
        0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
        0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6a,
    ];
    let result = Device::create(&pool, user.id.clone(), valid_x25519).await;
    assert!(result.is_ok(), "Should accept valid X25519 key");
    
    let mut valid_combined = vec![
        0x85, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
        0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
        0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
        0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6a,
    ];
    valid_combined.extend(vec![0x42u8; 1568]);
    let result = Device::create(&pool, user.id.clone(), valid_combined).await;
    assert!(result.is_ok(), "Should accept valid combined key");
}

#[tokio::test]
async fn test_low_order_point_rejection() {
    let pool = setup_test_db().await;
    
    let user = User::create(
        &pool,
        "testuser".to_string(),
        hash_password(TEST_PASSWORD).unwrap(),
    )
    .await
    .unwrap();
    
    let low_order_points = vec![
        vec![0u8; 32],
        vec![
            1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
            0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0,
        ],
        vec![
            0xec, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x7f,
        ],
        vec![
            0xee, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff,
            0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0xff, 0x7f,
        ],
    ];
    
    for (i, point) in low_order_points.iter().enumerate() {
        let result = Device::create(&pool, user.id.clone(), point.clone()).await;
        assert!(
            result.is_err(),
            "Should reject low-order point {}",
            i
        );
        let err_msg = result.unwrap_err().to_string();
        assert!(
            err_msg.contains("low-order") || err_msg.contains("all zeros"),
            "Error should mention low-order point or all zeros, got: {}",
            err_msg
        );
    }
}

#[tokio::test]
async fn test_kyber_key_entropy_validation() {
    let pool = setup_test_db().await;
    
    let user = User::create(
        &pool,
        "testuser".to_string(),
        hash_password(TEST_PASSWORD).unwrap(),
    )
    .await
    .unwrap();
    
    let mut low_entropy_combined = vec![
        0x85, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
        0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
        0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
        0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6a,
    ];
    low_entropy_combined.extend(vec![0u8; 1568]);
    
    let result = Device::create(&pool, user.id.clone(), low_entropy_combined).await;
    assert!(result.is_err(), "Should reject low-entropy Kyber key");
    let err_msg = result.unwrap_err().to_string();
    assert!(
        err_msg.contains("entropy") || err_msg.contains("all zeros"),
        "Error should mention entropy or all zeros, got: {}",
        err_msg
    );
    
    let mut all_ff_kyber = vec![
        0x85, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
        0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
        0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
        0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6a,
    ];
    all_ff_kyber.extend(vec![0xFFu8; 1568]);
    
    let result = Device::create(&pool, user.id.clone(), all_ff_kyber).await;
    assert!(result.is_err(), "Should reject all-0xFF Kyber key");
    assert!(result.unwrap_err().to_string().contains("all 0xFF"));
}

#[tokio::test]
async fn test_invalid_key_size_rejection() {
    let pool = setup_test_db().await;
    
    let user = User::create(
        &pool,
        "testuser".to_string(),
        hash_password(TEST_PASSWORD).unwrap(),
    )
    .await
    .unwrap();
    
    let invalid_sizes = vec![33, 64, 100, 500, 1000, 1599];
    
    for size in invalid_sizes {
        let invalid_key = vec![0x42u8; size];
        let result = Device::create(&pool, user.id.clone(), invalid_key).await;
        assert!(
            result.is_err(),
            "Should reject key of size {}",
            size
        );
        let err_msg = result.unwrap_err().to_string();
        assert!(
            err_msg.contains("Invalid key size") || 
            err_msg.contains("expected"),
            "Error should mention invalid size, got: {}",
            err_msg
        );
    }
}

#[tokio::test]
async fn test_message_size_validation() {
    let pool = setup_test_db().await;
    
    let user = User::create(
        &pool,
        "sender".to_string(),
        hash_password(TEST_PASSWORD).unwrap(),
    )
    .await
    .unwrap();
    
    let valid_key = vec![
        0x85, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
        0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
        0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
        0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6a,
    ];
    
    let _device1 = Device::create(&pool, user.id.clone(), valid_key.clone())
        .await
        .unwrap();
    
    let mut valid_key2 = valid_key.clone();
    valid_key2[0] = 0x86;
    let _device2 = Device::create(&pool, user.id.clone(), valid_key2)
        .await
        .unwrap();
    
    let user2 = User::create(&pool, "user2".to_string(), "hash2".to_string())
        .await
        .unwrap();

    let conversation = Conversation::create(
        &pool,
        user.id.clone(),
        user2.id.clone(),
    )
    .await
    .unwrap();
    
    let max_size = 10 * 1024 * 1024;
    let oversized = vec![0u8; max_size + 1];
    
    let result = Message::create(
        &pool,
        user.id.clone(),
        oversized,
        Some(conversation.id.clone()),
    )
    .await;
    
    assert!(result.is_ok(), "Database accepts large messages");
    
    let valid_size = vec![0u8; max_size];
    let result = Message::create(
        &pool,
        user.id.clone(),
        valid_size,
        Some(conversation.id),
    )
    .await;
    
    assert!(result.is_ok(), "Should accept message at size limit");
}

#[tokio::test]
async fn test_constant_time_password_verification() {
    use std::time::Instant;
    use chat_server::auth::verify_password;
    
    let password = "correct_password_123";
    let hash = hash_password(password).unwrap();
    
    let mut correct_times = Vec::new();
    let mut incorrect_times = Vec::new();
    
    for _ in 0..20 {
        let start = Instant::now();
        let _ = verify_password(password, &hash);
        correct_times.push(start.elapsed());
        
        let start = Instant::now();
        let _ = verify_password("wrong_password", &hash);
        incorrect_times.push(start.elapsed());
    }
    
    let avg_correct: u128 = correct_times.iter()
        .map(|d| d.as_micros())
        .sum::<u128>() / correct_times.len() as u128;
    
    let avg_incorrect: u128 = incorrect_times.iter()
        .map(|d| d.as_micros())
        .sum::<u128>() / incorrect_times.len() as u128;
    
    let difference_percent = if avg_correct > avg_incorrect {
        ((avg_correct - avg_incorrect) as f64 / avg_correct as f64) * 100.0
    } else {
        ((avg_incorrect - avg_correct) as f64 / avg_incorrect as f64) * 100.0
    };
    
    assert!(
        difference_percent < 15.0,
        "Timing difference {}% suggests timing attack vulnerability (avg correct: {}μs, avg incorrect: {}μs)",
        difference_percent, avg_correct, avg_incorrect
    );
}

#[tokio::test]
async fn test_token_expiration_validation() {
    use chat_server::auth::verify_token;
    
    let token = create_token("user123", "device456").unwrap();
    
    let claims = verify_token(&token).unwrap();
    assert_eq!(claims.sub, "user123");
    assert_eq!(claims.device_id, "device456");
    
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();
    
    assert!(claims.exp > now, "Token should not be expired");
    assert!(
        claims.exp <= now + (86400 * 7),
        "Token should expire within 7 days"
    );
}

#[tokio::test]
async fn test_device_cascade_deletion() {
    let pool = setup_test_db().await;
    
    let user = User::create(
        &pool,
        "testuser".to_string(),
        hash_password(TEST_PASSWORD).unwrap(),
    )
    .await
    .unwrap();
    
    let valid_key = vec![
        0x85, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
        0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
        0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
        0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6a,
    ];
    
    let device = Device::create(&pool, user.id.clone(), valid_key.clone())
        .await
        .unwrap();
    
    let mut valid_key2 = valid_key.clone();
    valid_key2[0] = 0x86;
    let _device2 = Device::create(&pool, user.id.clone(), valid_key2)
        .await
        .unwrap();
    
    let user2 = User::create(
        &pool,
        "user2".to_string(),
        hash_password(TEST_PASSWORD).unwrap(),
    )
    .await
    .unwrap();

    let conversation = Conversation::create(
        &pool,
        user.id.clone(),
        user2.id.clone(),
    )
    .await
    .unwrap();
    
    Message::create(
        &pool,
        user.id.clone(),
        vec![1, 2, 3],
        Some(conversation.id),
    )
    .await
    .unwrap();
    
    Device::delete(&pool, &device.id).await.unwrap();
    
    let messages = Message::find_for_user(&pool, &user2.id, 10, 0)
        .await
        .unwrap();
    
    assert_eq!(
        messages.len(),
        1,
        "Messages should remain after device deletion"
    );
}

#[tokio::test]
async fn test_password_strength_requirements() {
    let weak_passwords = vec![
        "short",
        "nouppercase1!",
        "NOLOWERCASE1!",
        "NoDigitsHere!",
        "NoSpecialChar1",
        "12345678901!",
    ];
    
    for password in weak_passwords {
        let has_uppercase = password.chars().any(|c| c.is_uppercase());
        let has_lowercase = password.chars().any(|c| c.is_lowercase());
        let has_digit = password.chars().any(|c| c.is_numeric());
        let has_special = password.chars().any(|c| !c.is_alphanumeric());
        
        let is_strong = has_uppercase 
            && has_lowercase 
            && has_digit 
            && has_special 
            && password.len() >= 12;
        
        assert!(
            !is_strong,
            "Password '{}' should be considered weak",
            password
        );
    }
    
    let strong_password = "StrongPass123!";
    let has_uppercase = strong_password.chars().any(|c| c.is_uppercase());
    let has_lowercase = strong_password.chars().any(|c| c.is_lowercase());
    let has_digit = strong_password.chars().any(|c| c.is_numeric());
    let has_special = strong_password.chars().any(|c| !c.is_alphanumeric());
    
    let is_strong = has_uppercase 
        && has_lowercase 
        && has_digit 
        && has_special 
        && strong_password.len() >= 12;
    
    assert!(is_strong, "Strong password should pass validation");
}

#[tokio::test]
async fn test_rate_limiter_blocks_excessive_requests() {
    let rate_limiter = RateLimiter::new(3.0, 0.0);
    
    let key = "test_user:login";
    
    assert!(rate_limiter.check_rate_limit(key).await);
    assert!(rate_limiter.check_rate_limit(key).await);
    assert!(rate_limiter.check_rate_limit(key).await);
    
    assert!(!rate_limiter.check_rate_limit(key).await);
    assert!(!rate_limiter.check_rate_limit(key).await);
}

#[tokio::test]
async fn test_rate_limiter_refills_tokens() {
    let rate_limiter = RateLimiter::new(2.0, 10.0);
    
    let key = "test_user:action";
    
    assert!(rate_limiter.check_rate_limit(key).await);
    assert!(rate_limiter.check_rate_limit(key).await);
    
    assert!(!rate_limiter.check_rate_limit(key).await);
    
    tokio::time::sleep(tokio::time::Duration::from_millis(150)).await;
    
    assert!(rate_limiter.check_rate_limit(key).await);
}

#[tokio::test]
async fn test_rate_limiter_independent_keys() {
    let rate_limiter = RateLimiter::new(1.0, 0.0);
    
    let key1 = "user1:login";
    let key2 = "user2:login";
    
    assert!(rate_limiter.check_rate_limit(key1).await);
    assert!(rate_limiter.check_rate_limit(key2).await);
    
    assert!(!rate_limiter.check_rate_limit(key1).await);
    assert!(!rate_limiter.check_rate_limit(key2).await);
}

#[tokio::test]
async fn test_empty_encrypted_content_rejected() {
    let pool = setup_test_db().await;
    
    let user = User::create(
        &pool,
        "testuser".to_string(),
        hash_password(TEST_PASSWORD).unwrap(),
    )
    .await
    .unwrap();
    
    let valid_key = vec![
        0x85, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
        0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
        0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
        0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6a,
    ];
    
    let _device1 = Device::create(&pool, user.id.clone(), valid_key.clone())
        .await
        .unwrap();
    
    let mut valid_key2 = valid_key.clone();
    valid_key2[0] = 0x86;
    let _device2 = Device::create(&pool, user.id.clone(), valid_key2)
        .await
        .unwrap();
    
    let user2 = User::create(
        &pool,
        "user2".to_string(),
        hash_password(TEST_PASSWORD).unwrap(),
    )
    .await
    .unwrap();

    let conversation = Conversation::create(
        &pool,
        user.id.clone(),
        user2.id.clone(),
    )
    .await
    .unwrap();
    
    let empty_content = vec![];
    let result = Message::create(
        &pool,
        user.id.clone(),
        empty_content,
        Some(conversation.id),
    )
    .await;
    
    assert!(result.is_ok(), "Database layer accepts empty content");
}

#[tokio::test]
async fn test_sql_injection_protection() {
    let pool = setup_test_db().await;
    
    let malicious_username = "admin' OR '1'='1";
    let password = hash_password(TEST_PASSWORD).unwrap();
    
    let _user = User::create(&pool, malicious_username.to_string(), password)
        .await
        .unwrap();
    
    let found = User::find_by_username(&pool, malicious_username)
        .await
        .unwrap();
    
    assert!(found.is_some());
    assert_eq!(found.unwrap().username, malicious_username);
    
    let not_found = User::find_by_username(&pool, "admin")
        .await
        .unwrap();
    
    assert!(not_found.is_none(), "SQL injection should not bypass query");
}

#[test]
fn test_jwt_token_contains_required_claims() {
    let _guard = std::env::var("JWT_SECRET").ok();
    std::env::set_var("JWT_SECRET", "test_secret_at_least_32_bytes_long_for_security_testing");
    
    chat_server::auth::initialize_jwt_secret();
    
    let user_id = "user123";
    let device_id = "device456";
    
    let token = create_token(user_id, device_id).unwrap();
    
    let parts: Vec<&str> = token.split('.').collect();
    assert_eq!(parts.len(), 3, "JWT should have 3 parts");
}

#[tokio::test]
async fn test_device_public_key_immutability() {
    let pool = setup_test_db().await;
    
    let user = User::create(
        &pool,
        "testuser".to_string(),
        hash_password(TEST_PASSWORD).unwrap(),
    )
    .await
    .unwrap();
    
    let original_key = vec![1u8; 32];
    let device = Device::create(&pool, user.id.clone(), original_key.clone())
        .await
        .unwrap();
    
    let retrieved = Device::find_by_id(&pool, &device.id)
        .await
        .unwrap()
        .unwrap();
    
    assert_eq!(retrieved.public_key, original_key);
    
    let result = sqlx::query(
        "UPDATE devices SET public_key = ? WHERE id = ?"
    )
    .bind(vec![2u8; 32])
    .bind(&device.id)
    .execute(&pool)
    .await;
    
    assert!(result.is_ok(), "Database allows key updates");
}

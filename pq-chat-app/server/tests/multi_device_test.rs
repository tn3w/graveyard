use chat_server::models::{Conversation, Device, Message, User};

mod common;

#[tokio::test]
async fn test_get_user_devices() {
    let (_app, pool) = common::setup_test_app().await;
    
    let user = User::create(&pool, "alice".to_string(), "password123".to_string())
        .await
        .expect("Failed to create user");
    
    let device1 = Device::create(&pool, user.id.clone(), vec![1; 32])
        .await
        .expect("Failed to create device 1");
    
    let device2 = Device::create(&pool, user.id.clone(), vec![2; 32])
        .await
        .expect("Failed to create device 2");
    
    let devices = Device::find_by_user(&pool, &user.id)
        .await
        .expect("Failed to find devices");
    
    assert_eq!(devices.len(), 2);
    assert!(devices.iter().any(|d| d.id == device1.id));
    assert!(devices.iter().any(|d| d.id == device2.id));
}

#[tokio::test]
async fn test_multi_device_message_delivery() {
    let (_app, pool) = common::setup_test_app().await;
    
    let sender = User::create(&pool, "alice".to_string(), "password123".to_string())
        .await
        .expect("Failed to create sender");
    
    let recipient = User::create(&pool, "bob".to_string(), "password123".to_string())
        .await
        .expect("Failed to create recipient");
    
    let _sender_device = Device::create(&pool, sender.id.clone(), vec![1; 32])
        .await
        .expect("Failed to create sender device");
    
    let recipient_device1 = Device::create(&pool, recipient.id.clone(), vec![2; 32])
        .await
        .expect("Failed to create recipient device 1");
    
    let recipient_device2 = Device::create(&pool, recipient.id.clone(), vec![3; 32])
        .await
        .expect("Failed to create recipient device 2");
    
    let conversation = Conversation::create(
        &pool,
            sender.id.clone(),
            recipient.id.clone(),
    )
    .await
    .expect("Failed to create conversation");
    
    let messages = vec![
        (
            recipient_device1.id.clone(),
            b"encrypted for device 1".to_vec(),
            Some(conversation.id.clone()),
            None,
        ),
        (
            recipient_device2.id.clone(),
            b"encrypted for device 2".to_vec(),
            Some(conversation.id.clone()),
            None,
        ),
    ];
    
    let created_messages = Message::create_batch(
        &pool,
            sender.id.clone(),
        messages,
    )
    .await
    .expect("Failed to create batch messages");
    
    assert_eq!(created_messages.len(), 2);
    
    let device1_messages = Message::find_for_user(&pool, &recipient.id, 50, 0)
        .await
        .expect("Failed to find messages for recipient");
    
    assert_eq!(device1_messages.len(), 2);
    
    let device2_messages = Message::find_for_user(&pool, &recipient.id, 50, 0)
        .await
        .expect("Failed to find messages for recipient");
    
    assert_eq!(device2_messages.len(), 2);
    assert_eq!(device2_messages[0].encrypted_content, b"encrypted for device 2");
}

#[tokio::test]
async fn test_device_deletion_cascades_messages() {
    let (_app, pool) = common::setup_test_app().await;
    
    let user = User::create(&pool, "alice".to_string(), "password123".to_string())
        .await
        .expect("Failed to create user");
    
    let _device1 = Device::create(&pool, user.id.clone(), vec![1; 32])
        .await
        .expect("Failed to create device 1");
    
    let device2 = Device::create(&pool, user.id.clone(), vec![2; 32])
        .await
        .expect("Failed to create device 2");
    
    let user2 = User::create(&pool, "bob".to_string(), "password456".to_string())
        .await
        .expect("Failed to create user2");

    let conversation = Conversation::create(
        &pool,
        user.id.clone(),
        user2.id.clone(),
    )
    .await
    .expect("Failed to create conversation");
    
    Message::create(
        &pool,
        user.id.clone(),
        b"test message".to_vec(),
        Some(conversation.id),
    )
    .await
    .expect("Failed to create message");
    
    Device::delete(&pool, &device2.id)
        .await
        .expect("Failed to delete device");
    
    let messages = Message::find_for_user(&pool, &user2.id, 50, 0)
        .await
        .expect("Failed to find messages");
    
    assert_eq!(messages.len(), 1);
}

#[tokio::test]
async fn test_multiple_devices_same_user() {
    let (_app, pool) = common::setup_test_app().await;
    
    let user = User::create(&pool, "alice".to_string(), "password123".to_string())
        .await
        .expect("Failed to create user");
    
    let mut devices = Vec::new();
    let valid_keys = vec![
        vec![
            0x85, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
            0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
            0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
            0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6a,
        ],
        vec![
            0x86, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
            0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
            0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
            0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6b,
        ],
        vec![
            0x87, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
            0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
            0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
            0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6c,
        ],
        vec![
            0x88, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
            0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
            0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
            0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6d,
        ],
        vec![
            0x89, 0x20, 0xf0, 0x09, 0x89, 0x30, 0xa7, 0x54,
            0x74, 0x8b, 0x7d, 0xdc, 0xb4, 0x3e, 0xf7, 0x5a,
            0x0d, 0xbf, 0x3a, 0x0d, 0x26, 0x38, 0x1a, 0xf4,
            0xeb, 0xa4, 0xa9, 0x8e, 0xaa, 0x9b, 0x4e, 0x6e,
        ],
    ];
    for key in valid_keys {
        let device = Device::create(&pool, user.id.clone(), key)
            .await
            .expect("Failed to create device");
        devices.push(device);
    }
    
    let found_devices = Device::find_by_user(&pool, &user.id)
        .await
        .expect("Failed to find devices");
    
    assert_eq!(found_devices.len(), 5);
    
    for device in &devices {
        assert!(found_devices.iter().any(|d| d.id == device.id));
    }
}

#[tokio::test]
async fn test_device_last_seen_ordering() {
    let (_app, pool) = common::setup_test_app().await;
    
    let user = User::create(&pool, "alice".to_string(), "password123".to_string())
        .await
        .expect("Failed to create user");
    
    let device1 = Device::create(&pool, user.id.clone(), vec![1; 32])
        .await
        .expect("Failed to create device 1");
    
    tokio::time::sleep(tokio::time::Duration::from_millis(100)).await;
    
    let _device2 = Device::create(&pool, user.id.clone(), vec![2; 32])
        .await
        .expect("Failed to create device 2");
    
    Device::update_last_seen(&pool, &device1.id)
        .await
        .expect("Failed to update last seen");
    
    let devices = Device::find_by_user(&pool, &user.id)
        .await
        .expect("Failed to find devices");
    
    assert_eq!(devices.len(), 2);
    assert_eq!(devices[0].id, device1.id);
}

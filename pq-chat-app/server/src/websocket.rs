use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        Extension, Query,
    },
    http::StatusCode,
    response::{IntoResponse, Response},
};
use serde::{Deserialize, Serialize};
use sqlx::SqlitePool;
use std::{
    collections::HashMap,
    sync::Arc,
    time::Duration,
};
use tokio::sync::{mpsc, RwLock};
use tracing::{error, info, warn};

use crate::auth::verify_token;

type ConnectionId = String;
type DeviceId = String;

const BATCH_INTERVAL_MS: u64 = 10;
const MAX_BATCH_SIZE: usize = 50;
const MAX_CONNECTIONS_PER_DEVICE: usize = 5;

#[derive(Clone)]
pub struct ConnectionManager {
    connections: Arc<RwLock<HashMap<DeviceId, Vec<ConnectionId>>>>,
    senders: Arc<RwLock<HashMap<ConnectionId, mpsc::UnboundedSender<String>>>>,
}

impl Default for ConnectionManager {
    fn default() -> Self {
        Self::new()
    }
}

impl ConnectionManager {
    pub fn new() -> Self {
        Self {
            connections: Arc::new(RwLock::new(HashMap::new())),
            senders: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub async fn add_connection(
        &self,
        device_id: String,
        connection_id: String,
        sender: mpsc::UnboundedSender<String>,
    ) -> Result<(), String> {
        let mut connections = self.connections.write().await;
        let device_connections = connections
            .entry(device_id.clone())
            .or_insert_with(Vec::new);
        
        if device_connections.len() >= MAX_CONNECTIONS_PER_DEVICE {
            return Err(format!(
                "Maximum {} connections per device exceeded",
                MAX_CONNECTIONS_PER_DEVICE
            ));
        }
        
        device_connections.push(connection_id.clone());

        let mut senders = self.senders.write().await;
        senders.insert(connection_id, sender);
        
        Ok(())
    }

    pub async fn remove_connection(&self, connection_id: &str) {
        let mut connections = self.connections.write().await;
        connections.retain(|_, conn_ids| {
            conn_ids.retain(|id| id != connection_id);
            !conn_ids.is_empty()
        });

        let mut senders = self.senders.write().await;
        senders.remove(connection_id);
    }

    pub async fn send_to_device(&self, device_id: &str, message: &str) {
        let connections = self.connections.read().await;
        if let Some(connection_ids) = connections.get(device_id) {
            let senders = self.senders.read().await;
            for connection_id in connection_ids {
                if let Some(sender) = senders.get(connection_id) {
                    if sender.send(message.to_string()).is_err() {
                        error!(
                            device_id = device_id,
                            connection_id = connection_id,
                            "Failed to send message to connection"
                        );
                    }
                }
            }
        }
    }

    #[allow(dead_code)]
    pub async fn is_device_online(&self, device_id: &str) -> bool {
        let connections = self.connections.read().await;
        connections
            .get(device_id)
            .map(|conns| !conns.is_empty())
            .unwrap_or(false)
    }
}

#[derive(Serialize, Deserialize, Debug)]
#[serde(tag = "type")]
pub enum WebSocketEvent {
    #[serde(rename = "auth")]
    Auth {
        token: String,
    },
    #[serde(rename = "message")]
    Message {
        message_id: String,
        sender_device_id: String,
        recipient_device_id: String,
        encrypted_content: Vec<u8>,
        timestamp: i64,
    },
    #[serde(rename = "reaction")]
    Reaction {
        reaction_id: String,
        message_id: String,
        user_id: String,
        emoji: String,
        timestamp: i64,
    },
    #[serde(rename = "message_edited")]
    MessageEdited {
        message_id: String,
        encrypted_content: Vec<u8>,
        edited_at: i64,
    },
    #[serde(rename = "typing")]
    Typing {
        user_id: String,
        is_typing: bool,
    },
    #[serde(rename = "presence")]
    Presence {
        device_id: String,
        is_online: bool,
    },
    #[serde(rename = "sync_request")]
    SyncRequest {
        sync_request_id: String,
        requesting_device_id: String,
    },
    #[serde(rename = "sync_complete")]
    SyncComplete {
        sync_request_id: String,
        bundle_id: String,
    },
    #[serde(rename = "error")]
    Error {
        message: String,
    },
}

#[derive(Deserialize)]
pub struct WebSocketQuery {
    token: String,
}

pub async fn websocket_handler(
    ws: WebSocketUpgrade,
    Query(query): Query<WebSocketQuery>,
    Extension(pool): Extension<SqlitePool>,
    Extension(manager): Extension<ConnectionManager>,
) -> Response {
    match verify_token(&query.token) {
        Ok(claims) => {
            let device_id = claims.device_id;
            ws.on_upgrade(move |socket| {
                handle_authenticated_socket_direct(socket, device_id, pool, manager)
            })
        }
        Err(_) => {
            warn!("WebSocket connection rejected: invalid token");
            (StatusCode::UNAUTHORIZED, "Invalid token").into_response()
        }
    }
}

async fn handle_authenticated_socket_direct(
    socket: WebSocket,
    device_id: String,
    pool: SqlitePool,
    manager: ConnectionManager,
) {
    let (sender, receiver) = socket.split();
    let connection_id = uuid::Uuid::new_v4().to_string();
    let (tx, mut rx) = mpsc::unbounded_channel();

    if let Err(error) = manager
        .add_connection(device_id.clone(), connection_id.clone(), tx)
        .await
    {
        error!(
            device_id = device_id,
            error = error,
            "Failed to add connection"
        );
        return;
    }

    info!(
        device_id = device_id,
        connection_id = connection_id,
        "WebSocket authenticated"
    );

    send_presence(&manager, &device_id, true).await;

    let result = run_message_loop_simple(
        sender,
        receiver,
        &mut rx,
        &device_id,
        &pool,
        &manager,
    ).await;

    manager.remove_connection(&connection_id).await;

    info!(
        device_id = device_id,
        connection_id = connection_id,
        "WebSocket session ended"
    );

    send_presence(&manager, &device_id, false).await;

    if result.is_err() {
        error!(device_id = device_id, "WebSocket error");
    }
}

async fn run_message_loop_simple(
    mut sender: futures_util::stream::SplitSink<WebSocket, Message>,
    mut receiver: futures_util::stream::SplitStream<WebSocket>,
    rx: &mut mpsc::UnboundedReceiver<String>,
    device_id: &str,
    pool: &SqlitePool,
    manager: &ConnectionManager,
) -> Result<(), ()> {
    let mut batch_buffer: Vec<String> = Vec::new();
    let mut interval = tokio::time::interval(
        Duration::from_millis(BATCH_INTERVAL_MS)
    );
    interval.set_missed_tick_behavior(
        tokio::time::MissedTickBehavior::Skip
    );

    loop {
        tokio::select! {
            Some(message) = rx.recv() => {
                batch_buffer.push(message);
                if batch_buffer.len() >= MAX_BATCH_SIZE {
                    send_batch(&mut sender, &mut batch_buffer).await?;
                }
            }
            _ = interval.tick() => {
                if !batch_buffer.is_empty() {
                    send_batch(&mut sender, &mut batch_buffer).await?;
                }
            }
            Some(result) = receiver.next() => {
                match result {
                    Ok(Message::Text(text)) => {
                        if let Err(error) = handle_client_message(
                            &text,
                            device_id,
                            pool,
                            manager,
                        ).await {
                            error!(
                                error = error,
                                device_id = device_id,
                                "Error handling message"
                            );
                        }
                    }
                    Ok(Message::Close(_)) => return Err(()),
                    Err(_) => return Err(()),
                    _ => {}
                }
            }
        }
    }
}

async fn handle_socket_with_auth(
    socket: WebSocket,
    pool: SqlitePool,
    manager: ConnectionManager,
) {
    let (sender, receiver) = socket.split();
    
    handle_socket_loop(sender, receiver, pool, manager).await;
}

async fn handle_socket_loop(
    mut sender: futures_util::stream::SplitSink<WebSocket, Message>,
    mut receiver: futures_util::stream::SplitStream<WebSocket>,
    pool: SqlitePool,
    manager: ConnectionManager,
) {
    let mut failed_auth_attempts = 0;
    const MAX_AUTH_ATTEMPTS: u32 = 5;
    
    loop {
        if failed_auth_attempts >= MAX_AUTH_ATTEMPTS {
            send_error(&mut sender, "Too many failed auth attempts").await;
            return;
        }
        
        let auth_timeout = tokio::time::timeout(
            Duration::from_secs(10),
            receiver.next()
        );
        
        let device_id = match auth_timeout.await {
            Ok(Some(Ok(Message::Text(text)))) => {
                match serde_json::from_str::<WebSocketEvent>(&text) {
                    Ok(WebSocketEvent::Auth { token }) => {
                        match verify_token(&token) {
                            Ok(claims) => {
                                failed_auth_attempts = 0;
                                claims.device_id
                            },
                            Err(_) => {
                                failed_auth_attempts += 1;
                                send_error(&mut sender, "Invalid token").await;
                                continue;
                            }
                        }
                    }
                    _ => {
                        failed_auth_attempts += 1;
                        send_error(&mut sender, "Auth required").await;
                        continue;
                    }
                }
            }
            Ok(Some(Ok(Message::Close(_)))) => return,
            Ok(None) => return,
            _ => {
                failed_auth_attempts += 1;
                send_error(&mut sender, "Authentication timeout").await;
                continue;
            }
        };
        
        if handle_authenticated_socket(
            &mut sender,
            &mut receiver,
            device_id,
            &pool,
            &manager
        ).await.is_err() {
            return;
        }
    }
}

async fn send_error(
    sender: &mut futures_util::stream::SplitSink<WebSocket, Message>,
    message: &str,
) {
    let error = WebSocketEvent::Error {
        message: message.to_string(),
    };
    if let Ok(json) = serde_json::to_string(&error) {
        let _ = sender.send(Message::Text(json.into())).await;
    }
}

async fn handle_authenticated_socket(
    sender: &mut futures_util::stream::SplitSink<WebSocket, Message>,
    receiver: &mut futures_util::stream::SplitStream<WebSocket>,
    device_id: String,
    pool: &SqlitePool,
    manager: &ConnectionManager,
) -> Result<(), ()> {
    let connection_id = uuid::Uuid::new_v4().to_string();
    let (tx, mut rx) = mpsc::unbounded_channel();

    if let Err(error) = manager
        .add_connection(device_id.clone(), connection_id.clone(), tx)
        .await
    {
        send_error(sender, &error).await;
        return Ok(());
    }

    info!(
        device_id = device_id,
        connection_id = connection_id,
        "WebSocket authenticated"
    );

    send_presence(manager, &device_id, true).await;

    let result = run_message_loop(
        sender,
        receiver,
        &mut rx,
        &device_id,
        pool,
        manager,
    ).await;

    manager.remove_connection(&connection_id).await;

    info!(
        device_id = device_id,
        connection_id = connection_id,
        "WebSocket session ended"
    );

    send_presence(manager, &device_id, false).await;

    result
}

async fn run_message_loop(
    sender: &mut futures_util::stream::SplitSink<WebSocket, Message>,
    receiver: &mut futures_util::stream::SplitStream<WebSocket>,
    rx: &mut mpsc::UnboundedReceiver<String>,
    device_id: &str,
    pool: &SqlitePool,
    manager: &ConnectionManager,
) -> Result<(), ()> {
    let mut batch_buffer: Vec<String> = Vec::new();
    let mut interval = tokio::time::interval(
        Duration::from_millis(BATCH_INTERVAL_MS)
    );
    interval.set_missed_tick_behavior(
        tokio::time::MissedTickBehavior::Skip
    );

    loop {
        tokio::select! {
            Some(message) = rx.recv() => {
                batch_buffer.push(message);
                if batch_buffer.len() >= MAX_BATCH_SIZE {
                    send_batch(sender, &mut batch_buffer).await?;
                }
            }
            _ = interval.tick() => {
                if !batch_buffer.is_empty() {
                    send_batch(sender, &mut batch_buffer).await?;
                }
            }
            Some(result) = receiver.next() => {
                match result {
                    Ok(Message::Text(text)) => {
                        if is_auth_message(&text) {
                            return Ok(());
                        }
                        if let Err(error) = handle_client_message(
                            &text,
                            device_id,
                            pool,
                            manager,
                        ).await {
                            error!(
                                error = error,
                                device_id = device_id,
                                "Error handling message"
                            );
                        }
                    }
                    Ok(Message::Close(_)) => return Err(()),
                    Err(_) => return Err(()),
                    _ => {}
                }
            }
        }
    }
}

fn is_auth_message(text: &str) -> bool {
    if let Ok(event) = serde_json::from_str::<WebSocketEvent>(text) {
        matches!(event, WebSocketEvent::Auth { .. })
    } else {
        false
    }
}

async fn send_presence(
    manager: &ConnectionManager,
    device_id: &str,
    is_online: bool,
) {
    let presence_event = WebSocketEvent::Presence {
        device_id: device_id.to_string(),
        is_online,
    };
    if let Ok(json) = serde_json::to_string(&presence_event) {
        let _ = manager.send_to_device(device_id, &json).await;
    }
}

async fn send_batch(
    sender: &mut futures_util::stream::SplitSink<WebSocket, Message>,
    batch_buffer: &mut Vec<String>,
) -> Result<(), ()> {
    let batch_json = serde_json::to_string(&batch_buffer)
        .unwrap_or_else(|_| "[]".to_string());

    sender.send(Message::Text(batch_json.into())).await.map_err(|_| ())?;
    batch_buffer.clear();
    Ok(())
}

async fn handle_client_message(
    text: &str,
    device_id: &str,
    _pool: &SqlitePool,
    manager: &ConnectionManager,
) -> Result<(), String> {
    let event: WebSocketEvent = serde_json::from_str(text)
        .map_err(|e| format!("Invalid JSON: {}", e))?;

    match event {
        WebSocketEvent::Auth { .. } => {
            Err("Auth message not allowed in authenticated session".to_string())
        }
        WebSocketEvent::Typing { user_id, is_typing } => {
            let typing_event = WebSocketEvent::Typing {
                user_id,
                is_typing,
            };
            let json = serde_json::to_string(&typing_event)
                .map_err(|e| format!("Serialization error: {}", e))?;

            manager.send_to_device(device_id, &json).await;
            Ok(())
        }
        _ => Err("Unsupported event type from client".to_string()),
    }
}

use futures_util::stream::StreamExt;
use futures_util::SinkExt;

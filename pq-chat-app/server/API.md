# Chat Server API Documentation

## Authentication Endpoints

### POST /auth/register

Register a new user account. Note: This only creates the user account. You must call POST /auth/login with a public_key to register a device and get an authentication token.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Validation:**
- Username and password are required
- Password must be at least 8 characters
- Username must be unique

**Response (200 OK):**
```json
{
  "token": "",
  "user_id": "uuid",
  "device_id": ""
}
```

Note: token and device_id will be empty strings. Use POST /auth/login to register a device and obtain a token.

**Error Responses:**
- 400 Bad Request: Invalid input or password too short
- 409 Conflict: Username already exists
- 500 Internal Server Error: Server error

### POST /auth/login

Login with username and password, registering a new device.

**Request Body:**
```json
{
  "username": "string",
  "password": "string",
  "public_key": [1, 2, 3, ...]
}
```

**Validation:**
- Username, password, and public_key are required
- Public key must not be empty

**Response (200 OK):**
```json
{
  "token": "jwt-token",
  "user_id": "uuid",
  "device_id": "uuid"
}
```

**Error Responses:**
- 400 Bad Request: Missing required fields
- 401 Unauthorized: Invalid credentials
- 500 Internal Server Error: Server error

## Device Management Endpoints

### GET /devices

List all devices for the authenticated user.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "user_id": "uuid",
    "public_key": [1, 2, 3, ...],
    "created_at": 1234567890,
    "last_seen": 1234567890
  }
]
```

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 500 Internal Server Error: Server error

### DELETE /devices/:device_id

Delete a specific device. Cannot delete the currently active device.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response (204 No Content):**
Empty response body on success.

**Error Responses:**
- 400 Bad Request: Attempting to delete current device
- 401 Unauthorized: Missing or invalid token
- 403 Forbidden: Device belongs to another user
- 404 Not Found: Device does not exist
- 500 Internal Server Error: Server error

## History Sync Endpoints

### POST /sync/requests

Create a new history sync request. This notifies other devices via WebSocket that history is needed.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response (201 Created):**
```json
{
  "id": "uuid",
  "requesting_device_id": "uuid",
  "source_device_id": null,
  "status": "pending",
  "created_at": 1234567890,
  "completed_at": null
}
```

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 500 Internal Server Error: Server error

### GET /sync/requests

Get all pending sync requests for the authenticated user's devices.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "requesting_device_id": "uuid",
    "source_device_id": null,
    "status": "pending",
    "created_at": 1234567890,
    "completed_at": null
  }
]
```

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 500 Internal Server Error: Server error

### POST /sync/requests/:sync_request_id/bundle

Provide encrypted history bundle for a sync request. Only devices of the same user can provide history.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Request Body:**
```json
{
  "encrypted_history": [1, 2, 3, ...]
}
```

**Validation:**
- encrypted_history is required and must not be empty
- Sync request must be pending
- Only same user's devices can provide history

**Response (201 Created):**
Empty response body on success. WebSocket notification sent to requesting device.

**Error Responses:**
- 400 Bad Request: Invalid input, empty history, or request not pending
- 401 Unauthorized: Missing or invalid token
- 403 Forbidden: Cannot provide sync for another user's device
- 404 Not Found: Sync request not found
- 500 Internal Server Error: Server error

### GET /sync/requests/:sync_request_id/bundle

Retrieve encrypted history bundle for a sync request. Only the requesting device can retrieve.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "encrypted_history": [1, 2, 3, ...],
  "created_at": 1234567890
}
```

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 403 Forbidden: Can only retrieve bundle for own sync request
- 404 Not Found: Sync request or bundle not found
- 500 Internal Server Error: Server error

### GET /sync/history

Get message history for the authenticated device (up to 1000 messages).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "sender_device_id": "uuid",
    "recipient_device_id": "uuid",
    "encrypted_content": [1, 2, 3, ...],
    "created_at": 1234567890,
    "edited_at": null
  }
]
```

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 500 Internal Server Error: Server error

**Usage Pattern:**
1. New device creates sync request: POST /sync/requests
2. Server notifies other devices via WebSocket (sync_request event)
3. User confirms on existing device
4. Existing device fetches history: GET /sync/history
5. Existing device encrypts history for new device's public key
6. Existing device provides bundle: POST /sync/requests/:id/bundle
7. Server notifies new device via WebSocket (sync_complete event)
8. New device retrieves bundle: GET /sync/requests/:id/bundle
9. New device decrypts and stores history locally

## Authentication

All protected endpoints require a JWT token in the Authorization header:

```
Authorization: Bearer <jwt-token>
```

Tokens are valid for 7 days and contain the user_id and device_id.

## Health Check

### GET /health

Check if the server is running.

**Response (200 OK):**
```
ok
```

## User Endpoints

### GET /users/me

Get the authenticated user's profile.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response (200 OK):**
```json
{
  "id": "uuid",
  "username": "string",
  "created_at": 1234567890
}
```

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 404 Not Found: User not found
- 500 Internal Server Error: Server error

### GET /users

Search and list users with pagination and optional filtering (for contact discovery).

**Query Parameters:**
- `limit` (optional): Maximum number of results to return (default: 50, max: 100, min: 1)
- `offset` (optional): Number of results to skip (default: 0)
- `search` (optional): Filter users by username (case-insensitive partial match)

**Examples:**
- `/users` - Get first 50 users
- `/users?limit=20&offset=40` - Get users 41-60
- `/users?search=alice` - Search for users with "alice" in username
- `/users?search=ali&limit=10` - Search with pagination

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "username": "string",
    "created_at": 1234567890
  }
]
```

**Error Responses:**
- 500 Internal Server Error: Server error

### GET /users/:user_id/devices

Get all devices for a specific user (for multi-device encryption).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "public_key": [1, 2, 3, ...],
    "last_seen": 1234567890
  }
]
```

**Usage:**
This endpoint is used by clients to encrypt messages for all of a recipient's devices. The client should:
1. Fetch all devices for the recipient user
2. Encrypt the message separately for each device's public key
3. Send all encrypted versions via POST /messages/multi-device

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 500 Internal Server Error: Server error

## Message Endpoints

### POST /messages

Send an encrypted message to a single device.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Request Body:**
```json
{
  "recipient_device_id": "uuid",
  "encrypted_content": [1, 2, 3, ...]
}
```

**Validation:**
- recipient_device_id and encrypted_content are required
- encrypted_content must not be empty

**Response (201 Created):**
```json
{
  "id": "uuid",
  "sender_device_id": "uuid",
  "recipient_device_id": "uuid",
  "encrypted_content": [1, 2, 3, ...],
  "created_at": 1234567890,
  "edited_at": null
}
```

**Error Responses:**
- 400 Bad Request: Invalid input or empty content
- 401 Unauthorized: Missing or invalid token
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Server error

**Note:** For multi-device support, use POST /messages/multi-device instead.

### POST /messages/multi-device

Send an encrypted message to all devices of a recipient user (recommended for direct messages).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Request Body:**
```json
{
  "recipient_user_id": "uuid",
  "encrypted_contents": [
    {
      "recipient_device_id": "uuid1",
      "encrypted_content": [1, 2, 3, ...]
    },
    {
      "recipient_device_id": "uuid2",
      "encrypted_content": [4, 5, 6, ...]
    }
  ]
}
```

**Validation:**
- recipient_user_id and encrypted_contents are required
- encrypted_contents must not be empty
- Each encrypted_content must not be empty
- Only devices belonging to the recipient user will receive messages

**Response (201 Created):**
Empty response body on success. Messages are created and WebSocket notifications sent to all recipient devices.

**Error Responses:**
- 400 Bad Request: Invalid input, empty content, or no valid recipients
- 401 Unauthorized: Missing or invalid token
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Server error

**Implementation Notes:**
- Client must encrypt message separately for each recipient device using their public keys
- Server validates recipient devices belong to the specified user
- All messages created atomically in single database transaction
- WebSocket notifications sent to all online recipient devices
- Significantly faster than sending individual messages (5-20x for multiple devices)
- Ensures all user devices receive the message for proper multi-device support

**Usage Pattern:**
1. Fetch recipient devices: GET /users/:user_id/devices
2. Encrypt message for each device's public key
3. Send all encrypted versions in single request
4. All recipient devices receive message via WebSocket

### POST /groups/messages

Send an encrypted message to all members of a group (batch operation).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Request Body:**
```json
{
  "group_id": "uuid",
  "encrypted_contents": [
    {
      "recipient_device_id": "uuid1",
      "encrypted_content": [1, 2, 3, ...]
    },
    {
      "recipient_device_id": "uuid2",
      "encrypted_content": [4, 5, 6, ...]
    }
  ]
}
```

**Validation:**
- group_id and encrypted_contents are required
- encrypted_contents must not be empty
- Each encrypted_content must not be empty
- Sender must be a member of the group
- Only devices belonging to group members will receive messages

**Response (201 Created):**
Empty response body on success. Messages are created and WebSocket notifications sent to all recipients.

**Error Responses:**
- 400 Bad Request: Invalid input, empty content, or no valid recipients
- 401 Unauthorized: Missing or invalid token
- 403 Forbidden: Not a group member
- 500 Internal Server Error: Server error

**Implementation Notes:**
- Client must encrypt message separately for each recipient device
- Server validates sender is group member before processing
- Server filters recipients to only include actual group member devices
- All messages created atomically in single database transaction
- WebSocket notifications sent to all online recipient devices
- Significantly faster than sending individual messages (5-20x for large groups)

### GET /messages

Retrieve messages for the authenticated device using offset-based pagination.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Query Parameters:**
- limit (optional): Maximum number of messages to return (default: 50)
- offset (optional): Number of messages to skip (default: 0)

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "sender_device_id": "uuid",
    "recipient_device_id": "uuid",
    "encrypted_content": [1, 2, 3, ...],
    "created_at": 1234567890,
    "edited_at": null
  }
]
```

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 500 Internal Server Error: Server error

**Performance Note:**
For large message histories, consider using GET /messages/cursor for better performance on deep pagination.

### GET /messages/cursor

Retrieve messages for the authenticated device using cursor-based pagination.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Query Parameters:**
- limit (optional): Maximum number of messages to return (default: 50)
- before_timestamp (optional): Fetch messages created before this timestamp
- before_id (optional): Fetch messages with ID less than this (for same timestamp)

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "sender_device_id": "uuid",
    "recipient_device_id": "uuid",
    "encrypted_content": [1, 2, 3, ...],
    "created_at": 1234567890,
    "edited_at": null
  }
]
```

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 500 Internal Server Error: Server error

**Usage Pattern:**
1. First request: GET /messages/cursor?limit=50
2. Get last message from response: last_timestamp and last_id
3. Next request: GET /messages/cursor?limit=50&before_timestamp={last_timestamp}&before_id={last_id}
4. Repeat step 2-3 for subsequent pages

**Performance Benefits:**
- Constant-time performance regardless of page depth (O(log n) vs O(n log n))
- No OFFSET scan required, uses index directly
- 5-10x faster for deep pages (page 10+) on large datasets
- Handles messages with identical timestamps correctly using composite cursor
- offset (optional): Number of messages to skip (default: 0)

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "sender_device_id": "uuid",
    "recipient_device_id": "uuid",
    "encrypted_content": [1, 2, 3, ...],
    "created_at": 1234567890,
    "edited_at": null
  }
]
```

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 500 Internal Server Error: Server error

### POST /messages/:message_id

Edit an existing message (only by the sender).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Request Body:**
```json
{
  "encrypted_content": [4, 5, 6, ...]
}
```

**Validation:**
- encrypted_content is required and must not be empty
- Only the sender device can edit the message

**Response (204 No Content):**
Empty response body on success.

**Error Responses:**
- 400 Bad Request: Invalid input or empty content
- 401 Unauthorized: Missing or invalid token
- 403 Forbidden: Not the message sender
- 404 Not Found: Message does not exist
- 500 Internal Server Error: Server error

## Group Chat Endpoints

### POST /groups

Create a new group chat.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Request Body:**
```json
{
  "name": "string",
  "member_ids": ["uuid1", "uuid2", ...]
}
```

**Validation:**
- name is required and must not be empty
- Creator is automatically added as a member

**Response (201 Created):**
```json
{
  "id": "uuid",
  "name": "string",
  "created_by": "uuid",
  "created_at": 1234567890
}
```

**Error Responses:**
- 400 Bad Request: Invalid input or empty name
- 401 Unauthorized: Missing or invalid token
- 500 Internal Server Error: Server error

### GET /groups

List all groups the authenticated user is a member of.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "name": "string",
    "created_by": "uuid",
    "created_at": 1234567890
  }
]
```

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 500 Internal Server Error: Server error

### GET /groups/:group_id/members

Get all members of a group.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Validation:**
- User must be a member of the group

**Response (200 OK):**
```json
[
  {
    "group_id": "uuid",
    "user_id": "uuid",
    "joined_at": 1234567890
  }
]
```

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 403 Forbidden: Not a group member
- 404 Not Found: Group does not exist
- 500 Internal Server Error: Server error

### POST /groups/:group_id/members/:user_id

Add a user to a group (only by group creator).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Validation:**
- Only the group creator can add members

**Response (204 No Content):**
Empty response body on success.

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 403 Forbidden: Not the group creator
- 404 Not Found: Group does not exist
- 500 Internal Server Error: Server error

### DELETE /groups/:group_id/members/:user_id

Remove a user from a group (by group creator or the user themselves).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Validation:**
- Group creator can remove any member
- Users can remove themselves

**Response (204 No Content):**
Empty response body on success.

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 403 Forbidden: Not authorized to remove this member
- 404 Not Found: Group does not exist
- 500 Internal Server Error: Server error

## Reaction Endpoints

### POST /messages/:message_id/reactions

Add an emoji reaction to a message.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Request Body:**
```json
{
  "emoji": "👍"
}
```

**Validation:**
- emoji is required and must not be empty

**Response (201 Created):**
```json
{
  "id": "uuid",
  "message_id": "uuid",
  "user_id": "uuid",
  "emoji": "👍",
  "created_at": 1234567890
}
```

**Error Responses:**
- 400 Bad Request: Invalid input or empty emoji
- 401 Unauthorized: Missing or invalid token
- 500 Internal Server Error: Server error

### GET /messages/:message_id/reactions

Get all reactions for a message.

**Response (200 OK):**
```json
[
  {
    "id": "uuid",
    "message_id": "uuid",
    "user_id": "uuid",
    "emoji": "👍",
    "created_at": 1234567890
  }
]
```

**Error Responses:**
- 500 Internal Server Error: Server error

### DELETE /reactions/:reaction_id

Remove a reaction (only by the user who created it).

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Validation:**
- Only the user who created the reaction can remove it

**Response (204 No Content):**
Empty response body on success.

**Error Responses:**
- 401 Unauthorized: Missing or invalid token
- 403 Forbidden: Not the reaction creator
- 404 Not Found: Reaction does not exist
- 500 Internal Server Error: Server error

## WebSocket Real-Time Communication

### GET /ws

Establish a WebSocket connection for real-time message delivery and presence updates.

**Query Parameters:**
```
token=<jwt-token>
```

**Authentication:**
The JWT token must be provided as a query parameter. The connection will be rejected if the token is invalid or missing.

**Message Format:**

**IMPORTANT:** All messages from server to client are sent as **batched arrays** for performance optimization. Each WebSocket frame contains a JSON array of event strings:

```json
[
  "{\"type\":\"message\",\"message_id\":\"...\",\"sender_device_id\":\"...\"}",
  "{\"type\":\"reaction\",\"reaction_id\":\"...\",\"message_id\":\"...\"}"
]
```

**Batching Behavior:**
- Messages are batched with 10ms interval timer for low latency
- Maximum batch size of 50 messages to prevent unbounded growth
- Single messages still arrive in array format: `["..."]`
- Reduces WebSocket frame overhead by 5-20x for burst traffic
- Critical for group messaging performance

**Connection Lifecycle:**

1. Client connects with valid token
2. Server sends presence event indicating device is online (in batch array)
3. Client receives real-time events for messages, reactions, edits, and typing (batched)
4. Client can send typing indicator events (individual JSON objects, not batched)
5. On disconnect, server sends presence event indicating device is offline

**Events from Server to Client:**

All events are delivered in batched array format. Parse the array first, then parse each event string.

#### Message Event
Sent when a new message is received.

```json
{
  "type": "message",
  "message_id": "uuid",
  "sender_device_id": "uuid",
  "recipient_device_id": "uuid",
  "encrypted_content": [1, 2, 3, ...],
  "timestamp": 1234567890
}
```

#### Message Edited Event
Sent when a message is edited.

```json
{
  "type": "message_edited",
  "message_id": "uuid",
  "encrypted_content": [4, 5, 6, ...],
  "edited_at": 1234567890
}
```

#### Reaction Event
Sent when a reaction is added to a message.

```json
{
  "type": "reaction",
  "reaction_id": "uuid",
  "message_id": "uuid",
  "user_id": "uuid",
  "emoji": "👍",
  "timestamp": 1234567890
}
```

#### Typing Event
Sent when a user starts or stops typing.

```json
{
  "type": "typing",
  "user_id": "uuid",
  "is_typing": true
}
```

#### Presence Event
Sent when a device connects or disconnects.

```json
{
  "type": "presence",
  "device_id": "uuid",
  "is_online": true
}
```

#### Sync Request Event
Sent when another device requests history sync.

```json
{
  "type": "sync_request",
  "sync_request_id": "uuid",
  "requesting_device_id": "uuid"
}
```

#### Sync Complete Event
Sent when history sync bundle is ready for retrieval.

```json
{
  "type": "sync_complete",
  "sync_request_id": "uuid",
  "bundle_id": "uuid"
}
```

#### Error Event
Sent when an error occurs processing a client message.

```json
{
  "type": "error",
  "message": "error description"
}
```

**Events from Client to Server:**

Client messages are sent as individual JSON objects (not batched).

#### Typing Event
Send to indicate typing status.

```json
{
  "type": "typing",
  "user_id": "uuid",
  "is_typing": true
}
```

**Connection Management:**

- Multiple WebSocket connections per device are supported
- Messages are delivered to all active connections for a device
- Connections automatically clean up on disconnect
- Reconnection is handled by establishing a new WebSocket connection

**Error Handling:**

- 401 Unauthorized: Invalid or missing token (connection rejected)
- Connection closes on authentication failure
- Invalid JSON messages from client are logged but don't close connection
- Unsupported event types from client return error response

**Example Usage:**

```javascript
const token = "your-jwt-token";
const ws = new WebSocket(`ws://localhost:3000/ws?token=${token}`);

ws.onopen = () => {
  console.log("Connected");
};

ws.onmessage = (event) => {
  // Parse the batched array first
  const batch = JSON.parse(event.data);
  
  // Process each event in the batch
  batch.forEach(eventStr => {
    const data = JSON.parse(eventStr);
    
    switch (data.type) {
      case "message":
        console.log("New message:", data);
        break;
      case "reaction":
      console.log("New reaction:", data);
      break;
    case "typing":
      console.log("Typing indicator:", data);
      break;
    case "presence":
      console.log("Presence update:", data);
      break;
  }
};

ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};

ws.onclose = () => {
  console.log("Disconnected");
};

function sendTypingIndicator(userId, isTyping) {
  ws.send(JSON.stringify({
    type: "typing",
    user_id: userId,
    is_typing: isTyping
  }));
}
```

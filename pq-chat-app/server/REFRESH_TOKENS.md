# Refresh Token Implementation

## Overview

The authentication system now uses separate access and refresh tokens for enhanced security.

## Token Types

### Access Token
- Short-lived (15 minutes)
- Used for API authentication
- Included in Authorization header: `Bearer <access_token>`
- Contains user_id, device_id, and token_type

### Refresh Token
- Long-lived (30 days)
- Used to obtain new access tokens
- Stored in database with hash
- Can be revoked

## API Endpoints

### POST /auth/login
Login and receive both tokens.

Request:
```json
{
  "username": "user",
  "password": "password",
  "public_key": [...]
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user_id": "uuid",
  "device_id": "uuid"
}
```

### POST /auth/refresh
Exchange refresh token for new tokens.

Request:
```json
{
  "refresh_token": "eyJ..."
}
```

Response:
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "user_id": "uuid",
  "device_id": "uuid"
}
```

### POST /auth/logout
Revoke refresh token.

Request:
```json
{
  "refresh_token": "eyJ..."
}
```

Response: 204 No Content

## Security Features

- Refresh tokens are hashed before storage
- Tokens can be revoked individually or per device
- Expired tokens are automatically cleaned up
- Token rotation on refresh (old token revoked)
- Access tokens validated for type in middleware

## Database Schema

```sql
CREATE TABLE refresh_tokens (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  device_id TEXT NOT NULL,
  token_hash TEXT NOT NULL,
  expires_at INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  revoked_at INTEGER,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (device_id) REFERENCES devices(id) ON DELETE CASCADE
);
```

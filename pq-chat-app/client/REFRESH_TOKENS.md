# Client-Side Refresh Token Implementation

## Overview

The client now implements automatic token refresh with seamless user experience.

## Architecture

### TokenManager
Manages access and refresh tokens with automatic refresh scheduling.

**Features:**
- Automatic token refresh before expiration
- Concurrent refresh request deduplication
- Token expiry tracking
- Scheduled refresh (1 minute before expiry)

**Key Methods:**
- `setTokens(accessToken, refreshToken)` - Initialize tokens
- `getAccessToken()` - Get current access token
- `ensureValidToken()` - Get valid token, refresh if needed
- `refresh()` - Manually refresh tokens
- `clear()` - Clear all tokens and timers

### API Module
Enhanced with automatic retry on 401 errors.

**Features:**
- Automatic token refresh on authentication failure
- Single retry per request to prevent loops
- Token manager integration
- Transparent to calling code

### Storage
Updated to store both access and refresh tokens.

**Schema:**
```javascript
{
  accessToken: "eyJ...",
  refreshToken: "eyJ...",
  userId: "uuid",
  deviceId: "uuid"
}
```

### WebSocket Manager
Updated to use fresh tokens on connection.

**Features:**
- Token refresh before WebSocket authentication
- Token manager integration
- Automatic reconnection with fresh tokens

## Usage

### Login
```javascript
const session = await auth.login(database, username, password);
// session.accessToken - short-lived access token
// session.refreshToken - long-lived refresh token
// session.tokenManager - manages automatic refresh
```

### Restore Session
```javascript
const session = await auth.restoreSession(database);
// Automatically refreshes token if needed
// Returns null if refresh fails
```

### Logout
```javascript
await auth.logout(database, session.refreshToken);
// Revokes refresh token on server
// Clears local session
```

### API Calls
```javascript
// Automatic token refresh on 401
const users = await api.searchUsers(session.accessToken, query);
// If token expired, automatically refreshes and retries
```

## Token Lifecycle

1. **Login**: Receive access (15 min) and refresh (30 days) tokens
2. **Storage**: Both tokens stored in IndexedDB
3. **Usage**: Access token used for API calls
4. **Refresh**: Automatic refresh 1 minute before expiry
5. **Retry**: On 401 error, refresh and retry once
6. **Logout**: Revoke refresh token on server

## Security Features

- Access tokens are short-lived (15 minutes)
- Refresh tokens stored securely in IndexedDB
- Automatic cleanup on logout
- Token rotation on refresh
- Single retry prevents infinite loops
- WebSocket uses fresh tokens

## Error Handling

### Token Refresh Failure
- Clears local session
- User redirected to login
- WebSocket disconnected

### API 401 Error
- Attempts token refresh once
- Retries request with new token
- Fails if refresh unsuccessful

### Session Restoration Failure
- Returns null session
- User must login again
- Clears invalid session data

## Configuration

Token expiry times in `token-manager.js`:
```javascript
const TOKEN_REFRESH_THRESHOLD = 60 * 1000;  // 1 minute
const TOKEN_EXPIRY_TIME = 15 * 60 * 1000;   // 15 minutes
```

## Testing

Build the client:
```bash
cd client
npm run build
```

Test token refresh:
1. Login to application
2. Wait 14 minutes
3. Make API call
4. Token automatically refreshes
5. Request succeeds

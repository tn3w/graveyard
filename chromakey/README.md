<h1 align="center">Chromakey</h1>

<h3 align="center">Secure, visual authentication for live presentations and streaming applications</h3>

<p align="center">
  Build presentation tools and streaming platforms with authentication that doesn't interrupt the flow
</p>

<p align="center">
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg?style=for-the-badge" alt="License: Apache 2.0">
  </a>
  <a href="https://www.python.org/downloads/">
    <img src="https://img.shields.io/badge/python-3.8+-blue.svg?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.8+">
  </a>
  <a href="https://flask.palletsprojects.com/">
    <img src="https://img.shields.io/badge/flask-2.0+-green.svg?style=for-the-badge&logo=flask&logoColor=white" alt="Flask">
  </a>
</p>

<p align="center">
  <a href="https://github.com/tn3w/chromakey">
    <img src="https://img.shields.io/github/stars/tn3w/chromakey?style=for-the-badge&logo=github&logoColor=white" alt="Stars">
  </a>
  <a href="https://github.com/tn3w/chromakey/actions">
    <img src="https://img.shields.io/github/actions/workflow/status/tn3w/chromakey/publish.yml?style=for-the-badge&logo=github&logoColor=white&label=CI" alt="CI">
  </a>
  <a href="https://pypi.org/project/flask-chromakey">
    <img src="https://img.shields.io/pypi/v/flask-chromakey?style=for-the-badge&logo=pypi&logoColor=white" alt="PyPI">
  </a>
  <a href="https://pepy.tech/project/flask-chromakey">
    <img src="https://img.shields.io/pepy/dt/flask-chromakey?style=for-the-badge&logo=python&logoColor=white" alt="Downloads">
  </a>
</p>

<p align="center">
  <a href="#-overview">📖 Overview</a> •
  <a href="#-quick-start">🚀 Quick Start</a> •
  <a href="#-features">✨ Features</a> •
  <a href="#-examples">💡 Examples</a> •
  <a href="#-configuration">⚙️ Configuration</a> •
  <a href="#-security">🔒 Security</a>
</p>

---

## 📖 Overview

**Chromakey** is a Flask-based authentication library designed specifically for developers building presentation tools, live streaming platforms, and interactive web applications where traditional login flows would disrupt the user experience.

Traditional authentication systems interrupt presentations with login forms, password fields, and multi-step verification flows. Chromakey solves this by providing authentication that's invisible until needed.

```python
from flask import Flask
from chromakey import Chromakey

app = Flask(__name__)
chromakey = Chromakey(app, require_auth=True)

@app.route('/')
def presentation():
    return '<h1>My Presentation</h1>'

# Access via: /chromakey/YOUR_TOKEN
# Or use visual challenge at: /chromakey/login
```

### Why Chromakey?

<table>
<tr>
<td width="50%" valign="top">

**🎯 Built for Presentations**

- Visual challenge-response authentication
- Token-based one-click access
- No disruptive login forms
- Seamless presenter experience

</td>
<td width="50%" valign="top">

**🛡️ Security First**

- JWT-based sessions
- Rate limiting built-in
- CSRF protection
- Constant-time verification

</td>
</tr>
<tr>
<td width="50%" valign="top">

**⚡ Zero Configuration**

- Automatic overlay injection
- No template modifications needed
- Environment-based setup
- Works with existing Flask apps

</td>
<td width="50%" valign="top">

**🎨 Perfect For**

- Presentation software
- Webinar platforms
- Live coding environments
- Screen sharing tools

</td>
</tr>
</table>

## 🚀 Quick Start

### Prerequisites

```bash
Python 3.8+  |  Flask 2.0+  |  PyJWT
```

### Installation

```bash
pip install flask-chromakey
```

### Setup in 3 Steps

**1. Generate your credentials**

```bash
# Generate secret key
python -c 'import secrets; print(secrets.token_hex(32))'

# Generate authentication password
python -c 'import secrets, hashlib; pwd = secrets.token_urlsafe(16); print(f"Password: {pwd}\nHash: {hashlib.sha256(pwd.encode()).hexdigest()}")'
```

**2. Set environment variables**

```bash
export CHROMAKEY_SECRET_KEY="your-secret-key-here"
export CHROMAKEY_AUTH_PASSWORD="your-sha256-hash-here"
```

**3. Initialize in your Flask app**

```python
from flask import Flask
from chromakey import Chromakey

app = Flask(__name__)
chromakey = Chromakey(app, require_auth=True, inject_overlay=True)

@app.route('/')
def index():
    return '<h1>My Presentation</h1>'

if __name__ == '__main__':
    app.run()
```

**Access your application:**
- Token auth: `http://localhost:5000/chromakey/YOUR_PASSWORD`
- Visual challenge: `http://localhost:5000/chromakey/login`

That's it! Your app is now protected with Chromakey authentication.

## ✨ Features

<table>
<tr>
<td width="50%" valign="top">

### 🔐 Authentication Methods

Multiple ways to authenticate without disrupting your flow:

- **Token Authentication** — One-time URL access
- **Visual Challenge** — Interactive shape/color matching
- **JWT Sessions** — Secure, stateless management
- **Session Revocation** — Instant logout capability

</td>
<td width="50%" valign="top">

### 🛡️ Security Features

Enterprise-grade security built-in:

- **Rate Limiting** — Per-IP and global throttling
- **CSRF Protection** — Token-based state protection
- **Secure Cookies** — HTTPOnly, Secure, SameSite
- **Challenge Expiry** — Time-limited authentication
- **Constant-Time Comparison** — Timing-attack resistant

</td>
</tr>
<tr>
<td width="50%" valign="top">

### 🎨 Integration Features

Seamless integration with your Flask app:

- **Overlay Injection** — Auto-inject UI without template changes
- **Decorator Support** — Protect routes with `@chromakey()`
- **Global Protection** — Enable auth for entire app
- **Flexible Config** — Environment or programmatic setup

</td>
<td width="50%" valign="top">

### ⚡ Developer Experience

Built for productivity:

- **Zero Template Changes** — Works with existing HTML
- **Auto-Detection** — Smart cookie security settings
- **Blueprint-Based** — Clean separation of concerns
- **Comprehensive Logging** — Debug and monitor easily

</td>
</tr>
</table>

## 💡 Examples

### Protect Specific Routes

```python
from chromakey import chromakey

@app.route('/admin')
@chromakey()
def admin_panel():
    return 'Admin Dashboard'

@app.route('/public')
def public_page():
    return 'Public Content'
```

### Custom Configuration

```python
chromakey = Chromakey(
    app,
    require_auth=True,           # Protect all routes
    inject_overlay=True,          # Add interactive overlay
    token_expiry=7200,            # 2-hour sessions
    max_attempts=3,               # Stricter rate limiting
    lockout_duration=600,         # 10-minute lockout
    cookie_secure=True,           # Force HTTPS cookies
    token_redirect_home=True      # Redirect after token auth
)
```

### Blueprint Registration

```python
from flask import Flask
from chromakey import Chromakey

app = Flask(__name__)

# Initialize later
chromakey = Chromakey()
chromakey.init_app(app, require_auth=True)
```

### Environment-Based Configuration

```bash
# Set in your environment or .env file
CHROMAKEY_SECRET_KEY=your-secret-key
CHROMAKEY_AUTH_PASSWORD=your-password-hash
CHROMAKEY_REQUIRE_AUTH=true
CHROMAKEY_INJECT_OVERLAY=true
CHROMAKEY_TOKEN_EXPIRY=3600
CHROMAKEY_TOKEN_REDIRECT_HOME=false
```

```python
# Flask will automatically use these
chromakey = Chromakey(app)
```

## ⚙️ Configuration

### Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `secret_key` | str | **Required** | JWT signing key (or set `CHROMAKEY_SECRET_KEY`) |
| `require_auth` | bool | `False` | Protect all routes globally |
| `inject_overlay` | bool | `True` | Add interactive overlay to HTML responses |
| `token_expiry` | int | `3600` | Session duration in seconds (1 hour) |
| `cookie_secure` | bool | Auto | Force HTTPS cookies (auto-detects in production) |
| `max_attempts` | int | `5` | Maximum auth attempts per minute |
| `lockout_duration` | int | `300` | Lockout period after max attempts (5 minutes) |
| `challenge_expiry` | int | `30` | Visual challenge validity period (30 seconds) |
| `token_redirect_home` | bool | `False` | Redirect to home after token authentication |

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chromakey/login` | GET | Visual challenge login page |
| `/chromakey/challenge` | GET | Fetch current challenge (authenticated) |
| `/chromakey/verify` | POST | Submit challenge solution |
| `/chromakey/challenge/<code>` | GET | URL-based challenge authentication |
| `/chromakey/<token>` | GET | Token-based authentication |
| `/chromakey/logout` | POST | Session termination |

## 🏗️ Architecture

### How It Works

```
┌─────────────────────────────────────────────────────────────┐
│                    Unauthenticated Request                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
         ┌────────────────────────┐
         │  Redirect to Login     │
         │  /chromakey/login      │
         └────────┬───────────────┘
                  │
                  ▼
    ┌─────────────────────────────┐
    │   Visual Challenge or       │
    │   Token URL                 │
    └─────────┬───────────────────┘
              │
              ▼
┌─────────────────────────────────┐
│  Verification                   │
│  - Constant-time comparison     │
│  - Rate limit check             │
│  - CSRF validation              │
└─────────┬───────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│  JWT Token Issued               │
│  - Session ID                   │
│  - Expiration time              │
│  - Secure cookie                │
└─────────┬───────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│  Overlay Injection              │
│  - Interactive controls         │
│  - No template changes          │
└─────────────────────────────────┘
```

### Module Structure

| Component | Responsibility |
|-----------|----------------|
| `Chromakey` | Main class for Flask integration and initialization |
| `chromakey()` | Decorator for protecting individual routes |
| `create_chromakey_blueprint()` | Blueprint factory with authentication endpoints |
| `generate_challenge()` | Visual challenge generation system |
| `verify_challenge()` | Constant-time challenge verification |
| `inject_overlay_html()` | Response processor for overlay injection |
| `check_authentication()` | JWT token validation and session checking |

## 🔒 Security

### Production Deployment Checklist

- ✅ Always use HTTPS in production
- ✅ Set `cookie_secure=True` explicitly
- ✅ Use strong, randomly generated secret keys (32+ bytes)
- ✅ Store `CHROMAKEY_AUTH_PASSWORD` as SHA256 hash only
- ✅ Never commit secrets to version control
- ✅ Rotate tokens periodically
- ✅ Monitor failed authentication attempts

### Multi-Layer Rate Limiting

Chromakey implements comprehensive rate limiting:

```
┌─────────────────────────────────────┐
│  Per-IP Limits                      │
│  Default: 5 attempts/minute         │
│  Automatic lockout after failures   │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Global Limits                      │
│  50 requests/minute across all IPs  │
│  Prevents distributed attacks       │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│  Challenge Expiry                   │
│  Time-limited to prevent replay     │
│  Automatic cleanup of old attempts  │
└─────────────────────────────────────┘
```

### Token Security Features

<table>
<tr>
<td width="50%" valign="top">

**JWT Protection**
- Expiration timestamps
- Session IDs for revocation
- HS256 algorithm
- Signature verification

</td>
<td width="50%" valign="top">

**Cookie Security**
- HTTPOnly (prevents XSS)
- Secure flag (HTTPS only)
- SameSite=Strict (prevents CSRF)
- Automatic expiration

</td>
</tr>
<tr>
<td width="50%" valign="top">

**Verification**
- Constant-time comparison
- Prevents timing attacks
- Secure random generation
- Challenge validation

</td>
<td width="50%" valign="top">

**Session Management**
- Server-side revocation
- Logout functionality
- Token invalidation
- Memory-efficient tracking

</td>
</tr>
</table>

## ⚡ Performance

<table>
<tr>
<td width="33%" align="center">

**< 1ms**

JWT validation overhead per request

</td>
<td width="33%" align="center">

**Zero DB**

No database required, stateless auth

</td>
<td width="33%" align="center">

**Single-Pass**

Efficient HTML overlay injection

</td>
</tr>
</table>

- **Minimal Overhead**: JWT validation adds less than 1ms per request
- **No Database Required**: Stateless authentication with in-memory session tracking
- **Efficient Overlay Injection**: Single-pass HTML modification
- **Rate Limit Cleanup**: Automatic expiry of old attempt records
- **Memory Efficient**: Bounded memory usage with automatic cleanup

## 🧪 Testing

```bash
# Run with debug mode to see detailed logs
export FLASK_DEBUG=1
python app.py

# Test authentication flow
curl -c cookies.txt http://localhost:5000/chromakey/YOUR_TOKEN
curl -b cookies.txt http://localhost:5000/

# Test rate limiting
for i in {1..10}; do 
  curl -X POST http://localhost:5000/chromakey/verify
done
```

### Template Requirements

Chromakey expects two templates in your `templates/` directory:

```
templates/
├── login.html      # Login page with challenge interface
└── overlay.html    # Interactive overlay controls
```

See the included templates for reference implementations.

## 📊 Comparison with Alternatives

### Chromakey vs Flask-Login

| Feature | Chromakey | Flask-Login |
|---------|:---------:|:-----------:|
| **Target Use Case** | Presentations, streaming | General web apps |
| **Login Flow** | Visual challenge, token URL | Username/password forms |
| **Session Management** | JWT-based | Server-side sessions |
| **Overlay Injection** | ✅ Built-in | ❌ Manual integration |
| **Rate Limiting** | ✅ Built-in | ❌ Requires extension |
| **Database Required** | ❌ No | ✅ Typically yes |
| **CSRF Protection** | ✅ Built-in | ❌ Separate extension |
| **Presentation-Friendly** | ✅ Yes | ❌ No |

### Chromakey vs Flask-HTTPAuth

| Feature | Chromakey | Flask-HTTPAuth |
|---------|:---------:|:--------------:|
| **Authentication Type** | Visual + Token | HTTP Basic/Digest |
| **User Experience** | Seamless overlay | Browser popup |
| **Session Persistence** | Cookie-based | Per-request |
| **CSRF Protection** | ✅ Built-in | ⚠️ Not applicable |
| **Presentation-Friendly** | ✅ Yes | ❌ No |
| **Rate Limiting** | ✅ Built-in | ❌ Manual |

<p align="center">
  <strong>Chromakey is purpose-built for scenarios where traditional authentication would disrupt the user experience.</strong>
</p>

## 🤝 Contributing

Contributions are welcome! We appreciate your help in making Chromakey better.

### How to Contribute

1. **Fork** the repository
2. **Create** your feature branch
   ```bash
   git checkout -b feature/amazing-feature
   ```
3. **Write** tests for new functionality
4. **Ensure** all tests pass
5. **Commit** your changes
   ```bash
   git commit -m 'Add amazing feature'
   ```
6. **Push** to the branch
   ```bash
   git push origin feature/amazing-feature
   ```
7. **Open** a Pull Request

### Development Setup

```bash
git clone https://github.com/tn3w/chromakey.git
cd chromakey
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### Areas for Contribution

- Additional authentication methods
- Enhanced visual challenges
- Performance optimizations
- Documentation improvements
- Example applications
- Test coverage expansion

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

```
Copyright 2026 TN3W

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

## 🔗 Resources

<p align="center">
  <a href="https://github.com/tn3w/chromakey">📦 GitHub</a> •
  <a href="https://github.com/tn3w/chromakey">📚 Documentation</a> •
  <a href="https://github.com/tn3w/chromakey/issues">🐛 Issues</a> •
  <a href="https://github.com/tn3w/chromakey/discussions">💬 Discussions</a> •
  <a href="https://pypi.org/project/flask-chromakey">🐍 PyPI</a>
</p>

---

<p align="center">
  <sub>Built with Flask and PyJWT</sub>
</p>

<p align="center">
  <sub>Made for developers who present, stream, and teach online</sub>
</p>

<p align="center">
  <a href="#chromakey">⬆️ Back to top</a>
</p>

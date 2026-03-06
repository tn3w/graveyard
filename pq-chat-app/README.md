# Post-Quantum Encrypted Chat

End-to-end encrypted chat application with post-quantum cryptography.

## Architecture

- **Server**: Rust backend with SQLite database
- **Client**: Web application with WebAssembly cryptography module
- **Security**: Post-quantum Signal Protocol, client-side encryption

## Development Setup

### Prerequisites

- Rust 1.75 or later
- Node.js 20 or later
- wasm-pack

### Server

```bash
cd server
cargo run
```

Server runs on http://localhost:3000

### Client

```bash
cd client
npm install
npm run wasm:build
npm run dev
```

Client runs on http://localhost:5173

## Project Structure

```
├── server/              # Rust backend
│   ├── src/            # Server source code
│   └── migrations/     # Database migrations
├── client-wasm/        # WebAssembly crypto module
│   └── src/           # WASM source code
└── client/            # Web client
    └── src/          # Client source code
```

## Testing

```bash
# Server tests
cd server
cargo test

# Client tests
cd client
npm test
```

# JSVM — Bytecode VM Signal Collection

A browser bot-detection challenge that compiles JavaScript signal-collection code into QuickJS bytecode, executes it inside a WASM-sandboxed VM, and scores the results server-side.

## How It Works

1. **Server** compiles a signal-collection payload into QuickJS bytecode and encrypts it with AES-256-CTR
2. **Client** fetches the encrypted bytecode bundle + WASM module, decrypts the bytecode in-browser, and runs it inside the QuickJS VM compiled to WebAssembly
3. **Payload** collects browser environment signals (navigator, screen, WebGL, automation markers, etc.) and returns them as JSON
4. **Server** scores the signals against known bot/automation patterns and issues a clearance token if the score passes

## Prerequisites

- Node.js >= 20
- Make
- A C compiler (for building the native `qjsc` bytecode compiler)

## Setup

### 1. Clone the repository

```sh
git clone <repo-url>
cd vigilus/jsvm
```

### 2. Install the Emscripten SDK

The WASM build requires Emscripten. Clone it into the parent directory:

```sh
cd ..
git clone https://github.com/emscripten-core/emsdk.git
cd emsdk
./emsdk install 5.0.3
./emsdk activate 5.0.3
cd ../jsvm
```

The Makefile expects emsdk at `../emsdk/` by default. Override with `EMSDK_DIR`:

```sh
make EMSDK_DIR=/path/to/emsdk
```

### 3. Get QuickJS

Clone QuickJS into the `quickjs/` directory:

```sh
git clone https://github.com/niclas-aspect/quickjs.git quickjs
```

Or use the upstream Bellard repo:

```sh
git clone https://github.com/niclas-aspect/quickjs.git quickjs
cd quickjs
git checkout 2025-09-13
cd ..
```

### 4. Install Node dependencies

```sh
npm install
```

## Building

### Build the WASM module

```sh
npm run build
```

This runs `make`, which sources `emsdk_env.sh` automatically and compiles QuickJS + the VM bridge into `public/vm.wasm` and `public/vm.js`.

### Clean build artifacts

```sh
make clean
```

## Running

```sh
npm start
```

Starts the server on port 3002 (override with `PORT`).

Open `http://localhost:3002` to run the challenge from the browser.

## Environment Variables

| Variable                 | Default   | Description                           |
| ------------------------ | --------- | ------------------------------------- |
| `PORT`                   | `3002`    | Server listen port                    |
| `CHALLENGE_TTL`          | `30000`   | Challenge expiry in ms                |
| `CLEARANCE_TTL`          | `3600000` | Clearance token expiry in ms          |
| `WASM_ROTATION_INTERVAL` | `60`      | Bytecode rotation interval in seconds |
| `SCORE_THRESHOLD`        | `0.3`     | Minimum score to pass (0–1)           |
| `VM_SECRET`              | random    | HMAC secret for clearance tokens      |

## API

| Method | Path                 | Description                                          |
| ------ | -------------------- | ---------------------------------------------------- |
| `POST` | `/vm/init`           | Create a challenge, returns bundle URL + key         |
| `GET`  | `/vm/bundle/:id.bin` | Download encrypted bytecode bundle                   |
| `POST` | `/vm/verify`         | Submit signals for scoring, returns clearance token  |
| `GET`  | `/vm/protected`      | Example protected endpoint (requires `Bearer` token) |

## Compile Script

Compile standalone JS files into encrypted QuickJS bytecode bundles:

```sh
node scripts/compile.js input.js --out output.vmbc --key <hex>
```

## Project Structure

```
jsvm/
├── Makefile              # WASM build (emcc)
├── package.json
├── server.js             # Express server + scoring
├── public/
│   ├── index.html        # Demo page
│   ├── loader.js         # Client-side WASM loader + decryption
│   ├── vm.js             # Emscripten JS glue (generated)
│   └── vm.wasm           # QuickJS WASM binary (generated)
├── quickjs/              # QuickJS engine source (cloned)
├── scripts/
│   ├── compile.js        # Standalone bytecode compiler
│   └── signals_payload.js# Signal collection payload
└── src/
    └── vm_bridge.c       # C bridge between QuickJS and browser APIs
```

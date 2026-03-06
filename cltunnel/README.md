# cltunnel

`cltunnel.py` is a minimal Python client that establishes an **Argo Tunnel**‑style connection
through Cloudflare’s edge network to expose a local service running on `localhost` to the
internet. It mimics the handshake used by `cloudflared` by speaking the QUIC‑based protocol
used by the official API (`api.trycloudflare.com`).

This project was kept as a reference / experiment and is not intended for production use.

## Features

- Requests a temporary tunnel credential from Cloudflare’s public API
- Connects to a Cloudflare edge server over QUIC using `aioquic`
- Forwards inbound HTTP/1.1 requests to a local port
- Handles basic protocol framing, metadata parsing, and registration
- Gracefully shuts down on SIGINT/SIGTERM

## Requirements

- Python 3.8+
- `aioquic` (QUIC/HTTP3 client library)
- `pycapnp` (Cap’n Proto bindings)
- `capnp` compiler to generate Python schemas (used at runtime)

Install dependencies with pip:

```bash
python3 -m pip install aioquic pycapnp
```

## Usage

```bash
# expose local service listening on port 8080
python3 cltunnel.py 8080
```

The script will validate that something is listening on the given port, request
a tunnel from `api.trycloudflare.com`, and then print a banner containing the
public hostname. Incoming requests will be forwarded to the local service until
the process is interrupted.

The only command‑line argument is the local port number (1‑65535). Example:

```
$ python3 cltunnel.py 5000
Validating local service...
Requesting tunnel from api.trycloudflare.com...

+-----------------------------+
| https://ab12cd34ef56.foo.cf  |
+-----------------------------+
Tunnel is ready! Serving requests...
```

Press `Ctrl+C` to stop the tunnel.

## Limitations

- Simplified protocol support (only basic HTTP forwarding)
- No retry logic or reconnection
- Ignores TLS verification (`verify_mode=False`)
- Uses hard‑coded edge server and API endpoint

## License

Public domain (use at your own risk).

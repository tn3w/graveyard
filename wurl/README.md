# wurl

The simplest HTTP/HTTPS client. A clean, minimal reimplementation of curl in Rust.

## Features

- HTTP and HTTPS (TLS 1.2/1.3 via rustls, pure Rust)
- Automatic redirect following (up to 10 hops)
- Chunked transfer encoding
- Content-Length and connection-close body reading
- curl-compatible CLI options
- Zero C dependencies

## Usage

```sh
wurl https://ubuntu.com/robots.txt
wurl -d '{"key":"val"}' -H "Content-Type: application/json" https://api.example.com
wurl -I https://example.com
wurl -o page.html https://example.com
wurl -u user:pass https://example.com/api
wurl -v https://example.com
```

## Options

```
 -d, --data <data>          HTTP POST data
 -f, --fail                 Fail with no output on HTTP errors
 -I, --head                 Show document info only
 -H, --header <header>      Pass custom header to server
 -h, --help                 Show help
 -o, --output <file>        Write to file instead of stdout
 -O, --remote-name          Write output to remote filename
 -i, --show-headers         Show response headers in output
 -s, --silent               Silent mode
 -T, --upload-file <file>   Transfer local file to destination
 -u, --user <user:password> Server user and password (Basic auth)
 -A, --user-agent <name>    Send User-Agent to server
 -v, --verbose              Make the operation more talkative
 -V, --version              Show version number and quit
 -X, --request <method>     Specify request method (GET/POST/PUT/HEAD)
```

## Library

```rust
let url = wurl::Url::parse("https://example.com/api")?;
let mut request = wurl::Request::new(url);
request.method = wurl::Method::Post;
request.body = Some(b"hello".to_vec());
let response = wurl::send(&request)?;
println!("{}", response.body_string());
```

## Build

```sh
cargo build --release
```

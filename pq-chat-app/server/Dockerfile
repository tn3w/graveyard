FROM rust:latest as builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY Cargo.toml Cargo.lock ./
COPY server ./server
COPY client-wasm ./client-wasm

RUN cargo build --release --bin chat-server

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/target/release/chat-server /app/chat-server
COPY --from=builder /app/server/migrations /app/migrations

ENV RUST_LOG=info
ENV DATABASE_URL=/data/chat.db
ENV JWT_SECRET=""

EXPOSE 3000

VOLUME ["/data"]

CMD ["/app/chat-server"]

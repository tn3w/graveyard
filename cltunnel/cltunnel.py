#!/usr/bin/env python3
import sys
import json
import socket
import asyncio
import signal
from urllib.request import Request, urlopen
from urllib.error import URLError
from uuid import UUID
from aioquic.asyncio import connect
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import StreamDataReceived
import capnp


API_ENDPOINT = "https://api.trycloudflare.com/tunnel"
EDGE_SERVER = "region1.v2.argotunnel.com"
EDGE_PORT = 7844
TIMEOUT = 15

DATA_STREAM_SIGNATURE = bytes([0x0A, 0x36, 0xCD, 0x12, 0xA1, 0x3E])
RPC_STREAM_SIGNATURE = bytes([0x52, 0xBB, 0x82, 0x5C, 0xDB, 0x65])
PROTOCOL_VERSION = b"01"


capnp.remove_import_hook()
tunnelrpc = capnp.load("cloudflared/tunnelrpc/proto/tunnelrpc.capnp")
quic_metadata = capnp.load("cloudflared/tunnelrpc/proto/quic_metadata_protocol.capnp")


class Credentials:
    def __init__(self, tunnel_id, account_tag, secret):
        self.tunnel_id = UUID(tunnel_id)
        self.account_tag = account_tag
        if isinstance(secret, list):
            self.secret = bytes(secret)
        else:
            self.secret = secret


class TunnelProtocol:
    def __init__(self, quic, local_port, credentials):
        self.quic = quic
        self.local_port = local_port
        self.credentials = credentials
        self.running = False
        self.control_stream_id = None
        self.control_sock_quic = None
        self.control_sock_rpc = None
        self.data_streams = {}
        self.registered = False

    async def register_connection(self):
        self.control_stream_id = self.quic._quic.get_next_available_stream_id()
        
        self.control_sock_quic, self.control_sock_rpc = socket.socketpair()
        self.control_sock_quic.setblocking(False)
        self.control_sock_rpc.setblocking(False)
        
        self.quic._quic.send_stream_data(self.control_stream_id, RPC_STREAM_SIGNATURE, end_stream=False)
        self.quic.transmit()
        
        print("Starting RPC registration...")
        
        async with capnp.kj_loop():
            stream = await capnp.AsyncIoStream.create_connection(sock=self.control_sock_rpc)
            client = capnp.TwoPartyClient(stream)
            
            registration_server = client.bootstrap().cast_as(tunnelrpc.RegistrationServer)
            
            request = registration_server.registerConnection_request()
            
            auth = request.auth
            auth.accountTag = self.credentials.account_tag
            auth.tunnelSecret = self.credentials.secret
            
            request.tunnelId = self.credentials.tunnel_id.bytes
            request.connIndex = 0
            
            options = request.options
            client_info = options.client
            client_info.clientId = b"cltunnel.py"
            client_info.features = []
            client_info.version = "1.0"
            client_info.arch = "amd64"
            
            options.originLocalIp = bytes([127, 0, 0, 1])
            options.replaceExisting = False
            options.compressionQuality = 0
            options.numPreviousAttempts = 0
            
            print("Sending registration request...")
            
            response_promise = request.send()
            
            for i in range(100):
                await asyncio.sleep(0.1)
                
                while True:
                    event = self.quic._quic.next_event()
                    if event is None:
                        break
                    
                    if isinstance(event, StreamDataReceived):
                        if event.stream_id == self.control_stream_id:
                            print(f"Received {len(event.data)} bytes on control stream")
                            loop = asyncio.get_event_loop()
                            await loop.sock_sendall(self.control_sock_quic, event.data)
                
                loop = asyncio.get_event_loop()
                try:
                    data = await loop.sock_recv(self.control_sock_quic, 4096)
                    if data:
                        print(f"Sending {len(data)} bytes to QUIC")
                        self.quic._quic.send_stream_data(self.control_stream_id, data, end_stream=False)
                        self.quic.transmit()
                except BlockingIOError:
                    pass
            
            print("Waiting for registration response...")
            response = await response_promise
            
            result = response.result
            if result.which() == "error":
                error = result.error
                raise Exception(f"Registration failed: {error.cause}")
            
            details = result.connectionDetails
            location = details.locationName
            self.registered = True
            print(f"Tunnel registered successfully at {location}")

    async def handle_data_stream(self, stream_id, data):
        if stream_id not in self.data_streams:
            self.data_streams[stream_id] = bytearray()
        
        self.data_streams[stream_id].extend(data)
        stream_data = self.data_streams[stream_id]
        
        if len(stream_data) < 8:
            return
        
        if bytes(stream_data[:6]) != DATA_STREAM_SIGNATURE:
            return
        
        if bytes(stream_data[6:8]) != PROTOCOL_VERSION:
            return
        
        try:
            message_bytes = bytes(stream_data[8:])
            
            msg = capnp.load_packed(message_bytes)
            request_root = msg.get_root_as_any()
            request = request_root.as_struct(quic_metadata.ConnectRequest.schema)
            
            http_request = self.build_http_request(request)
            response_data = await self.forward_to_local(http_request)
            
            response_msg = quic_metadata.ConnectResponse.new_message()
            response_msg.error = ""
            response_msg.init("metadata", 0)
            
            response = bytearray()
            response.extend(DATA_STREAM_SIGNATURE)
            response.extend(PROTOCOL_VERSION)
            response.extend(response_msg.to_bytes_packed())
            response.extend(response_data)
            
            self.quic._quic.send_stream_data(stream_id, bytes(response), end_stream=True)
            self.quic.transmit()
            
            del self.data_streams[stream_id]
        except Exception as e:
            print(f"Error handling data stream: {e}")
            import traceback
            traceback.print_exc()

    def build_http_request(self, request):
        method = "GET"
        host = "localhost"
        dest = request.dest
        headers = {}
        
        metadata_list = request.metadata
        for i in range(len(metadata_list)):
            metadata = metadata_list[i]
            key = metadata.key
            val = metadata.val
            
            if key == "HttpMethod":
                method = val
            elif key == "HttpHost":
                host = val
            elif key.startswith("HttpHeader:"):
                header_name = key.split(":", 1)[1]
                headers[header_name] = val
        
        http_req = f"{method} {dest} HTTP/1.1\r\n"
        http_req += f"Host: {host}\r\n"
        
        for name, value in headers.items():
            http_req += f"{name}: {value}\r\n"
        
        http_req += "\r\n"
        return http_req.encode()

    async def forward_to_local(self, http_request):
        try:
            reader, writer = await asyncio.open_connection("127.0.0.1", self.local_port)
            writer.write(http_request)
            await writer.drain()
            
            response = await reader.read(65536)
            
            writer.close()
            await writer.wait_closed()
            
            return response
        except Exception as e:
            print(f"Error forwarding to local: {e}")
            return b"HTTP/1.1 502 Bad Gateway\r\n\r\n"

    def stop(self):
        self.running = False
        if self.control_sock_quic:
            self.control_sock_quic.close()
        if self.control_sock_rpc:
            self.control_sock_rpc.close()


class ClTunnelClient:
    def __init__(self, local_port):
        self.local_port = local_port
        self.credentials = None
        self.hostname = None
        self.protocol = None

    def request_tunnel(self):
        request = Request(
            API_ENDPOINT,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "User-Agent": "cltunnel.py/1.0"
            }
        )
        
        try:
            with urlopen(request, timeout=TIMEOUT) as response:
                data = json.loads(response.read())
                
                if not data.get("success"):
                    errors = data.get("errors", [])
                    raise Exception(f"API error: {errors}")
                
                result = data["result"]
                self.credentials = Credentials(
                    result["id"],
                    result["account_tag"],
                    result["secret"]
                )
                self.hostname = result["hostname"]
                
        except URLError as error:
            raise Exception(f"Failed to request tunnel: {error}")

    def validate_local_service(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", self.local_port))
            sock.close()
            
            if result != 0:
                raise Exception(f"Local service not reachable on port {self.local_port}")
        except Exception as error:
            raise Exception(f"Port validation failed: {error}")

    async def establish_connection(self):
        configuration = QuicConfiguration(
            is_client=True,
            alpn_protocols=["argotunnel"],
            server_name="quic.cftunnel.com",
            verify_mode=False
        )
        
        try:
            async with connect(EDGE_SERVER, EDGE_PORT, configuration=configuration) as quic:
                self.protocol = TunnelProtocol(quic, self.local_port, self.credentials)
                
                await self.protocol.register_connection()
                await self.run_tunnel(quic)
                
        except Exception as error:
            raise Exception(f"Connection failed: {error}")

    async def run_tunnel(self, quic):
        self.protocol.running = True
        
        print("Tunnel is ready! Serving requests...")
        
        while self.protocol.running:
            try:
                await asyncio.sleep(0.01)
                
                while True:
                    event = quic._quic.next_event()
                    if event is None:
                        break
                    
                    if isinstance(event, StreamDataReceived):
                        if event.stream_id != self.protocol.control_stream_id:
                            await self.protocol.handle_data_stream(event.stream_id, event.data)
                
                quic.transmit()
                    
            except Exception as e:
                print(f"Error in tunnel loop: {e}")
                import traceback
                traceback.print_exc()
                break

    def stop(self):
        if self.protocol:
            self.protocol.stop()


def print_banner(hostname):
    url = f"https://{hostname}"
    border = "+" + "-" * (len(url) + 2) + "+"
    
    print()
    print(border)
    print(f"| {url} |")
    print(border)
    print()


def main():
    if len(sys.argv) != 2:
        print("Usage: cltunnel.py <port>")
        sys.exit(1)
    
    try:
        port = int(sys.argv[1])
        if not (1 <= port <= 65535):
            raise ValueError()
    except ValueError:
        print("Error: Port must be between 1 and 65535")
        sys.exit(1)
    
    client = ClTunnelClient(port)
    
    def signal_handler(sig, frame):
        print("\nShutting down...")
        client.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        print("Validating local service...")
        client.validate_local_service()
        
        print("Requesting tunnel from api.trycloudflare.com...")
        client.request_tunnel()
        
        print_banner(client.hostname)
        
        print("Establishing connection to Cloudflare edge...")
        asyncio.run(client.establish_connection())
        
    except Exception as error:
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()

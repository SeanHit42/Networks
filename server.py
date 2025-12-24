import threading
import socket
from typing import Dict, Optional

HOST = "localhost"
PORT = 10000
BUFFER_SIZE = 1024

class ChatServer:
    """A chat server that handles multiple client connections."""
    
    def __init__(self, host: str = HOST, port: int = PORT):
        self.host = host
        self.port = port
        self.server_socket: Optional[socket.socket] = None
        self.clients: Dict[socket.socket, str] = {}  # Maps socket to username
        self.lock = threading.Lock()
        
    def start(self):
        """Start the server and begin accepting connections."""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            print(f"[SERVER] Started on {self.host}:{self.port}")
            print(f"[SERVER] Waiting for clients...")
            
            while True:
                client_socket, client_address = self.server_socket.accept()
                print(f"[NEW CONNECTION] {client_address}")
                
                # Handle each client in a separate thread
                handler = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                handler.start()
                
        except KeyboardInterrupt:
            print("\n[SERVER] Shutting down...")
        except Exception as e:
            print(f"[SERVER ERROR] {e}")
        finally:
            self.shutdown()
    
    def _handle_client(self, client_socket: socket.socket, client_address):
        """Handle a single client connection."""
        username = None
        try:
            # Send welcome message and get username
            welcome_msg = "Welcome! Enter your username"
            client_socket.send(welcome_msg.encode('utf-8'))
            
            username = client_socket.recv(BUFFER_SIZE).decode('utf-8').strip()
            
            with self.lock:
                self.clients[client_socket] = username
            
            print(f"[USER JOINED] {username} from {client_address}")
            self.broadcast(f"{username} joined the chat", exclude=client_socket)
            
            # Listen for messages from this client
            while True:
                data = client_socket.recv(BUFFER_SIZE).decode('utf-8')
                if not data:
                    break
                
                print(f"[{username}] {data}")
                self.broadcast(f"{username}: {data}", exclude=client_socket)
                
        except Exception as e:
            print(f"[ERROR] {username or 'Unknown'}: {e}")
        finally:
            with self.lock:
                if client_socket in self.clients:
                    username = self.clients.pop(client_socket)
                    print(f"[USER LEFT] {username}")
                    self.broadcast(f"{username} left the chat")
            
            try:
                client_socket.close()
            except:
                pass
    
    def broadcast(self, message: str, exclude: Optional[socket.socket] = None):
        """Send a message to all connected clients."""
        with self.lock:
            for client_socket in self.clients:
                if client_socket != exclude:
                    try:
                        client_socket.send(message.encode('utf-8'))
                    except:
                        pass
    
    def shutdown(self):
        """Shutdown the server."""
        with self.lock:
            for client_socket in self.clients:
                try:
                    client_socket.close()
                except:
                    pass
            self.clients.clear()
        
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        print("[SERVER] Shutdown complete.")


if __name__ == "__main__":
    server = ChatServer()
    server.start()
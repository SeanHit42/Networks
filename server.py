import socket
import threading
import time
from typing import Dict, Optional


HOST = "0.0.0.0"   # Listen on all network interfaces
PORT = 10000
BUFFER_SIZE = 1024
BROADCAST_PORT = 9999  # UDP port for server discovery


def get_local_ip():
    """Get the local machine's IP address on the network."""
    try:
        # Connect to an external host (doesn't actually send data)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class ChatServer:
    """
    Multi-client TCP chat server.
    Handles connections, message broadcasting, and graceful shutdown.
    """

    def __init__(self, host: str = HOST, port: int = PORT, backlog: int = 5): 
        self.host = host
        self.port = port
        self.backlog = backlog  # Number of pending connections to queue
        self.server_socket: Optional[socket.socket] = None
        self.clients: Dict[socket.socket, str] = {}  # socket -> username
        self.lock = threading.Lock()
        self.running = True
        self.broadcast_thread: Optional[threading.Thread] = None

    # ---------- START ----------

    def start(self):
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(self.backlog)

            local_ip = get_local_ip()
            print(f"\n{'='*60}")
            print(f"[SERVER] Listening on {self.host}:{self.port}")
            print(f"[SERVER] Server IP for clients: {local_ip}:{self.port}")
            print(f"[SERVER] Waiting for clients...")
            print(f"{'='*60}\n")

            # Start broadcasting server presence
            self.broadcast_thread = threading.Thread(
                target=self._broadcast_presence,
                args=(local_ip,),
                daemon=True
            )
            self.broadcast_thread.start()

            while self.running:
                client_socket, client_address = self.server_socket.accept()
                print(f"[NEW CONNECTION] {client_address}")

                handler = threading.Thread(
                    target=self._handle_client,
                    args=(client_socket, client_address),
                    daemon=True
                )
                handler.start()

        except KeyboardInterrupt:
            print("\n[SERVER] Shutdown requested by user")

        except Exception as e:
            print(f"[SERVER ERROR] {e}")

        finally:
            self.shutdown()

    # ---------- CLIENT HANDLING ----------

    def _broadcast_presence(self, local_ip: str):
        """Broadcast server presence on local network using UDP."""
        try:
            broadcast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            broadcast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            message = f"CHAT_SERVER|{local_ip}|{self.port}".encode("utf-8")
            
            while self.running:
                try:
                    # Broadcast to all devices on the network
                    broadcast_socket.sendto(message, ("<broadcast>", BROADCAST_PORT))
                except:
                    pass
                time.sleep(2)  # Broadcast every 2 seconds
                
            broadcast_socket.close()
        except Exception as e:
            print(f"[BROADCAST ERROR] {e}")

    # ---------- CLIENT HANDLING ----------

    def _handle_client(self, client_socket: socket.socket, client_address):
        username = None
        try:
            # Welcome + username
            client_socket.send(b"Welcome! Please enter your username")
            username = client_socket.recv(BUFFER_SIZE).decode("utf-8").strip()

            if not username:
                return

            with self.lock:
                self.clients[client_socket] = username

            print(f"[USER JOINED] {username} from {client_address}")
            
            # Broadcast updated user list to all clients
            self._broadcast_user_list()
            
            # Notify others
            self.broadcast(f"[SYSTEM] {username} joined the chat", exclude=client_socket)

            # Message loop
            while True:
                data = client_socket.recv(BUFFER_SIZE)
                if not data:
                    break

                message = data.decode("utf-8")
                print(f"[{username}] {message}")
                
                # Check if it's a private message (starts with @)
                if message.startswith("@"):
                    self._handle_private_message(username, message)
                else:
                    self.broadcast(f"{username}: {message}", exclude=client_socket)

        except Exception as e:
            print(f"[ERROR] {username or 'Unknown'}: {e}")

        finally:
            self._disconnect_client(client_socket)

    def _handle_private_message(self, sender: str, message: str):
        """Handle private messages (format: @username message)"""
        parts = message.split(" ", 1)
        if len(parts) < 2:
            return
        
        recipient_name = parts[0][1:]  # Remove @ symbol
        msg_content = parts[1]
        
        with self.lock:
            for client_socket, username in self.clients.items():
                if username == recipient_name:
                    try:
                        private_msg = f"@{sender} (private): {msg_content}"
                        client_socket.send(private_msg.encode("utf-8"))
                        print(f"[PRIVATE] {sender} -> {recipient_name}: {msg_content}")
                    except:
                        pass
                    break
            else:
                # User not found
                print(f"[PRIVATE ERROR] {sender} tried to message {recipient_name} but user not found")

    def _broadcast_user_list(self):
        """Send the current list of online users to all clients"""
        with self.lock:
            usernames = ",".join(self.clients.values())
        
        message = f"USERS|{usernames}"
        with self.lock:
            for client in self.clients.keys():
                try:
                    client.send(message.encode("utf-8"))
                except:
                    pass

    # ---------- BROADCAST ----------

    def broadcast(self, message: str, exclude: Optional[socket.socket] = None):
        with self.lock:
            for client in list(self.clients.keys()):
                if client != exclude:
                    try:
                        client.send(message.encode("utf-8"))
                    except:
                        pass

    # ---------- DISCONNECT ----------

    def _disconnect_client(self, client_socket: socket.socket):
        with self.lock:
            username = self.clients.pop(client_socket, None)

        if username:
            print(f"[USER LEFT] {username}")
            self.broadcast(f"[SYSTEM] {username} left the chat")
            # Broadcast updated user list to remaining clients
            self._broadcast_user_list()

        try:
            client_socket.close()
        except:
            pass

    # ---------- SHUTDOWN ----------

    def shutdown(self):
        self.running = False

        with self.lock:
            for client in self.clients:
                try:
                    client.close()
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

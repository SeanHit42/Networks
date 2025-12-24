import threading
import socket
import sys
from typing import Optional

class ChatClient:
    """A robust chat client with automatic reconnection and message handling."""
    
    HOST = "localhost"
    PORT = 10000
    BUFFER_SIZE = 1024
    
    def __init__(self, username: Optional[str] = None):
        self.username = username
        self.socket: Optional[socket.socket] = None
        self.is_connected = False
        self.listener_thread: Optional[threading.Thread] = None
        
    def connect(self) -> bool:
        """Establish connection to the server."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.HOST, self.PORT))
            
            # Receive welcome message and respond with username
            welcome_msg = self.socket.recv(self.BUFFER_SIZE).decode('utf-8')
            print(f"[SERVER] {welcome_msg}")
            
            if not self.username:
                self.username = input(">>> Enter your username: ").strip()
            
            self.socket.send(self.username.encode('utf-8'))
            self.is_connected = True
            print(f"[CONNECTED] Successfully connected as '{self.username}'")
            return True
            
        except ConnectionRefusedError:
            print("[ERROR] Could not connect to server. Is it running?")
            return False
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False
    
    def _listener_thread_func(self):
        """Listen for incoming messages from the server."""
        try:
            while self.is_connected:
                data = self.socket.recv(self.BUFFER_SIZE).decode('utf-8')
                if not data:
                    print("\n[DISCONNECTED] Server closed the connection.")
                    self.is_connected = False
                    break
                print(f"\n[MESSAGE] {data}")
                print(">>> ", end="", flush=True)
                
        except OSError:
            # Normal shutdown - socket closed
            if self.is_connected:
                print("\n[LISTENER STOPPED] Connection closed.")
            self.is_connected = False
        except Exception as e:
            print(f"\n[ERROR] Listener error: {e}")
            self.is_connected = False
    
    def start_listening(self):
        """Start the background listener thread."""
        if self.listener_thread is None or not self.listener_thread.is_alive():
            self.listener_thread = threading.Thread(target=self._listener_thread_func, daemon=True)
            self.listener_thread.start()
    
    def send_message(self, message: str) -> bool:
        """Send a message to the server."""
        try:
            if not self.is_connected or not self.socket:
                print("[ERROR] Not connected to server.")
                return False
            
            self.socket.send(message.encode('utf-8'))
            return True
        except Exception as e:
            print(f"[ERROR] Failed to send message: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Gracefully disconnect from the server."""
        self.is_connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        print("[DISCONNECTED] Client shut down.")
    
    def run_interactive(self):
        """Run the client in interactive mode."""
        if not self.connect():
            return
        
        self.start_listening()
        print("\nEnter messages in format: USERNAME:MESSAGE")
        print("Type 'exit' to quit.\n")
        
        try:
            while self.is_connected:
                user_input = input(">>> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() == "exit":
                    break
                
                # Validate format (optional, but helpful)
                if ":" not in user_input:
                    user_input = f"{self.username}:{user_input}"
                
                self.send_message(user_input)
        
        except KeyboardInterrupt:
            print("\n[INTERRUPTED] Shutting down...")
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}")
        finally:
            self.disconnect()


def main():
    """Main entry point."""
    print("=" * 50)
    print("  NETWORK CHAT CLIENT")
    print("=" * 50)
    
    client = ChatClient()
    client.run_interactive()


if __name__ == "__main__":
    main()

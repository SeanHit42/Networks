import socket
import threading
from typing import Optional, Callable


class ChatClient:
    """
    TCP Chat Client.
    Handles network communication only (no UI logic).
    """

    BUFFER_SIZE = 1024

    def __init__(
        self,
        host: str = "localhost",
        port: int = 10000,
        username: Optional[str] = None,
        on_message: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ):
        self.host = host
        self.port = port
        self.username = username

        self.on_message = on_message
        self.on_status = on_status

        self.socket: Optional[socket.socket] = None
        self.is_connected = False
        self.listener_thread: Optional[threading.Thread] = None

    # ---------- CONNECTION ----------

    def connect(self) -> bool:
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(5)  # 5 second connection timeout
            
            if self.on_status:
                self.on_status(f"Connecting to {self.host}:{self.port}...")
            
            self.socket.connect((self.host, self.port))

            # Receive welcome message
            welcome = self.socket.recv(self.BUFFER_SIZE).decode("utf-8")

            if self.on_message:
                self.on_message(f"[SERVER] {welcome}")

            if not self.username:
                raise ValueError("Username must be provided")

            # Send username to server (use sendall for full delivery)
            self.socket.sendall(self.username.encode("utf-8"))
            self.is_connected = True
            self.socket.settimeout(None)  # Switch to blocking mode for listening

            if self.on_status:
                self.on_status(f"Connected as {self.username}")

            return True

        except ConnectionRefusedError:
            if self.on_status:
                self.on_status("Connection refused - is server running on that IP/port?")
            self.is_connected = False
            return False
        except socket.timeout:
            if self.on_status:
                self.on_status("Connection timed out - check server IP and firewall")
            self.is_connected = False
            return False
        except Exception as e:
            if self.on_status:
                self.on_status(f"Connection failed: {type(e).__name__}: {e}")
            self.is_connected = False
            return False

    # ---------- LISTENER ----------

    def start_listening(self):
        if self.listener_thread and self.listener_thread.is_alive():
            return

        self.listener_thread = threading.Thread(
            target=self._listen_loop,
            daemon=True
        )
        self.listener_thread.start()

    def _listen_loop(self):
        try:
            while self.is_connected and self.socket:
                data = self.socket.recv(self.BUFFER_SIZE)
                if not data:
                    break

                message = data.decode("utf-8")

                if self.on_message:
                    self.on_message(message)

        except OSError:
            pass
        except Exception as e:
            if self.on_status:
                self.on_status(f"Listener error: {e}")

        finally:
            self.is_connected = False
            if self.on_status:
                self.on_status("Disconnected from server")

    # ---------- SEND ----------

    def send_message(self, message: str) -> bool:
        if not self.is_connected or not self.socket:
            return False

        try:
            self.socket.send(message.encode("utf-8"))
            return True
        except Exception as e:
            if self.on_status:
                self.on_status(f"Send failed: {e}")
            self.is_connected = False
            return False

    # ---------- DISCONNECT ----------

    def disconnect(self):
        self.is_connected = False
        if self.socket:
            try:
                self.socket.close()
            except:
                pass
        if self.on_status:
            self.on_status("Client disconnected")


# ---------- OPTIONAL: CLI TEST MODE ----------
# Not used by GUI, but useful for debugging.

if __name__ == "__main__":
    def print_message(msg):
        print(msg)

    def print_status(status):
        print(f"[STATUS] {status}")

    client = ChatClient(
        host="localhost",
        port=10000,
        username="test_user",
        on_message=print_message,
        on_status=print_status,
    )

    if client.connect():
        client.start_listening()
        try:
            while True:
                msg = input("> ")
                if msg.lower() == "exit":
                    break
                client.send_message(msg)
        except KeyboardInterrupt:
            pass
        finally:
            client.disconnect()

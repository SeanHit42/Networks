import tkinter as tk
from tkinter import ttk, messagebox
import threading
import datetime

from client import ChatClient


class ChatGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TCP Network Chat")
        self.root.geometry("720x500")
        self.root.minsize(650, 450)

        self.client: ChatClient | None = None

        self._setup_style()
        self._build_ui()

    # ---------- STYLE ----------

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "Header.TLabel",
            font=("Segoe UI", 14, "bold")
        )
        style.configure(
            "Status.TLabel",
            font=("Segoe UI", 9)
        )
        style.configure(
            "Send.TButton",
            font=("Segoe UI", 10, "bold")
        )

    # ---------- UI ----------

    def _build_ui(self):
        # Header
        header = ttk.Frame(self.root, padding=10)
        header.pack(fill="x")

        ttk.Label(
            header,
            text="TCP Network Chat",
            style="Header.TLabel"
        ).pack(side="left")

        self.status_label = ttk.Label(
            header,
            text="Disconnected",
            style="Status.TLabel",
            foreground="red"
        )
        self.status_label.pack(side="right")

        # Chat area
        chat_frame = ttk.Frame(self.root, padding=(10, 5))
        chat_frame.pack(fill="both", expand=True)

        self.chat_box = tk.Text(
            chat_frame,
            state="disabled",
            wrap="word",
            font=("Segoe UI", 10),
            bg="#f8f8f8"
        )
        self.chat_box.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(chat_frame, command=self.chat_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.chat_box.config(yscrollcommand=scrollbar.set)

        # Input
        input_frame = ttk.Frame(self.root, padding=10)
        input_frame.pack(fill="x")

        self.message_entry = ttk.Entry(
            input_frame,
            font=("Segoe UI", 10)
        )
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.message_entry.bind("<Return>", self._send_message_event)

        self.send_button = ttk.Button(
            input_frame,
            text="Send",
            style="Send.TButton",
            command=self.send_message,
            state="disabled"
        )
        self.send_button.pack(side="right")

        # Debug log panel
        log_frame = ttk.LabelFrame(self.root, text="Debug Log", padding=6)
        log_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.debug_log = tk.Text(
            log_frame,
            height=4,
            state="disabled",
            wrap="word",
            font=("Courier", 8),
            bg="#1e1e1e",
            fg="#00ff00"
        )
        self.debug_log.pack(fill="both", expand=True)

        # Connect popup
        self._show_connect_popup()

    # ---------- CONNECT POPUP ----------

    def _show_connect_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Connect to Server")
        popup.geometry("320x240")
        popup.resizable(False, False)
        popup.grab_set()

        frame = ttk.Frame(popup, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Username:").pack(anchor="w")
        username_entry = ttk.Entry(frame)
        username_entry.pack(fill="x")

        ttk.Label(frame, text="Server IP:").pack(anchor="w", pady=(8, 0))
        ip_entry = ttk.Entry(frame)
        ip_entry.insert(0, "192.168.1.212")  # Change to actual server IP
        ip_entry.pack(fill="x")

        ttk.Label(frame, text="Port:").pack(anchor="w", pady=(8, 0))
        port_entry = ttk.Entry(frame)
        port_entry.insert(0, "10000")
        port_entry.pack(fill="x")

        def connect():
            username = username_entry.get().strip()
            host = ip_entry.get().strip()
            port = port_entry.get().strip()

            if not username or not host or not port:
                messagebox.showerror("Error", "All fields are required")
                return

            try:
                port_int = int(port)
            except ValueError:
                messagebox.showerror("Error", "Port must be a number")
                return

            popup.destroy()
            self._connect_client(username, host, port_int)

        ttk.Button(frame, text="Connect", command=connect).pack(pady=12)
        popup.bind("<Return>", lambda _: connect())

        username_entry.focus()

    # ---------- CLIENT ----------

    def _connect_client(self, username: str, host: str, port: int):
        self.client = ChatClient(
            host=host,
            port=port,
            username=username,
            on_message=self._on_message,
            on_status=self._on_status
        )

        threading.Thread(
            target=self._connect_background,
            daemon=True
        ).start()

    def _connect_background(self):
        if self.client and self.client.connect():
            self.client.start_listening()
            self.root.after(0, self._enable_input)

    # ---------- CALLBACKS ----------

    def _on_message(self, message: str):
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.root.after(
            0,
            lambda: self._append_message(f"[{timestamp}] {message}")
        )
        self.root.after(0, lambda: self._append_debug(f"MSG: {message}"))

    def _on_status(self, status: str):
        self.root.after(0, lambda: self._update_status(status))
        self.root.after(0, lambda: self._append_debug(f"STATUS: {status}"))

    def _append_debug(self, text: str):
        try:
            self.debug_log.configure(state="normal")
            self.debug_log.insert("end", text + "\n")
            self.debug_log.see("end")
            self.debug_log.configure(state="disabled")
        except Exception:
            pass

    def _append_message(self, message: str):
        self.chat_box.configure(state="normal")
        self.chat_box.insert("end", message + "\n")
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def _update_status(self, status: str):
        self.status_label.config(text=status)
        if status.lower().startswith("connected"):
            self.status_label.config(foreground="green")
        else:
            self.status_label.config(foreground="red")

    def _enable_input(self):
        self.send_button.config(state="normal")

    # ---------- SEND ----------

    def _send_message_event(self, _):
        self.send_message()

    def send_message(self):
        if not self.client or not self.client.is_connected:
            return

        message = self.message_entry.get().strip()
        if not message:
            return

        self.client.send_message(message)
        self.message_entry.delete(0, "end")

    # ---------- CLOSE ----------

    def on_close(self):
        if self.client:
            self.client.disconnect()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = ChatGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()

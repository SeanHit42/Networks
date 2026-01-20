import tkinter as tk
from tkinter import ttk, messagebox
import threading
import datetime

from client import ChatClient


class ChatGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("TCP Network Chat")
        self.root.geometry("920x500")
        self.root.minsize(850, 450)

        self.client: ChatClient | None = None
        self.username: str | None = None
        self.online_users: list[str] = []
        self.mention_popup: tk.Toplevel | None = None
        self.mention_listbox: tk.Listbox | None = None

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

        # Main container (chat + users list)
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        # Left side: Chat area
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        chat_label = ttk.Label(left_frame, text="Messages:", font=("Segoe UI", 9, "bold"))
        chat_label.pack(anchor="w", pady=(0, 4))

        chat_frame = ttk.Frame(left_frame)
        chat_frame.pack(fill="both", expand=True)

        self.chat_box = tk.Text(
            chat_frame,
            state="disabled",
            wrap="word",
            font=("Segoe UI", 10),
            bg="#f8f8f8",
            height=15
        )
        self.chat_box.pack(side="left", fill="both", expand=True)

        # Configure text tags for different message types
        self.chat_box.tag_configure("private_msg", foreground="#FF6B6B", font=("Segoe UI", 10, "bold"))
        self.chat_box.tag_configure("system_msg", foreground="#6C63FF", font=("Segoe UI", 9, "italic"))
        self.chat_box.tag_configure("normal_msg", foreground="#000000")
        self.chat_box.tag_configure("timestamp", foreground="#888888", font=("Segoe UI", 8))
        self.chat_box.tag_configure("own_msg", foreground="#4CAF50", font=("Segoe UI", 10, "bold"))

        scrollbar = ttk.Scrollbar(chat_frame, command=self.chat_box.yview)
        scrollbar.pack(side="right", fill="y")
        self.chat_box.config(yscrollcommand=scrollbar.set)

        # Right side: Online Users List
        right_frame = ttk.LabelFrame(self.root, text="Online Users", padding=8)
        right_frame.pack(side="right", fill="y", padx=(0, 10), pady=(15, 10))

        self.users_listbox = tk.Listbox(
            right_frame,
            font=("Segoe UI", 10),
            width=15,
            height=20,
            bg="#f0f0f0",
            selectmode="single"
        )
        self.users_listbox.pack(fill="both", expand=True)

        users_scrollbar = ttk.Scrollbar(right_frame, command=self.users_listbox.yview)
        users_scrollbar.pack(side="right", fill="y", before=self.users_listbox)
        self.users_listbox.config(yscrollcommand=users_scrollbar.set)

        # Input area - more prominent
        input_label = ttk.Label(main_frame, text="Your message (use @username for private):", font=("Segoe UI", 9, "bold"))
        input_label.pack(anchor="w", pady=(10, 4))

        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill="x")

        self.message_entry = ttk.Entry(
            input_frame,
            font=("Segoe UI", 11)
        )
        self.message_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.message_entry.bind("<Return>", self._send_message_event)
        self.message_entry.bind("<KeyRelease>", self._on_message_entry_change)

        self.send_button = tk.Button(
            input_frame,
            text="➤ Send",
            font=("Segoe UI", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            activebackground="#45a049",
            command=self.send_message,
            state="disabled",
            width=10,
            padx=10,
            pady=6
        )
        self.send_button.pack(side="right")

        # Debug log panel (smaller, at bottom)
        log_frame = ttk.LabelFrame(self.root, text="Debug Log", padding=6)
        log_frame.pack(fill="x", padx=10, pady=(0, 10))
        self.debug_log = tk.Text(
            log_frame,
            height=3,
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
        popup.geometry("450x420")
        popup.resizable(False, False)
        popup.grab_set()

        frame = ttk.Frame(popup, padding=10)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Username:").pack(anchor="w")
        username_entry = ttk.Entry(frame)
        username_entry.pack(fill="x", pady=(0, 12))

        # Local Network Discovery Section
        local_frame = ttk.LabelFrame(frame, text="Local Network (Auto-Discover)", padding=8)
        local_frame.pack(fill="x", pady=(0, 12))
        
        server_var = tk.StringVar()
        server_combo = ttk.Combobox(local_frame, textvariable=server_var, state="readonly", width=30)
        server_combo.pack(side="left", fill="x", expand=True, padx=(0, 8))
        server_combo.insert(0, "Searching...")
        
        def refresh_servers():
            refresh_btn.config(state="disabled", text="Searching...")
            popup.update()
            
            servers = ChatClient.discover_servers(timeout=2.0)
            if servers:
                server_list = [f"{ip}:{port}" for ip, port in servers.items()]
                server_combo.config(values=server_list)
                if server_list:
                    server_combo.current(0)
            else:
                server_combo.config(values=["No servers found"])
                server_combo.current(0)
            
            refresh_btn.config(state="normal", text="🔄 Refresh")
        
        refresh_btn = ttk.Button(local_frame, text="🔄 Refresh", command=refresh_servers, width=12)
        refresh_btn.pack(side="right")
        
        # Auto-refresh on startup
        threading.Thread(target=refresh_servers, daemon=True).start()

        # Manual Entry Section
        manual_frame = ttk.LabelFrame(frame, text="Other Networks (Manual Entry)", padding=8)
        manual_frame.pack(fill="x", pady=(0, 12))
        
        ttk.Label(manual_frame, text="Server IP/Hostname:").pack(anchor="w")
        ip_entry = ttk.Entry(manual_frame, width=35)
        ip_entry.pack(fill="x", pady=(4, 8))
        
        ttk.Label(manual_frame, text="Port:").pack(anchor="w")
        port_entry = ttk.Entry(manual_frame, width=35)
        port_entry.insert(0, "10000")
        port_entry.pack(fill="x")
        
        # Help text
        help_text = ttk.Label(
            frame,
            text="For different networks: Use public IP + port forwarding, or share IP with server admin",
            font=("Segoe UI", 8),
            foreground="gray"
        )
        help_text.pack(anchor="w", pady=(8, 12))

        def connect():
            username = username_entry.get().strip()
            
            if not username:
                messagebox.showerror("Error", "Username is required")
                return
            
            # Try local network selection first
            server_str = server_var.get().strip()
            manual_ip = ip_entry.get().strip()
            
            if server_str and "No servers found" not in server_str:
                # Use auto-discovered server
                try:
                    if ":" in server_str:
                        host, port_str = server_str.rsplit(":", 1)
                        port_int = int(port_str)
                    else:
                        host = server_str
                        port_int = int(port_entry.get().strip())
                except ValueError:
                    messagebox.showerror("Error", "Port must be a number")
                    return
            elif manual_ip:
                # Use manual entry
                host = manual_ip
                try:
                    port_int = int(port_entry.get().strip())
                except ValueError:
                    messagebox.showerror("Error", "Port must be a number")
                    return
            else:
                messagebox.showerror("Error", "Please select a server or enter IP manually")
                return

            popup.destroy()
            self._connect_client(username, host, port_int)

        join_btn = tk.Button(
            frame,
            text="Join Chat",
            font=("Segoe UI", 11, "bold"),
            bg="#4CAF50",
            fg="white",
            activebackground="#45a049",
            command=connect,
            width=15,
            padx=10,
            pady=6
        )
        join_btn.pack(pady=12)
        popup.bind("<Return>", lambda _: connect())
        popup.bind("<Return>", lambda _: connect())

        username_entry.focus()

    # ---------- CLIENT ----------

    def _connect_client(self, username: str, host: str, port: int):
        self.username = username
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
        
        # Check if it's a user list update (format: "USERS|user1,user2,user3")
        if message.startswith("USERS|"):
            users_str = message[6:]  # Remove "USERS|" prefix
            self.online_users = [u.strip() for u in users_str.split(",") if u.strip() and u.strip() != self.username]
            self.root.after(0, self._update_users_list)
            return
        
        # Determine message type and apply appropriate styling
        is_private = False
        is_system = message.startswith("[")
        
        if not is_system:
            # Check if it's a private message (format: "username (private):" or "@username:")
            if " (private):" in message or message.startswith("@"):
                is_private = True
        
        self.root.after(
            0,
            lambda: self._append_message_styled(message, is_private=is_private, is_system=is_system, timestamp=timestamp)
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

    def _append_message_styled(self, message: str, is_private: bool = False, is_system: bool = False, timestamp: str = ""):
        self.chat_box.configure(state="normal")
        
        if timestamp and not is_system:
            self.chat_box.insert("end", f"[{timestamp}] ", "timestamp")
        
        if is_private:
            self.chat_box.insert("end", message + "\n", "private_msg")
        elif is_system:
            self.chat_box.insert("end", message + "\n", "system_msg")
        else:
            self.chat_box.insert("end", message + "\n", "normal_msg")
        
        self.chat_box.configure(state="disabled")
        self.chat_box.see("end")

    def _append_message(self, message: str):
        """Legacy method for backward compatibility"""
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

    def _update_users_list(self):
        """Update the online users listbox"""
        try:
            self.users_listbox.delete(0, "end")
            for user in sorted(self.online_users):
                self.users_listbox.insert("end", user)
        except Exception as e:
            self._append_debug(f"Error updating users list: {e}")

    def _on_message_entry_change(self, event):
        """Handle @ mention autocomplete"""
        text = self.message_entry.get()
        
        # Close popup if text is empty or no @ found
        if not text or "@" not in text:
            self._close_mention_popup()
            return
        
        # Find the @ mention pattern
        at_index = text.rfind("@")
        if at_index == -1 or (at_index > 0 and text[at_index - 1].isalnum()):
            self._close_mention_popup()
            return
        
        # Get text after @
        text_after_at = text[at_index + 1:]
        parts = text_after_at.split()
        
        # Close popup if nothing after @
        if not parts:
            self._close_mention_popup()
            return
        
        mention_text = parts[0]
        
        # Filter matching users
        matching_users = [u for u in self.online_users if u.lower().startswith(mention_text.lower())]
        
        if not matching_users:
            self._close_mention_popup()
            return
        
        # Show popup with suggestions
        self._show_mention_popup(matching_users, at_index)

    def _show_mention_popup(self, users: list[str], at_index: int):
        """Show a popup with user suggestions"""
        if self.mention_popup and self.mention_popup.winfo_exists():
            self.mention_listbox.delete(0, "end")
            for user in users:
                self.mention_listbox.insert("end", user)
        else:
            self.mention_popup = tk.Toplevel(self.root)
            self.mention_popup.wm_overrideredirect(True)
            
            self.mention_listbox = tk.Listbox(
                self.mention_popup,
                font=("Segoe UI", 9),
                height=min(5, len(users)),
                width=20
            )
            self.mention_listbox.pack()
            
            # Position popup near entry field
            self.message_entry.update_idletasks()
            x = self.message_entry.winfo_rootx()
            y = self.message_entry.winfo_rooty() + self.message_entry.winfo_height()
            self.mention_popup.geometry(f"+{x}+{y}")
            
            # Bind selection
            self.mention_listbox.bind("<Button-1>", lambda e: self._select_mention(self.mention_listbox.curselection(), at_index))
            self.mention_listbox.bind("<Return>", lambda e: self._select_mention(self.mention_listbox.curselection(), at_index))

    def _close_mention_popup(self):
        """Close the mention popup"""
        if self.mention_popup and self.mention_popup.winfo_exists():
            self.mention_popup.destroy()
            self.mention_popup = None
            self.mention_listbox = None

    def _select_mention(self, selection, at_index: int):
        """Insert selected mention into message entry"""
        if not selection:
            return
        
        selected_user = self.mention_listbox.get(selection[0])
        text = self.message_entry.get()
        
        # Replace @ mention with @username
        before = text[:at_index]
        after = text[self.message_entry.index("insert"):]
        new_text = f"{before}@{selected_user} {after}"
        
        self.message_entry.delete(0, "end")
        self.message_entry.insert(0, new_text)
        self.message_entry.icursor(len(f"{before}@{selected_user} "))
        
        self._close_mention_popup()

    # ---------- SEND ----------

    def _send_message_event(self, _):
        self.send_message()

    def send_message(self):
        if not self.client or not self.client.is_connected:
            return

        message = self.message_entry.get().strip()
        if not message:
            return

        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        
        # Check if it's a private message (starts with @)
        is_private = message.startswith("@")
        
        if is_private:
            display_msg = f"[{timestamp}] You (private): {message}"
            self.root.after(0, lambda: self._append_message_styled(display_msg, is_private=True))
        else:
            display_msg = f"[{timestamp}] {self.username} (You): {message}"
            self.root.after(0, lambda: self._append_message(display_msg))
        
        self.client.send_message(message)
        self.message_entry.delete(0, "end")
        self._close_mention_popup()

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

import tkinter as tk
from tkinter import ttk, messagebox
from client import ChatClient
import datetime
import threading
from typing import Optional


class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.frame = ttk.Frame(canvas)
        vsb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.create_window((0, 0), window=self.frame, anchor="nw")

        def _on_frame_config(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        self.frame.bind("<Configure>", _on_frame_config)


class ChatGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Network Chat — Redesigned")
        self.root.geometry("900x560")
        self.root.minsize(760, 480)

        self.client: Optional[ChatClient] = None
        self.username: Optional[str] = None
        self.theme = "light"

        self._build_style()
        self._build_layout()

    # ---------- UI BUILD ----------

    def _build_style(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("Small.TLabel", font=("Segoe UI", 9))
        style.configure("Send.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("User.TListbox", background="#ffffff")

    def _build_layout(self):
        # Top header
        header = ttk.Frame(self.root)
        header.pack(fill="x")

        header_left = ttk.Frame(header, padding=8)
        header_left.pack(side="left")
        ttk.Label(header_left, text="NetChat", style="Header.TLabel").pack(side="left")

        header_right = ttk.Frame(header, padding=8)
        header_right.pack(side="right")
        self.status_label = ttk.Label(header_right, text="Disconnected", style="Small.TLabel", foreground="red")
        self.status_label.pack(side="left", padx=(0, 8))

        ttk.Button(header_right, text="Theme", command=self._toggle_theme).pack(side="left")

        # Main area (chat + sidebar)
        main = ttk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=10, pady=(6, 10))

        # Chat column
        chat_col = ttk.Frame(main)
        chat_col.pack(side="left", fill="both", expand=True)

        # Conversation area (scrollable frames with bubbles)
        conv_frame = ttk.LabelFrame(chat_col, text="Conversation")
        conv_frame.pack(fill="both", expand=True)

        self.messages = ScrollableFrame(conv_frame, padding=6)
        self.messages.pack(fill="both", expand=True)

        # Input area with emoji and attach
        input_bar = ttk.Frame(chat_col, padding=8)
        input_bar.pack(fill="x")

        ttk.Button(input_bar, text="😊", width=3, command=self._open_emoji_picker).pack(side="left", padx=(0, 6))
        self.message_entry = ttk.Entry(input_bar, font=("Segoe UI", 10))
        self.message_entry.pack(side="left", fill="x", expand=True)
        self.message_entry.bind("<Return>", self._send_message_event)

        self.send_button = ttk.Button(input_bar, text="Send", style="Send.TButton", command=self.send_message, state="disabled")
        self.send_button.pack(side="right")

        # Sidebar (users / quick actions)
        sidebar = ttk.Frame(main, width=220)
        sidebar.pack(side="right", fill="y")

        users_box = ttk.LabelFrame(sidebar, text="Users")
        users_box.pack(fill="both", expand=False, padx=(8, 0))
        self.users_list = tk.Listbox(users_box, height=10)
        self.users_list.pack(fill="both", expand=True, padx=6, pady=6)

        quick_box = ttk.Frame(sidebar)
        quick_box.pack(fill="x", pady=(8, 0), padx=(8, 0))
        ttk.Button(quick_box, text="Connect", command=self._prompt_username).pack(fill="x")
        ttk.Button(quick_box, text="Clear Chat", command=self._clear_messages).pack(fill="x", pady=(6, 0))

        # prompt for username/connect
        self._prompt_username()

    # ---------- CONNECTION ----------

    def _prompt_username(self):
        popup = tk.Toplevel(self.root)
        popup.title("Connect to Chat")
        popup.geometry("360x160")
        popup.resizable(False, False)
        popup.grab_set()

        ttk.Label(popup, text="Choose a display name:", padding=8).pack(anchor="w", padx=12, pady=(8, 0))
        username_entry = ttk.Entry(popup)
        username_entry.pack(padx=12, fill="x")
        username_entry.focus()

        def connect():
            username = username_entry.get().strip()
            if not username:
                messagebox.showerror("Error", "Username cannot be empty")
                return

            popup.destroy()
            self.username = username
            self._connect_client(username)

        btn_frame = ttk.Frame(popup)
        btn_frame.pack(fill="x", pady=12, padx=12)
        ttk.Button(btn_frame, text="Connect", command=connect).pack(side="right")
        popup.bind("<Return>", lambda _: connect())

    def _connect_client(self, username: str):
        self.client = ChatClient(
            username=username,
            on_message=self._on_message,
            on_status=self._on_status
        )

        threading.Thread(target=self._connect_background, daemon=True).start()

    def _connect_background(self):
        success = self.client.connect()
        if success:
            self.client.start_listening()
            self.root.after(0, self._enable_input)

    # ---------- UI CALLBACKS ----------

    def _on_message(self, message: str):
        timestamp = datetime.datetime.now().strftime("%H:%M")
        # Expecting messages like "user: message" — try to split
        sender = ""
        body = message
        if ": " in message:
            parts = message.split(": ", 1)
            sender, body = parts[0], parts[1]

        self.root.after(0, lambda: self._append_message(sender, body, timestamp))

    def _on_status(self, status: str):
        self.root.after(0, lambda: self._update_status(status))

    def _append_message(self, message: str):
        # Deprecated: old text box approach
        pass

    def _append_message(self, sender: str, text: str, timestamp: str):
        # Create a message bubble in the scrollable frame
        bubble = ttk.Frame(self.messages.frame)
        is_me = (self.username is not None and sender == self.username)
        bg = "#DCF8C6" if is_me else "#FFFFFF"
        fg = "#000000"

        # container aligns left or right
        container = ttk.Frame(bubble)
        container.pack(fill="x", padx=6, pady=2)

        if is_me:
            container.pack(anchor="e")
        else:
            container.pack(anchor="w")

        msg_lbl = tk.Label(container, text=text, bg=bg, fg=fg, justify="left", wraplength=520,
                           font=("Segoe UI", 10), bd=0, padx=8, pady=6)
        msg_lbl.pack(side="left" if not is_me else "right")

        ts = ttk.Label(container, text=timestamp, style="Small.TLabel")
        ts.pack(side="left" if not is_me else "right", padx=(6, 0))

        bubble.pack(fill="x")
        self.root.after(50, self._scroll_to_bottom)

    def _update_status(self, status: str):
        self.status_label.config(text=status)
        if status.lower().startswith("connected"):
            self.status_label.config(foreground="green")
        else:
            self.status_label.config(foreground="red")

    def _scroll_to_bottom(self):
        # Find the canvas inside ScrollableFrame and scroll to bottom
        for child in self.messages.winfo_children():
            if isinstance(child, tk.Canvas):
                child.yview_moveto(1.0)
                return

    def _enable_input(self):
        self.send_button.config(state="normal")

    def _clear_messages(self):
        for w in self.messages.frame.winfo_children():
            w.destroy()

    def _toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        if self.theme == "dark":
            self.root.configure(bg="#2b2b2b")
        else:
            self.root.configure(bg="#f0f0f0")

    # ---------- SEND ----------

    def _send_message_event(self, _):
        self.send_message()

    def send_message(self):
        if not self.client or not getattr(self.client, "is_connected", False):
            return

        message = self.message_entry.get().strip()
        if not message:
            return

        # Append locally immediately
        timestamp = datetime.datetime.now().strftime("%H:%M")
        if self.username:
            self._append_message(self.username, message, timestamp)

        try:
            self.client.send_message(message)
        except Exception:
            pass

        self.message_entry.delete(0, "end")

    def _open_emoji_picker(self):
        win = tk.Toplevel(self.root)
        win.title("Emoji")
        win.resizable(False, False)
        emojis = ["😀", "😂", "😍", "😅", "😎", "👍", "🙏"]
        for e in emojis:
            b = ttk.Button(win, text=e, command=lambda em=e: self._insert_emoji(em))
            b.pack(side="left", padx=6, pady=6)

    def _insert_emoji(self, emoji: str):
        cur = self.message_entry.get()
        self.message_entry.delete(0, "end")
        self.message_entry.insert(0, cur + emoji)

    # ---------- CLEANUP ----------

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

import threading
import websocket

from Message import Message, MessageType


class WSClient:
    def __init__(self, ctx, username, on_connect_callback=None, on_message_callback=None, on_users_list_callback=None):
        self.url = ctx.url()
        self.username = username
        self.on_connect_callback = on_connect_callback
        self.on_message_callback = on_message_callback
        self.on_users_list_callback = on_users_list_callback
        self._ws = None

    def connect(self):
        """Connects to the WebSocket server (blocking). Call from a background thread."""
        ws = websocket.WebSocketApp(
            self.url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )
        self._ws = ws
        ws.run_forever()

    def connect_async(self):
        """Connects in a background thread (non-blocking)."""
        t = threading.Thread(target=self.connect, daemon=True)
        t.start()

    def _on_open(self, ws):
        decl = Message(MessageType.DECLARATION, emitter=self.username, receiver="SERVER", value=self.username)
        ws.send(decl.to_json())
        if self.on_connect_callback:
            self.on_connect_callback()

    def _on_message(self, ws, raw):
        try:
            msg = Message.from_json(raw)
        except Exception:
            return

        if msg.message_type == MessageType.RECEPTION.CLIENT_LIST and self.on_users_list_callback:
            self.on_users_list_callback(msg.value)
        elif self.on_message_callback:
            self.on_message_callback(msg)

    def _on_error(self, ws, error):
        print(f"[WSClient] Erreur: {error}")

    def _on_close(self, ws, close_status_code, close_msg):
        print(f"[WSClient] Connexion fermée")

    def send(self, msg: Message):
        if self._ws:
            self._ws.send(msg.to_json())

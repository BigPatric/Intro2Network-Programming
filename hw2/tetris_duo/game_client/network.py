import socket, threading
try:
    from config import GAME_CONNECT_HOST
except Exception:
    GAME_CONNECT_HOST = '127.0.0.1'
from common.protocol import send_msg, recv_msg

class NetworkClient:
    def __init__(self, host=GAME_CONNECT_HOST, port=10002, on_snapshot=None, on_welcome=None, on_game_over=None):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        try:
            self.sock.connect((host, port))
            self.connected = True
        except Exception:
            self.connected = False
        self.on_snapshot = on_snapshot
        self.on_welcome = on_welcome
        self.on_game_over = on_game_over
        self._welcome_received = False
        threading.Thread(target=self._listen, daemon=True).start()

    def hello(self, roomId=None, userId=None, version=1):
        if not self.connected:
            return
        try:
            send_msg(self.sock, {"type": "HELLO", "version": version, "roomId": roomId, "userId": userId})
        except Exception:
            self.connected = False

    def send_input(self, action):
        if not self.connected:
            return
        try:
            send_msg(self.sock, {"type": "INPUT", "action": action})
        except Exception:
            self.connected = False

    def _listen(self):
        while self.connected:
            try:
                msg = recv_msg(self.sock)
                if msg is None:
                    self.connected = False
                    break
                # 第一次收到 WELCOME
                if not self._welcome_received and msg.get('type') == 'WELCOME':
                    self._welcome_received = True
                    if self.on_welcome:
                        self.on_welcome(msg)
                    continue
                # SNAPSHOT
                if msg.get('type') == 'SNAPSHOT' and self.on_snapshot:
                    self.on_snapshot(msg)
                # GAME_OVER
                if msg.get('type') == 'GAME_OVER' and self.on_game_over:
                    self.on_game_over(msg)
            except Exception:
                self.connected = False
                break

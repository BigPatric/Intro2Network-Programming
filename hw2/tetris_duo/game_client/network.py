import socket, threading
from common.protocol import send_msg, recv_msg

class NetworkClient:
    def __init__(self, host='127.0.0.1', port=10002, on_snapshot=None):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = False
        try:
            self.sock.connect((host, port))
            self.connected = True
        except Exception:
            # 無法連線時保留 connected=False，讓上層可決定是否重試
            self.connected = False
        self.on_snapshot = on_snapshot
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
            # 伺服器已關閉或管線損壞，標記為斷線，避免崩潰
            self.connected = False

    def _listen(self):
        while True:
            if not self.connected:
                break
            msg = recv_msg(self.sock)
            if msg is None:
                # 遠端關閉
                self.connected = False
                break
            if self.on_snapshot:
                self.on_snapshot(msg)

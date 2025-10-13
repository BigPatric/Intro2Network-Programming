import json
import socket
from typing import Optional

from config import BUFFER_SIZE, ACCOUNTS_FILE

# socket helpers for JSON messages over TCP

# 透過 TCP socket 發送 JSON 物件
def send_json_tcp(conn: socket.socket, obj: dict):
    data = (json.dumps(obj) + '\n').encode()
    conn.sendall(data)

# 從 TCP socket 接收 JSON 物件
def recv_json_tcp(conn: socket.socket) -> Optional[dict]:
    # read until newline
    buf = b''
    while True:
        chunk = conn.recv(BUFFER_SIZE)
        if not chunk:
            return None
        buf += chunk
        if b'\n' in buf:
            line, rest = buf.split(b'\n', 1)
            try:
                return json.loads(line.decode())
            except Exception:
                return None


# accounts persistence

# 從檔案載入帳戶資料
def load_accounts():
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# 儲存帳戶資料到檔案
def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=2)
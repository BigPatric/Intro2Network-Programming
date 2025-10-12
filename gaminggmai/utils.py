import json
import socket
from typing import Optional

from config import BUFFER_SIZE, ACCOUNTS_FILE

# socket helpers for JSON messages over TCP

def send_json_tcp(conn: socket.socket, obj: dict):
    data = (json.dumps(obj) + '\n').encode()
    conn.sendall(data)


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

def load_accounts():
    try:
        with open(ACCOUNTS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_accounts(accounts):
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=2)
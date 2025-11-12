import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import socket, threading
from common.protocol import send_msg, recv_msg
from db_server.storage import Database

db = Database('data.json')

def handle_client(conn, addr):
    print(f"[DB] Connected: {addr}")
    try:
        while True:
            req = recv_msg(conn)
            if req is None:
                break
            res = db.handle_request(req)
            send_msg(conn, res)
    except Exception as e:
        print(f"[DB] Error: {e}")
    finally:
        conn.close()

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', 10001))
    s.listen()
    print("[DB] Server running on 10001")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == '__main__':
    main()
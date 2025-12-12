# server/server_main.py
import socket
import threading
import sys
import os

# 確保可以 import common
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# [Fix 1] 必須引入 send_file
from common.protocol import recv_json, send_json, send_file
from server.developer_service import handle_developer_upload
from server.lobby_service import handle_lobby_request

HOST = '0.0.0.0'
PORT = 8888
UPLOAD_DIR = 'server/uploaded_games' # 定義上傳路徑常數

def client_handler(conn, addr):
    print(f"Connected by {addr}")
    try:
        while True:
            request = recv_json(conn)
            if not request:
                break
            
            command = request.get('command')
            response = {'status': 'error', 'message': 'Unknown command'}

            # --- 路由邏輯 ---
            if command == 'upload_game':
                # 處理上傳 (接收檔案)
                response = handle_developer_upload(conn, request)
                send_json(conn, response)

            elif command == 'download_game':
                # [Fix 2] 處理下載 (發送檔案)
                # 1. 先詢問 Lobby Service 檔案是否存在
                response = handle_lobby_request(conn, request)
                send_json(conn, response)
                
                # 2. 如果狀態是 ready_to_send，緊接著發送二進位檔案
                if response['status'] == 'ready_to_send':
                    game_name = request.get('game_name')
                    file_path = os.path.join(UPLOAD_DIR, f"{game_name}.zip")
                    print(f"Sending file {file_path} to {addr}...")
                    send_file(conn, file_path)
            
            else:
                # 其他一般指令 (List games, Login, Create Room...)
                response = handle_lobby_request(conn, request)
                send_json(conn, response)

    except Exception as e:
        print(f"Error handling client {addr}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

def main():
    # 確保必要的資料夾存在
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    # [Fix 3] 初始化資料庫 (避免第一次執行時 table 不存在)
    from server.db_manager import init_db
    init_db()

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # 允許快速重啟 Server
    s.bind((HOST, PORT))
    s.listen()
    print(f"Server listening on {HOST}:{PORT}")

    while True:
        conn, addr = s.accept()
        t = threading.Thread(target=client_handler, args=(conn, addr))
        t.start()

if __name__ == '__main__':
    main()
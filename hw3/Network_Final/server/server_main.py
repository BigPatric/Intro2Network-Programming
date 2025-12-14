# server/server_main.py
import socket
import threading
import json
import os
import sys

# 將專案根目錄添加到 sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from common.protocol import recv_json, send_json
from common.ip_port_config import SERVER_IP, SERVER_PORT
from server.lobby_service import LobbyService
from server.developer_service import DeveloperService
from server.connection_manager import connection_manager
from server.db_manager import DatabaseManager

class Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        self.db_manager = DatabaseManager()
        # 初始化服務，並傳入資料庫和連線管理器
        self.lobby_service = LobbyService(self.db_manager, connection_manager)
        self.developer_service = DeveloperService(self.db_manager, connection_manager)

    def start(self):
        """啟動伺服器並開始監聽連線"""
        self.sock.bind((self.host, self.port))
        self.sock.listen(5)
        print(f"伺服器啟動於 {self.host}:{self.port}")

        try:
            while True:
                conn, addr = self.sock.accept()
                print(f"新的連線來自: {addr}")
                # 為每個客戶端建立一個新的執行緒來處理
                thread = threading.Thread(target=self.handle_client, args=(conn,))
                thread.daemon = True
                thread.start()
        except KeyboardInterrupt:
            print("伺服器正在關閉...")
        finally:
            self.sock.close()

    def handle_client(self, conn):
        """處理單一客戶端連線的所有請求"""
        try:
            while True:
                data = recv_json(conn)
                if not data:
                    # 如果收到空資料，表示客戶端已斷開連線
                    break
                
                command = data.get('command')
                role = data.get('role')

                # 登出是特殊指令，直接處理
                if command == 'logout':
                    connection_manager.remove_connection(conn)
                    # 登出後不需要回傳，客戶端會自行處理介面切換
                    continue

                # 根據角色將請求分派給對應的服務
                if role == 'player':
                    self.lobby_service.handle_request(conn, data)
                elif role == 'developer':
                    self.developer_service.handle_request(conn, data)
                else:
                    # 如果請求沒有指定角色（除了登出），視為無效請求
                    send_json(conn, {'status': 'fail', 'message': '無效的請求，缺少角色資訊'})

        except (ConnectionResetError, json.JSONDecodeError, TypeError, OSError) as e:
            # 處理客戶端突然中斷連線等網路錯誤
            print(f"客戶端連線錯誤: {e}")
        finally:
            # 無論如何，最終都要從連線管理器中移除並關閉連線
            peer_name = conn.getpeername() if conn.fileno() != -1 else "未知連線"
            print(f"連線 {peer_name} 已關閉")
            connection_manager.remove_connection(conn)
            conn.close()

if __name__ == '__main__':
    server = Server(SERVER_IP, SERVER_PORT)
    server.start()
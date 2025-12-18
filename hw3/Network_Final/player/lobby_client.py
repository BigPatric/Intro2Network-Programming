import socket
import json
import os
import threading
import sys
import subprocess
import zipfile

# 確保可以從上層目錄 import
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.protocol import send_json, recv_json, recv_file
from common.ip_port_config import SERVER_IP, SERVER_PORT

DOWNLOAD_BASE = 'player/downloads'

class LobbyClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None
        self.listener_thread = None
        self.stop_listening = False
        self.current_room_id = None
        
    def start_listening(self):
        if self.listener_thread and self.listener_thread.is_alive():
            return
        self.stop_listening = False
        self.listener_thread = threading.Thread(target=self.listen_to_server, daemon=True)
        self.listener_thread.start()
        
    def connect(self):
        try:
            self.sock.connect((SERVER_IP, SERVER_PORT))
            return True
        except Exception as e:
            print(f"連線到大廳伺服器失敗: {e}")
            return False

    def login_with_credentials(self, username, password):
        # 登入請求中加入 role，以便伺服器分派
        send_json(self.sock, {'command': 'login', 'username': username, 'password': password, 'role': 'player'})
        res = recv_json(self.sock)
        print(f"[Lobby Client] 收到登入回應: {res}") # 偵錯日誌
        if res and res.get('status') == 'success':
            self.username = username
            return True, "登入成功"
        else:
            return False, res.get('message') if res else '沒有回應'

    def register_user(self, username, password):
        send_json(self.sock, {'command': 'register', 'username': username, 'password': password, 'role': 'player'})
        res = recv_json(self.sock)
        print(f"[Lobby Client] 收到註冊回應: {res}") # 偵錯日誌
        if res and res.get('status') == 'success':
            return True, res.get('message')
        else:
            return False, res.get('message') if res else '沒有回應'

    def logout(self):
        if not self.username:
            return
        send_json(self.sock, {'command': 'logout', 'role': 'player'})
        res = recv_json(self.sock)
        print(f"登出回應: {res}")
        self.username = None

    def get_online_players(self):
        send_json(self.sock, {'command': 'get_online_players', 'role': 'player'})
        res = recv_json(self.sock)
        print(f"[Lobby Client] 收到線上玩家回應: {res}")
        if res and res.get('status') == 'success':
            return res.get('players', [])
        else:
            print(f"取得線上玩家失敗: {res.get('message') if res else '沒有回應'}")
            return []

    def get_game_list(self):
        send_json(self.sock, {'command': 'get_game_list', 'role': 'player'})
        res = recv_json(self.sock)
        if res and res.get('status') == 'success':
            return res.get('games', [])
        return []

    def create_room(self, game_name):
        version = self.get_local_game_version(game_name)
        send_json(self.sock, {'command': 'create_room', 'game_name': game_name ,'version': version, 'role': 'player'})
        res = recv_json(self.sock)
        if res and res.get('status') == 'success':
            self.current_room_id = res.get('room_id')
            return True, res.get('room_id')
        else:
            return False, res.get('message') if res else '沒有回應'

    def list_rooms(self):
        send_json(self.sock, {'command': 'list_rooms', 'role': 'player'})
        res = recv_json(self.sock)
        if res and res.get('status') == 'success':
            return res.get('rooms', [])
        return []

    def join_room(self, room_id):
        rooms = self.list_rooms()
        game_name = None
        for room in rooms:
            if room['room_id'] == room_id:
                game_name = room['game']
                break
        version = self.get_local_game_version(game_name) if game_name else ""
        send_json(self.sock, {'command': 'join_room', 'room_id': room_id, 'version': version, 'role': 'player'})
        res = recv_json(self.sock)
        if res and res.get('status') == 'success':
            room_info = res.get('room_info', {})
            self.current_room_id = room_id
            return True, room_info
        else:
            return False, res.get('message') if res else '沒有回應'
        
    def listen_to_server(self):
        print("[Listener] 監聽伺服器訊息中...")
        while not self.stop_listening:
            try:
                res = recv_json(self.sock)
                
                if res is None:
                    print("[Listener] 連線中斷")
                    break
                
                print(f"[Listener] 收到訊息: {res}")
                
                if res.get('status') == 'start_game':
                    try:
                        game_name = res['game_name']
                        ip = res['ip']
                        port = res['port']
                        self.launch_game_client(game_name, ip, port)
                    except Exception as e:
                        print(f"[Listener] 啟動遊戲客戶端失敗: {e}")
                    
            except Exception as e:
                print(f"[Listener] 錯誤 (若為 socket timeout 可忽略): {e}")
                if self.stop_listening:
                    break
                # 嚴重錯誤才 break，否則 continue
                break
    
    def start_game(self, room_id):
        send_json(self.sock, {'command': 'start_game', 'room_id': room_id, 'role': 'player'})
   
    def launch_game_client(self, game_name, ip, port):
        game_client_path = os.path.join(DOWNLOAD_BASE, self.username, game_name, 'client.py')
        print(f"[Lobby Client] 嘗試啟動遊戲客戶端: {game_client_path} with IP: {ip}, Port: {port}")
        if os.path.exists(game_client_path):
            subprocess.Popen([sys.executable, game_client_path, ip, str(port)])
        else:
            print(f"找不到遊戲客戶端: {game_client_path}")

    def download_game(self, game_name):
        send_json(self.sock, {'command': 'download_game', 'game_name': game_name, 'role': 'player'})
        res = recv_json(self.sock)
        if res and res.get('status') == 'ready':
            user_dir = os.path.join(DOWNLOAD_BASE, self.username, game_name)
            os.makedirs(user_dir, exist_ok=True)
            client_py_path = os.path.join(user_dir, "client.py")
            recv_file(self.sock, client_py_path)
            return True
        return False
    
    def get_local_game_version(self, game_name):
        user_dir = os.path.join(DOWNLOAD_BASE, self.username, game_name)
        config_path = os.path.join(user_dir, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    info = json.load(f)
                    return info.get("version", "")
            except Exception:
                return ""
        return ""

    def close(self):
        self.sock.close()
        try:
            self.sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        self.sock.close()
        if self.listener_thread.is_alive():
            self.listener_thread.join(timeout=1)
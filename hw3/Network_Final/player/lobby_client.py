import socket
import json
import os
import sys
import subprocess

# 確保可以從上層目錄 import
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.protocol import send_json, recv_json, recv_file
from common.ip_port_config import SERVER_IP, SERVER_PORT

DOWNLOAD_BASE = 'player/downloads'

class LobbyClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None

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
        send_json(self.sock, {'command': 'create_room', 'game_name': game_name , 'role': 'player'})
        res = recv_json(self.sock)
        return res and res.get('status') == 'success'

    def list_rooms(self):
        send_json(self.sock, {'command': 'list_rooms', 'role': 'player'})
        res = recv_json(self.sock)
        if res and res.get('status') == 'success':
            return res.get('rooms', [])
        return []

    def launch_game_client(self, game_name, ip, port):
        game_client_path = os.path.join(DOWNLOAD_BASE, self.username, game_name, 'client.py')
        if os.path.exists(game_client_path):
            subprocess.Popen(['python3', game_client_path, '--ip', ip, '--port', str(port)])
        else:
            print(f"找不到遊戲客戶端: {game_client_path}")

    def close(self):
        self.sock.close()
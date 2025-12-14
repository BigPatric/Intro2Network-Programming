import socket
import json
import os
import zipfile
import subprocess
import time
import sys

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
            print(f"Cannot connect to server: {e}")
            return False

    def login_with_credentials(self, username, password):
        send_json(self.sock, {'command': 'login', 'username': username, 'password': password, 'role': 'player'})
        res = recv_json(self.sock)
        if res and res.get('status') == 'success':
            self.username = username
            return True, "登入成功"
        else:
            return False, res.get('message') if res else 'No response'
    def register_user(self, username, password):
        send_json(self.sock, {'command': 'register', 'username': username, 'password': password, 'role': 'player'})
        res = recv_json(self.sock)
        if res and res.get('status') == 'success':
            return True
        else:
            return False
    def logout(self):
        if not self.sock:
            return
        try:
            send_json(self.sock, {'command': 'logout'})
            # 登出後不需要等待伺服器回應
        except Exception as e:
            print(f"登出時發生錯誤: {e}")
    def get_game_list(self):
        send_json(self.sock, {'command': 'get_game_list'})
        res = recv_json(self.sock)
        return res.get('games', []) if res and res.get('status') == 'success' else []

    def create_room(self, game_name):
        send_json(self.sock, {'command': 'create_room', 'username': self.username, 'game_name': game_name})
        res = recv_json(self.sock)
        if res and res.get('status') == 'success':
            return True, res.get('room_id')
        else:
            return False, res.get('message') if res else 'No response'

    def list_rooms(self):
        send_json(self.sock, {'command': 'list_rooms'})
        res = recv_json(self.sock)
        return res.get('rooms', []) if res and res.get('status') == 'success' else []

    def launch_game_client(self, game_name, ip, port):
        config_path = os.path.join(DOWNLOAD_BASE, game_name, 'game_config.json')
        with open(config_path) as f:
            cfg = json.load(f)
        client_script = os.path.join(DOWNLOAD_BASE, game_name, cfg.get('client_exe_file', 'client.py'))
        run_cmd = cfg.get('run_cmd', 'python')
        subprocess.Popen([run_cmd, client_script, ip, str(port)])

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None
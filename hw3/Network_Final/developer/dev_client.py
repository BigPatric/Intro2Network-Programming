import socket
import os
import zipfile
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.protocol import send_json, recv_json, send_file
from common.ip_port_config import SERVER_IP, SERVER_PORT

class DeveloperClient:
    def __init__(self):
        self.sock = None
        self.username = None

    def connect(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.sock.connect((SERVER_IP, SERVER_PORT))
            return True
        except Exception:
            return False

    def ensure_connection(self):
        try:
            self.sock.sendall(b'')
            return True
        except Exception:
            return self.connect()

    def login(self, username, password):
        if not self.ensure_connection():
            return {'status': 'fail', 'message': '連線失敗'}
        send_json(self.sock, {'command': 'login', 'username': username, 'password': password, 'role': 'developer'})
        res = recv_json(self.sock)
        if res and res.get('status') == 'success':
            self.username = username
        return res

    def register(self, username, password):
        if not self.ensure_connection():
            return {'status': 'fail', 'message': '連線失敗'}
        send_json(self.sock, {'command': 'register', 'username': username, 'password': password, 'role': 'developer'})
        res = recv_json(self.sock)
        return res

    def zip_game(self, folder):
        game_name = os.path.basename(folder)
        zip_name = f"{game_name}.zip"
        with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root_dir, _, files in os.walk(folder):
                for file in files:
                    file_path = os.path.join(root_dir, file)
                    arcname = os.path.relpath(file_path, folder)
                    zipf.write(file_path, arcname)
        return zip_name

    def upload_game(self, folder):
        if not self.ensure_connection():
            return {'status': 'fail', 'message': '連線失敗'}
        if not folder or not os.path.isdir(folder):
            return {'status': 'fail', 'message': '請選擇正確的遊戲資料夾'}
        game_name = os.path.basename(folder)
        zip_name = self.zip_game(folder)
        try:
            send_json(self.sock, {'command': 'upload_game', 'game_name': game_name, 'version': '1.0.0', 'role': 'developer'})
            send_file(self.sock, zip_name)
            res = recv_json(self.sock)
        finally:
            os.remove(zip_name)
        return res

    def get_game_list(self):
        if not self.ensure_connection():
            return None
        send_json(self.sock, {'command': 'get_developer_games', 'username': self.username, 'role': 'developer'})
        res = recv_json(self.sock)
        if res and res.get('status') == 'success':
            return res.get('games')
        return []

    def update_game(self, folder):
        if not self.ensure_connection():
            return {'status': 'fail', 'message': '連線失敗'}
        if not folder or not os.path.isdir(folder):
            return {'status': 'fail', 'message': '請選擇正確的遊戲資料夾'}
        game_name = os.path.basename(folder)
        zip_name = self.zip_game(folder)
        try:
            send_json(self.sock, {'command': 'update_game', 'game_name': game_name, 'version': '1.0.1', 'role': 'developer'})
            send_file(self.sock, zip_name)
            res = recv_json(self.sock)
        finally:
            os.remove(zip_name)
        return res

    def logout(self):
        if self.username and self.ensure_connection():
            try:
                send_json(self.sock, {'command': 'logout', 'role': 'developer'})
            except Exception:
                pass
        self.username = None

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
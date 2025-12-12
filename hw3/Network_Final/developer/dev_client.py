# developer/dev_client.py
import socket
import sys
import os
import shutil
import zipfile

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.protocol import send_json, recv_json, send_file
from common.ip_port_config import SERVER_IP, SERVER_PORT

class DeveloperClient:
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

    def login(self):
        while True:
            print("=== Developer 登入/註冊 ===")
            print("1. Login")
            print("2. Register")
            print("3. Exit")
            op = input("Select: ")
            if op in ['1', '2']:
                u = input("Username: ")
                p = input("Password: ")
                if u and p:
                    cmd = 'login' if op == '1' else 'register'
                    send_json(self.sock, {'command': cmd, 'username': u, 'password': p, 'role': 'developer'})
                    res = recv_json(self.sock)
                    if res and res.get('status') == 'success':
                        self.username = u
                        print(f"Welcome, {u}!")
                        return True
                    else:
                        print(f"Failed: {res.get('message') if res else 'No response'}")
                        continue
            elif op == '3':
                return False
            else:
                print("Invalid input, try again.")

    def zip_game(self, game_path, output_filename):
        """將遊戲資料夾壓縮成 zip"""
        with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(game_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # 保留相對路徑
                    arcname = os.path.relpath(file_path, os.path.dirname(game_path))
                    zipf.write(file_path, arcname)

    def upload_game(self):
        game_name = input("Enter game name (folder name in games/): ")
        game_path = os.path.join('developer/games', game_name)
        
        if not os.path.exists(game_path):
            print("Game folder not found!")
            return

        # 1. 壓縮遊戲
        zip_name = f"{game_name}.zip"
        self.zip_game(game_path, zip_name)
        
        # 2. 發送上傳請求
        req = {
            'command': 'upload_game',
            'game_name': game_name,
            'version': '1.0.0' # 可以從 config 讀取
        }
        send_json(self.sock, req)
        
        # 3. 發送檔案
        print("Uploading file...")
        send_file(self.sock, zip_name)
        
        # 4. 接收結果
        res = recv_json(self.sock)
        print("Server response:", res)
        
        # 清理暫存 zip
        os.remove(zip_name)

    def run(self):
        if not self.connect():
            print("Goodbye!")
            return
        if not self.login():
            print("Goodbye!")
            return
        while True:
            print("\n=== Developer Menu ===")
            print("1. Upload Game")
            print("2. Exit")
            choice = input("Select: ")
            if choice == '1':
                self.upload_game()
            elif choice == '2':
                print("Exiting...")
                break

        self.sock.close()

if __name__ == '__main__':
    client = DeveloperClient()
    client.run()
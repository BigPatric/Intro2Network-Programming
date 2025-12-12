import socket
import json
import os
import sys
import zipfile
import subprocess
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.protocol import send_json, recv_json, recv_file

SERVER_IP = '127.0.0.1'
PORT = 8888
PLAYER_ID = "Player1" # 預設，登入後會改
DOWNLOAD_BASE = f'player/downloads'

class LobbyClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.username = None
        self.current_room = None

    def connect(self):
        try:
            self.sock.connect((SERVER_IP, PORT))
            return True
        except:
            print("Cannot connect to server.")
            return False

    def login(self):
        print("=== 登入/註冊 ===")
        print("1. Login")
        print("2. Register")
        op = input("Select: ")
        u = input("Username: ")
        p = input("Password: ")
        
        cmd = 'login' if op == '1' else 'register'
        send_json(self.sock, {'command': cmd, 'username': u, 'password': p, 'role': 'player'})
        res = recv_json(self.sock)
        
        if res['status'] == 'success':
            self.username = u
            global PLAYER_ID, DOWNLOAD_BASE
            PLAYER_ID = u
            DOWNLOAD_BASE = f'player/downloads/{PLAYER_ID}'
            if not os.path.exists(DOWNLOAD_BASE): os.makedirs(DOWNLOAD_BASE)
            print(f"Welcome, {u}!")
            return True
        else:
            print(f"Login failed: {res.get('message')}")
            return False

    def download_game(self, game_name):
        # [Use Case P2]
        print(f"Requesting download for {game_name}...")
        send_json(self.sock, {'command': 'download_game', 'game_name': game_name})
        
        res = recv_json(self.sock)
        if res.get('status') == 'ready_to_send':
            zip_path = os.path.join(DOWNLOAD_BASE, f"{game_name}.zip")
            if recv_file(self.sock, zip_path):
                print("Download complete. Unzipping...")
                extract_path = os.path.join(DOWNLOAD_BASE, game_name)
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_path)
                print("Game installed.")
                os.remove(zip_path) # 清理 zip
            else:
                print("Download failed.")
        else:
            print(f"Server error: {res.get('message')}")

    def enter_lobby(self):
        while True:
            print(f"\n=== LOBBY ({self.username}) ===")
            print("1. List Games (Shop)")
            print("2. My Downloaded Games")
            print("3. Create Room")
            print("4. Join Room")
            print("5. Exit")
            
            choice = input("Select: ")
            
            if choice == '1':
                send_json(self.sock, {'command': 'get_game_list'})
                res = recv_json(self.sock)
                for g in res['games']:
                    print(f"- {g['game_name']} (v{g['version']})")
                
                opt = input("Download a game? (Enter name or Enter to skip): ")
                if opt: self.download_game(opt)

            elif choice == '3':
                g_name = input("Game name to play: ")
                # 檢查本地是否有遊戲
                if not os.path.exists(os.path.join(DOWNLOAD_BASE, g_name)):
                    print("Game not downloaded! Go to shop first.")
                    continue
                
                send_json(self.sock, {'command': 'create_room', 'username': self.username, 'game_name': g_name})
                res = recv_json(self.sock)
                if res['status'] == 'success':
                    self.room_wait_loop(res['room_id'], g_name, is_host=True)

            elif choice == '4':
                send_json(self.sock, {'command': 'list_rooms'})
                res = recv_json(self.sock)
                print(res['rooms'])
                rid = input("Room ID to join: ")
                send_json(self.sock, {'command': 'join_room', 'username': self.username, 'room_id': rid})
                res = recv_json(self.sock)
                if res['status'] == 'success':
                    # 假設 Join 的人不知道遊戲名，實務上 Server Join 回應要帶遊戲名
                    # 這裡簡化，假設 Join 成功就等待開始
                    print("Joined! Waiting for host to start...")
                    # 這裡需要一個 loop 輪詢房間狀態，為了簡化省略
            
            elif choice == '5':
                break

    def room_wait_loop(self, room_id, game_name, is_host):
        print(f"In Room {room_id}. Waiting for players...")
        while True:
            if is_host:
                cmd = input("Type 'start' to play, 'exit' to leave: ")
                if cmd == 'start':
                    send_json(self.sock, {'command': 'start_game', 'room_id': room_id})
                    res = recv_json(self.sock)
                    
                    if res.get('status') == 'game_started':
                        # [Use Case P3] 啟動本地 Game Client
                        self.launch_game_client(game_name, res['server_ip'], res['server_port'])
                        break
            else:
                # 一般玩家的輪詢邏輯 (Polling)
                time.sleep(1)
                # 實作上應該發送 'check_room_status' 請求
                pass

    def launch_game_client(self, game_name, ip, port):
        # 讀取 config
        config_path = os.path.join(DOWNLOAD_BASE, game_name, 'game_config.json')
        with open(config_path) as f:
            cfg = json.load(f)
        
        client_script = os.path.join(DOWNLOAD_BASE, game_name, cfg['client_exe_file'])
        run_cmd = cfg['run_cmd'] # python
        
        print(f"Launching Client connecting to {ip}:{port}")
        subprocess.Popen([run_cmd, client_script, ip, str(port)])

if __name__ == '__main__':
    client = LobbyClient()
    if client.connect():
        if client.login():
            client.enter_lobby()
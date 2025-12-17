import os
import sys
from common.protocol import send_json, send_file
from common.ip_port_config import SERVER_IP, SERVER_PORT
import time
import string
import random
import json
import subprocess
import socket

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
UPLOADED_GAMES_DIR = os.path.join(os.path.dirname(__file__), 'uploaded_games')

class LobbyService:
    def __init__(self, db_manager, conn_manager):
        self.db_manager = db_manager
        self.conn_manager = conn_manager
        self.game_rooms = {} # room_name: {host: str, players: [str], game: str}
        self.current_room_id = None

    def handle_request(self, conn, data):
        command = data.get('command')

        # 登入和註冊是特例
        if command == 'login':
            self.login(conn, data)
            return
        elif command == 'register':
            self.register(conn, data)
            return

        # 其他指令需要先確認使用者已登入
        username = self.conn_manager.get_username(conn)
        if not username:
            send_json(conn, {'status': 'fail', 'message': '未經授權的操作，請先登入'})
            return
        if command == 'get_online_players':
            self.get_online_players(conn)
        elif command == 'get_game_rooms':
            self.get_game_rooms(conn)
        elif command == 'create_room':
            self.create_room(conn, data, username)
        elif command == 'logout':
            username = self.conn_manager.get_username(conn)
            self.conn_manager.remove_connection(conn)
            if username:
                try:
                    self.db_manager.remove_online_user(username)
                except Exception as e:
                    print(f"[DEBUG] remove_online_user on logout error: {e}")
                    # 登出後不需要回傳，客戶端會自行處理介面切換
        elif command == 'list_rooms':
            self.list_rooms(conn)
        elif command == 'join_room':
            self.join_room(conn, data, username)
        elif command == 'get_game_list':
            self.get_game_list(conn)
        elif command == 'download_game':
            self.download_game(conn, data)
        elif command == 'start_game':
            self.start_game(conn, data, username)
        else:
            send_json(conn, {'status': 'fail', 'message': f'未知的大廳指令: {command}'})

    def login(self, conn, data):
        username = data.get('username')
        password = data.get('password')
        user = self.db_manager.login_user(username, password, 'player')
        if user:
            if not self.conn_manager.add_connection(conn, username):
                send_json(conn, {'status': 'fail', 'message': '此帳號已在其他地方登入'})
                return
            send_json(conn, {'status': 'success', 'message': '玩家登入成功'})
        else:
            send_json(conn, {'status': 'fail', 'message': '帳號或密碼錯誤'})

    def logout(self, conn):
        self.conn_manager.remove_connection(conn)
        send_json(conn, {'status': 'success', 'message': '已成功登出'})
        
    def register(self, conn, data):
        username = data.get('username')
        password = data.get('password')
        success = self.db_manager.register_user(username, password, 'player')
        if success:
            send_json(conn, {'status': 'success', 'message': '玩家註冊成功'})
        else:
            send_json(conn, {'status': 'fail', 'message': '註冊失敗，帳號可能已存在'})

    def get_online_players(self, conn):
        try:
            players = self.db_manager.get_online_users()
        except Exception as e:
            print(f"無法取得線上玩家: {e}")
            players = []
        send_json(conn, {'status': 'success', 'players': players})
        print("sent all online players")
        
    def create_room(self, conn, data, username):
        game_name = data.get('game_name')
        room_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        while room_id in self.game_rooms:
            room_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self.game_rooms[room_id] = {
            'host': username,
            'players': [username],
            'game': game_name
        }
        send_json(conn, {'status': 'success', 'room_id': room_id, 'message': f'房間 {room_id} 建立成功'})
        
    def list_rooms(self, conn):
        rooms = []
        for room_id, details in self.game_rooms.items():
            rooms.append({
                'room_id': room_id,
                'host': details['host'],
                'game': details['game'],
                'player_count': len(details['players'])
            })
        send_json(conn, {'status': 'success', 'rooms': rooms})
    
    def join_room(self, conn, data, username):
        room_id = data.get('room_id')
        if not room_id or room_id not in self.game_rooms:
            send_json(conn, {'status': 'fail', 'message': '房間不存在'})
            return
        if username in self.game_rooms[room_id]['players']:
            send_json(conn, {'status': 'fail', 'message': '你已在房間內'})
            return
        self.game_rooms[room_id]['players'].append(username)
        send_json(conn, {'status': 'success', 'message': f'已加入房間 {room_id}'})
        
    def get_game_list(self, conn):
        try:
            games = []
            extracted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploaded_games_extracted'))
            for game_name in os.listdir(extracted_dir):
                game_dir = os.path.join(extracted_dir, game_name)
                if not os.path.isdir(game_dir):
                    continue
                # read config.json
                config_path = os.path.join(game_dir, 'config.json')
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                    # 補充必要欄位
                    info.setdefault('game_name', game_name)
                    info.setdefault('maker', '')
                    info.setdefault('version', '')
                    info.setdefault('description', '')
                    games.append(info)
                else:
                    # 沒有 config 則只顯示名稱
                    games.append({"game_name": game_name, "maker": "", "version": "", "description": ""})
            send_json(conn, {'status': 'success', 'games': games})
        except Exception as e:
            print(f"無法取得遊戲列表: {e}")
            send_json(conn, {'status': 'fail', 'message': '無法取得遊戲列表'})
    def download_game(self, conn, data):
        game_name = data.get('game_name')
        client_py_path = os.path.join("server/uploaded_games_extracted", game_name, "client.py")
        if not os.path.exists(client_py_path):
            send_json(conn, {'status': 'fail', 'message': '遊戲檔案不存在'})
            return
        send_json(conn, {'status': 'ready'})
        send_file(conn, client_py_path)
    def start_game(self, conn, data, username):
        room_id = data.get('room_id')
        if not room_id or room_id not in self.game_rooms:
            send_json(conn, {'status': 'fail', 'message': '房間不存在'})
            return
        room = self.game_rooms[room_id]
        if username != room['host']:
            send_json(conn, {'status': 'fail', 'message': '只有房主可以啟動遊戲'})
            return
        # 動態分配一個可用 port
        s = socket.socket()
        s.bind(('', 0))
        port = s.getsockname()[1]
        s.close()

        # 啟動遊戲伺服器進程
        game_dir = os.path.abspath(f"server/uploaded_games_extracted/{room['game']}")
        server_py = os.path.join(game_dir, "game_server.py")
        subprocess.Popen(['python3', server_py, str(port)], cwd=game_dir)

        # 通知所有房內玩家
        for player in room['players']:
            sock = self.conn_manager.user_to_sock.get(player)
            if sock:
                send_json(sock, {
                    'status': 'start_game',
                    'game_name': room['game'],
                    'ip': SERVER_IP,
                    'port': port
                })
            print(f"Notified player {player} to start game {room['game']} at {SERVER_IP}:{port}")
        send_json(conn, {'status': 'success', 'message': '遊戲已啟動'})
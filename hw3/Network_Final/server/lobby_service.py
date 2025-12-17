import os
import sys
from common.protocol import send_json
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class LobbyService:
    def __init__(self, db_manager, conn_manager):
        self.db_manager = db_manager
        self.conn_manager = conn_manager
        self.game_rooms = {} # room_name: {host: str, players: [str], game: str}

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

    def get_game_rooms(self, conn):
        # 簡化回傳的房間資訊
        room_info = {name: {'host': details['host'], 'game': details['game'], 'player_count': len(details['players'])} 
                     for name, details in self.game_rooms.items()}
        send_json(conn, {'status': 'success', 'rooms': room_info})

    def create_room(self, conn, data, username):
        room_name = data.get('room_name')
        game_name = data.get('game_name')
        if not room_name or not game_name:
            send_json(conn, {'status': 'fail', 'message': '缺少房間名稱或遊戲名稱'})
            return
        
        if room_name in self.game_rooms:
            send_json(conn, {'status': 'fail', 'message': '房間名稱已被使用'})
            return

        self.game_rooms[room_name] = {
            'host': username,
            'players': [username],
            'game': game_name
        }
        send_json(conn, {'status': 'success', 'message': f'房間 {room_name} 建立成功'})
        print(f"玩家 {username} 建立了房間 {room_name} 來玩 {game_name}")

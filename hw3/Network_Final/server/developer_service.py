import os
import sys
from common.protocol import send_json, recv_file

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

UPLOADED_GAMES_DIR = os.path.abspath("server/uploaded_games")
EXTRACTED_GAMES_DIR = os.path.abspath("server/uploaded_games_extracted")

class DeveloperService:
    def __init__(self, db_manager, conn_manager):
        self.db_manager = db_manager
        self.conn_manager = conn_manager
        if not os.path.exists(UPLOADED_GAMES_DIR):
            os.makedirs(UPLOADED_GAMES_DIR)
        if not os.path.exists(EXTRACTED_GAMES_DIR):
            os.makedirs(EXTRACTED_GAMES_DIR)

    def handle_request(self, conn, data):
        command = data.get('command')
        
        # 登入和註冊是特例，不需要預先驗證 username
        if command == 'login':
            self.login(conn, data)
        elif command == 'register':
            self.register(conn, data)
        else:
            # 其他指令需要先確認使用者已登入
            username = self.conn_manager.get_username(conn)
            if not username:
                send_json(conn, {'status': 'fail', 'message': '未經授權的操作，請先登入'})
                return

            if command == 'upload_game':
                self.upload_game(conn, data, username)
            else:
                send_json(conn, {'status': 'fail', 'message': f'未知的開發者指令: {command}'})

    def login(self, conn, data):
        username = data.get('username')
        password = data.get('password')
        user = self.db_manager.login_user(username, password, 'developer')
        if user:
            self.conn_manager.add_connection(conn, username)
            send_json(conn, {'status': 'success', 'message': '開發者登入成功'})
        else:
            send_json(conn, {'status': 'fail', 'message': '帳號或密碼錯誤'})

    def register(self, conn, data):
        username = data.get('username')
        password = data.get('password')
        success = self.db_manager.register_user(username, password, 'developer')
        if success:
            send_json(conn, {'status': 'success', 'message': '開發者註冊成功'})
        else:
            send_json(conn, {'status': 'fail', 'message': '註冊失敗，帳號可能已存在'})

    def upload_game(self, conn, data, developer_name):
        game_name = data.get('game_name')
        version = data.get('version')
        
        if not game_name or not version:
            send_json(conn, {'status': 'fail', 'message': '缺少遊戲名稱或版本資訊'})
            return

        zip_path = os.path.join(UPLOADED_GAMES_DIR, f"{game_name}.zip")
        
        try:
            recv_file(conn, zip_path)
            # 在此處可以加入解壓縮和驗證遊戲檔案的邏輯
            
            # 將遊戲資訊存入資料庫
            self.db_manager.add_game(game_name, developer_name, f"server/uploaded_games/{game_name}", version)
            
            send_json(conn, {'status': 'success', 'message': f'遊戲 {game_name} 上傳成功'})
        except Exception as e:
            print(f"上傳遊戲失敗: {e}")
            send_json(conn, {'status': 'fail', 'message': f'檔案接收或處理失敗: {e}'})

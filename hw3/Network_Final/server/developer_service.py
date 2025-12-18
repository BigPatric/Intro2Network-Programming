import os
import sys
import zipfile
import json
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
            elif command == 'update_game':
                self.update_game(conn, data, username)
            elif command == 'get_game_list':
                self.get_game_list(conn)
            else:
                send_json(conn, {'status': 'fail', 'message': f'未知的開發者指令: {command}'})

    def get_game_list(self, conn):
        try:
            games = []
            extracted_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'uploaded_games_extracted'))
            for game_name in os.listdir(extracted_dir):
                game_dir = os.path.join(extracted_dir, game_name)
                if not os.path.isdir(game_dir):
                    continue
                config_path = os.path.join(game_dir, 'config.json')
                if os.path.exists(config_path):
                    with open(config_path, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                    info.setdefault('game_name', game_name)
                    info.setdefault('maker', '')
                    info.setdefault('version', '')
                    info.setdefault('description', '')
                    games.append(info)
                else:
                    games.append({"game_name": game_name, "maker": "", "version": "", "description": ""})
            send_json(conn, {'status': 'success', 'games': games})
        except Exception as e:
            print(f"無法取得遊戲列表: {e}")
            send_json(conn, {'status': 'fail', 'message': '無法取得遊戲列表'})

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

    def _process_game_files(self, conn, game_name):
        os.makedirs(UPLOADED_GAMES_DIR, exist_ok=True)
        os.makedirs(EXTRACTED_GAMES_DIR, exist_ok=True)
        zip_path = os.path.join(UPLOADED_GAMES_DIR, f"{game_name}.zip")
        recv_file(conn, zip_path)
        extract_path = os.path.join(EXTRACTED_GAMES_DIR, game_name)
        if os.path.exists(extract_path):
            import shutil
            shutil.rmtree(extract_path)
        os.makedirs(extract_path, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        return extract_path

    def upload_game(self, conn, data, developer_name):
        game_name = data.get('game_name')
        version = data.get('version')
        if not game_name or not version:
            send_json(conn, {'status': 'fail', 'message': '缺少遊戲名稱或版本'})
            return
        
        if self.db_manager.get_game_info(game_name):
            send_json(conn, {'status': 'fail', 'message': '此遊戲已存在，請使用更新功能'})
            return

        extract_path = self._process_game_files(conn, game_name)
        
        if self.db_manager.add_game(game_name, developer_name, version, extract_path):
            send_json(conn, {'status': 'success', 'message': '遊戲上傳成功'})
        else:
            send_json(conn, {'status': 'fail', 'message': '遊戲資訊儲存失敗'})

    def update_game(self, conn, data, developer_name):
        game_name = data.get('game_name')
        version = data.get('version')
        if not game_name or not version:
            send_json(conn, {'status': 'fail', 'message': '缺少遊戲名稱或版本'})
            return

        game_info = self.db_manager.get_game_info(game_name)
        if not game_info:
            send_json(conn, {'status': 'fail', 'message': '找不到此遊戲，請先上傳'})
            return
        
        if game_info['developer_name'] != developer_name:
            send_json(conn, {'status': 'fail', 'message': '您沒有權限更新此遊戲'})
            return

        extract_path = self._process_game_files(conn, game_name)

        if self.db_manager.update_game_version(game_name, version, extract_path):
            send_json(conn, {'status': 'success', 'message': '遊戲更新成功'})
        else:
            send_json(conn, {'status': 'fail', 'message': '遊戲資訊更新失敗'})
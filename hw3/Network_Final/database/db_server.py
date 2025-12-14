import socket
import threading
import sqlite3
import json
import os

class DBServer:
    def __init__(self, host='127.0.0.1', port=9000, db_name='DATABASE.db'):
        self.host = host
        self.port = port
        
        # 1. 取得這支程式 (db_server.py) 所在的資料夾路徑 (即 Network_Final/database/)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 2. 設定 storage 資料夾路徑
        self.storage_dir = os.path.join(base_dir, 'storage')
        
        # 3. 如果 storage 資料夾不存在，自動建立
        if not os.path.exists(self.storage_dir):
            os.makedirs(self.storage_dir)
            print(f"已建立資料庫目錄: {self.storage_dir}")

        # 4. 組合完整的資料庫檔案路徑
        self.db_path = os.path.join(self.storage_dir, db_name)
        
        # 連線資料庫
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self.init_tables()
        print(f"DBServer 啟動於 {self.host}:{self.port}")
        print(f"資料庫位置: {self.db_path}")

    def init_tables(self):
        with self.conn:
            self.conn.execute('''CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
            self.conn.execute('''CREATE TABLE IF NOT EXISTS games (
                name TEXT PRIMARY KEY,
                version TEXT,
                description TEXT,
                exe_file TEXT,
                client_exe_file TEXT,
                run_cmd TEXT,
                developer TEXT,
                reviews TEXT
            )''')
            self.conn.execute('''CREATE TABLE IF NOT EXISTS rooms (
                room_name TEXT,
                host TEXT,
                public INTEGER DEFAULT 1,
                PRIMARY KEY (room_name, host)
            )''')
            self.conn.execute('''CREATE TABLE IF NOT EXISTS online_users (
                username TEXT PRIMARY KEY, login_time TEXT)''')

    def handle_client(self, conn):
        with conn:
            try:
                data = conn.recv(65536)
                if not data:
                    return
                req = json.loads(data.decode())
                action = req.get('action')
                params = req.get('params', {})
                
                if action == 'insert':
                    resp = self.handle_insert(params)
                elif action == 'select':
                    resp = self.handle_select(params)
                elif action == 'update':
                    resp = self.handle_update(params)
                elif action == 'delete':
                    resp = self.handle_delete(params)
                else:
                    resp = {'status': 'fail', 'message': 'Unknown action'}
                
                conn.sendall(json.dumps(resp).encode())
            except Exception as e:
                print(f"處理請求時發生錯誤: {e}")

    def handle_insert(self, params):
        try:
            with self.lock, self.conn:
                self.conn.execute(params['query'], params['args'])
            return {'status': 'ok'}
        except Exception as e:
            return {'status': 'fail', 'message': str(e)}

    def handle_select(self, params):
        try:
            with self.lock:
                cur = self.conn.execute(params['query'], params.get('args', []))
                result = cur.fetchall()
            return {'status': 'ok', 'result': result}
        except Exception as e:
            return {'status': 'fail', 'message': str(e)}

    def handle_update(self, params):
        try:
            with self.lock, self.conn:
                self.conn.execute(params['query'], params['args'])
            return {'status': 'ok'}
        except Exception as e:
            return {'status': 'fail', 'message': str(e)}

    def handle_delete(self, params):
        try:
            with self.lock, self.conn:
                self.conn.execute(params['query'], params['args'])
            return {'status': 'ok'}
        except Exception as e:
            return {'status': 'fail', 'message': str(e)}

    def serve(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # 加入這行避免 Port 被佔用
            s.bind((self.host, self.port))
            s.listen(5)
            print(f"DBServer listening on {self.host}:{self.port}")
            try:
                while True:
                    conn, addr = s.accept()
                    # print(f"DB 連線來自: {addr}")
                    threading.Thread(target=self.handle_client, args=(conn,), daemon=True).start()
            except KeyboardInterrupt:
                print("DBServer 關閉中...")

if __name__ == '__main__':
    DBServer().serve()
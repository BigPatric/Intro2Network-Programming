import socket
import json
import sqlite3
import threading
import os

# 確定資料庫檔案的路徑
DB_FILE = os.path.join(os.path.dirname(__file__), 'storage', 'DATABASE.db')
HOST = '127.0.0.1'
PORT = 9000

def db_init():
    """初始化資料庫和資料表"""
    print(f"正在使用資料庫檔案: {DB_FILE}")
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # 使用者資料表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    ''')
    # 遊戲資料表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS games (
            name TEXT PRIMARY KEY,
            developer TEXT,
            version TEXT,
            description TEXT,
            entry_point TEXT
        )
    ''')
    # 遊戲房間資料表
    cur.execute('''
        CREATE TABLE IF NOT EXISTS rooms (
            name TEXT PRIMARY KEY,
            host TEXT,
            public INTEGER
        )
    ''')
    conn.commit()
    conn.close()
    print("資料庫初始化完成。")

def handle_client_request(conn):
    """處理來自 db_manager 的單一請求"""
    try:
        data = conn.recv(4096)
        if not data:
            return

        request = json.loads(data.decode('utf-8'))
        action = request.get('action')
        params = request.get('params')
        
        print(f"[DB Server] 收到請求: action={action}, params={params}") # 偵錯日誌

        db_conn = sqlite3.connect(DB_FILE)
        cur = db_conn.cursor()
        response = {'status': 'error', 'message': '未知操作'}

        if action in ['insert', 'delete', 'update']:
            try:
                cur.execute(params['query'], params.get('args', []))
                db_conn.commit()
                response = {'status': 'ok'}
            except sqlite3.IntegrityError as e:
                response = {'status': 'error', 'message': f'資料庫完整性錯誤: {e}'}
            except Exception as e:
                response = {'status': 'error', 'message': str(e)}

        elif action == 'select':
            try:
                cur.execute(params['query'], params.get('args', []))
                result = cur.fetchall()
                response = {'status': 'ok', 'result': result}
                print(f"[DB Server] 查詢成功，結果: {result}") # 偵錯日誌
            except Exception as e:
                response = {'status': 'error', 'message': str(e)}
        
        conn.sendall(json.dumps(response).encode('utf-8'))

    except json.JSONDecodeError:
        print("[DB Server] 錯誤: 無法解析收到的 JSON 資料")
    except Exception as e:
        print(f"[DB Server] 處理請求時發生錯誤: {e}")
    finally:
        conn.close()

def main():
    """主函式，啟動資料庫伺服器"""
    db_init()
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    print(f"資料庫伺服器正在監聽 {HOST}:{PORT}")

    while True:
        conn, addr = server_socket.accept()
        # 為每個請求建立一個新執行緒
        thread = threading.Thread(target=handle_client_request, args=(conn,), daemon=True)
        thread.start()

if __name__ == '__main__':
    main()
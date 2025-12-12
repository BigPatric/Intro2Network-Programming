import sqlite3
import os

DB_PATH = 'server/users.db'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # 使用者資料表
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (username TEXT PRIMARY KEY, password TEXT, role TEXT)''')
    # 遊戲資料表
    c.execute('''CREATE TABLE IF NOT EXISTS games
                 (name TEXT PRIMARY KEY, version TEXT, description TEXT, 
                  exe_file TEXT, client_exe_file TEXT, run_cmd TEXT)''')
    conn.commit()
    conn.close()

def register_user(username, password, role='player'):
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO users VALUES (?, ?, ?)", (username, password, role))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def login_user(username, password, role=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if role:
        c.execute("SELECT role FROM users WHERE username=? AND password=? AND role=?", (username, password, role))
    else:
        c.execute("SELECT role FROM users WHERE username=? AND password=?", (username, password))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def add_game_metadata(info):
    """更新或新增遊戲資訊"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO games 
                 (name, version, description, exe_file, client_exe_file, run_cmd)
                 VALUES (?, ?, ?, ?, ?, ?)''', 
                 (info['game_name'], info['version'], info.get('description', ''),
                  info.get('server_exe', 'server.py'), 
                  info.get('client_exe', 'client.py'),
                  info.get('run_cmd', 'python')))
    conn.commit()
    conn.close()

def get_all_games():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM games")
    rows = c.fetchall()
    conn.close()
    # 轉換成 List of Dict
    games = []
    for r in rows:
        games.append({
            "game_name": r[0], "version": r[1], "description": r[2],
            "server_exe": r[3], "client_exe": r[4], "run_cmd": r[5]
        })
    return games
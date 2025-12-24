import sqlite3
import os

# 取得與 db_server.py 相同的資料庫路徑
DB_FILE = os.path.join(os.path.dirname(__file__), 'storage', 'DATABASE.db')

# 要注入的使用者資料（範例）
users = [
    ('deva', 'aaaaaa', 'developer'),
    ('playera', 'aaaaaa', 'player'),
    ('playerb', 'bbbbbb', 'player')
]

def reset_users():
    print(f"正在操作資料庫檔案: {DB_FILE}")
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()
    # 清空 users 資料表
    cur.execute("DELETE FROM users;")
    cur.execute("DELETE FROM games;")
    cur.execute("DELETE FROM rooms;")
    # 插入新使用者
    cur.executemany("INSERT INTO users (username, password, role) VALUES (?, ?, ?);", users)
    conn.commit()
    conn.close()
    print("已清空 users 並注入新資料。")

if __name__ == '__main__':
    reset_users()
import os
import sqlite3
from db_manager import init_db, register_user

DB_PATH = 'server/users.db'

def clear_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Database cleared.")
    else:
        print("No database found to clear.")

def initialize_db():
    init_db()
    print("Database initialized.")
    users = [
        ('deva', 'aaaa', 'developer'),
        ('devb', 'bbbb', 'developer'),
        ('playera', 'aaaaa', 'player'),
        ('playerb', 'bbbbb', 'player'),
    ]
    for u, p, r in users:
        if register_user(u, p, r):
            print(f"Registered user: {u} with role: {r}")
        else:
            print(f"User {u} already exists.")

if __name__ == "__main__":
    print("正在清空資料庫...")
    clear_db()
    print("正在初始化資料庫...")
    initialize_db()
    print("資料庫初始化完成。")
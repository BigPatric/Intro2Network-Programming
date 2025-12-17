"""
db_manager.py
資料庫管理 (SQLite)
"""
import socket
import json

DB_SERVER_HOST = '127.0.0.1'
DB_SERVER_PORT = 9000
    

def db_request(action, params=None):
    params = params or {}
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((DB_SERVER_HOST, DB_SERVER_PORT))
        s.sendall(json.dumps({'action': action, 'params': params}).encode())
        data = s.recv(65536)
        resp = json.loads(data.decode())
        return resp

def _register_user(username, password, role='player'):
    resp = db_request('insert', {
        'query': "INSERT INTO users VALUES (?, ?, ?)",
        'args': [username, password, role]
    })
    if resp['status'] == 'ok':
        return True
    elif 'UNIQUE constraint failed' in resp.get('message', ''):
        return False
    else:
        return False

def _login_user(username, password, role):
    if role == 'developer':
        query = "SELECT role FROM users WHERE username=? AND password=? AND role='developer'"
    else:
        query = "SELECT role FROM users WHERE username=? AND password=? AND role='player'"
    resp = db_request('select', {
        'query': query,
        'args': [username, password]
    })
    if resp['status'] == 'ok' and resp['result']:
        return resp['result'][0][0]
    return None

def _add_game_metadata(info):
    resp = db_request('insert', {
        'query': '''INSERT OR REPLACE INTO games \
                 (name, version, description, exe_file, client_exe_file, run_cmd)\
                 VALUES (?, ?, ?, ?, ?, ?)''',
        'args': [
            info['game_name'], info['version'], info.get('description', ''),
            info.get('server_exe', 'server.py'),
            info.get('client_exe', 'client.py'),
            info.get('run_cmd', 'python')
        ]
    })
    return resp['status'] == 'ok'

def _get_all_games():
    resp = db_request('select', {
        'query': "SELECT * FROM games"
    })
    games = []
    if resp['status'] == 'ok' and resp['result']:
        for r in resp['result']:
            games.append({
                "game_name": r[0], "version": r[1], "description": r[2],
                "server_exe": r[3], "client_exe": r[4], "run_cmd": r[5]
            })
    return games

def _add_room(room_name, host, public=1):
    resp = db_request('insert', {
        'query': "INSERT INTO rooms (room_name, host, public) VALUES (?, ?, ?)",
        'args': [room_name, host, public]
    })
    return resp['status'] == 'ok'

def _get_all_rooms():
    resp = db_request('select', {
        'query': "SELECT room_name, host, public FROM rooms"
    })
    rooms = []
    if resp['status'] == 'ok' and resp['result']:
        for r in resp['result']:
            rooms.append({
                "room_name": r[0], "host": r[1], "public": bool(r[2])
            })
    return rooms

def _add_online_user(username, login_time):
    resp = db_request('insert', {
        'query': "INSERT OR REPLACE INTO online_users VALUES (?, ?)",
        'args': [username, login_time]
    })
    return resp['status'] == 'ok'

def _remove_online_user(username):
    resp = db_request('delete', {
        'query': "DELETE FROM online_users WHERE username=?",
        'args': [username]
    })
    return resp['status'] == 'ok'

def _get_online_users():
    resp = db_request('select', {
        'query': "SELECT username FROM online_users"
    })
    if resp and resp.get('status') == 'ok' and resp.get('result') is not None:
        return [row[0] for row in resp['result']]
    return []

class DatabaseManager:
    def register_user(self, username, password, role='player'):
        return _register_user(username, password, role)

    def login_user(self, username, password, role):
        return _login_user(username, password, role)

    def add_game_metadata(self, info):
        return _add_game_metadata(info)
    
    def get_all_games(self):
        return _get_all_games()
    
    def add_room(self, room_name, host, public=1):
        return _add_room(room_name, host, public)
    
    def get_all_rooms(self):
        return _get_all_rooms()
    
    def add_online_user(self, username, login_time):
        return _add_online_user(username, login_time)
    
    def remove_online_user(self, username):
        return _remove_online_user(username)
    
    def get_online_users(self):
        return _get_online_users()
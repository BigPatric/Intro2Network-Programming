import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import socket, threading, subprocess, random
import hashlib, os, binascii
from common.protocol import send_msg, recv_msg
from lobby_server.db_client import DBClient
from lobby_server.room_manager import RoomManager
try:
    from config import LOBBY_HOST, LOBBY_PORT, GAME_PORT_MIN, GAME_PORT_MAX
except Exception:
    # fallback defaults if config import fails
    LOBBY_HOST, LOBBY_PORT = '127.0.0.1', 10000
    GAME_PORT_MIN, GAME_PORT_MAX = 10002, 20000

PORT_MIN = GAME_PORT_MIN
PORT_MAX = GAME_PORT_MAX

class LobbyServer:
    def __init__(self, host=LOBBY_HOST, port=LOBBY_PORT):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen()
        print(f"[Lobby] Running on {port}")
        self.db = DBClient()
        self.rooms = RoomManager()
        # self.clients: username -> connection
        self.clients = {}
        self.active_game_procs = {}
        self.game_servers = {}
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # --- Password utilities (PBKDF2-HMAC-SHA256) ---
    def _hash_password(self, password: str, salt: bytes = None):
        if salt is None:
            salt = os.urandom(16)
        # 100k iterations; returns hex strings for storage
        dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
        return binascii.hexlify(salt).decode('ascii'), binascii.hexlify(dk).decode('ascii')

    def _verify_password(self, password: str, salt_hex: str, hash_hex: str) -> bool:
        try:
            salt = binascii.unhexlify(salt_hex.encode('ascii'))
            expected = binascii.unhexlify(hash_hex.encode('ascii'))
            cand = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100_000)
            # constant-time compare
            return hashlib.sha256(cand).digest() == hashlib.sha256(expected).digest()
        except Exception:
            return False

    def _pick_port(self):
        # naive random pick, ensure not used
        for _ in range(50):
            p = random.randint(PORT_MIN, PORT_MAX)
            if p not in self.active_game_procs:
                return p
        raise RuntimeError('no free port')

    def _launch_game_server(self, room_id, port):
        # Launch local game server as a subprocess. Assumes game_server/game_server.py exists.
        # On course machines, ensure python path and working dir are correct.
        try:
            cmd = ['python3', '-m', 'game_server.game_server', str(port)]
            self.game_servers[room_id] = subprocess.Popen(cmd, cwd=self.project_root)
            return self.game_servers[room_id]
        except Exception as e:
            print(f"[Lobby] Failed to launch game server: {e}")
            raise

    def handle_client(self, conn, addr):
        print(f"[Lobby] Connected: {addr}")
        user = None
        try:
            while True:
                msg = recv_msg(conn)
                if msg is None:
                    break
                action = msg.get('action')
                data = msg.get('data', {})

                if action == 'register':
                    name = (data.get('name') or '').strip()
                    password = data.get('password') or ''
                    if not name or not password:
                        send_msg(conn, {'error': 'name and password required'})
                        continue
                    # duplicate check
                    exist = self.db.query('User', {'name': name}).get('result', [])
                    if exist:
                        send_msg(conn, {'error': 'user exists'})
                        continue
                    salt_hex, hash_hex = self._hash_password(password)
                    user = {'name': name, 'pw_salt': salt_hex, 'pw_hash': hash_hex}
                    res = self.db.create('User', user)
                    if res.get('status') == 'ok':
                        send_msg(conn, {'status': 'ok'})
                    else:
                        send_msg(conn, {'error': 'db error'})

                elif action == 'login':
                    name = (data.get('name') or '').strip()
                    password = data.get('password') or ''
                    # Duplicate login prevention: if user already logged in and different conn
                    if name in self.clients and self.clients[name] is not conn:
                        send_msg(conn, {'error': 'already logged in elsewhere'})
                        continue
                    r = self.db.query('User', {'name': name})
                    rows = r.get('result', [])
                    if rows:
                        user = rows[0]
                        salt_hex = user.get('pw_salt')
                        hash_hex = user.get('pw_hash')
                        if salt_hex and hash_hex:
                            if not password:
                                send_msg(conn, {'error': 'password required'})
                                continue
                            if not self._verify_password(password, salt_hex, hash_hex):
                                send_msg(conn, {'error': 'invalid credential'})
                                continue
                        else:
                            # legacy user without password set: only allow empty password
                            if password:
                                send_msg(conn, {'error': 'password not set; use empty password or re-register'})
                                continue
                        self.clients[user['name']] = conn
                        # 登入時設 is_online 為 True
                        self.db.update('User', 'id', user.get('id'), {'is_online': True})
                        send_msg(conn, {'status': 'ok', 'user': {'name': user['name'], 'id': user.get('id')}})
                    else:
                        send_msg(conn, {'error': 'user not found'})

                elif action == 'list_rooms':
                    db_rooms = self.db.query('Room', {'visibility': 'public'}).get('result', [])
                    mem_rooms = self.rooms.list_public()
                    # 取交集：只顯示同時存在於 DB 及記憶體的房間
                    db_ids = set(r.get('id') for r in db_rooms if r.get('id') is not None)
                    mem_ids = set(r.get('id') for r in mem_rooms if r.get('id') is not None)
                    intersect_ids = db_ids & mem_ids
                    rooms = [r for r in mem_rooms if r.get('id') in intersect_ids]
                    send_msg(conn, {'rooms': rooms})
                elif action == 'list_users':
                    db_res = self.db.query('User', {'is_online': True})
                    users = [u.get('name') for u in db_res.get('result', [])]
                    send_msg(conn, {'users': users})


                elif action == 'create_room':
                    if not user:
                        send_msg(conn, {'error': 'not logged in'})
                        continue
                    room = self.rooms.create(user['name'], name=data.get('name'), visibility=data.get('visibility', 'public'))
                    self.db.create('Room', room)
                    send_msg(conn, {'status': 'ok', 'room': room})

                elif action == 'join_room':
                    rid = data.get('room_id')
                    res = self.rooms.join(rid, user['name'])
                    if res is False:
                        send_msg(conn, {'error': 'room full'})
                    elif res is None:
                        send_msg(conn, {'error': 'no such room'})
                    else:
                        send_msg(conn, {'status': 'ok', 'room': res})

                elif action == 'start_game':
                    rid = data.get('room_id')
                    room = self.rooms.rooms.get(rid)
                    if not room or len(room['players']) < 2:
                        send_msg(conn, {'error': 'need 2 players to start'})
                        continue
                    port = self._pick_port()
                    # Launch game server with port argument
                    proc = self._launch_game_server(rid, port)
                    # update room state and persist
                    room['status'] = 'playing'
                    room['game_port'] = port 
                    self.db.update('Room', 'id', rid, {'status': 'playing', 'game_port': port})
                    send_msg(conn, {'status': 'ok', 'game_port': port})

                else:
                    send_msg(conn, {'error': 'unknown action'})
        except Exception as e:
            print('[Lobby] error', e)
        finally:
            try:
                if user and user.get('name') in self.clients and self.clients[user['name']] is conn:
                    del self.clients[user['name']]
                    # 登出時設 is_online 為 False
                    self.db.update('User', 'id', user.get('id'), {'is_online': False})
            except Exception:
                pass
            conn.close()

    def run(self):
        while True:
            conn, addr = self.server.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()

if __name__ == '__main__':
    LobbyServer().run()
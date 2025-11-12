import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import socket, threading, subprocess, random
from common.protocol import send_msg, recv_msg
from lobby_server.db_client import DBClient
from lobby_server.room_manager import RoomManager

PORT_MIN = 10002
PORT_MAX = 20000

class LobbyServer:
    def __init__(self, host='127.0.0.1', port=10000):
        self.host = host
        self.port = port
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen()
        print(f"[Lobby] Running on {port}")
        self.db = DBClient()
        self.rooms = RoomManager()
        self.clients = {}
        self.active_game_procs = {}
        self.game_servers = {}  # 用來追蹤遊戲伺服器進程
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

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
            cmd = ['uv', 'run', '-m', 'game_server.game_server', str(port)]
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
                    res = self.db.create('User', data)
                    send_msg(conn, res)

                elif action == 'login':
                    r = self.db.query('User', {'name': data.get('name')})
                    rows = r.get('result', [])
                    if rows:
                        user = rows[0]
                        self.clients[user['name']] = conn
                        send_msg(conn, {'status': 'ok', 'user': user})
                    else:
                        send_msg(conn, {'error': 'user not found'})

                elif action == 'list_rooms':
                    send_msg(conn, {'rooms': self.rooms.list_public()})

                elif action == 'create_room':
                    if not user:
                        send_msg(conn, {'error': 'not logged in'})
                        continue
                    room = self.rooms.create(user['name'], name=data.get('name'))
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
                    room['game_port'] = port  # <--- 關鍵：同步更新 RoomManager 內的 room
                    self.db.update('Room', 'id', rid, {'status': 'playing', 'game_port': port})
                    send_msg(conn, {'status': 'ok', 'game_port': port})

                else:
                    send_msg(conn, {'error': 'unknown action'})
        except Exception as e:
            print('[Lobby] error', e)
        finally:
            conn.close()

    def run(self):
        while True:
            conn, addr = self.server.accept()
            threading.Thread(target=self.handle_client, args=(conn, addr), daemon=True).start()

if __name__ == '__main__':
    LobbyServer().run()
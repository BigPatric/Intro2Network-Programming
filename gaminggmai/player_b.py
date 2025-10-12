import socket
import json
import threading
from utils import send_json_tcp, recv_json_tcp
from config import LOBBY_HOST, LOBBY_PORT, UDP_PORT_START, UDP_PORT_END, BUFFER_SIZE
from game_logic import TicTacToe

LOBBY_ADDR = (LOBBY_HOST, LOBBY_PORT)

def lobby_login(sock):
    while True:
        op = input('login or register? (l/r): ').strip().lower()
        username = input('username: ').strip()
        password = input('password: ').strip()
        send_json_tcp(sock, {
            'action': 'register' if op == 'r' else 'login',
            'username': username,
            'password': password
        })
        resp = recv_json_tcp(sock)
        print('→', resp)
        if resp and resp.get('status') == 'OK':
            return username

def start_game_client(ip, port):
    conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conn.connect((ip, port))
    print(f'[B] Connected to game host at {ip}:{port}')

    t = TicTacToe()

    def recv_msg():
        data = b''
        while True:
            chunk = conn.recv(1024)
            if not chunk:
                return None
            data += chunk
            if b'\n' in data:
                msg, _ = data.split(b'\n', 1)
                try:
                    return json.loads(msg.decode())
                except:
                    return None

    send_msg = lambda o: conn.sendall((json.dumps(o)+'\n').encode())

    symbol = 'O'
    names = {}
    opponent_name = ''
    while True:
        msg = recv_msg()
        if not msg:
            print('Connection closed.')
            break
        typ = msg.get('type')
        if typ == 'START':
            symbol = msg.get('symbol')
            names = msg.get('names', {})
            opponent_name = names.get('X', 'Opponent')
            print('Game start. You are O.')
        elif typ == 'MOVE':
            t.make_move(msg['idx'], 'X')
        elif typ == 'END':
            print('Game over! Winner:', msg.get('winner'))
            break

        if t.turn == 'O' and not t.winner:
            print(t.printable())
            # 驗證輸入格式、範圍，以及該位置是否空
            while True:
                move_input = input('Your move (0–8): ').strip()
                try:
                    idx = int(move_input)
                except ValueError:
                    print('Invalid input, enter integer 0–8.')
                    continue
                if idx < 0 or idx > 8:
                    print('Index out of range, enter 0–8.')
                    continue
                # 嘗試在本地下子；如果失敗（已被佔用或非法），提醒重試
                if not t.make_move(idx, 'O'):
                    print('Invalid move (occupied or illegal), retry.')
                    continue
                # 成功下子後送出
                send_msg({'type': 'MOVE', 'idx': idx})
                # 下棋後秀出當前板子並等待對手
                print(t.printable())
                print(f"waiting for opponent ({opponent_name})")
                break

    conn.close()

def udp_listener(username, listen_port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', listen_port))
    print(f'[B] Waiting for invites on UDP {listen_port}')

    while True:
        data, addr = s.recvfrom(BUFFER_SIZE)
        try:
            obj = json.loads(data.decode())
        except Exception:
            if data == b'PING':
                s.sendto(json.dumps({'status': 'WAITING', 'username': username}).encode(), addr)
            continue

        if obj.get('type') == 'INVITE':
            print(f"Invite from {obj.get('from')} at {addr}")
            ans = input('Accept? (y/n): ').strip().lower()
            if ans == 'y':
                s.sendto(json.dumps({'type': 'ACCEPT', 'from': username}).encode(), addr)
            else:
                s.sendto(json.dumps({'type': 'DECLINE', 'from': username}).encode(), addr)
        elif obj.get('type') == 'TCP_INFO':
            ip, port = obj.get('ip'), obj.get('port')
            print(f'Received TCP info {ip}:{port}')
            s.close()
            start_game_client(ip, port)
            break

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(LOBBY_ADDR)
    username = lobby_login(sock)

    port = int(input(f'Choose UDP port ({UDP_PORT_START}-{UDP_PORT_END}): '))
    udp_listener(username, port)
    sock.close()
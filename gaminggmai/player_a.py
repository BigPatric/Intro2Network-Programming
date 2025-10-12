import socket
import json
import threading
import random
import time
from utils import send_json_tcp, recv_json_tcp
from config import LOBBY_HOST, LOBBY_PORT, UDP_PORT_START, UDP_PORT_END, BUFFER_SIZE, CSIT_SERVERS
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

def scan_for_players(scan_range=None, timeout=0.3):
    if scan_range is None:
        scan_range = range(UDP_PORT_START, UDP_PORT_END + 1)
    found = []
    for host in CSIT_SERVERS:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(timeout)
        for port in scan_range:
            try:
                s.sendto(b'PING', (host, port))
                data, addr = s.recvfrom(BUFFER_SIZE)
                info = json.loads(data.decode())
                if info.get('status') == 'WAITING':
                    found.append((addr[0], addr[1], info.get('username')))
            except socket.timeout:
                continue
            except Exception:
                continue
        s.close()
    return found

def send_invite(target_ip, target_port, myname):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(5)
    packet = json.dumps({'type': 'INVITE', 'from': myname})
    s.sendto(packet.encode(), (target_ip, target_port))
    try:
        data, addr = s.recvfrom(BUFFER_SIZE)
        obj = json.loads(data.decode())
        return obj
    except Exception:
        return None
    finally:
        s.close()

def start_game_server(username, port):
    t = TicTacToe()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', port))
    s.listen(1)
    print(f"[A] TCP game server on port {port}")
    return s, t

if __name__ == '__main__':
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(LOBBY_ADDR)
    username = lobby_login(sock)

    print('\nScanning CSIT servers for Player B...')
    found = scan_for_players()
    if not found:
        print('No players found. Make sure Player B is running.')
        exit()

    for i, (ip, port, name) in enumerate(found):
        print(f'[{i}] {name}@{ip}:{port}')
    idx = int(input('Choose player to invite: '))
    ip, port, bname = found[idx]

    resp = send_invite(ip, port, username)
    if resp and resp.get('type') == 'ACCEPT':
        print(f'{bname} accepted! Starting TCP server...')
        tcp_port = random.randint(10001, 20000)
        s, t = start_game_server(username, tcp_port)

        # 先發送 TCP_INFO
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        msg = json.dumps({'type': 'TCP_INFO', 'ip': '127.0.0.1', 'port': tcp_port})
        udp.sendto(msg.encode(), (ip, port))
        udp.close()

        # 再等待 Player B 連線
        conn, addr = s.accept()
        print('[A] Player B connected from', addr)

        send_msg = lambda o: conn.sendall((json.dumps(o)+'\n').encode())

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

        send_msg({'type': 'START', 'symbol': 'X'})
        print('You are X (start first). Index 0–8.')

        while True:
            print(t.printable())
            if t.turn == 'X' and t.winner is None:
                idx = int(input('Your move (0–8): '))
                if not t.make_move(idx, 'X'):
                    print('Invalid move, retry.')
                    continue
                send_msg({'type': 'MOVE', 'idx': idx})
            elif t.turn == 'O' and t.winner is None:
                msg = recv_msg()
                if not msg:
                    print('Connection closed.')
                    break
                if msg.get('type') == 'MOVE':
                    t.make_move(msg['idx'], 'O')

            if t.winner:
                print('Game over! Winner:', t.winner)
                send_msg({'type': 'END', 'winner': t.winner})
                break

        conn.close()
        s.close()
import socket
import json
import threading
import random
import time
from utils import send_json_tcp, recv_json_tcp
from config import LOBBY_HOST, LOBBY_PORT, UDP_PORT_START, UDP_PORT_END, BUFFER_SIZE, CSIT_SERVERS
from game_logic import TicTacToe

LOBBY_ADDR = (LOBBY_HOST, LOBBY_PORT)

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

def lobby_login(sock):
    stats = None
    while True:
        op = input('login or register? (l/r): ').strip().lower()
        username = input('username: ').strip()
        password = input('password: ').strip()
        action = 'register' if op == 'r' else 'login'
        send_json_tcp(sock, {
            'action': action,
            'username': username,
            'password': password
        })
        resp = recv_json_tcp(sock)
        print('→', resp)
        if resp and resp.get('status') == 'OK':
            if action == 'login':
                stats = resp.get('stats')
            return username, stats

def lobby_logout(sock, username):
    send_json_tcp(sock, {'action': 'logout', 'username': username})
    sock.close()

def start_game_server(username, port_range=(10001, 20000)):
    t = TicTacToe()
    s = None
    tcp_port = -1
    for port in range(port_range[0], port_range[1]):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(('0.0.0.0', port))
            s.listen(1)
            tcp_port = port
            print(f"[A] TCP game server on port {tcp_port}")
            break
        except OSError: # port in use
            s.close()
            continue
    if s is None:
        print("Could not find an available port for the game server.")
        return None, None, -1
    return s, t, tcp_port

def play_game(lobby_sock, conn, addr, username, bname, t, stats):
    send_msg = lambda o: conn.sendall((json.dumps(o)+'\n').encode())

    def recv_msg():
        data = b''
        while True:
            try:
                chunk = conn.recv(1024)
                if not chunk: return None
                data += chunk
                if b'\n' in data:
                    msg, data = data.split(b'\n', 1)
                    return json.loads(msg.decode())
            except (ConnectionResetError, json.JSONDecodeError):
                return None

    names = {'X': username, 'O': bname}
    send_msg({'type': 'START', 'symbol': 'O', 'names': names})
    print(f'You are X (start first). Index 0–8. Opponent: {bname}')

    last_my_move = None
    game_over = False
    winner_name = None
    while not game_over:
        print(t.printable())
        if t.turn == 'X' and t.winner is None:
            # Check for opponent disconnection before input
            try:
                conn.settimeout(0.1)
                chunk = conn.recv(1)
                if not chunk:
                    print('Opponent disconnected. Game over.')
                    game_over = True
                    continue
            except socket.timeout:
                pass
            except:
                print('Opponent disconnected. Game over.')
                game_over = True
                continue
            finally:
                conn.settimeout(None)
            
            while True:
                move_input = input('Your move (0–8 or 67 to surrender): ').strip()
                if move_input == '67':
                    send_msg({'type': 'SURRENDER'})
                    winner_name = bname
                    game_over = True
                    break
                try:
                    idx = int(move_input)
                    if not 0 <= idx <= 8:
                        print('Index out of range, enter 0–8.')
                        continue
                    if not t.make_move(idx, 'X'):
                        print('Invalid move (occupied or illegal), retry.')
                        continue
                    last_my_move = idx
                    send_msg({'type': 'MOVE', 'idx': idx})
                    print(f"waiting for opponent ({bname})")
                    break
                except ValueError:
                    print('Invalid input, enter integer 0–8 or 67 to surrender.')
                    continue

        elif t.turn == 'O' and t.winner is None:
            msg = recv_msg()
            if not msg:
                print('Opponent disconnected. Game over.')
                game_over = True
                continue

            mtype = msg.get('type')
            if mtype == 'MOVE':
                idx = msg.get('idx')
                if not isinstance(idx, int) or not 0 <= idx <= 8:
                    send_msg({'type': 'INVALID', 'reason': 'bad index'})
                    continue
                if not t.make_move(idx, 'O'):
                    send_msg({'type': 'INVALID', 'reason': 'illegal move'})
                    continue
            elif mtype == 'INVALID':
                print('Opponent reported our previous move invalid. Reverting and please retry.')
                if last_my_move is not None:
                    t.board[last_my_move] = ' '
                    t.turn = 'X'
                    t.moves -=1
                    last_my_move = None
                continue
            elif mtype == 'SURRENDER':
                print(f'Opponent ({bname}) surrendered!')
                winner_name = username
                game_over = True
            elif mtype == 'END':
                print('Final board:'); print(t.printable())
                winner_name = msg.get('winner')
                print('Opponent ended the game:', winner_name)
                game_over = True

        if t.winner:
            print('Final board:'); print(t.printable())
            winner_name = names.get(t.winner, t.winner)
            print('Game over! Winner:', winner_name)
            send_msg({'type': 'END', 'winner': winner_name})
            game_over = True

    conn.close()
    
    # Report game result to lobby server
    report = {'action': 'report_game'}
    if winner_name == username:
        report['winner'] = username
        report['loser'] = bname
    elif winner_name == bname:
        report['winner'] = bname
        report['loser'] = username
    else: # Tie or disconnect
        report['tie'] = True
        report['winner'] = username # both players are part of the "tie"
        report['loser'] = bname
    send_json_tcp(lobby_sock, report)
    # refresh stats
    stats['games_played'] += 1
    if winner_name == username:
        stats['games_won'] += 1


    print("\nReturning to lobby...")

def main_loop(sock, username, stats):
    while True:
        print('\n--- Lobby ---')
        print(f'Your stats: Games Played: {stats.get("games_played", 0)}, Games Won: {stats.get("games_won", 0)}')
        print('s: scan for players | q: quit')
        choice = input('> ').strip().lower()

        if choice == 'q':
            break
        if choice != 's':
            continue

        print('\nScanning CSIT servers for Player B...')
        found = scan_for_players()
        if not found:
            print('No players found. Make sure Player B is running.')
            continue

        for i, (ip, port, name) in enumerate(found):
            print(f'[{i}] {name}@{ip}:{port}')
        try:
            idx = int(input('Choose player to invite: '))
            ip, port, bname = found[idx]
        except (ValueError, IndexError):
            print("Invalid choice.")
            continue

        resp = send_invite(ip, port, username)
        if resp and resp.get('type') == 'ACCEPT':
            print(f'{bname} accepted! Starting TCP server...')
            s, t, tcp_port = start_game_server(username)
            if s is None: continue

            udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            msg = json.dumps({'type': 'TCP_INFO', 'ip': '140.113.235.152', 'port': tcp_port})
            udp.sendto(msg.encode(), (ip, port))
            udp.close()

            s.settimeout(10) # 10s for B to connect
            try:
                conn, addr = s.accept()
                print('[A] Player B connected from', addr)
                s.settimeout(None)
                play_game(sock, conn, addr, username, bname, t, stats)
            except socket.timeout:
                print("Player B did not connect in time.")
            finally:
                s.close()
        else:
            print(f"{bname} declined or invite failed.")

if __name__ == '__main__':
    lobby_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lobby_sock.connect(LOBBY_ADDR)
        username, stats = lobby_login(lobby_sock)
        print("Logged in. Current stats:", stats)

        main_loop(lobby_sock, username, stats)
        send_json_tcp(lobby_sock, {'action': 'update_stats', 'username': username, 'stats': stats})

    except ConnectionRefusedError:
        print("Lobby server is not running.")
    except KeyboardInterrupt:
        print("\nCaught Ctrl+C, logging out...")
    finally:
        if 'username' in locals():
            lobby_logout(lobby_sock, username)
        else:
            lobby_sock.close()
        print("Bye.")
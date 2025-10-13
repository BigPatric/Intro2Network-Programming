import socket
import json
import threading
from utils import send_json_tcp, recv_json_tcp
from config import LOBBY_HOST, LOBBY_PORT, UDP_PORT_START, UDP_PORT_END, BUFFER_SIZE
from game_logic import TicTacToe

LOBBY_ADDR = (LOBBY_HOST, LOBBY_PORT)

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

def start_game_client(ip, port, username, stats):
    try:
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect((ip, port))
        print(f'[B] Connected to game host at {ip}:{port}')
    except ConnectionRefusedError:
        print("Game host is not ready. Returning to lobby.")
        return

    t = TicTacToe()

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

    send_msg = lambda o: conn.sendall((json.dumps(o)+'\n').encode())

    symbol = 'O'
    names = {}
    opponent_name = ''
    game_over = False
    winner_name = None
    while not game_over:
        msg = recv_msg()
        if not msg:
            print('Opponent disconnected. Game over.')
            game_over = True
            continue

        typ = msg.get('type')
        if typ == 'START':
            symbol = msg.get('symbol', 'O') # Player B is usually O
            names = msg.get('names', {})
            opponent_name = names.get('X', 'Opponent')
            t.turn = 'X' # Player A (X) always starts
            print(f'Game start. You are {symbol}. Opponent: {opponent_name}')
        elif typ == 'MOVE':
            if not t.make_move(msg['idx'], 'X'):
                # This should ideally not happen if server logic is correct
                print("Received an invalid move from opponent. Ignoring.")
        elif typ == 'END':
            print('Final board:'); print(t.printable())
            winner_name = msg.get('winner')
            print('Game over! Winner:', winner_name)
            game_over = True
            continue # prevent from asking for a move
        elif typ == 'INVALID':
             print('Server reported our previous move invalid. Please retry.')
             # No state change needed for B, just re-prompt for input.
        elif typ == 'SURRENDER':
            print(f'Opponent ({opponent_name}) surrendered!')
            winner_name = username
            game_over = True

        if t.turn == symbol and not t.winner:
            print(t.printable())
            while True:
                move_input = input('Your move (0–8 or 67 to surrender): ').strip()
                if move_input == '67':
                    send_msg({'type': 'SURRENDER'})
                    winner_name = opponent_name
                    game_over = True
                    break
                try:
                    idx = int(move_input)
                    if not 0 <= idx <= 8:
                        print('Index out of range, enter 0–8.')
                        continue
                    if not t.make_move(idx, symbol):
                        print('Invalid move (occupied or illegal), retry.')
                        continue
                    send_msg({'type': 'MOVE', 'idx': idx})
                    print(t.printable())
                    print(f"waiting for opponent ({opponent_name})")
                    break
                except ValueError:
                    print('Invalid input, enter integer 0–8 or 67 to surrender.')
                    continue
    
    # B doesn't report, A does. But B can update its local stats
    stats['games_played'] += 1
    if winner_name == username:
        stats['games_won'] += 1

    conn.close()
    print("\nReturning to lobby...")


def udp_listener(username, listen_port, stats):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.bind(('0.0.0.0', listen_port))
    except OSError:
        print(f"Port {listen_port} is already in use. Try another one.")
        return

    print(f'[B] Waiting for invites on UDP {listen_port}')
    print(f'Your stats: Games Played: {stats.get("games_played", 0)}, Games Won: {stats.get("games_won", 0)}')


    while True:
        try:
            data, addr = s.recvfrom(BUFFER_SIZE)
            try:
                obj = json.loads(data.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
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
                s.close() # close UDP listener to start game
                start_game_client(ip, port, username, stats)
                return # game finished, exit listener loop to re-prompt for port
        except KeyboardInterrupt:
            break # allow clean exit
    s.close()

if __name__ == '__main__':
    lobby_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        lobby_sock.connect(LOBBY_ADDR)
        username, stats = lobby_login(lobby_sock)
        print("Logged in. Current stats:", stats)

        while True:
            try:
                port_str = input(f'Choose UDP port to listen on ({UDP_PORT_START}-{UDP_PORT_END}), or q to quit: ')
                if port_str.lower() == 'q':
                    break
                port = int(port_str)
                if not UDP_PORT_START <= port <= UDP_PORT_END:
                    print("Port out of range.")
                    continue
                udp_listener(username, port, stats)
            except ValueError:
                print("Invalid input. Please enter a number.")
            except KeyboardInterrupt:
                print("\nStopping listener...")
                break

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
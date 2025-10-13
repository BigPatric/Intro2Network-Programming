import socket
import threading
import json
import time
from utils import load_accounts, save_accounts, recv_json_tcp, send_json_tcp
from config import LOBBY_HOST, LOBBY_PORT, SERVER_HOST

accounts_lock = threading.Lock()
accounts = load_accounts()  # {username: {"password": ..., "last_login": ...}}

active_sessions = {}  # username -> (addr, thread)


def handle_client(conn, addr):
    try:
        while True:
            req = recv_json_tcp(conn)
            if req is None:
                break
            action = req.get('action')
            username = req.get('username')
            password = req.get('password')

            if action == 'register':
                with accounts_lock:
                    if username in accounts:
                        send_json_tcp(conn, {'status': 'ERR', 'reason': 'duplicate'})
                    else:
                        accounts[username] = {
                            'password': password,
                            'created': time.time(),
                            'last_login': None,
                            'stats': {'login_count': 0, 'games_played': 0, 'games_won': 0}
                        }
                        save_accounts(accounts)
                        send_json_tcp(conn, {'status': 'OK'})

            elif action == 'login':
                with accounts_lock:
                    if username not in accounts:
                        send_json_tcp(conn, {'status': 'ERR', 'reason': 'notfound'})
                    elif accounts[username]['password'] != password:
                        send_json_tcp(conn, {'status': 'ERR', 'reason': 'badpass'})
                    else:
                        # handle duplicate login: reject if already logged in
                        if username in active_sessions:
                            send_json_tcp(conn, {'status': 'ERR', 'reason': 'already_logged_in'})
                        else:
                            accounts[username]['last_login'] = time.time()
                            # a new login, increment login_count
                            if 'stats' not in accounts[username]: # for backward compatibility
                                accounts[username]['stats'] = {}
                            stats = accounts[username]['stats']
                            stats.setdefault('login_count', 0)
                            stats.setdefault('games_played', 0)
                            stats.setdefault('games_won', 0)
                            stats['login_count'] += 1
                            save_accounts(accounts)
                            active_sessions[username] = addr
                            send_json_tcp(conn, {'status': 'OK', 'stats': accounts[username]['stats']})

            elif action == 'logout':
                with accounts_lock:
                    if username in active_sessions:
                        active_sessions.pop(username, None)
                send_json_tcp(conn, {'status': 'OK'})

            elif action == 'update_stats':
                stats = req.get('stats')
                with accounts_lock:
                    if username in accounts and stats is not None:
                        # only update the fields that are sent (only login_count, games_played, games_won allowed)
                        for key, value in stats.items():
                            if key in ('login_count', 'games_played', 'games_won'):
                                accounts[username]['stats'][key] = value
                        save_accounts(accounts)
                        send_json_tcp(conn, {'status': 'OK'})
                    else:
                        send_json_tcp(conn, {'status': 'ERR', 'reason': 'update failed'})
            
            elif action == 'report_game':
                winner = req.get('winner')
                loser = req.get('loser')
                is_tie = req.get('tie', False)
                with accounts_lock:
                    if winner and winner in accounts:
                        accounts[winner]['stats']['games_played'] += 1
                        if not is_tie:
                            accounts[winner]['stats']['games_won'] += 1
                    if loser and loser in accounts:
                        accounts[loser]['stats']['games_played'] += 1
                    save_accounts(accounts)
                send_json_tcp(conn, {'status': 'OK'})

            else:
                send_json_tcp(conn, {'status': 'ERR', 'reason': 'unknown_action'})

    except Exception as e:
        print('client err', e)
    finally:
        # cleanup any sessions tied to this addr
        for u, a in list(active_sessions.items()):
            if a == addr:
                active_sessions.pop(u, None)
        conn.close()


def start_lobby():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((SERVER_HOST, LOBBY_PORT))
    s.listen()
    print('Lobby server listening on', (SERVER_HOST, LOBBY_PORT))

    try:
        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            t.start()
    except KeyboardInterrupt:
        print('Shutting down')
    finally:
        s.close()


if __name__ == '__main__':
    start_lobby()
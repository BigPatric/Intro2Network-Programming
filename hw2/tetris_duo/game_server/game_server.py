import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Optional port arg
import socket, threading, time, sys, random
from common.protocol import send_msg, recv_msg
from game_server.tetris_logic import Board
from lobby_server.db_client import DBClient
try:
    from config import DB_HOST, DB_PORT, GAME_BIND_HOST
except Exception:
    DB_HOST, DB_PORT = '127.0.0.1', 10001
    GAME_BIND_HOST = '0.0.0.0'

class PlayerConn:
    def __init__(self, conn, name):
        self.conn = conn
        self.name = name
        self.board = Board(seed=None)
        self.alive = True

    def send(self, data):
        try:
            send_msg(self.conn, data)
        except Exception:
            self.alive = False

players = {}

# Game params: seed, bag, gravity
GAME_SEED = None
BAG_RULE = '7bag'
GRAVITY_PLAN = {"mode": "fixed", "dropMs": 500}


def handle_input(pconn: PlayerConn):
    while True:
        msg = recv_msg(pconn.conn)
        if msg is None:
            pconn.alive = False
            break
        tp = msg.get('type')
        if tp == 'INPUT':
            act = msg.get('action')
            if act == 'LEFT':
                pconn.board.move(-1)
            elif act == 'RIGHT':
                pconn.board.move(1)
            elif act == 'SOFT':
                pconn.board.soft_drop()
            elif act == 'HARD':
                pconn.board.hard_drop()
            elif act == 'ROT':
                pconn.board.rotate()
            elif act == 'HOLD':
                pconn.board.hold_piece()
        elif tp == 'HELLO':
            # Ignore; WELCOME sent in main()
            pass


def broadcast_snapshot(tick):
    snapshot = {name: p.board.snapshot() for name, p in players.items()}
    payload = {'type':'SNAPSHOT', 'tick': tick, 'players': snapshot}
    for p in players.values():
        p.send(payload)

def broadcast_tempo(plan):
    payload = {"type": "TEMPO", **plan, "effectiveAt": int(time.time()*1000)}
    for p in players.values():
        p.send(payload)


def game_tick_loop(start_time):
    tick = 0
    winner = None
    duration_sec = 60 
    while True:
        now = int(time.time() * 1000)
        active_players = [p for p in players.values() if p.alive and not p.board.game_over]
        # End by time
        if (now - start_time) // 1000 >= duration_sec:
            # Decide winner by score
            scores = {name: p.board.score for name, p in players.items()}
            max_score = max(scores.values())
            winners = [name for name, score in scores.items() if score == max_score]
            winner = winners[0] if len(winners) == 1 else None  # Tie: winner=None
            print(f"[Game] Time up! Scores: {scores}")
            break
        # End if someone dies
        if len(active_players) < len(players):
            # Find alive player
            for name, p in players.items():
                if p.alive and not p.board.game_over:
                    winner = name
            break
        for p in active_players:
            p.board.tick()
            if p.board.game_over:
                p.alive = False
        broadcast_snapshot(tick)
        tick += 1
        time.sleep(0.5)

    # Game over: log & broadcast
    db = DBClient(DB_HOST, DB_PORT)
    end_time = int(time.time()*1000)
    g = {
        'matchId': start_time,
        'users': list(players.keys()),
        'startAt': start_time,
        'endAt': end_time,
        'results': [],
        'winner': winner
    }
    for name, p in players.items():
        g['results'].append({'userId': name, 'score': p.board.score, 'lines': p.board.lines})
    db.create('GameLog', g)
    print(f"[Game] Winner: {winner}")
    summary = {name: {'score': p.board.score, 'lines': p.board.lines} for name, p in players.items()}
    payload = {'type': 'GAME_OVER', 'winner': winner, 'summary': summary}
    for p in players.values():
        p.send(payload)

def main():
    port = 10002
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except:
            pass
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((GAME_BIND_HOST, port))
    s.listen(2)
    print(f"[Game] Waiting for players on {port}...")

    start_time = int(time.time()*1000)
    global GAME_SEED
    GAME_SEED = random.randint(1, 2**31-1)
    while len(players) < 2:
        conn, addr = s.accept()
        hello = recv_msg(conn)
        name = hello.get('userId', f'P{len(players)+1}') if hello else f'P{len(players)+1}'
        pconn = PlayerConn(conn, name)
        players[name] = pconn
        # Reply WELCOME with role, seed, bag, gravity
        role = 'P1' if len(players) == 1 else 'P2'
        try:
            send_msg(conn, {
                'type': 'WELCOME',
                'role': role,
                'seed': GAME_SEED,
                'bagRule': BAG_RULE,
                'gravityPlan': GRAVITY_PLAN,
            })
        except Exception:
            pass
        threading.Thread(target=handle_input, args=(pconn,), daemon=True).start()
        print(f"[Game] Player joined: {name}")

    # Start game loop
    # Rebuild boards with same seed & bag
    for p in players.values():
        p.board = Board(seed=GAME_SEED)

    # Broadcast TEMPO
    broadcast_tempo(GRAVITY_PLAN)
    # Send initial snapshot
    broadcast_snapshot(tick=0)
    game_tick_loop(start_time)

if __name__ == '__main__':
    main()
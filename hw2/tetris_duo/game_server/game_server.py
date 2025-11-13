import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# Arg: optional port
import socket, threading, time, sys, random
from common.protocol import send_msg, recv_msg
from game_server.tetris_logic import Board
from lobby_server.db_client import DBClient

DB_HOST = '127.0.0.1'
DB_PORT = 10001

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

# Global game parameters (seed, bag rule, gravity/tempo)
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
            # Ignore here; WELCOME is sent at join time in main()
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
        # 時間到直接結束比賽
        if (now - start_time) // 1000 >= duration_sec:
            # 依分數決定勝負
            scores = {name: p.board.score for name, p in players.items()}
            max_score = max(scores.values())
            winners = [name for name, score in scores.items() if score == max_score]
            winner = winners[0] if len(winners) == 1 else None  # 平手 winner=None
            print(f"[Game] Time up! Scores: {scores}")
            break
        # 有一方死亡就結束
        if len(active_players) < len(players):
            # 找出還活著的玩家
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

    # game over: write gamelog
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

def main():
    port = 10002
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except:
            pass
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', port))
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
        # 先回覆 WELCOME，包含角色、隨機種子、bag 規則與節奏
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

    # start game loop
    # 統一重建玩家棋盤，確保使用相同的 seed 與 7-bag 順序
    for p in players.values():
        p.board = Board(seed=GAME_SEED)

    # 廣播一次 TEMPO 訊息
    broadcast_tempo(GRAVITY_PLAN)
    # 遊戲開始前送出一次初始快照
    broadcast_snapshot(tick=0)
    game_tick_loop(start_time)

if __name__ == '__main__':
    main()
import socket
import threading
import sys

BOARD_SIZE = 15

class GomokuServer:
    def __init__(self, host, port):
        self.board = [[0]*BOARD_SIZE for _ in range(BOARD_SIZE)]
        self.turn = 1  # 1:黑 2:白
        self.players = [None, None]  # [黑, 白]
        self.socks = []
        self.lock = threading.Lock()
        self.host = host
        self.port = port
        self.running = True

    def start(self):
        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((self.host, self.port))
        s.listen(2)
        print(f"Game server running on {self.host}:{self.port}")
        while len(self.socks) < 2:
            conn, addr = s.accept()
            print(f"Player connected from {addr}")
            self.socks.append(conn)
            threading.Thread(target=self.handle, args=(conn, len(self.socks)), daemon=True).start()
        # 通知雙方開始
        self.send(self.socks[0], f"START 1")
        self.send(self.socks[1], f"START 2")
        self.send(self.socks[0], f"TURN 1")
        self.send(self.socks[1], f"TURN 1")

        while self.running:
            pass  # 主執行緒什麼都不做

    def handle(self, conn, color):
        color = int(color)
        while self.running:
            try:
                data = conn.recv(1024)
                if not data:
                    break
                for line in data.decode().splitlines():
                    self.handle_cmd(conn, color, line.strip())
            except Exception as e:
                print("Player disconnected:", e)
                break
        self.running = False
        for sock in self.socks:
            try:
                sock.close()
            except:
                pass

    def handle_cmd(self, conn, color, msg):
        if msg.startswith("MOVE"):
            _, x, y = msg.split()
            x, y = int(x), int(y)
            with self.lock:
                if self.turn != color or self.board[y][x] != 0:
                    self.send(conn, "MSG 非法落子")
                    return
                self.board[y][x] = color
                for sock in self.socks:
                    self.send(sock, f"MOVE {x} {y} {color}")
                if self.check_win(x, y, color):
                    for sock in self.socks:
                        self.send(sock, f"WIN {color}")
                    self.running = False
                    return
                elif self.check_draw():
                    for sock in self.socks:
                        self.send(sock, "DRAW")
                    self.running = False
                    return
                self.turn = 1 if self.turn == 2 else 2
                for sock in self.socks:
                    self.send(sock, f"TURN {self.turn}")

    def send(self, conn, msg):
        try:
            conn.sendall((msg + "\n").encode())
        except:
            pass

    def check_win(self, x, y, color):
        def count(dx, dy):
            cnt = 1
            for d in [1, -1]:
                nx, ny = x, y
                while True:
                    nx += dx * d
                    ny += dy * d
                    if 0 <= nx < BOARD_SIZE and 0 <= ny < BOARD_SIZE and self.board[ny][nx] == color:
                        cnt += 1
                    else:
                        break
            return cnt
        for dx, dy in [(1,0),(0,1),(1,1),(1,-1)]:
            if count(dx, dy) >= 5:
                return True
        return False

    def check_draw(self):
        return all(self.board[y][x] != 0 for y in range(BOARD_SIZE) for x in range(BOARD_SIZE))

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python game_server.py <port>")
        sys.exit(1)
    host = "0.0.0.0"
    port = int(sys.argv[1])
    GomokuServer(host, port).start()
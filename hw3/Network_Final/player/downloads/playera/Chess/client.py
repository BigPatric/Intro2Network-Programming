import socket
import sys
import threading
import tkinter as tk
from tkinter import messagebox

BOARD_SIZE = 15
CELL_SIZE = 40
STONE_RADIUS = 16

class GomokuClient:
    def __init__(self, host, port):
        self.sock = socket.socket()
        self.sock.connect((host, int(port)))
        self.root = tk.Tk()
        self.root.title("五子棋 Gomoku")
        self.canvas = tk.Canvas(self.root, width=BOARD_SIZE*CELL_SIZE, height=BOARD_SIZE*CELL_SIZE, bg="#F9E4B7")
        self.canvas.pack()
        self.board = [[0]*BOARD_SIZE for _ in range(BOARD_SIZE)]  # 0:空 1:黑 2:白
        self.my_turn = False
        self.my_color = 1  # 1:黑 2:白
        self.running = True

        self.cursor_x = BOARD_SIZE // 2
        self.cursor_y = BOARD_SIZE // 2

        self.canvas.focus_set()
        self.canvas.bind("<Key>", self.on_key)
        threading.Thread(target=self.listen_server, daemon=True).start()

    def draw_board(self):
        self.canvas.delete("all")
        for i in range(BOARD_SIZE):
            self.canvas.create_line(CELL_SIZE//2, CELL_SIZE//2 + i*CELL_SIZE,
                                    CELL_SIZE//2 + (BOARD_SIZE-1)*CELL_SIZE, CELL_SIZE//2 + i*CELL_SIZE)
            self.canvas.create_line(CELL_SIZE//2 + i*CELL_SIZE, CELL_SIZE//2,
                                    CELL_SIZE//2 + i*CELL_SIZE, CELL_SIZE//2 + (BOARD_SIZE-1)*CELL_SIZE)
        for y in range(BOARD_SIZE):
            for x in range(BOARD_SIZE):
                if self.board[y][x] == 1:
                    self.canvas.create_oval(
                        x*CELL_SIZE+CELL_SIZE//2-STONE_RADIUS, y*CELL_SIZE+CELL_SIZE//2-STONE_RADIUS,
                        x*CELL_SIZE+CELL_SIZE//2+STONE_RADIUS, y*CELL_SIZE+CELL_SIZE//2+STONE_RADIUS,
                        fill="black"
                    )
                elif self.board[y][x] == 2:
                    self.canvas.create_oval(
                        x*CELL_SIZE+CELL_SIZE//2-STONE_RADIUS, y*CELL_SIZE+CELL_SIZE//2-STONE_RADIUS,
                        x*CELL_SIZE+CELL_SIZE//2+STONE_RADIUS, y*CELL_SIZE+CELL_SIZE//2+STONE_RADIUS,
                        fill="white"
                    )
        # 畫游標
        self.canvas.create_rectangle(
            self.cursor_x*CELL_SIZE+CELL_SIZE//2-STONE_RADIUS-2,
            self.cursor_y*CELL_SIZE+CELL_SIZE//2-STONE_RADIUS-2,
            self.cursor_x*CELL_SIZE+CELL_SIZE//2+STONE_RADIUS+2,
            self.cursor_y*CELL_SIZE+CELL_SIZE//2+STONE_RADIUS+2,
            outline="red", width=2
        )

    def on_key(self, event):
        if not self.my_turn:
            return
        key = event.keysym
        if key == "Up":
            if self.cursor_y > 0:
                self.cursor_y -= 1
        elif key == "Down":
            if self.cursor_y < BOARD_SIZE - 1:
                self.cursor_y += 1
        elif key == "Left":
            if self.cursor_x > 0:
                self.cursor_x -= 1
        elif key == "Right":
            if self.cursor_x < BOARD_SIZE - 1:
                self.cursor_x += 1
        elif key == "Return":
            if self.board[self.cursor_y][self.cursor_x] == 0:
                self.sock.sendall(f"MOVE {self.cursor_x} {self.cursor_y}\n".encode())
        self.draw_board()

    def listen_server(self):
        try:
            while self.running:
                data = self.sock.recv(1024)
                if not data:
                    break
                for line in data.decode().splitlines():
                    self.handle_server_msg(line.strip())
        except Exception as e:
            print("連線中斷:", e)
        finally:
            self.sock.close()
            self.running = False
            self.root.quit()

    def handle_server_msg(self, msg):
        if msg.startswith("START"):
            color = int(msg.split()[1])
            self.my_color = color
            self.my_turn = (color == 1)
            self.root.after(0, lambda: messagebox.showinfo("遊戲開始", f"你是{'黑子' if color==1 else '白子'}"))
        elif msg.startswith("MOVE"):
            _, x, y, color = msg.split()
            x, y, color = int(x), int(y), int(color)
            self.board[y][x] = color
            self.root.after(0, self.draw_board)
        elif msg.startswith("TURN"):
            turn = int(msg.split()[1])
            self.my_turn = (turn == self.my_color)
            if self.my_turn:
                self.root.after(0, lambda: self.root.title("輪到你下棋！"))
            else:
                self.root.after(0, lambda: self.root.title("等待對手..."))
        elif msg.startswith("WIN"):
            winner = int(msg.split()[1])
            if winner == self.my_color:
                self.root.after(0, lambda: messagebox.showinfo("遊戲結束", "你贏了！"))
            else:
                self.root.after(0, lambda: messagebox.showinfo("遊戲結束", "你輸了！"))
            self.running = False
            self.root.after(1000, self.root.quit)
        elif msg.startswith("DRAW"):
            self.root.after(0, lambda: messagebox.showinfo("遊戲結束", "平手！"))
            self.running = False
            self.root.after(1000, self.root.quit)
        elif msg.startswith("MSG"):
            self.root.after(0, lambda: messagebox.showinfo("訊息", msg[4:]))

    def run(self):
        self.draw_board()
        self.canvas.focus_set()
        self.root.mainloop()
        self.running = False

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("用法: python client.py <server_ip> <port>")
        sys.exit(1)
    host, port = sys.argv[1], int(sys.argv[2])
    client = GomokuClient(host, port)
    client.run()
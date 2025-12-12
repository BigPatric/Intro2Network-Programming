import socket
import json
import threading
import tkinter as tk
import sys
import struct

# Lobby Client 會傳入 IP 與 Port
SERVER_IP = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
SERVER_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9999

class GameClient:
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.root = tk.Tk()
        self.root.title("My Agario")
        self.canvas = tk.Canvas(self.root, width=500, height=500, bg="white")
        self.canvas.pack()
        
        self.running = True
        self.state = {'players': [], 'food': []}
        
        # Input handling
        self.root.bind("<KeyPress>", self.on_key)
        
    def connect(self):
        try:
            self.sock.connect((SERVER_IP, SERVER_PORT))
            print("Connected to game server!")
            threading.Thread(target=self.receive_loop, daemon=True).start()
            self.update_ui()
            self.root.mainloop()
        except Exception as e:
            print(f"Connection failed: {e}")

    def on_key(self, event):
        dx, dy = 0, 0
        step = 10
        if event.keysym == 'Up': dy = -step
        if event.keysym == 'Down': dy = step
        if event.keysym == 'Left': dx = -step
        if event.keysym == 'Right': dx = step
        
        if dx != 0 or dy != 0:
            msg = json.dumps({'dx': dx, 'dy': dy}).encode()
            try:
                self.sock.sendall(msg)
            except:
                self.running = False

    def receive_loop(self):
        while self.running:
            try:
                header = self.sock.recv(4)
                if not header: break
                length = int.from_bytes(header, 'big')
                
                data = b''
                while len(data) < length:
                    packet = self.sock.recv(length - len(data))
                    if not packet: break
                    data += packet
                    
                self.state = json.loads(data.decode())
            except Exception as e:
                print(f"Recv error: {e}")
                self.running = False
                break

    def update_ui(self):
        if not self.running:
            self.root.destroy()
            return
            
        self.canvas.delete("all")
        
        # Draw Food
        for f in self.state.get('food', []):
            x, y = f['x'], f['y']
            self.canvas.create_oval(x-3, y-3, x+3, y+3, fill=f['c'])
            
        # Draw Players
        for p in self.state.get('players', []):
            x, y, s = p['x'], p['y'], p['size']
            self.canvas.create_oval(x-s, y-s, x+s, y+s, fill=p['color'])
            self.canvas.create_text(x, y, text=p['id'])
            
        self.root.after(50, self.update_ui)

if __name__ == '__main__':
    GameClient().connect()
import socket
import threading
import json
import time
import sys
import random

# Lobby Service 會傳入 Port 作為第一個參數
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9999
HOST = '0.0.0.0'

players = {} # {addr: {'id': id, 'x': x, 'y': y, 'color': c, 'size': s}}
food = []
lock = threading.Lock()

def generate_food(count=5):
    for _ in range(count):
        food.append({'x': random.randint(0, 500), 'y': random.randint(0, 500), 'c': 'green'})

def broadcast_state(sock_list):
    while True:
        time.sleep(0.05) # 20 FPS
        with lock:
            state = {
                'players': list(players.values()),
                'food': food
            }
            data = json.dumps(state).encode()
            
        header = len(data).to_bytes(4, 'big')
        to_remove = []
        for s in sock_list:
            try:
                s.sendall(header + data)
            except:
                to_remove.append(s)
        
        for s in to_remove:
            sock_list.remove(s)

def client_handler(conn, addr, sock_list):
    print(f"Player {addr} joined game")
    sock_list.append(conn)
    
    # Init player
    pid = f"P{random.randint(10,99)}"
    with lock:
        players[str(addr)] = {
            'id': pid, 
            'x': random.randint(50, 450), 
            'y': random.randint(50, 450),
            'color': random.choice(['red', 'blue', 'orange', 'purple']),
            'size': 20
        }

    try:
        while True:
            # Receive movement (dx, dy)
            data = conn.recv(1024)
            if not data: break
            
            try:
                move = json.loads(data.decode())
                dx = move.get('dx', 0)
                dy = move.get('dy', 0)
                
                with lock:
                    p = players[str(addr)]
                    p['x'] = max(0, min(500, p['x'] + dx))
                    p['y'] = max(0, min(500, p['y'] + dy))
                    
                    # Eat food check
                    # (Simplified collision)
                    for f in food[:]:
                        if abs(p['x'] - f['x']) < p['size'] and abs(p['y'] - f['y']) < p['size']:
                            p['size'] += 2
                            food.remove(f)
                            generate_food(1)
            except:
                pass
                
    except Exception as e:
        print(f"Error {addr}: {e}")
    finally:
        with lock:
            if str(addr) in players: del players[str(addr)]
        if conn in sock_list: sock_list.remove(conn)
        conn.close()
        print(f"Player {addr} left")

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    print(f"Game Server running on port {PORT}")
    
    generate_food(20)
    sock_list = []
    
    # Broadcast thread
    threading.Thread(target=broadcast_state, args=(sock_list,), daemon=True).start()
    
    while True:
        conn, addr = s.accept()
        threading.Thread(target=client_handler, args=(conn, addr, sock_list), daemon=True).start()

if __name__ == '__main__':
    main()
import socket
import threading
import random
import sys

HOST = '0.0.0.0'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9009

def handle_client(conn, addr):
    answer = random.randint(1, 10)
    conn.sendall("歡迎來到猜數字遊戲！請猜 1~10 的數字：\n".encode('utf-8'))
    while True:
        data = conn.recv(1024)
        if not data:
            break
        try:
            guess = int(data.decode().strip())
            if guess == answer:
                conn.sendall("恭喜答對！\n".encode('utf-8'))
                break
            elif guess < answer:
                conn.sendall("太小了，再試一次：\n".encode('utf-8'))
            else:
                conn.sendall("太大了，再試一次：\n".encode('utf-8'))
        except:
            conn.sendall("請輸入數字：\n".encode('utf-8'))
    conn.close()

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Game server running on {HOST}:{PORT}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr)).start()

if __name__ == "__main__":
    main()
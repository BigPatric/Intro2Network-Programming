import socket

HOST = input("請輸入遊戲伺服器 IP（預設 127.0.0.1）：") or "127.0.0.1"
PORT = int(input("請輸入遊戲伺服器 PORT（預設 9009）：") or 9009)

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    while True:
        data = s.recv(1024)
        if not data:
            break
        print(data.decode(), end='')
        if "恭喜答對" in data.decode():
            break
        guess = input()
        s.sendall(guess.encode())
import socket
import sys

if len(sys.argv) >= 3:
    HOST = sys.argv[1]
    PORT = int(sys.argv[2])
else:
    HOST = "127.0.0.1"
    PORT = 9009

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
import socket
import sys

SERVER_IP = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
SERVER_PORT = int(sys.argv[2]) if len(sys.argv) > 2 else 9999

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((SERVER_IP, SERVER_PORT))
    print("Connected to Echo Game Server!")
    print("Type something and press Enter (type 'exit' to quit):")
    while True:
        msg = input("> ")
        if msg == 'exit':
            break
        s.sendall(msg.encode())
        data = s.recv(1024)
        print("Echo:", data.decode())
    s.close()

if __name__ == '__main__':
    main()
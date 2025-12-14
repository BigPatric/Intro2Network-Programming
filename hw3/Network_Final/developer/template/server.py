import socket
import threading
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 9999
HOST = '0.0.0.0'

def handle_client(conn, addr):
    print(f"Client {addr} connected.")
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            # Echo back
            conn.sendall(data)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
        print(f"Client {addr} disconnected.")

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen()
    print(f"Echo Game Server running on port {PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == '__main__':
    main()
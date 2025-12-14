import threading

class ConnectionManager:
    def __init__(self):
        self.connections = {}  # sock: username
        self.user_to_sock = {} # username: sock
        self._lock = threading.Lock()

    def add_connection(self, sock, username):
        with self._lock:
            self.connections[sock] = username
            self.user_to_sock[username] = sock
        print(f"使用者 {username} 已登入。目前連線數: {len(self.connections)}")

    def remove_connection(self, sock):
        with self._lock:
            if sock in self.connections:
                username = self.connections.pop(sock)
                if username in self.user_to_sock:
                    del self.user_to_sock[username]
                print(f"使用者 {username} 已離線。目前連線數: {len(self.connections)}")

    def get_username(self, sock):
        with self._lock:
            return self.connections.get(sock)

    def get_all_usernames(self):
        with self._lock:
            return list(self.user_to_sock.keys())

# 全域單例
connection_manager = ConnectionManager()
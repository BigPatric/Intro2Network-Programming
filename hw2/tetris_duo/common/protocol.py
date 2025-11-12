import struct, json, socket

MAX_LENGTH = 65568  # 最大訊息長度

def send_msg(sock: socket.socket, data: dict):
    """
    傳送 dict 資料，前面加 4 位元組長度。
    """
    body = json.dumps(data).encode('utf-8')
    length = len(body)
    if length > MAX_LENGTH:
        raise ValueError(f"Message too long: {length} > {MAX_LENGTH}")
    sock.sendall(struct.pack('!I', length) + body)

def recv_all(sock, n):
    """
    從 socket 讀取 n 個位元組。
    """
    data = b''
    while len(data) < n:
        chunk = sock.recv(n - len(data))
        if not chunk:
            return None
        data += chunk
    return data

def recv_msg(sock: socket.socket):
    """
    接收 4 位元組長度 + JSON body。
    """
    header = recv_all(sock, 4)
    if not header:
        return None
        
    (length,) = struct.unpack('!I', header)
    if length > MAX_LENGTH:
        raise ValueError(f"Message length {length} exceeds {MAX_LENGTH}")
    if length == 0:
        return None
        
    body = recv_all(sock, length)
    if not body:
        return None 

    try:
        decoded_body = body.decode('utf-8')
        return json.loads(decoded_body)
    except UnicodeDecodeError:
        print(f"[Protocol Error] 非 UTF-8 資料，長度: {length}")
        raise
    except json.JSONDecodeError as e:
        print("JSON 解析失敗！")
        print(f"原因: {e}")
        print(f"長度: {length}")
        print(f"資料: {body.decode('utf-8', errors='replace')!r}") 
        return None
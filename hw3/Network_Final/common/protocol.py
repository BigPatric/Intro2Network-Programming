# common/protocol.py
import json
import struct
import socket

def send_json(sock, data):
    """傳送 JSON 資料 (解決 TCP黏包: 4 bytes 長度 + JSON 內容)"""
    json_str = json.dumps(data)
    data_bytes = json_str.encode('utf-8')
    # Big-endian unsigned int for length
    sock.sendall(struct.pack('!I', len(data_bytes)) + data_bytes)

def recv_json(sock):
    """接收 JSON 資料"""
    try:
        header = sock.recv(4)
        if not header:
            return None
        length = struct.unpack('!I', header)[0]
        
        data = b''
        while len(data) < length:
            packet = sock.recv(length - len(data))
            if not packet:
                return None
            data += packet
        return json.loads(data.decode('utf-8'))
    except Exception as e:
        print(f"Connection error: {e}")
        return None

def send_file(sock, file_path):
    """傳送二進位檔案"""
    with open(file_path, 'rb') as f:
        file_data = f.read()
    # 先傳送檔案大小
    sock.sendall(struct.pack('!Q', len(file_data)))  # 8 bytes for large files
    # 再傳送檔案內容
    sock.sendall(file_data)

def recv_file(sock, save_path):
    """接收二進位檔案"""
    header = sock.recv(8)
    if not header: return False
    file_size = struct.unpack('!Q', header)[0]
    
    received = 0
    with open(save_path, 'wb') as f:
        while received < file_size:
            chunk = sock.recv(min(4096, file_size - received))
            if not chunk: break
            f.write(chunk)
            received += len(chunk)
    return True
# developer/dev_client.py
import socket
import sys
import os
import shutil
import zipfile

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from common.protocol import send_json, recv_json, send_file

SERVER_IP = '127.0.0.1'
SERVER_PORT = 8888

def zip_game(game_path, output_filename):
    """將遊戲資料夾壓縮成 zip"""
    with zipfile.ZipFile(output_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(game_path):
            for file in files:
                file_path = os.path.join(root, file)
                # 保留相對路徑
                arcname = os.path.relpath(file_path, os.path.dirname(game_path))
                zipf.write(file_path, arcname)

def upload_game(sock):
    game_name = input("Enter game name (folder name in games/): ")
    game_path = os.path.join('developer/games', game_name)
    
    if not os.path.exists(game_path):
        print("Game folder not found!")
        return

    # 1. 壓縮遊戲
    zip_name = f"{game_name}.zip"
    zip_game(game_path, zip_name)
    
    # 2. 發送上傳請求
    req = {
        'command': 'upload_game',
        'game_name': game_name,
        'version': '1.0.0' # 可以從 config 讀取
    }
    send_json(sock, req)
    
    # 3. 發送檔案
    print("Uploading file...")
    send_file(sock, zip_name)
    
    # 4. 接收結果
    res = recv_json(sock)
    print("Server response:", res)
    
    # 清理暫存 zip
    os.remove(zip_name)

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((SERVER_IP, SERVER_PORT))
        while True:
            print("\n=== Developer Menu ===")
            print("1. Upload Game")
            print("2. Exit")
            choice = input("Select: ")
            
            if choice == '1':
                upload_game(sock)
            elif choice == '2':
                break
    except Exception as e:
        print(f"Error: {e}")
    finally:
        sock.close()

if __name__ == '__main__':
    main()
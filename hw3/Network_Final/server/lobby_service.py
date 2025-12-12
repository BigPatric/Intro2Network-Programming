import socket
import subprocess
import os
import random
import sys
import threading  # [Fix] 引入 threading
from server.db_manager import get_all_games, login_user, register_user

# 狀態儲存
ROOMS = {} 
lobby_lock = threading.Lock()  # [Fix] 建立鎖，保護 ROOMS

UPLOAD_DIR = 'server/uploaded_games'
EXTRACT_DIR = 'server/uploaded_games_extracted'

def find_free_port():
    """尋找一個閒置的 Port"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def handle_lobby_request(conn, request):
    cmd = request.get('command')
    user = request.get('username')
    
    # --- 帳號相關 (DB Manager 內部已有 connection 隔離，無需額外鎖) ---
    if cmd == 'login':
        role = login_user(user, request.get('password'))
        if role:
            return {'status': 'success', 'role': role}
        return {'status': 'fail', 'message': 'Invalid credentials'}
    
    elif cmd == 'register':
        if register_user(user, request.get('password')):
            return {'status': 'success'}
        return {'status': 'fail', 'message': 'User exists'}

    # --- 遊戲列表與下載 ---
    elif cmd == 'get_game_list':
        # 讀取 DB，唯讀操作
        return {'status': 'success', 'games': get_all_games()}
    
    elif cmd == 'download_game':
        game_name = request.get('game_name')
        file_path = os.path.join(UPLOAD_DIR, f"{game_name}.zip")
        if os.path.exists(file_path):
            return {'status': 'ready_to_send', 'file_size': os.path.getsize(file_path)}
        else:
            return {'status': 'error', 'message': 'Game file not found'}

    # --- 房間邏輯 (必須加鎖！) ---
    elif cmd == 'create_room':
        game_name = request.get('game_name')
        room_id = str(random.randint(1000, 9999))
        
        with lobby_lock:  # [Lock] 寫入 ROOMS
            # 檢查 ID 是否重複 (極低機率，但為了嚴謹)
            while room_id in ROOMS:
                room_id = str(random.randint(1000, 9999))
                
            ROOMS[room_id] = {
                'game_name': game_name,
                'players': [user],
                'status': 'WAITING',
                'game_port': None
            }
        
        print(f"Room {room_id} created for game {game_name} by {user}")
        return {'status': 'success', 'room_id': room_id}

    elif cmd == 'list_rooms':
        with lobby_lock:  # [Lock] 讀取 ROOMS
            room_list = []
            for rid, data in ROOMS.items():
                status = data['status']
                p_count = len(data['players'])
                room_list.append(f"Room {rid}: {data['game_name']} ({p_count} players) [{status}]")
        return {'status': 'success', 'rooms': room_list}

    elif cmd == 'join_room':
        room_id = request.get('room_id')
        
        with lobby_lock:  # [Lock] 修改 ROOMS
            if room_id in ROOMS:
                room = ROOMS[room_id]
                if room['status'] != 'WAITING':
                    return {'status': 'error', 'message': 'Game already started'}
                
                if user not in room['players']:
                    room['players'].append(user)
                return {'status': 'success', 'game_name': room['game_name']}
            else:
                return {'status': 'error', 'message': 'Room not found'}

    elif cmd == 'start_game':
        room_id = request.get('room_id')
        
        # 1. 先在鎖內檢查房間狀態並分配 Port (避免重複啟動)
        target_room = None
        with lobby_lock:
            if room_id in ROOMS:
                room = ROOMS[room_id]
                if room['status'] == 'WAITING':
                    # 標記為啟動中，避免其他 thread 同時啟動
                    room['status'] = 'STARTING' 
                    target_room = room
                elif room['status'] == 'PLAYING':
                     # 如果已經啟動，直接回傳既有的 Port
                     return {
                        'status': 'game_started', 
                        'server_ip': '127.0.0.1',
                        'server_port': room['game_port']
                    }
        
        if not target_room:
            return {'status': 'error', 'message': 'Room not found or already started'}

        # 2. 啟動 subprocess (比較耗時，可以放在鎖外面，或者在鎖內做完簡單操作)
        # 這裡為了安全與簡化，我們先分配 Port
        game_port = find_free_port()
        
        game_dir = os.path.join(EXTRACT_DIR, target_room['game_name'])
        script_path = os.path.join(game_dir, 'server.py') # 假設固定為 server.py
        
        if not os.path.exists(script_path):
            with lobby_lock: target_room['status'] = 'WAITING' # 失敗則還原
            return {'status': 'error', 'message': 'Server script not found'}

        print(f"[*] Starting Game Server: {script_path} on port {game_port}")
        
        try:
            # 啟動遊戲 Server
            subprocess.Popen([sys.executable, script_path, str(game_port)], cwd=game_dir)
            
            # 更新房間狀態
            with lobby_lock:
                target_room['game_port'] = game_port
                target_room['status'] = 'PLAYING'
            
            return {
                'status': 'game_started', 
                'server_ip': '127.0.0.1', 
                'server_port': game_port
            }
        except Exception as e:
            with lobby_lock: target_room['status'] = 'WAITING' # 失敗還原
            print(f"Failed to start game process: {e}")
            return {'status': 'error', 'message': str(e)}

    return {'status': 'error', 'message': 'Unknown command'}
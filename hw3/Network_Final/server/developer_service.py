# server/developer_service.py
import os
import zipfile # [Fix 4] 引入 zipfile
from common.protocol import recv_file
from server.db_manager import add_game_metadata

UPLOAD_DIR = 'server/uploaded_games'
EXTRACT_DIR = 'server/uploaded_games_extracted' # 解壓後的存放區

def handle_developer_upload(conn, request):
    game_name = request.get('game_name')
    if not game_name:
        return {'status': 'fail', 'message': 'Missing game_name'}

    # 確保目錄存在
    if not os.path.exists(UPLOAD_DIR): os.makedirs(UPLOAD_DIR)
    if not os.path.exists(EXTRACT_DIR): os.makedirs(EXTRACT_DIR)

    save_path = os.path.join(UPLOAD_DIR, f"{game_name}.zip")
    
    print(f"Receiving game file for: {game_name}...")
    try:
        # 1. 接收檔案
        recv_file(conn, save_path)
        
        # 2. [Fix 5] 立即解壓縮
        extract_path = os.path.join(EXTRACT_DIR, game_name)
        with zipfile.ZipFile(save_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)
        print(f"Game extracted to {extract_path}")

        # 3. 更新資料庫
        # 這裡簡化：假設 metadata 都在 request 裡，或者解壓後讀取 config
        game_info = {
            'game_name': game_name,
            'version': request.get('version', '1.0.0'),
            'description': request.get('description', 'No description'),
            # 預設執行檔名，實際應從 game_config.json 讀取
            'server_exe': 'server.py',
            'client_exe': 'client.py',
            'run_cmd': 'python'
        }
        add_game_metadata(game_info)
        
        return {'status': 'success', 'message': 'Upload and extraction complete'}
    except Exception as e:
        print(f"Upload error: {e}")
        return {'status': 'error', 'message': str(e)}
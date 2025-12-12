import os
import json
import shutil

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), 'template')
GAMES_DIR = os.path.join(os.path.dirname(__file__), 'games')

def create_template():
    print("=== Create New Game Project ===")
    game_name = input("Enter game name (english, no spaces): ").strip()
    
    if not game_name:
        print("Invalid name.")
        return

    target_dir = os.path.join(GAMES_DIR, game_name)
    if os.path.exists(target_dir):
        print(f"Error: Game '{game_name}' already exists.")
        return

    # 建立目錄
    os.makedirs(target_dir)
    
    # 建立預設 config
    config = {
        "name": game_name,
        "version": "1.0.0",
        "description": "Description here",
        "run_cmd": "python",
        "server_exe_file": "server.py",
        "client_exe_file": "client.py"
    }
    
    with open(os.path.join(target_dir, 'game_config.json'), 'w') as f:
        json.dump(config, f, indent=2)

    # 複製或建立基礎程式碼 (這裡簡單建立空檔案或範例)
    # Server
    with open(os.path.join(target_dir, 'server.py'), 'w') as f:
        f.write("# Game Server\nimport sys\n\nif __name__ == '__main__':\n    port = sys.argv[1]\n    print(f'Server started on port {port}')\n    # TODO: Implement server logic\n    while True: pass\n")
    
    # Client
    with open(os.path.join(target_dir, 'client.py'), 'w') as f:
        f.write("# Game Client\nimport sys\n\nif __name__ == '__main__':\n    ip = sys.argv[1]\n    port = sys.argv[2]\n    print(f'Connecting to {ip}:{port}')\n    # TODO: Implement client logic\n")

    print(f"Success! Game project created at: {target_dir}")
    print("Modify server.py and client.py to implement your game.")

if __name__ == '__main__':
    if not os.path.exists(GAMES_DIR):
        os.makedirs(GAMES_DIR)
    create_template()
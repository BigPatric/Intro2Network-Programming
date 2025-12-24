import sys
import os
import socket
import time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
# 也將專案根目錄加入路徑，便於匯入 common 與 lobby 的工具
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import threading
from game_client.network import NetworkClient
try:
    from config import LOBBY_HOST, LOBBY_PORT, GAME_CONNECT_HOST
except Exception:
    LOBBY_HOST, LOBBY_PORT = '127.0.0.1', 10000
    GAME_CONNECT_HOST = '127.0.0.1'
from game_client.renderer import Renderer
from game_client.input_handler import InputHandler
from common.protocol import send_msg, recv_msg
from lobby_server.db_client import DBClient
import pygame

class GameClientApp:
    def __init__(self, lobby_host=LOBBY_HOST, lobby_port=LOBBY_PORT, direct=None):
        self.name = None # 將在登入後設定
        self.lobby_host = lobby_host
        self.lobby_port = lobby_port
        self.lobby_sock = None
        self.current_room_id = None
        self.is_room_host = False
        # direct: (host, port) 直接連到 Game Server
        if direct:
            host, port = direct
            self._run_direct(host, port)
        else:
            self.main_menu()

    def main_menu(self):
        while True:
            print("\n--- Welcome to Tetris Duo ---")
            print("1. 登入 (Login)")
            print("2. 註冊 (Register)")
            print("3. 離開 (Exit)")
            choice = input("請輸入選項: ")

            if choice == '1':
                if self._login():
                    print(f"登入成功！歡迎，{self.name}。")
                    self.lobby_menu()
                    break # 離開 lobby_menu 後結束程式
                else:
                    print("登入失敗，請檢查名稱是否正確或伺服器是否運作中。")
            elif choice == '2':
                if self._register():
                    print("註冊成功！請返回主選單進行登入。")
                else:
                    print("註冊失敗，可能名稱已存在或伺服器未啟動。")
            elif choice == '3':
                if self.lobby_sock:
                    self.lobby_sock.close()
                break
            else:
                print("無效的選項。")

    def _connect_to_lobby(self):
        # 如果已有連線，先關閉舊的
        if self.lobby_sock:
            self.lobby_sock.close()
        
        self.lobby_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.lobby_sock.connect((self.lobby_host, self.lobby_port))
            return True
        except ConnectionRefusedError:
            print("[Client] 無法連線到 Lobby。請先啟動 DB 與 Lobby 伺服器。")
            return False
        except Exception as e:
            print(f"[Client] 連線時發生未知錯誤: {e}")
            return False

    def _login(self):
        name = input("請輸入您的名稱 (Your Name): ")
        password = input("請輸入密碼 (Password): ")
        if not name:
            return False
        if not self._connect_to_lobby():
            return False
        req_data = {"action": "login", "data": {"name": name, "password": password}}
        res = self._lobby_req(self.lobby_sock, req_data)
        if res and res.get('status') == 'ok':
            self.name = name # 登入成功，設定客戶端名稱
            return True
        return False

    def _register(self):
        name = input("請輸入要註冊的名稱 (Choose a Name): ")
        password = input("請設定密碼 (Set Password): ")
        confirm = input("再次輸入密碼 (Confirm Password): ")
        if password != confirm:
            print("兩次密碼不一致。")
            return False
        if not name:
            return False
        if not self._connect_to_lobby():
            return False

        res = self._lobby_req(self.lobby_sock, {"action": "register", "data": {"name": name, "password": password}})
        self.lobby_sock.close() # 註冊完就斷線，讓使用者重新登入
        if res and res.get('status') == 'ok':
            return True
        return False

    def _lobby_req(self, sock, payload):
        try:
            send_msg(sock, payload)
            return recv_msg(sock) or {}
        except (ConnectionResetError, BrokenPipeError):
            print("[Client] 與伺服器的連線中斷。")
            return None

    def lobby_menu(self):
        while True:
            print("\n--- Tetris Duo Lobby ---")
            print("1. 列出房間 (List Rooms)")
            print("2. 建立房間 (Create Room)")
            print("3. 加入房間 (Join Room)")
            print("4. 顯示線上使用者 (Show Online Users)")
            print("5. 登出 (Logout)")
            choice = input("請輸入選項: ")

            if choice == '1':
                self.list_rooms()
            elif choice == '2':
                self.create_room()
            elif choice == '3':
                self.join_room()
            elif choice == '4':
                self.show_online_users()
            elif choice == '5':
                self.lobby_sock.close()
                print("已登出。")
                break
            else:
                print("無效的選項，請重新輸入。")

    def show_online_users(self):
        res = self._lobby_req(self.lobby_sock, {"action": "list_users"})
        if not res:
            print("[Client] 取得線上使用者失敗。")
            return
        users = res.get('users', [])
        print("\n--- 線上使用者列表 ---")
        if not users:
            print("目前沒有線上使用者。")
        else:
            for u in users:
                print(f"- {u}")
        print("--------------------")

    def list_rooms(self):
        res = self._lobby_req(self.lobby_sock, {"action": "list_rooms"})
        if not res: return
        rooms = res.get('rooms', [])
        print("\n--- 公開房間列表 ---")
        if not rooms:
            print("目前沒有公開房間。")
        for r in rooms:
            players = ", ".join(r.get('players', []))
            print(f"ID: {r['id']}, Name: {r['name']}, Players: [{players}] ({len(r.get('players',[]))}/2), Status: {r['status']}")
        print("--------------------")

    def create_room(self):
        room_name = input("請輸入房間名稱 (留空則自動命名): ")
        if not room_name:
            room_name = f"Room-{self.name}"
        
        visibility = input("房間類型？(public/private，預設 public): ").strip().lower()
        if visibility not in ("public", "private"):
            visibility = "public"
        res = self._lobby_req(self.lobby_sock, {
            "action": "create_room",
            "data": {"name": room_name, "visibility": visibility}
        })
        if res and res.get('status') == 'ok':
            room = res['room']
            print(f"[Client] 已建立房間 #{room['id']}，等待另一位玩家加入...")
            self._wait_for_game_start(room['id'], is_host=True)
        elif res:
            print(f"[Client] 建立房間失敗: {res.get('error')}")

    def join_room(self):
        self.list_rooms()
        try:
            room_id_str = input("請輸入要加入的房間 ID: ")
            if not room_id_str: return
            room_id = int(room_id_str)
        except ValueError:
            print("無效的 ID。")
            return

        res = self._lobby_req(self.lobby_sock, {"action": "join_room", "data": {"room_id": room_id}})
        if res and res.get('status') == 'ok':
            room = res['room']
            print(f"[Client] 已加入房間 #{room['id']}")
            self._wait_for_game_start(room['id'], is_host=False)
        elif res:
            print(f"[Client] 加入房間失敗: {res.get('error')}")

    def _wait_for_game_start(self, room_id, is_host):
        game_port = None
        start_deadline = time.time() + 120

        print("[Client] 等待遊戲開始...")
        while time.time() < start_deadline and game_port is None:
            time.sleep(2)
            if is_host:
                # 房主需要主動檢查並啟動遊戲
                # 為了不阻塞，我們用一個新的短連線來操作
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_check:
                    s_check.connect((self.lobby_host, self.lobby_port))
                    # 重新建立短連線時，使用空密碼即可通過舊帳號（無密碼）的相容流程
                    self._lobby_req(s_check, {"action": "login", "data": {"name": self.name, "password": ""}})
                    lr = self._lobby_req(s_check, {"action": "list_rooms"})
                    my_room = next((r for r in lr.get('rooms', []) if r.get('id') == room_id), None)

                    if my_room and len(my_room.get('players', [])) >= 2:
                        sg = self._lobby_req(s_check, {"action": "start_game", "data": {"room_id": room_id}})
                        if sg and sg.get('status') == 'ok':
                            game_port = sg.get('game_port')
                            print(f"[Client] 遊戲開始，取得 game_port={game_port}")
                            break 
            else:
                # 非房主，只需被動等待 game_port 出現
                # 我們也用短連線來查詢，避免主連線邏輯混亂
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_check:
                    s_check.connect((self.lobby_host, self.lobby_port))
                    self._lobby_req(s_check, {"action": "login", "data": {"name": self.name, "password": ""}})
                    res = self._lobby_req(s_check, {"action": "list_rooms"})
                    my_room = next((r for r in res.get('rooms', []) if r.get('id') == room_id), None)
                    if my_room and my_room.get('game_port'):
                        game_port = my_room['game_port']
                        print(f"[Client] 偵測到房間已開始，game_port={game_port}")
                        break
        
        # 記錄房間資訊（不關閉 lobby 連線）
        self.current_room_id = room_id
        self.is_room_host = is_host

        if not game_port:
            print("[Client] 等待對手或 game_port 超時。")
            return

        self.start_game_connection(GAME_CONNECT_HOST, game_port, room_id)

    def start_game_connection(self, game_host, game_port, room_id):
        print(f"[Client] Connecting to Game Server at {game_host}:{game_port}")
        time.sleep(1)  # wait for game server to start
        self.renderer = Renderer()
        self.input_handler = InputHandler(None)  # 先建立，稍後補上 network
        self._welcome_data = None
        self._game_over = None

        def on_welcome(msg):
            self._welcome_data = msg

        def on_game_over(msg):
            self._game_over = msg

        # 用 NetworkClient 並指定 callbacks
        self.net = NetworkClient(game_host, game_port, on_snapshot=self.on_snapshot, on_welcome=on_welcome, on_game_over=on_game_over)
        if not self.net.connected:
            print("[Client] 無法連線到 Game Server。")
            return

        # 送 HELLO
        self.net.hello(userId=self.name)

        # 等待 WELCOME callback
        wait_start = time.time()
        while self._welcome_data is None and self.net.connected and time.time() - wait_start < 5:
            time.sleep(0.05)
        welcome = self._welcome_data
        if not welcome:
            print("[Client] 沒收到 WELCOME 或連線中斷。")
            return

        role = welcome.get('role', 'P1')
        seed = welcome.get('seed')
        start_time = int(time.time() * 1000)
        effective_room_id = room_id if room_id is not None else game_port
        self.renderer.set_room_info(effective_room_id, role, start_time, user_name=self.name)
        self.input_handler.network = self.net  # 補上 network

        # 主迴圈：分離事件輪詢與渲染，降低 pygame 事件衝突
        while self._game_over is None:
            self.input_handler.pump()  # 處理鍵盤事件並送出
            if self.input_handler.quit_requested or not self.net.connected:
                break
            self.renderer.render_frame()  # 單幀渲染

        # 遊戲迴圈結束（玩家關閉視窗或斷線）
        try:
            import pygame
            pygame.display.quit()
            pygame.quit()
        except Exception:
            pass

        # 若遊戲正常結束（收到 GAME_OVER）
        if self._game_over:
            print("\n=== 對局結束 ===")
            winner = self._game_over.get('winner')
            summary = self._game_over.get('summary', {})
            if winner:
                print(f"勝方: {winner}")
            else:
                print("平手！")
            print("成績:")
            for n, info in summary.items():
                print(f" - {n}: 分數 {info.get('score')} 行 {info.get('lines')}")
            self._room_post_game_loop(effective_room_id)
        else:
            # 非正常：玩家中途退出或斷線，回到 Lobby 選單
            if self.lobby_sock:
                print("[Client] 對局中途結束，返回 Lobby 選單。")
                self.lobby_menu()
            else:
                self.main_menu()

    def _room_post_game_loop(self, room_id):
        # 讓房主可以選擇再戰，其他玩家等待
        while True:
            if self.is_room_host:
                print("\n房間選項: 1=再戰 (Start Again)  2=退出房間回 Lobby  3=離開程式")
                opt = input("選擇: ")
                if opt == '1':
                    # 房主啟動 start_game
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s_check:
                        s_check.connect((self.lobby_host, self.lobby_port))
                        self._lobby_req(s_check, {"action": "login", "data": {"name": self.name, "password": ""}})
                        sg = self._lobby_req(s_check, {"action": "start_game", "data": {"room_id": room_id}})
                        if sg and sg.get('status') == 'ok':
                            game_port = sg.get('game_port')
                            print(f"[Client] 再戰開始，game_port={game_port}")
                            self.start_game_connection(GAME_CONNECT_HOST, game_port, room_id)
                            return
                        else:
                            print("[Client] 無法啟動再戰，可能人數不足。")
                elif opt == '2':
                    print("[Client] 離開房間，返回 Lobby 選單。")
                    self.lobby_menu()
                    return
                elif opt == '3':
                    print("[Client] 再見！")
                    return
                else:
                    print("無效選項。")
            else:
                print("等待房主選擇是否再戰，或輸入 q 退出房間回 Lobby。")
                ipt = input("(q 退出): ")
                if ipt.lower() == 'q':
                    print("[Client] 離開房間，返回 Lobby 選單。")
                    self.lobby_menu()
                    return
                # 其他輸入忽略，繼續等待

    def on_snapshot(self, msg):
        if msg.get('type') != 'SNAPSHOT':
            return
        players = msg.get('players', {})
        if not players:
            return
        # assign states
        if self.name in players:
            my_state = players[self.name]
            opp_state = None
            for n, s in players.items():
                if n != self.name:
                    opp_state = s
                    break
        else:
            my_state = None
            opp_state = list(players.values())[0]
        self.renderer.update_state(my_state, opp_state)

    # main_loop 已整合到 start_game_connection，不再需要獨立 main_loop

    def _run_direct(self, host, port):
        # 直接連到遊戲伺服器，不經 Lobby。適合本地兩人測試。
        print("\n--- 直連模式 (Direct Mode) ---")
        if not self.name:
            self.name = input("請輸入您的名稱 (Your Name): ") or "Player"
        try:
            self.start_game_connection(host, int(port), None)
        except Exception as e:
            print(f"[Client] 連線失敗或中斷: {e}")
            print("提示：請先在另一個終端啟動 Game Server，例如：\n  uv run -m game_server.game_server 10002")
        # 直連模式下結束即整個程序結束
        return

if __name__ == '__main__':
    # 可選參數：--direct host:port
    direct = None
    for i, arg in enumerate(sys.argv[1:]):
        if arg == '--direct' and i+2 <= len(sys.argv[1:]):
            hp = sys.argv[1:][i+1]
            if ':' in hp:
                h, p = hp.split(':', 1)
                direct = (h, p)
            break
    GameClientApp(direct=direct)
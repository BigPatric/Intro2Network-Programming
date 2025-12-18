import tkinter as tk
from tkinter import messagebox, simpledialog
from lobby_client import LobbyClient
import os
import threading
import shutil

class LobbyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("玩家大廳")
        self.client = LobbyClient()
        if not self.client.connect():
            messagebox.showerror("錯誤", "無法連線到伺服器")
            root.destroy()
            return

        self.login_frame = tk.Frame(root)
        self.register_frame = tk.Frame(root)
        self.lobby_frame = tk.Frame(root)
        self.room_frame = tk.Frame(root)

        self.setup_login_frame()
        self.setup_register_frame()
        self.setup_lobby_frame()
        self.setup_room_frame()

        self.login_frame.pack()

    def hide_all_frames(self):
        self.login_frame.pack_forget()
        self.register_frame.pack_forget()
        self.lobby_frame.pack_forget()
        self.room_frame.pack_forget()

    def setup_login_frame(self):
        tk.Label(self.login_frame, text="帳號:").grid(row=0, column=0)
        tk.Label(self.login_frame, text="密碼:").grid(row=1, column=0)
        self.username_entry = tk.Entry(self.login_frame)
        self.password_entry = tk.Entry(self.login_frame, show="*")
        self.username_entry.grid(row=0, column=1)
        self.password_entry.grid(row=1, column=1)
        tk.Button(self.login_frame, text="登入", command=self.login).grid(row=2, column=0)
        tk.Button(self.login_frame, text="註冊", command=self.show_register_frame).grid(row=2, column=1)
        tk.Button(self.login_frame, text="離開", command=self.exit_app).grid(row=2, column=2)

    def setup_register_frame(self):
        tk.Label(self.register_frame, text="註冊新玩家帳號").grid(row=0, column=0, columnspan=2, pady=5)
        tk.Label(self.register_frame, text="帳號:").grid(row=1, column=0)
        tk.Label(self.register_frame, text="密碼:").grid(row=2, column=0)
        tk.Label(self.register_frame, text="再次輸入密碼:").grid(row=3, column=0)
        self.reg_username_entry = tk.Entry(self.register_frame)
        self.reg_password_entry = tk.Entry(self.register_frame, show="*")
        self.reg_password_confirm_entry = tk.Entry(self.register_frame, show="*")
        self.reg_username_entry.grid(row=1, column=1)
        self.reg_password_entry.grid(row=2, column=1)
        self.reg_password_confirm_entry.grid(row=3, column=1)
        tk.Label(self.register_frame, text="帳號: 4-16字母或數字\n密碼: 6-20字母或數字").grid(row=4, column=0, columnspan=2, pady=5)
        tk.Button(self.register_frame, text="註冊", command=self.register).grid(row=5, column=0)
        tk.Button(self.register_frame, text="返回", command=self.show_login_frame).grid(row=5, column=1)

    def setup_lobby_frame(self):
        self.welcome_label = tk.Label(self.lobby_frame, text="歡迎來到遊戲大廳")
        self.welcome_label.pack(pady=10)
        self.games_listbox = tk.Listbox(self.lobby_frame, width=40)
        self.games_listbox.pack()
        tk.Button(self.lobby_frame, text="顯示上線玩家", command=self.show_online_players).pack()
        tk.Button(self.lobby_frame, text="顯示遊戲房間", command=self.show_game_rooms).pack()     
        tk.Button(self.lobby_frame, text="刷新遊戲商城", command=self.refresh_games).pack()
        tk.Button(self.lobby_frame, text="我的遊戲", command=self.show_my_games).pack()
        tk.Button(self.lobby_frame, text="建立房間", command=self.create_room).pack()
        tk.Button(self.lobby_frame, text="登出", command=self.logout).pack()

    def setup_room_frame(self):
        self.room_label = tk.Label(self.room_frame, text="房間資訊")
        self.room_label.pack()
        self.start_btn = tk.Button(self.room_frame, text="開始遊戲", command=self.start_game)
        self.start_btn.pack()
        self.leave_btn = tk.Button(self.room_frame, text="離開房間", command=self.leave_room)
        self.leave_btn.pack()

    def show_register_frame(self):
        self.hide_all_frames()
        self.reg_username_entry.delete(0, 'end')
        self.reg_password_entry.delete(0, 'end')
        self.reg_password_confirm_entry.delete(0, 'end')
        self.register_frame.pack()

    def show_login_frame(self):
        self.hide_all_frames()
        self.username_entry.delete(0, 'end')
        self.password_entry.delete(0, 'end')
        self.login_frame.pack()

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        success, msg = self.client.login_with_credentials(username, password)
        if success:
            messagebox.showinfo("登入成功", msg)
            self.hide_all_frames()
            self.lobby_frame.pack()
            self.refresh_games()
            
        else:
            messagebox.showerror("登入失敗", str(msg))

    def register(self):
        username = self.reg_username_entry.get()
        password = self.reg_password_entry.get()
        password2 = self.reg_password_confirm_entry.get()
        # 帳號密碼規則檢查
        if not (4 <= len(username) <= 16 and username.isalnum()):
            messagebox.showerror("格式錯誤", "帳號需為4-16字母或數字")
            return
        if not (6 <= len(password) <= 20 and password.isalnum()):
            messagebox.showerror("格式錯誤", "密碼需為6-20字母或數字")
            return
        if password != password2:
            messagebox.showerror("密碼不一致", "兩次輸入的密碼不一致")
            return
        success = self.client.register_user(username, password)
        if success:
            messagebox.showinfo("註冊成功", "您已成功註冊，請重新登入")
            self.show_login_frame()
        else:
            messagebox.showerror("註冊失敗", "此帳號已被使用")

    def show_online_players(self):
        players = self.client.get_online_players()
        messagebox.showinfo("上線玩家", "\n".join(players) if players else "目前沒有玩家上線")

    def show_game_rooms(self):
        rooms = self.client.list_rooms()
        top = tk.Toplevel(self.root)
        top.title("遊戲房間列表")
        top.geometry("400x300")
        if not rooms:
            tk.Label(top, text="目前沒有房間").pack(pady=20)
        else:
            tk.Label(top, text="房間列表：").pack()
            room_listbox = tk.Listbox(top, width=50)
            room_listbox.pack()
            for room in rooms:
                room_listbox.insert(
                    tk.END,
                    f"{room['room_id']} | {room['game']} | Host: {room['host']} | Players: {room.get('player_count', '?')}"                )
            def join_selected():
                sel = room_listbox.curselection()
                if not sel:
                    messagebox.showwarning("提示", "請選擇一個房間")
                    return
                room_id = rooms[sel[0]]['room_id']
                game_name = rooms[sel[0]]['game']
                # check if downloaded
                ## later add the version check
                user_dir = os.path.join('player/downloads', self.client.username, game_name)
                if not os.path.exists(user_dir):
                    res = messagebox.askyesno("尚未下載", f"你尚未下載 {game_name}，是否現在下載？")
                    if res:
                        ok = self.client.download_game(game_name)
                        if not ok:
                            messagebox.showerror("下載失敗", "遊戲下載失敗")
                            return
                    else:
                        return
                success, msg = self.client.join_room(room_id)
                if success:
                    self.client.start_listening()
                    messagebox.showinfo("加入房間", "加入成功！" + str(msg))
                    self.hide_all_frames()
                    self.room_frame.pack()
                else:
                    messagebox.showerror("加入失敗", "加入失敗：" + str(msg))
            tk.Button(top, text="加入房間", command=join_selected).pack()
        tk.Button(top, text="返回", command=top.destroy).pack(pady=5)

    def refresh_games(self):
        self.games_listbox.delete(0, tk.END)
        # The title
        if not hasattr(self, 'store_title_label'):
            self.store_title_label = tk.Label(self.lobby_frame, text="遊戲商城", font=("Arial", 16, "bold"))
            self.store_title_label.pack(before=self.games_listbox)
        # The entry
        if not hasattr(self, 'games_list_title'):
            self.games_list_title = tk.Label(self.lobby_frame, text="Game Name | Developer", font=("Arial", 12, "bold"), anchor="w", justify="left")
            self.games_list_title.pack(before=self.games_listbox)
        self.games_info = self.client.get_game_list()  # 存下所有遊戲資訊
        for g in self.games_info:
            display = f"{g.get('game_name', '')} | {g.get('maker', '')}"
            self.games_listbox.insert(tk.END, display)
        if not hasattr(self, 'download_btn'):
            self.download_btn = tk.Button(self.lobby_frame, text="下載", command=self.download_selected_game)
            self.download_btn.pack()
        # 綁定雙擊事件
        self.games_listbox.bind('<Double-Button-1>', self.show_game_detail)

    def show_game_detail(self, event):
        selection = self.games_listbox.curselection()
        if not selection:
            return
        idx = selection[0]
        game = self.games_info[idx]
        detail = f"遊戲名稱: {game.get('game_name', '')}\n"
        detail += f"製作者: {game.get('maker', '')}\n"
        detail += f"版本: {game.get('version', '')}\n"
        detail += f"描述: {game.get('description', '')}\n"
        # 顯示評論
        reviews = game.get('reviews', [])
        if reviews:
            detail += "\n評論：\n"
            for r in reviews:
                detail += f"- {r}\n"
        import tkinter as tk
        top = tk.Toplevel(self.root)
        top.title("遊戲詳細資訊")
        label = tk.Label(top, text=detail, justify="left", anchor="w", font=("Arial", 12))
        label.pack(padx=20, pady=20)

    def download_selected_game(self):
        selection = self.games_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "請先選擇一個遊戲")
            return
        game_info = self.games_listbox.get(selection[0])
        game_name = game_info.split(' ')[0]
        user_dir = os.path.join('player/downloads', self.client.username, game_name)
        if os.path.exists(user_dir):
            shutil.rmtree(user_dir)
        ok = self.client.download_game(game_name)
        if ok:
            messagebox.showinfo("下載成功", f"遊戲 {game_name} 下載完成")
        else:
            messagebox.showerror("下載失敗", f"遊戲 {game_name} 下載失敗")

    def create_room(self):
        game_name = self.choose_downloaded_game()
        if not game_name:
            return
        success, result = self.client.create_room(game_name)
        if success:
            self.client.start_listening()
            messagebox.showinfo("建立房間", "房間建立成功，房號：" + str(result))
            self.hide_all_frames()
            self.room_frame.pack()
        else:
            messagebox.showerror("建立失敗", "建立房間失敗：" + str(result))

    def show_my_games(self):
        user_dir = os.path.join('player/downloads', self.client.username)
        if not os.path.exists(user_dir):
            messagebox.showinfo("我的遊戲", "你尚未下載任何遊戲")
            return
        games = [d for d in os.listdir(user_dir) if os.path.isdir(os.path.join(user_dir, d))]
        if not games:
            messagebox.showinfo("我的遊戲", "你尚未下載任何遊戲")
        else:
            messagebox.showinfo("我的遊戲", "\n".join(games))

    def leave_room(self):
        self.hide_all_frames()
        self.lobby_frame.pack()

    def logout(self):
        try:
            if self.client.username:
                self.client.logout()
        except Exception as e:
            print(f"登出時發生錯誤: {e}")
        self.hide_all_frames()
        self.login_frame.pack()
        self.username_entry.delete(0, 'end')
        self.password_entry.delete(0, 'end')
        self.client.username = None
        self.welcome_label.config(text="歡迎來到遊戲大廳")
        
    def start_game(self):
        print("starting game...")
        if hasattr(self.client, 'current_room_id'):
            self.client.start_game(self.client.current_room_id)
        else:
            messagebox.showerror("error", "無法取得房間ID")   

    def choose_downloaded_game(self):
        user_dir = os.path.join('player/downloads', self.client.username)
        if not os.path.exists(user_dir):
            messagebox.showinfo("我的遊戲", "你尚未下載任何遊戲")
            return None
        games = [d for d in os.listdir(user_dir) if os.path.isdir(os.path.join(user_dir, d))]
        if not games:
            messagebox.showinfo("我的遊戲", "你尚未下載任何遊戲")
            return None
        msg = "你已下載的遊戲：\n" + "\n".join(games) + "\n請輸入要選擇的遊戲名稱："
        game_name = simpledialog.askstring("選擇遊戲", msg)
        if game_name not in games:
            messagebox.showerror("錯誤", "請輸入正確的遊戲名稱")
            return None
        return game_name

    def exit_app(self):
        print()
        print("Goodbye...")
        self.client.close()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("800x600")
    app = LobbyGUI(root)
    root.mainloop()
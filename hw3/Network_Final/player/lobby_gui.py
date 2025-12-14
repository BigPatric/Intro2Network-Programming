import tkinter as tk
from tkinter import messagebox, simpledialog
from lobby_client import LobbyClient

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
        tk.Button(self.lobby_frame, text="瀏覽遊戲商城", command=self.refresh_games).pack()
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
            messagebox.showerror("登入失敗", "帳號或密碼錯誤")

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
                room_listbox.insert(tk.END, room)
        tk.Button(top, text="返回", command=top.destroy).pack(pady=5)

    def refresh_games(self):
        self.games_listbox.delete(0, tk.END)
        games = self.client.get_game_list()
        for g in games:
            self.games_listbox.insert(tk.END, g)

    def create_room(self):
        selection = self.games_listbox.curselection()
        if not selection:
            messagebox.showwarning("提示", "請先選擇一個遊戲")
            return
        game_info = self.games_listbox.get(selection[0])
        game_name = game_info.split(' ')[0]
        success, result = self.client.create_room(game_name)
        if success:
            messagebox.showinfo("建立房間", "房間建立成功，房號：" + str(result))
            self.hide_all_frames()
            self.room_frame.pack()
        else:
            messagebox.showerror("建立失敗", "建立房間失敗：" + str(result))

    def show_my_games(self):
        messagebox.showinfo("我的遊戲", "showing downloaded games")

    def leave_room(self):
        self.hide_all_frames()
        self.lobby_frame.pack()

    def logout(self):
        if self.client.username:
            self.client.logout()
        self.hide_all_frames()
        self.login_frame.pack()
        self.username_entry.delete(0, 'end')
        self.password_entry.delete(0, 'end')
        self.client.username = None
        self.welcome_label.config(text="歡迎來到遊戲大廳")

    def wait_for_game_start(self):
        print("waiting for game to start...")

    def start_game(self):
        print("starting game...")

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
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from developer.dev_client import DeveloperClient

class DevGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("開發者模式")
        self.client = DeveloperClient()
        if not self.client.connect():
            self.root.destroy()
            return
        self.selected_folder = None

        self.login_frame = tk.Frame(root)
        self.register_frame = tk.Frame(root)
        self.upload_frame = tk.Frame(root)

        self.setup_login_frame()
        self.setup_register_frame()
        self.setup_upload_frame()

        self.login_frame.pack()

    def hide_all_frames(self):
        self.login_frame.pack_forget()
        self.register_frame.pack_forget()
        self.upload_frame.pack_forget()

    def setup_login_frame(self):
        tk.Label(self.login_frame, text="帳號:").grid(row=0, column=0)
        tk.Label(self.login_frame, text="密碼:").grid(row=1, column=0)
        self.username_entry = tk.Entry(self.login_frame)
        self.password_entry = tk.Entry(self.login_frame, show="*")
        self.username_entry.grid(row=0, column=1)
        self.password_entry.grid(row=1, column=1)
        tk.Button(self.login_frame, text="登入", command=self.login).grid(row=2, column=0)
        tk.Button(self.login_frame, text="註冊", command=self.show_register_frame).grid(row=2, column=1)

    def setup_register_frame(self):
        tk.Label(self.register_frame, text="註冊新開發者帳號").grid(row=0, column=0, columnspan=2, pady=5)
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

    def setup_upload_frame(self):
        tk.Label(self.upload_frame, text="選擇要上傳的遊戲資料夾").pack(pady=10)
        tk.Button(self.upload_frame, text="選擇資料夾", command=self.select_folder).pack()
        self.selected_label = tk.Label(self.upload_frame, text="")
        self.selected_label.pack()
        tk.Button(self.upload_frame, text="上傳遊戲", command=self.upload_game).pack(pady=10)
        tk.Button(self.upload_frame, text="登出", command=self.logout).pack()

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
        res = self.client.login(username, password)
        if res and res.get('status') == 'success':
            self.hide_all_frames()
            messagebox.showinfo("登入成功", f"歡迎 {username}")
            self.upload_frame.pack()
        else:
            messagebox.showerror("登入失敗", res.get('message', '帳號或密碼錯誤'))

    def register(self):
        username = self.reg_username_entry.get()
        password = self.reg_password_entry.get()
        password2 = self.reg_password_confirm_entry.get()
        if not (4 <= len(username) <= 16 and username.isalnum()):
            messagebox.showerror("格式錯誤", "帳號需為4-16字母或數字")
            return
        if not (6 <= len(password) <= 20 and password.isalnum()):
            messagebox.showerror("格式錯誤", "密碼需為6-20字母或數字")
            return
        if password != password2:
            messagebox.showerror("密碼不一致", "兩次輸入的密碼不一致")
            return
        res = self.client.register(username, password)
        if res and res.get('status') == 'success':
            messagebox.showinfo("註冊成功", "您已成功註冊，請重新登入")
            self.show_login_frame()
        else:
            messagebox.showerror("註冊失敗", res.get('message', '此帳號已被使用'))

    def select_folder(self):
        folder = filedialog.askdirectory(initialdir=os.path.abspath("developer/games"))
        if folder:
            self.selected_folder = folder
            self.selected_label.config(text=os.path.basename(folder))

    def upload_game(self):
        res = self.client.upload_game(self.selected_folder)
        if res and res.get('status') == 'success':
            messagebox.showinfo("上傳成功", res.get('message', '上傳成功'))
        else:
            messagebox.showerror("上傳失敗", res.get('message', '未知錯誤'))

    def logout(self):
        self.client.logout()
        self.hide_all_frames()
        self.upload_frame.pack_forget()
        self.login_frame.pack()
        self.username_entry.delete(0, 'end')
        self.password_entry.delete(0, 'end')

if __name__ == '__main__':
    root = tk.Tk()
    root.geometry("400x300")
    app = DevGUI(root)
    def on_closing():
        app.client.close()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
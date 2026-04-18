
import os

gui_content = r'''
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import sys
import os
import time

# 導入原本的下載邏輯
try:
    from extract_m3u8 import download_video
except ImportError:
    messagebox.showerror("CRITICAL ERROR", "System Core 'extract_m3u8.py' not found.")
    sys.exit(1)

class CyberButton(tk.Canvas):
    """自定義霓虹發光按鈕"""
    def __init__(self, parent, text, command=None, color="#00F0FF", width=200, height=45):
        super().__init__(parent, width=width, height=height, bg="#0F0F13", highlightthickness=0, cursor="hand2")
        self.command = command
        self.color = color
        self.text = text
        self.width = width
        self.height = height
        
        self.rect = self.create_rounded_rect(2, 2, width-2, height-2, radius=10, outline=color, width=2, fill="#1A1A23")
        self.label = self.create_text(width/2, height/2, text=text, fill=color, font=("Microsoft JhengHei", 10, "bold"))
        
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<Button-1>", self.on_click)

    def create_rounded_rect(self, x1, y1, x2, y2, radius=10, **kwargs):
        points = [x1+radius, y1, x1+radius, y1, x2-radius, y1, x2-radius, y1, x2, y1, x2, y1+radius, x2, y1+radius, x2, y2-radius, x2, y2-radius, x2, y2, x2-radius, y2, x2-radius, y2, x1+radius, y2, x1+radius, y2, x1, y2, x1, y2-radius, x1, y2-radius, x1, y1+radius, x1, y1+radius, x1, y1]
        return self.create_polygon(points, **kwargs, smooth=True)

    def on_enter(self, e):
        self.itemconfig(self.rect, fill="#2D2D3F", width=3)
        self.itemconfig(self.label, fill="#FFFFFF")

    def on_leave(self, e):
        self.itemconfig(self.rect, fill="#1A1A23", width=2)
        self.itemconfig(self.label, fill=self.color)

    def on_click(self, e):
        if self.command:
            self.command()

class DownloaderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("⚡ HUGO DOWNLOADER: NEON OVERDRIVE ⚡")
        self.root.geometry("1000x800")
        self.root.configure(bg="#0F0F13")
        
        self.colors = {
            "bg": "#0F0F13",
            "card": "#1A1A23",
            "cyan": "#00F0FF",
            "purple": "#BD00FF",
            "green": "#39FF14",
            "red": "#FF3131",
            "dim": "#555566"
        }
        
        # --- UI 佈局 ---
        self.main = tk.Frame(root, bg=self.colors["bg"], padx=40, pady=30)
        self.main.pack(fill="both", expand=True)
        
        # 標題
        title_box = tk.Frame(self.main, bg=self.colors["bg"])
        title_box.pack(fill="x", pady=(0, 30))
        tk.Label(title_box, text="NEON OVERDRIVE", font=("Consolas", 28, "bold"), fg=self.colors["cyan"], bg=self.colors["bg"]).pack(side="left")
        tk.Label(title_box, text="DOWNLOADER v3.0", font=("Consolas", 10), fg=self.colors["purple"], bg=self.colors["bg"]).pack(side="left", padx=15, pady=(15, 0))

        # 輸入區卡片
        input_frame = tk.Frame(self.main, bg=self.colors["card"], padx=25, pady=25, highlightbackground=self.colors["purple"], highlightthickness=1)
        input_frame.pack(fill="x")
        
        tk.Label(input_frame, text="TARGET URL / 影片網址", font=("Microsoft JhengHei", 9, "bold"), fg=self.colors["cyan"], bg=self.colors["card"]).pack(anchor="w")
        
        entry_row = tk.Frame(input_frame, bg=self.colors["card"])
        entry_row.pack(fill="x", pady=(10, 20))
        
        self.url_entry = tk.Entry(entry_row, font=("Microsoft JhengHei", 12), bg="#0F0F13", fg="white", insertbackground=self.colors["cyan"], borderwidth=0)
        self.url_entry.pack(side="left", fill="x", expand=True, ipady=8)
        tk.Frame(entry_row, height=2, bg=self.colors["cyan"]).place(relx=0, rely=1, relwidth=1)
        
        self.add_btn = CyberButton(entry_row, "＋ ADD TO QUEUE", command=self.add_to_queue, color=self.colors["purple"], width=160)
        self.add_btn.pack(side="right", padx=(20, 0))

        # 路徑設定
        tk.Label(input_frame, text="SAVE PATH / 儲存路徑", font=("Microsoft JhengHei", 9, "bold"), fg=self.colors["dim"], bg=self.colors["card"]).pack(anchor="w")
        path_row = tk.Frame(input_frame, bg=self.colors["card"])
        path_row.pack(fill="x", pady=(5, 0))
        
        self.dir_path = tk.StringVar(value=r"G:\AI下載")
        self.dir_entry = tk.Entry(path_row, textvariable=self.dir_path, font=("Consolas", 10), bg=self.colors["card"], fg=self.colors["dim"], borderwidth=0)
        self.dir_entry.pack(side="left", fill="x", expand=True)
        
        tk.Button(path_row, text="BROWSE", command=self.select_dir, font=("Consolas", 8), bg="#2D2D3F", fg="white", relief="flat", padx=10).pack(side="right")

        # 隊列區
        mid_row = tk.Frame(self.main, bg=self.colors["bg"])
        mid_row.pack(fill="x", pady=(30, 10))
        tk.Label(mid_row, text="SYSTEM QUEUE / 下載隊列", font=("Consolas", 11, "bold"), fg="white", bg=self.colors["bg"]).pack(side="left")
        tk.Button(mid_row, text="CLEAR COMPLETED", command=self.clear_completed, font=("Consolas", 8), bg=self.colors["bg"], fg=self.colors["red"], relief="flat").pack(side="right")

        # 自定義 Treeview 樣式
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Cyber.Treeview", background=self.colors["card"], foreground="white", fieldbackground=self.colors["card"], rowheight=40, borderwidth=0)
        style.configure("Cyber.Treeview.Heading", background="#0F0F13", foreground=self.colors["cyan"], font=("Consolas", 10, "bold"), borderwidth=0)
        style.map("Cyber.Treeview", background=[("selected", "#2D2D3F")])

        self.tree = ttk.Treeview(self.main, columns=("id", "url", "status", "progress"), show="headings", style="Cyber.Treeview")
        self.tree.heading("id", text="ID")
        self.tree.heading("url", text="SOURCE URL")
        self.tree.heading("status", text="STATUS")
        self.tree.heading("progress", text="PROGRESS")
        self.tree.column("id", width=50, anchor="center")
        self.tree.column("url", width=500)
        self.tree.column("status", width=150, anchor="center")
        self.tree.column("progress", width=150, anchor="center")
        self.tree.pack(fill="both", expand=True)

        # 底部日誌與啟動
        footer = tk.Frame(self.main, bg=self.colors["bg"])
        footer.pack(fill="x", pady=(30, 0))
        
        self.log_text = tk.Text(footer, height=5, bg="#050507", fg=self.colors["green"], font=("Consolas", 9), borderwidth=1, relief="flat", padx=10, pady=10)
        self.log_text.pack(side="left", fill="x", expand=True, padx=(0, 20))
        
        self.start_btn = CyberButton(footer, "⚡ INITIATE DOWNLOAD", command=self.start_batch_download, color=self.colors["cyan"], width=220, height=80)
        self.start_btn.pack(side="right")

        self.download_queue = []
        self.is_running = False
        self.task_counter = 0

    def select_dir(self):
        selected = filedialog.askdirectory(initialdir=self.dir_path.get())
        if selected: self.dir_path.set(selected)

    def log(self, msg):
        self.log_text.insert(tk.END, f"> {msg}\n")
        self.log_text.see(tk.END)

    def add_to_queue(self):
        url = self.url_entry.get().strip()
        if not url: return
        self.task_counter += 1
        tid = self.tree.insert("", "end", values=(self.task_counter, url, "WAITING", "0%"))
        self.download_queue.append({"id": self.task_counter, "url": url, "tree_id": tid, "status": "WAITING"})
        self.url_entry.delete(0, tk.END)
        self.log(f"TASK ADDED: {url}")
        if not self.is_running: self.root.after(100, self.start_batch_download)

    def clear_completed(self):
        for item in self.tree.get_children():
            if "DONE" in self.tree.item(item)["values"][2]: self.tree.delete(item)
        self.download_queue = [t for t in self.download_queue if self.tree.exists(t["tree_id"])]

    def start_batch_download(self):
        if self.is_running: return
        self.is_running = True
        threading.Thread(target=self.process_queue, daemon=True).start()

    def process_queue(self):
        while self.is_running:
            task = next((t for t in self.download_queue if t["status"] == "WAITING"), None)
            if not task: break
            
            task["status"] = "ACTIVE"
            self.root.after(0, lambda: self.tree.item(task["tree_id"], values=(task["id"], task["url"], "🔥 DOWNLOADING", "0%")))
            self.log(f"INITIATING: {task['url']}")
            
            try:
                download_video(task["url"], output_dir=self.dir_path.get(), progress_callback=lambda p: self.root.after(0, lambda: self.tree.item(task["tree_id"], values=(task["id"], task["url"], "🔥 DOWNLOADING", f"{p:.1f}%"))))
                task["status"] = "DONE"
                self.root.after(0, lambda: self.tree.item(task["tree_id"], values=(task["id"], task["url"], "✅ DONE", "100%")))
            except Exception as e:
                task["status"] = "FAILED"
                self.root.after(0, lambda: self.tree.item(task["tree_id"], values=(task["id"], task["url"], "❌ FAILED", "ERROR")))
                self.log(f"CRITICAL FAILURE: {e}")
            
        self.is_running = False
        self.log("SYSTEM STANDBY / ALL TASKS COMPLETED")

if __name__ == "__main__":
    root = tk.Tk()
    app = DownloaderGUI(root)
    root.mainloop()
'''

# 1. 寫入全新的下載器檔案
with open(r"G:\AI下載\downloader_cyber.py", "w", encoding="utf-8") as f:
    f.write(gui_content.strip())

# 2. 更新啟動批次檔，指向新檔案
bat_content = r'''@echo off
cd /d "%~dp0"
start "" pythonw downloader_cyber.py
exit
'''
with open(r"G:\AI下載\啟動下載器.bat", "w", encoding="utf-8") as f:
    f.write(bat_content.strip())

print("✅ 已更新為 NEON OVERDRIVE 版本，並修改了啟動腳本。")

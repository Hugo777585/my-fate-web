# downloader_gui.py 
# Download Master Pro - Modern GUI 
# 需要安裝： 
# pip install customtkinter yt-dlp 

import os 
import threading 
import subprocess 
import tkinter as tk 
from tkinter import filedialog, messagebox 
import customtkinter as ctk 


APP_TITLE = "Download Master Pro" 
DEFAULT_DIR = os.path.join(os.path.expanduser("~"), "Downloads") 


ctk.set_appearance_mode("dark") 
ctk.set_default_color_theme("blue") 


class DownloadMaster(ctk.CTk): 
    def __init__(self): 
        super().__init__() 

        self.title(APP_TITLE) 
        self.geometry("980x680") 
        self.minsize(880, 600) 

        self.accent_color = "#7C3AED" 
        self.output_dir = DEFAULT_DIR 
        self.opacity_value = 0.96 

        self.configure(fg_color="#0F111A") 
        self.attributes("-alpha", self.opacity_value) 

        self.grid_columnconfigure(0, weight=1) 
        self.grid_rowconfigure(1, weight=1) 

        self.build_header() 
        self.build_body() 
        self.build_footer() 

    def build_header(self): 
        self.header = ctk.CTkFrame( 
            self, 
            height=210, 
            corner_radius=22, 
            fg_color="#171A26" 
        ) 
        self.header.grid(row=0, column=0, padx=18, pady=(18, 10), sticky="nsew") 
        self.header.grid_propagate(False) 

        self.header.grid_columnconfigure(0, weight=3) 
        self.header.grid_columnconfigure(1, weight=1) 

        left = ctk.CTkFrame(self.header, fg_color="transparent") 
        left.grid(row=0, column=0, padx=24, pady=20, sticky="nsew") 
        left.grid_columnconfigure(0, weight=1) 

        title = ctk.CTkLabel( 
            left, 
            text="⚡ Download Master Pro", 
            font=ctk.CTkFont(size=30, weight="bold"), 
            text_color="#FFFFFF" 
        ) 
        title.grid(row=0, column=0, sticky="w") 

        subtitle = ctk.CTkLabel( 
            left, 
            text="高質感影音下載工具｜支援影片、音訊、下載資料夾、進度追蹤", 
            font=ctk.CTkFont(size=14), 
            text_color="#AAB0C5" 
        ) 
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 18)) 

        self.url_entry = ctk.CTkEntry( 
            left, 
            placeholder_text="貼上影片網址，例如 YouTube / 其他 yt-dlp 支援網站", 
            height=46, 
            corner_radius=14, 
            fg_color="#0F111A", 
            border_color="#2A2F45", 
            border_width=1, 
            text_color="#FFFFFF", 
            placeholder_text_color="#717891" 
        ) 
        self.url_entry.grid(row=2, column=0, sticky="ew", pady=(0, 12)) 

        controls = ctk.CTkFrame(left, fg_color="transparent") 
        controls.grid(row=3, column=0, sticky="ew") 
        controls.grid_columnconfigure(0, weight=1) 
        controls.grid_columnconfigure(1, weight=1) 
        controls.grid_columnconfigure(2, weight=1) 

        self.mode_menu = ctk.CTkOptionMenu( 
            controls, 
            values=["影片 MP4", "音訊 MP3", "最佳格式"], 
            height=40, 
            corner_radius=12, 
            fg_color=self.accent_color, 
            button_color=self.accent_color, 
            button_hover_color="#5B21B6" 
        ) 
        self.mode_menu.grid(row=0, column=0, padx=(0, 8), sticky="ew") 
        self.mode_menu.set("影片 MP4") 

        self.quality_menu = ctk.CTkOptionMenu( 
            controls, 
            values=["最佳品質", "1080p", "720p", "480p"], 
            height=40, 
            corner_radius=12, 
            fg_color="#24293A", 
            button_color="#30364A", 
            button_hover_color="#3C435A" 
        ) 
        self.quality_menu.grid(row=0, column=1, padx=8, sticky="ew") 
        self.quality_menu.set("最佳品質") 

        self.folder_btn = ctk.CTkButton( 
            controls, 
            text="📁 選擇資料夾", 
            height=40, 
            corner_radius=12, 
            fg_color="#24293A", 
            hover_color="#343B52", 
            command=self.choose_folder 
        ) 
        self.folder_btn.grid(row=0, column=2, padx=(8, 0), sticky="ew") 

        right = ctk.CTkFrame(self.header, fg_color="#111421", corner_radius=20) 
        right.grid(row=0, column=1, padx=(0, 20), pady=20, sticky="nsew") 
        right.grid_columnconfigure(0, weight=1) 

        ctk.CTkLabel( 
            right, 
            text="外觀設定", 
            font=ctk.CTkFont(size=18, weight="bold"), 
            text_color="#FFFFFF" 
        ).grid(row=0, column=0, padx=18, pady=(18, 10), sticky="w") 

        self.color_menu = ctk.CTkOptionMenu( 
            right, 
            values=["紫色", "藍色", "綠色", "橘色", "紅色"], 
            command=self.change_color, 
            height=36, 
            corner_radius=12 
        ) 
        self.color_menu.grid(row=1, column=0, padx=18, pady=6, sticky="ew") 
        self.color_menu.set("紫色") 

        ctk.CTkLabel( 
            right, 
            text="透明度", 
            text_color="#AAB0C5" 
        ).grid(row=2, column=0, padx=18, pady=(12, 2), sticky="w") 

        self.opacity_slider = ctk.CTkSlider( 
            right, 
            from_=0.75, 
            to=1.0, 
            number_of_steps=25, 
            command=self.change_opacity, 
            progress_color=self.accent_color 
        ) 
        self.opacity_slider.grid(row=3, column=0, padx=18, pady=(0, 12), sticky="ew") 
        self.opacity_slider.set(self.opacity_value) 

    def build_body(self): 
        self.body = ctk.CTkFrame( 
            self, 
            corner_radius=22, 
            fg_color="#171A26" 
        ) 
        self.body.grid(row=1, column=0, padx=18, pady=10, sticky="nsew") 
        self.body.grid_columnconfigure(0, weight=1) 
        self.body.grid_rowconfigure(1, weight=1) 

        top = ctk.CTkFrame(self.body, fg_color="transparent") 
        top.grid(row=0, column=0, padx=22, pady=(20, 10), sticky="ew") 
        top.grid_columnconfigure(0, weight=1) 

        self.status_label = ctk.CTkLabel( 
            top, 
            text=f"目前儲存位置：{self.output_dir}", 
            text_color="#AAB0C5", 
            font=ctk.CTkFont(size=13) 
        ) 
        self.status_label.grid(row=0, column=0, sticky="w") 

        self.start_btn = ctk.CTkButton( 
            top, 
            text="🚀 開始下載", 
            width=150, 
            height=42, 
            corner_radius=14, 
            fg_color=self.accent_color, 
            hover_color="#5B21B6", 
            command=self.start_download 
        ) 
        self.start_btn.grid(row=0, column=1, sticky="e") 

        self.progress = ctk.CTkProgressBar( 
            self.body, 
            height=14, 
            corner_radius=10, 
            progress_color=self.accent_color, 
            fg_color="#2A2F45" 
        ) 
        self.progress.grid(row=1, column=0, padx=22, pady=(4, 14), sticky="ew") 
        self.progress.set(0) 

        self.log_box = ctk.CTkTextbox( 
            self.body, 
            corner_radius=18, 
            fg_color="#0F111A", 
            border_color="#2A2F45", 
            border_width=1, 
            text_color="#DCE2F2", 
            font=ctk.CTkFont(size=13) 
        ) 
        self.log_box.grid(row=2, column=0, padx=22, pady=(0, 22), sticky="nsew") 
        self.log("系統已就緒。請貼上網址後開始下載。") 

        self.body.grid_rowconfigure(2, weight=1) 

    def build_footer(self): 
        self.footer = ctk.CTkFrame(self, height=48, fg_color="transparent") 
        self.footer.grid(row=2, column=0, padx=18, pady=(0, 12), sticky="ew") 
        self.footer.grid_columnconfigure(0, weight=1) 

        ctk.CTkLabel( 
            self.footer, 
            text="提示：若下載失敗，請先確認 yt-dlp 是否已安裝，或執行 pip install -U yt-dlp customtkinter", 
            text_color="#747B91", 
            font=ctk.CTkFont(size=12) 
        ).grid(row=0, column=0, sticky="w") 

    def choose_folder(self): 
        folder = filedialog.askdirectory(initialdir=self.output_dir) 
        if folder: 
            self.output_dir = folder 
            self.status_label.configure(text=f"目前儲存位置：{self.output_dir}") 
            self.log(f"已切換下載資料夾：{self.output_dir}") 

    def change_color(self, value): 
        colors = { 
            "紫色": "#7C3AED", 
            "藍色": "#2563EB", 
            "綠色": "#059669", 
            "橘色": "#EA580C", 
            "紅色": "#DC2626", 
        } 

        self.accent_color = colors.get(value, "#7C3AED") 

        self.mode_menu.configure( 
            fg_color=self.accent_color, 
            button_color=self.accent_color 
        ) 
        self.start_btn.configure(fg_color=self.accent_color) 
        self.progress.configure(progress_color=self.accent_color) 
        self.opacity_slider.configure(progress_color=self.accent_color) 

        self.log(f"主題色已切換：{value}") 

    def change_opacity(self, value): 
        self.opacity_value = float(value) 
        self.attributes("-alpha", self.opacity_value) 

    def log(self, text): 
        self.log_box.insert("end", f"{text}\n") 
        self.log_box.see("end") 

    def start_download(self): 
        url = self.url_entry.get().strip() 

        if not url: 
            messagebox.showwarning("缺少網址", "請先貼上影片網址。") 
            return 
 
        self.start_btn.configure(state="disabled", text="下載中...") 
        self.progress.set(0.08) 
        self.log("開始建立下載任務...") 
        self.log(f"網址：{url}") 
 
        thread = threading.Thread(target=self.download_worker, args=(url,), daemon=True) 
        thread.start() 
 
    def build_command(self, url): 
        mode = self.mode_menu.get() 
        quality = self.quality_menu.get() 
 
        output_template = os.path.join(self.output_dir, "%(title)s.%(ext)s") 
 
        cmd = [ 
            "python", 
            "-m", 
            "yt_dlp", 
            url, 
            "-o", 
            output_template, 
            "--newline" 
        ] 
 
        if mode == "音訊 MP3": 
            cmd += [ 
                "-x", 
                "--audio-format", 
                "mp3", 
                "--audio-quality", 
                "0" 
            ] 
 
        elif mode == "影片 MP4": 
            if quality == "1080p": 
                cmd += ["-f", "bestvideo[height<=1080]+bestaudio/best[height<=1080]"] 
            elif quality == "720p": 
                cmd += ["-f", "bestvideo[height<=720]+bestaudio/best[height<=720]"] 
            elif quality == "480p": 
                cmd += ["-f", "bestvideo[height<=480]+bestaudio/best[height<=480]"] 
            else: 
                cmd += ["-f", "bestvideo+bestaudio/best"] 
 
            cmd += ["--merge-output-format", "mp4"] 
 
        else: 
            cmd += ["-f", "best"] 
 
        return cmd 
 
    def download_worker(self, url): 
        try: 
            cmd = self.build_command(url) 
 
            self.safe_log("執行下載引擎 yt-dlp...") 
            self.safe_log(" ".join(cmd)) 
 
            process = subprocess.Popen( 
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                text=True, 
                encoding="utf-8", 
                errors="replace" 
            ) 
 
            for line in process.stdout: 
                line = line.strip() 
                if line: 
                    self.safe_log(line) 
                    self.update_progress_from_line(line) 
 
            process.wait() 
 
            if process.returncode == 0: 
                self.safe_progress(1.0) 
                self.safe_log("✅ 下載完成。") 
            else: 
                self.safe_log("❌ 下載失敗，請檢查網址或 yt-dlp 是否需要更新。") 
 
        except FileNotFoundError: 
            self.safe_log("❌ 找不到 yt-dlp。請先執行：pip install -U yt-dlp") 
        except Exception as e: 
            self.safe_log(f"❌ 發生錯誤：{e}") 
        finally: 
            self.after(0, lambda: self.start_btn.configure(state="normal", text="🚀 開始下載")) 
 
    def update_progress_from_line(self, line): 
        if "[download]" in line and "%" in line: 
            try: 
                percent_part = line.split("%")[0].split()[-1] 
                percent = float(percent_part) / 100 
                self.safe_progress(percent) 
            except Exception: 
                pass 
 
    def safe_log(self, text): 
        self.after(0, lambda: self.log(text)) 
 
    def safe_progress(self, value): 
        self.after(0, lambda: self.progress.set(value)) 
 
 
if __name__ == "__main__": 
    app = DownloadMaster() 
    app.mainloop()

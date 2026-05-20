import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import re
import tkinter as tk
from tkinter import scrolledtext, messagebox
import threading
import re
from openai import OpenAI
import os # 強制開啟 Windows 高解析度支援（解決字體模糊問題）
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
except:
    pass
                           
# 本地金鑰檔名
CONFIG_FILENAME = 'api_config.txt'

class HugoAIEditor:
	def __init__(self, root):
		self.root = root
		self.root.title("⚡ HUGO AI CODE EDITOR v1.0 ⚡")
		self.root.geometry("1200x800")
		self.root.configure(bg="#0F0F13")
		
		self.colors = {"bg": "#0F0F13", "card": "#1A1A23", "cyan": "#00F0FF", "text": "#E0E0E0"}

		# 左側：程式碼編輯區
		self.left_frame = tk.Frame(self.root, bg=self.colors["bg"], padx=10, pady=10)
		self.left_frame.place(relx=0, rely=0, relwidth=0.7, relheight=1)
		self.left_frame_label = tk.Label(self.left_frame, text="< CODE EDITOR />", fg=self.colors["cyan"], bg=self.colors["bg"], font=("Consolas", 14, "bold"))
		self.left_frame_label.pack(anchor="w", pady=(0, 10))
		self.code_editor = scrolledtext.ScrolledText(self.left_frame, bg=self.colors["card"], fg=self.colors["text"], font=("Consolas", 12), insertbackground=self.colors["cyan"], borderwidth=0)
		self.code_editor.pack(fill="both", expand=True)

		# 右側：AI 助手對話區
		self.right_frame = tk.Frame(self.root, bg="#15151D", padx=10, pady=10)
		self.right_frame.place(relx=0.7, rely=0, relwidth=0.3, relheight=1)
		self.right_label = tk.Label(self.right_frame, text="⚡ AI ASSISTANT", fg=self.colors["cyan"], bg="#15151D", font=("Consolas", 14, "bold"))
		self.right_label.pack(anchor="w", pady=(0, 10))
		
		# API Key 輸入與儲存區
		self.api_key_var = tk.StringVar()
		self.client = None
		self.api_key = None
		self._key_visible = False

		key_row = tk.Frame(self.right_frame, bg="#15151D")
		key_row.pack(fill="x", pady=(0, 8))
		self.key_label = tk.Label(key_row, text="API Key:", fg="#888899", bg="#15151D", font=("Microsoft JhengHei", 9))
		self.key_label.pack(side="left")
		self.api_key_entry = tk.Entry(key_row, textvariable=self.api_key_var, show='*', font=("Consolas", 10), bg=self.colors["bg"], fg="white", borderwidth=1, relief="solid")
		self.api_key_entry.pack(side="left", fill="x", expand=True, padx=(6,6))
		self.show_key_btn = tk.Button(key_row, text="👁", command=self.toggle_key_visibility, bg="#2D2D3F", fg=self.colors["cyan"], relief="flat", width=3)
		self.show_key_btn.pack(side="left")
		self.save_key_btn = tk.Button(key_row, text="💾 儲存金鑰", command=self.save_api_key, bg="#1A1A23", fg="#39FF14", relief="flat")
		self.save_key_btn.pack(side="left", padx=(6,0))

		# 載入本地金鑰（若存在）
		self.load_api_key()

		self.chat_history = scrolledtext.ScrolledText(self.right_frame, bg=self.colors["bg"], fg=self.colors["text"], font=("Microsoft JhengHei", 10), borderwidth=0, state='disabled')
		self.chat_history.pack(fill="both", expand=True, pady=(0, 10))
		# 設定 chat_history 的 tag，用於程式碼區塊的視覺化
		self.chat_history.tag_configure('codeblock', background='#050507', foreground='#39FF14', font=('Consolas', 10))
		self.chat_history.tag_configure('normal', foreground=self.colors['text'], font=('Microsoft JhengHei', 10))

		self.prompt_label = tk.Label(self.right_frame, text="Prompt 指令:", fg="#888899", bg="#15151D", font=("Microsoft JhengHei", 10))
		self.prompt_label.pack(anchor="w")
		self.prompt_entry = tk.Entry(self.right_frame, font=("Microsoft JhengHei", 11), bg=self.colors["bg"], fg="white", insertbackground=self.colors["cyan"], borderwidth=1, relief="solid")
		self.prompt_entry.pack(fill="x", ipady=5, pady=(5, 8))

		# 按鈕列（送出 + 套用）
		btn_row = tk.Frame(self.right_frame, bg="#15151D")
		btn_row.pack(fill="x")
		self.ask_btn = tk.Button(btn_row, text="🚀 送出給 AI", command=self.ask_ai_thread, bg="#2D2D3F", fg=self.colors["cyan"], font=("Microsoft JhengHei", 11, "bold"), relief="flat", cursor="hand2")
		self.ask_btn.pack(side="left", fill="x", expand=True, ipady=8, padx=(0,6))

		self.apply_btn = tk.Button(btn_row, text="📋 套用至編輯區", command=self.apply_code_from_latest_ai, bg="#1A1A23", fg="#39FF14", font=("Microsoft JhengHei", 10, "bold"), relief="flat", cursor="hand2")
		self.apply_btn.pack(side="right", ipady=8)

		# 儲存最近一則 AI 回覆的文字（用於套用程式碼）
		self.last_ai_reply = None

	def log_chat(self, sender, message):
		# 插入訊息並對 code block 做簡單的高亮（以 tag 處理）
		self.chat_history.config(state='normal')
		header = f"[{sender}]\n"
		self.chat_history.insert(tk.END, header, 'normal')

		code_blocks = re.split(r"(```(?:python)?\n.*?```)", message, flags=re.DOTALL)
		for part in code_blocks:
			if not part:
				continue
			if part.startswith('```') and part.rstrip().endswith('```'):
				# 取出內部程式碼，不包含 ``` 標記
				inner = re.sub(r"^```(?:python)?\n|```$", "", part, flags=re.DOTALL)
				self.chat_history.insert(tk.END, inner + "\n\n", 'codeblock')
			else:
				self.chat_history.insert(tk.END, part + "\n\n", 'normal')

		self.chat_history.see(tk.END)
		self.chat_history.config(state='disabled')

		# 若是 AI 回覆，儲存內容以供套用按鈕使用
		if sender.upper() == 'AI':
			self.last_ai_reply = message

	def extract_code_blocks(self, text):
		if not text:
			return []
		return re.findall(r"```(?:python)?\n(.*?)```", text, flags=re.DOTALL)

	def apply_code_from_latest_ai(self):
		if not self.last_ai_reply:
			messagebox.showinfo("套用程式碼", "尚無 AI 回覆可供套用。")
			return
		blocks = self.extract_code_blocks(self.last_ai_reply)
		if not blocks:
			messagebox.showinfo("套用程式碼", "找不到程式碼區塊。請先讓 AI 回覆包含 ```python 的程式碼。")
			return
		# 預設採用第一個程式碼區塊，覆蓋編輯器內容
		code = blocks[0].rstrip() + "\n"
		self.code_editor.delete("1.0", tk.END)
		self.code_editor.insert(tk.END, code)
		self.log_chat("SYSTEM", "已將 AI 程式碼套用到編輯區。")

	def _get_config_path(self):
		# 使用腳本目錄下的 config 檔
		base = os.path.dirname(os.path.abspath(__file__))
		return os.path.join(base, CONFIG_FILENAME)

	def load_api_key(self):
		path = self._get_config_path()
		if os.path.exists(path):
			try:
				with open(path, 'r', encoding='utf-8') as f:
					key = f.read().strip()
					if key:
						self.api_key_var.set(key)
						self.api_key = key
						self.init_client(key)
			except Exception as e:
				self.log_chat('SYSTEM', f'讀取金鑰失敗: {e}')

	def save_api_key(self):
		key = self.api_key_var.get().strip()
		if not key:
			messagebox.showwarning('儲存金鑰', '金鑰不可為空。')
			return
		path = self._get_config_path()
		try:
			with open(path, 'w', encoding='utf-8') as f:
				f.write(key)
			self.api_key = key
			self.init_client(key)
			self.log_chat('SYSTEM', '金鑰已儲存並初始化。')
		except Exception as e:
			messagebox.showerror('儲存金鑰', f'寫入失敗: {e}')

	def toggle_key_visibility(self):
		self._key_visible = not self._key_visible
		if self._key_visible:
			self.api_key_entry.config(show='')
			self.show_key_btn.config(text='🙈')
		else:
			self.api_key_entry.config(show='*')
			self.show_key_btn.config(text='👁')

	def init_client(self, key):
		try:
			self.client = OpenAI(api_key=key)
			self.log_chat('SYSTEM', 'OpenAI client 已初始化。')
		except Exception as e:
			self.client = None
			self.log_chat('SYSTEM', f'初始化 OpenAI client 失敗: {e}')

	def ask_ai_thread(self):
		prompt = self.prompt_entry.get().strip()
		if not prompt: return
		# 防呆：需先設定 API Key
		if not self.client:
			messagebox.showwarning('需要 API Key', '請先填入並儲存你的 OpenAI API Key！')
			return
		
		code_context = self.code_editor.get("1.0", tk.END).strip()
		self.prompt_entry.delete(0, tk.END)
		self.log_chat("HUGO", prompt)
		self.ask_btn.config(text="⏳ AI 思考中...", state="disabled")
		
		threading.Thread(target=self.call_openai_api, args=(prompt, code_context), daemon=True).start()

	def call_openai_api(self, prompt, code_context):
		try:
			system_msg = "你是一個專業的資深工程師。請根據使用者提供的程式碼與指令，給出修改建議或除錯結果。"
			user_msg = f"我的程式碼如下：\n```python\n{code_context}\n```\n\n我的問題/指令：{prompt}"

			response = self.client.chat.completions.create(
				model="gpt-3.5-turbo", 
				messages=[
					{"role": "system", "content": system_msg},
					{"role": "user", "content": user_msg}
				],
				temperature=0.3
			)

			ai_reply = response.choices[0].message.content
			self.root.after(0, lambda: self.log_chat("AI", ai_reply))
		
		except Exception as e:
			self.root.after(0, lambda: self.log_chat("SYSTEM ERROR", str(e)))
		
		finally:
			self.root.after(0, lambda: self.ask_btn.config(text="🚀 送出給 AI", state="normal"))

if __name__ == "__main__":
	root = tk.Tk()
	app = HugoAIEditor(root)
	root.mainloop()

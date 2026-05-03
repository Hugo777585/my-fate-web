from google import genai
import os

# 診斷模型可用性
api_key = "AIzaSyAyrM5rk3-TVID44iHWCUwvdnT0sAOEx4c"
client = genai.Client(api_key=api_key)

print("--- 正在列出目前 API Key 可用的模型 ---")
try:
    for m in client.models.list():
        print(f"模型名稱: {m.name}, 顯示名稱: {m.display_name}")
except Exception as e:
    print(f"列出模型時出錯: {e}")

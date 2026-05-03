import os
import google.generativeai as genai
from dotenv import load_dotenv

# 載入 .env 檔案
load_dotenv()

# 獲取 API Key
my_key = os.getenv("GOOGLE_API_KEY")

if not my_key:
    print("❌ 錯誤：在 .env 檔案中找不到 GOOGLE_API_KEY")
else:
    print(f"✅ 成功讀取 API Key (前四碼): {my_key[:4]}...")
    
    # 配置 API
    genai.configure(api_key=my_key)

    try:
        print("\n--- 你的 API Key 目前真正能用的模型名單 ---")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
        print("------------------------------------------")
        
        # 執行一個簡單的生成測試
        print("\n🚀 正在執行簡單的生成測試 (使用 gemini-flash-latest)...")
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content("你好，請跟我說聲嗨！")
        print(f"🤖 AI 回覆：{response.text}")
        print("\n✨ Gemini API 連線測試成功！")
        
    except Exception as e:
        print(f"\n❌ API 連線或執行發生錯誤：{e}")

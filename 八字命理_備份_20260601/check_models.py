import google.generativeai as genai
import os

api_key = "AIzaSyDmxSH4B2B9cytqI4tfH8TEszOc_q4uvoQ"
genai.configure(api_key=api_key)

print("--- 您的新 API Key 可用的模型清單 ---")
try:
    models = genai.list_models()
    for m in models:
        if 'generateContent' in m.supported_generation_methods:
            print(f"ID: {m.name}, Display: {m.display_name}")
    
    print("\n--- 實際生成測試 (gemini-2.0-flash) ---")
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content("Hello, this is a connection test. Please reply with 'Success!'.")
    print(f"AI 回應: {response.text}")
    
except Exception as e:
    print(f"錯誤: {e}")
print("--------------------------------")

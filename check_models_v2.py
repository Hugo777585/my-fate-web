import google.generativeai as genai
import os

api_key = "AIzaSyDmxSH4B2B9cytqI4tfH8TEszOc_q4uvoQ"
genai.configure(api_key=api_key)

print("--- 實際生成測試 (gemini-2.5-flash) ---")
try:
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content("Hello, this is a connection test. Please reply with 'Success!'.")
    print(f"AI 回應: {response.text}")
except Exception as e:
    print(f"錯誤: {e}")

print("\n--- 實際生成測試 (gemini-1.5-pro) ---")
try:
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content("Hello, this is a connection test. Please reply with 'Success!'.")
    print(f"AI 回應: {response.text}")
except Exception as e:
    print(f"錯誤: {e}")

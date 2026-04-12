import google.generativeai as genai

my_key = "AIzaSyDmxSH4B2B9cytqI4tfH8TEszOc_q4uvoQ".strip()

# 就是漏了下面這一行！把鑰匙交給套件
genai.configure(api_key=my_key)

print("--- 你的 API Key 目前真正能用的模型名單 ---")
for m in genai.list_models():
    if 'generateContent' in m.supported_generation_methods:
        print(m.name)
print("------------------------------------------")
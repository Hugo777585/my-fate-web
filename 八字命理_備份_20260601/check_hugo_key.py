
import json
import os

def verify_key():
    key_file = "hugo-key.json"
    if not os.path.exists(key_file):
        print(f"❌ 錯誤：找不到 {key_file}")
        return

    try:
        with open(key_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            email = data.get("client_email", "未知")
            print(f"✅ 成功讀取 {key_file}")
            print(f"📧 目前服務帳號 Email: {email}")
            
            if "hugo-new-crm" in email:
                print("✨ 確認為最新的 hugo-new-crm 帳號！")
            else:
                print("⚠️ 注意：這似乎不是最新的 hugo-new-crm 帳號。")
                
    except Exception as e:
        print(f"❌ 讀取時發生錯誤：{e}")

if __name__ == "__main__":
    verify_key()

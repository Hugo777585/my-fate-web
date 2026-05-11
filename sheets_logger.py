import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit as st

def log_to_sheets(client_name, gender, birth_date, birth_time, mbti, report_summary):
    # 1. 設定連線權限與金鑰檔案
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    
    # 從 st.secrets 讀取憑證
    service_account_info = None
    if "GCP_SERVICE_ACCOUNT" in st.secrets:
        service_account_info = dict(st.secrets["GCP_SERVICE_ACCOUNT"])
    elif "gcp_service_account" in st.secrets:
        service_account_info = dict(st.secrets["gcp_service_account"])
    
    if service_account_info:
        if "private_key" in service_account_info:
            service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")
        creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)
    else:
        # 如果沒有 secrets，使用本地檔案（但不推薦）
        creds = ServiceAccountCredentials.from_json_keyfile_name('google-credentials.json', scope)
    
    client = gspread.authorize(creds)

    # 2. 開啟您的試算表 (請將括號內換成您試算表的真正名稱)
    try:
        sheet = client.open("雨果天命智庫客戶紀錄").sheet1 
        
        # 3. 準備要寫入的一列資料
        # 這裡我們預留了欄位：時間、姓名、性別、生日、時辰、MBTI、解析摘要
        import datetime
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        row = [timestamp, client_name, gender, birth_date, birth_time, mbti, report_summary]

        # 4. 寫入資料 (使用 USER_ENTERED 確保公式能運作)
        sheet.append_row(row, value_input_option='USER_ENTERED')
        print(f"✅ 成功！客戶 {client_name} 的資料已紀錄至試算表。")
        
    except Exception as e:
        print(f"❌ 發生錯誤：{e}")

# --- 測試執行 ---
if __name__ == "__main__":
    # 這裡可以先試跑一筆資料看看
    log_to_sheets("測試小幫手", "女", "1990-01-01", "12:00", "ENFP", "這是一筆測試紀錄")
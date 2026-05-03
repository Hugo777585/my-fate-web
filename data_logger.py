import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import datetime
import hashlib
import uuid
import os

def get_gsheet_client():
    """初始化並回傳 Google Sheets 客戶端"""
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        
        # 支援 Streamlit Cloud Secrets 與 local secrets.toml
        if "gcp_service_account" in st.secrets:
            service_account_info = dict(st.secrets["gcp_service_account"])
            if "private_key" in service_account_info:
                service_account_info["private_key"] = service_account_info["private_key"].replace("\\n", "\n")
            
            creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            return gspread.authorize(creds)
        elif os.path.exists("hugo-key.json"):
            creds = Credentials.from_service_account_file("hugo-key.json", scopes=scopes)
            return gspread.authorize(creds)
        else:
            return None
    except Exception as e:
        print(f"初始化 Google Sheets 失敗: {e}")
        return None

def ensure_worksheet(sheet_name, headers):
    """確保工作表存在且標題列正確"""
    try:
        client = get_gsheet_client()
        if not client: return None
        
        spreadsheet_id = st.secrets.get("google_sheets", {}).get("spreadsheet_id")
        if not spreadsheet_id: return None
        
        spreadsheet = client.open_by_key(spreadsheet_id)
        
        try:
            worksheet = spreadsheet.worksheet(sheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows="100", cols=len(headers))
            if headers:
                worksheet.append_row(headers)
            return worksheet
            
        # 檢查標題列
        current_headers = worksheet.row_values(1)
        if not current_headers and headers:
            worksheet.append_row(headers)
            
        return worksheet
    except Exception as e:
        print(f"確保工作表 {sheet_name} 失敗: {e}")
        return None

def get_anonymous_id():
    """取得匿名化的 IP Hash 與 User Agent"""
    try:
        # 嘗試從 Streamlit 1.34.0+ 的 st.context 取得資訊
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = st.context.headers
            ip = headers.get("X-Forwarded-For", "unknown").split(",")[0]
            ua = headers.get("User-Agent", "unknown")
        else:
            # 舊版 Streamlit 或是本地運行 fallback
            ip = "127.0.0.1"
            ua = "local-browser"
            
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]
        return ip_hash, ua
    except Exception as e:
        print(f"取得匿名 ID 失敗: {e}")
        return "unknown_hash", "unknown_ua"

def append_user_submission(data):
    """將使用者輸入資料寫入 Google Sheets"""
    try:
        headers = [
            "created_at", "user_name", "gender", "job_status", 
            "birth_year", "birth_month", "birth_day", "birth_hour", "birth_minute",
            "analysis_mode", "question", "is_couple_mode",
            "partner_name", "partner_gender", "partner_birth_year", 
            "partner_birth_month", "partner_birth_day", "partner_birth_hour", "partner_birth_minute",
            "user_ip_hash", "user_agent", "session_id"
        ]
        
        worksheet = ensure_worksheet("user_submissions", headers)
        if not worksheet: return
        
        ip_hash, ua = get_anonymous_id()
        
        # 限制問題長度
        safe_question = str(data.get("question", ""))[:3000]
        
        row = [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data.get("user_name"),
            data.get("gender"),
            data.get("job_status"),
            data.get("birth_year"),
            data.get("birth_month"),
            data.get("birth_day"),
            data.get("birth_hour"),
            data.get("birth_minute"),
            data.get("analysis_mode"),
            safe_question,
            "Yes" if data.get("is_couple_mode") else "No",
            data.get("partner_name", ""),
            data.get("partner_gender", ""),
            data.get("partner_birth_year", ""),
            data.get("partner_birth_month", ""),
            data.get("partner_birth_day", ""),
            data.get("partner_birth_hour", ""),
            data.get("partner_birth_minute", ""),
            ip_hash,
            ua,
            st.session_state.get('session_id', 'no_session')
        ]
        worksheet.append_row(row)
    except Exception as e:
        print(f"寫入 user_submissions 失敗: {e}")

def log_site_visit(page_name):
    """紀錄網站瀏覽紀錄，相同 session 僅紀錄一次同頁面瀏覽"""
    try:
        if 'visited_pages' not in st.session_state:
            st.session_state.visited_pages = set()
            
        if page_name in st.session_state.visited_pages:
            return
            
        headers = [
            "visited_at", "page_name", "session_id", 
            "user_ip_hash", "user_agent", "referrer", 
            "screen_width", "screen_height"
        ]
        
        worksheet = ensure_worksheet("site_visits", headers)
        if not worksheet: return
        
        ip_hash, ua = get_anonymous_id()
        referrer = ""
        try: referrer = st.context.headers.get("Referer", "")
        except: pass
        
        row = [
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            page_name,
            st.session_state.get('session_id', 'no_session'),
            ip_hash,
            ua,
            referrer,
            "", # screen_width 暫無直接取得方式
            ""  # screen_height 暫無直接取得方式
        ]
        worksheet.append_row(row)
        st.session_state.visited_pages.add(page_name)
    except Exception as e:
        print(f"寫入 site_visits 失敗: {e}")

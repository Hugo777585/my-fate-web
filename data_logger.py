import streamlit as st
from pyairtable import Table
import datetime
import hashlib
import uuid


def get_airtable_credentials():
    """從 Streamlit Secrets 中讀取 Airtable API Key 與 Base ID。"""
    api_key = st.secrets.get("AIRTABLE_API_KEY") or st.secrets.get("airtable_api_key")
    base_id = st.secrets.get("AIRTABLE_BASE_ID") or st.secrets.get("airtable_base_id")

    if not api_key:
        st.error("⚠️ 無法取得 Airtable API Key，請在 Streamlit Secrets 中設定 AIRTABLE_API_KEY。")
        print("Airtable 認證失敗：缺少 AIRTABLE_API_KEY")
        return None, None

    if not base_id:
        st.error("⚠️ 無法取得 Airtable Base ID，請在 Streamlit Secrets 中設定 AIRTABLE_BASE_ID。")
        print("Airtable 認證失敗：缺少 AIRTABLE_BASE_ID")
        return None, None

    return api_key, base_id


def get_airtable_table(table_name):
    api_key, base_id = get_airtable_credentials()
    if not api_key or not base_id:
        return None

    try:
        return Table(api_key, base_id, table_name)
    except Exception as e:
        st.error(f"⚠️ 無法建立 Airtable 客戶端：{e}")
        print(f"Airtable 客戶端初始化失敗: {e}")
        import traceback
        print(traceback.format_exc())
        return None


def get_anonymous_id():
    """取得匿名化的 IP Hash 與 User Agent"""
    try:
        if hasattr(st, "context") and hasattr(st.context, "headers"):
            headers = st.context.headers
            ip = headers.get("X-Forwarded-For", "unknown").split(",")[0]
            ua = headers.get("User-Agent", "unknown")
        else:
            ip = "127.0.0.1"
            ua = "local-browser"

        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:16]
        return ip_hash, ua
    except Exception as e:
        print(f"取得匿名 ID 失敗: {e}")
        return "unknown_hash", "unknown_ua"


def append_user_submission(data):
    """目前僅保留接口，實際寫入僅記錄分析結果與網站訪客。"""
    print("Airtable logging: user_submissions skipped.")


def log_site_visit(page_name):
    """紀錄網站訪客資料到 Airtable site_visits 表。"""
    try:
        if 'visited_pages' not in st.session_state:
            st.session_state.visited_pages = set()

        if page_name in st.session_state.visited_pages:
            return

        table = get_airtable_table("site_visits")
        if not table:
            return

        ip_hash, ua = get_anonymous_id()
        referrer = ""
        try:
            referrer = st.context.headers.get("Referer", "")
        except Exception:
            pass

        record = {
            "Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Page Name": page_name,
            "Session ID": st.session_state.get('session_id', 'no_session'),
            "IP Hash": ip_hash,
            "User Agent": ua,
            "Referrer": referrer,
            "Screen Width": "",
            "Screen Height": ""
        }
        table.create(record)
        st.session_state.visited_pages.add(page_name)
    except Exception as e:
        st.error(f"⚠️ Airtable 寫入失敗，site_visits 錯誤：{e}")
        print(f"寫入 site_visits 失敗: {e}")
        import traceback
        print(traceback.format_exc())


def append_analysis_result(data):
    """將分析結果寫入 Airtable analysis_results 表。"""
    try:
        table = get_airtable_table("analysis_results")
        if not table:
            return

        ip_hash, ua = get_anonymous_id()
        safe_response = str(data.get("ai_response", ""))[:10000]
        safe_question = str(data.get("question", ""))[:1000]
        safe_user_questions = str(data.get("User_Questions", ""))[:1000]
        safe_outline = str(data.get("AI_Outline", ""))[:2000]
        birth_date = f"{data.get('birth_year', '')}-{data.get('birth_month', '')}-{data.get('birth_day', '')}"

        record = {
            "Time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Name": data.get("user_name", ""),
            "Gender": data.get("gender", ""),
            "Birth Date": birth_date,
            "Analysis Mode": data.get("analysis_mode", ""),
            "Question": safe_question,
            "User_Questions": safe_user_questions,
            "AI_Outline": safe_outline,
            "AI Response": safe_response,
            "Master Mode": "Yes" if data.get("is_master_mode") else "No",
            "IP Hash": ip_hash,
            "Session ID": st.session_state.get('session_id', 'no_session')
        }
        table.create(record)
        print(f"成功寫入分析結果到 Airtable: {data.get('user_name', '')}")
    except Exception as e:
        st.error(f"⚠️ Airtable 寫入失敗，analysis_results 錯誤：{e}")
        print(f"寫入 analysis_results 失敗: {e}")
        import traceback
        print(traceback.format_exc())

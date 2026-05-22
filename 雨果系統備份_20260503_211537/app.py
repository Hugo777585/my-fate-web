import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import google.genai as genai
from google.genai import types
import datetime
import time
import os
import re
import json
import csv
import base64
import hashlib
import uuid
from ziwei_engine import calculate_ziwei
from dotenv import load_dotenv
from lunar_python import Lunar, Solar
from tone_engine import analyze_tone_strategy
from fpdf import FPDF
# from data_logger import log_site_visit, append_user_submission, append_analysis_result

load_dotenv()
today = datetime.date.today()
year_context = f"今天是 {today}。請務必針對目前的 2026 丙午年以及未來的 2027 丁未年進行深度流年分析，絕對不要分析已經過去的 2024 或 2025 年。"
st.set_page_config(page_title="HUGO 天命智庫", page_icon="🔮", layout="wide")

# --- 抓取 OpenAI 金鑰 ---
openai_api_key = st.secrets.get("OPENAI_API_KEY") or \
                 st.secrets.get("openai_api_key") or \
                 st.secrets.get("openai", {}).get("api_key") or \
                 os.getenv("OPENAI_API_KEY")

if not openai_api_key:
    st.error("尚未設定 OPENAI_API_KEY，請先到 Streamlit Cloud Secrets 加入金鑰。")
    st.stop()

client = OpenAI(api_key=openai_api_key)

# --- 抓取 Google API 金鑰 ---
google_api_key = st.secrets.get("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not google_api_key:
    st.error("尚未設定 GOOGLE_API_KEY，請先到 Streamlit Cloud Secrets 加入金鑰。")
    st.stop()

genai_client = genai.Client(api_key=google_api_key)

# --- Hugo 大師專屬：專業命理顧問感樣式 --- 
st.markdown(""" 
<style> 
    .stApp { background-color: #FDFCF9; color: #3E3A39; font-family: 'Noto Serif TC', serif; } 
    hr, .stDivider, div[data-testid="stDivider"], header, footer { display: none !important; }
    .block-container { padding-top: 2rem; padding-bottom: 2rem; max-width: 1200px; } 
    .main-card { background-color: #FFFFFF; padding: 40px; border-radius: 25px; box-shadow: 0 15px 50px rgba(154, 122, 56, 0.1); margin-bottom: 35px; border: 1px solid #E2E2CC; }
    .section-bar { background-color: #F4F4ED; padding: 18px 30px; border-radius: 20px; font-weight: 900; font-size: 26px; color: #9A7A38; margin: 45px 0 30px 0; border-left: 12px solid #9A7A38; box-shadow: 0 5px 15px rgba(0,0,0,0.03); letter-spacing: 2px; }
    .feature-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 25px; margin-bottom: 35px; }
    .feature-card { background-color: #FFFFFF; border-radius: 25px; padding: 35px; text-align: center; box-shadow: 0 10px 30px rgba(0,0,0,0.05); transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1); border: 1px solid #F4F4ED; height: 100%; display: flex; flex-direction: column; justify-content: space-between; }
    .feature-card:hover { transform: translateY(-8px); box-shadow: 0 20px 45px rgba(154, 122, 56, 0.12); border-color: #9A7A38; }
    .feature-icon { font-size: 50px; margin-bottom: 20px; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1)); }
    .feature-title { font-size: 26px; font-weight: 900; color: #3E3A39; margin-bottom: 15px; letter-spacing: 1px; }
    .feature-desc { font-size: 17px; color: #666; line-height: 1.8; margin-bottom: 30px; }
    .classic-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 25px; }
    .classic-card { background-color: #FFFFFF; padding: 30px; border-radius: 22px; border: 1px solid #F4F4ED; box-shadow: 0 8px 20px rgba(0,0,0,0.03); transition: all 0.3s ease; }
    .classic-card:hover { border-color: #9A7A38; }
    .classic-header { color: #9A7A38; font-weight: 900; font-size: 21px; margin-bottom: 15px; border-bottom: 1px solid #F4F4ED; padding-bottom: 10px; }
    .stButton > button { height: 56px !important; border-radius: 18px !important; font-weight: 900 !important; font-size: 19px !important; background: linear-gradient(135deg, #9A7A38, #B38E45) !important; color: white !important; border: none !important; box-shadow: 0 8px 20px rgba(154, 122, 56, 0.25) !important; transition: all 0.4s ease !important; width: 100% !important; letter-spacing: 2px; }
    .logo-img { max-width: 180px; height: auto; }
</style> 
""", unsafe_allow_html=True)

def get_ziwei_data(birth_year, birth_month, birth_day, birth_hour):
    if birth_hour not in range(12): birth_hour = birth_hour // 2 % 12
    return calculate_ziwei(birth_year, birth_month, birth_day, birth_hour)

def render_ziwei_chart(ziwei_data, user_info=None):
    if not ziwei_data or 'palaces' not in ziwei_data: return ""
    ziwei_css = """
    <style>
    .ziwei-container { width: 100%; overflow-x: auto; padding: 20px 0; display: flex; justify-content: center; background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%); }
    .ziwei-grid { display: grid; grid-template-columns: repeat(4, 1fr); grid-template-rows: repeat(4, 1fr); gap: 8px; width: 100%; max-width: 650px; aspect-ratio: 1 / 1; background: linear-gradient(145deg, #1e1e1e, #2a2a2a); border: 3px solid #d4af37; border-radius: 32px; padding: 12px; }
    .ziwei-cell { background: linear-gradient(145deg, #2c2c2c, #1f1f1f); border: 1px solid rgba(212, 175, 55, 0.3); padding: 12px; display: flex; flex-direction: column; position: relative; border-radius: 20px; }
    .ziwei-center { grid-column: 2 / 4; grid-row: 2 / 4; display: flex; flex-direction: column; justify-content: center; align-items: center; text-align: center; color: #f5e8c0; border: 2px solid #d4af37; border-radius: 50%; }
    .palace-name { position: absolute; bottom: 10px; right: 10px; font-weight: 900; color: #d4af37; font-size: 10px; }
    .star-list { display: flex; flex-direction: column; gap: 5px; color: #ffb84d; font-weight: 900; font-size: 12px; }
    </style>
    """
    palaces = ziwei_data["palaces"]
    grid_map = {"巳": "grid-area: 1 / 1;", "午": "grid-area: 1 / 2;", "未": "grid-area: 1 / 3;", "申": "grid-area: 1 / 4;", "辰": "grid-area: 2 / 1;", "酉": "grid-area: 2 / 4;", "卯": "grid-area: 3 / 1;", "戌": "grid-area: 3 / 4;", "寅": "grid-area: 4 / 1;", "丑": "grid-area: 4 / 2;", "子": "grid-area: 4 / 3;", "亥": "grid-area: 4 / 4;"}
    cells_html = ""
    for dz, pos in grid_map.items():
        p_info = palaces.get(dz, {"name": "", "stars": [], "main_star": "", "minor_stars": []})
        stars_html = f'<div class="main-star">{p_info.get("main_star", "")}</div>'
        for star in p_info.get("minor_stars", []): stars_html += f"<span>{star}</span>"
        cells_html += f'<div class="ziwei-cell" style="{pos}"><div class="star-list">{stars_html}</div><div class="palace-name">{p_info["name"]}</div></div>'
    chart_html = f'<div class="ziwei-container"><div class="ziwei-grid">{cells_html}<div class="ziwei-center">HUGO<br>天命智庫</div></div></div>'
    return ziwei_css + chart_html

def generate_content_with_retry(model, contents, config=None, max_retries=1):
    attempt = 0
    while True:
        try: return genai_client.models.generate_content(model=model, contents=contents, config=config)
        except Exception:
            if attempt < max_retries: attempt += 1; time.sleep(1); continue
            raise

def extract_ai_outline(text):
    if not text: return ""
    markers = ["AI Outline:", "大綱：", "AI 大綱："]
    for marker in markers:
        idx = text.find(marker)
        if idx != -1: return text[idx + len(marker):].strip()
    return ""

def ai_reply(prompt, is_master=False):
    system_role = "你是一位精通命理的大師 Hugo。"
    try:
        response = generate_content_with_retry(model='gemini-flash-latest', contents=prompt, config=types.GenerateContentConfig(system_instruction=system_role))
        return response.text
    except Exception as e: return f"AI 連線失敗：{str(e)}"

def calculate_bazi(y, m, d, h, minute):
    try:
        solar = Solar.fromYmdHms(int(y), int(m), int(d), int(h), int(minute), 0)
        lunar = solar.getLunar()
        eight_char = lunar.getEightChar()
        return {'year_tg': eight_char.getYearGan(), 'year_dz': eight_char.getYearZhi(), 'year_ss': eight_char.getYearShiShenGan(), 'year_hide': "".join(eight_char.getYearHideGan()), 'month_tg': eight_char.getMonthGan(), 'month_dz': eight_char.getMonthZhi(), 'month_ss': eight_char.getMonthShiShenGan(), 'month_hide': "".join(eight_char.getMonthHideGan()), 'day_tg': eight_char.getDayGan(), 'day_dz': eight_char.getDayZhi(), 'day_ss': '日主', 'day_hide': "".join(eight_char.getDayHideGan()), 'hour_tg': eight_char.getTimeGan(), 'hour_dz': eight_char.getTimeZhi(), 'hour_ss': eight_char.getTimeShiShenGan(), 'hour_hide': "".join(eight_char.getTimeHideGan()), 'full': {'year': eight_char.getYear(), 'month': eight_char.getMonth(), 'day': eight_char.getDay(), 'hour': eight_char.getTime()}}
    except: return None

# --- Main App Logic ---
if 'analysis_mode' not in st.session_state:
    if 'visited_home' not in st.session_state:
        st.session_state.visited_home = True
        # log_site_visit("home") # 已封印
    st.title("HUGO 天命智庫")
    col1, col2 = st.columns(2)
    if col1.button("開始八字分析"): st.session_state.analysis_mode = "八字命理分析"; st.rerun()
    if col2.button("開始紫微分析"): st.session_state.analysis_mode = "紫微斗數分析"; st.rerun()
    st.stop()

if 'analysis_mode' in st.session_state:
    mode = st.session_state.analysis_mode
    # log_site_visit(mode) # 已封印
    st.write(f"模式：{mode}")
    if st.button("⬅️ 返回首頁"): del st.session_state.analysis_mode; st.rerun()
    
    name = st.text_input("姓名")
    b_year = st.selectbox("年", range(1930, 2027), index=50)
    b_month = st.selectbox("月", range(1, 13))
    b_day = st.selectbox("日", range(1, 32))
    b_hour = st.selectbox("時", range(0, 24), index=12)
    b_min = st.selectbox("分", range(0, 60))
    question = st.text_area("問題")
    
    if st.button("🚀 開始分析"):
        if name and question:
            # submission_data = {...} # 已封印
            # append_user_submission(submission_data) # 已封印
            
            bazi = calculate_bazi(b_year, b_month, b_day, b_hour, b_min)
            if mode == "紫微斗數分析":
                ziwei_data = get_ziwei_data(b_year, b_month, b_day, b_hour)
                components.html(render_ziwei_chart(ziwei_data, {'name': name}), height=1000, scrolling=True)
                result = ai_reply(f"分析：{question}，命盤：{ziwei_data}")
            else:
                result = ai_reply(f"分析：{question}，八字：{bazi}")
            
            st.markdown(f'<div class="main-card">{result}</div>', unsafe_allow_html=True)
            # analysis_data = {...} # 已封印
            # append_analysis_result(analysis_data) # 已封印
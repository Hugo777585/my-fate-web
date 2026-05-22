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
    /* 1. 全局背景色：#FDFCF9 (高級米白) */ 
    .stApp { 
        background-color: #FDFCF9; 
        color: #3E3A39; 
        font-family: 'Noto Serif TC', serif;
    } 

    /* 隱藏預設元素與多餘白條 */
    hr, .stDivider, div[data-testid="stDivider"], header, footer { display: none !important; }
    .block-container { 
        padding-top: 2rem; 
        padding-bottom: 2rem; 
        max-width: 1200px;
    } 
    
    /* 2. 主內容卡片：皇家典藏白 */
    .main-card {
        background-color: #FFFFFF;
        padding: 40px;
        border-radius: 25px;
        box-shadow: 0 15px 50px rgba(154, 122, 56, 0.1);
        margin-bottom: 35px;
        border: 1px solid #E2E2CC;
    }

    /* 3. 區塊橫桿：典雅金色 #9A7A38 */
    .section-bar {
        background-color: #F4F4ED;
        padding: 18px 30px;
        border-radius: 20px;
        font-weight: 900;
        font-size: 26px;
        color: #9A7A38;
        margin: 45px 0 30px 0;
        border-left: 12px solid #9A7A38;
        box-shadow: 0 5px 15px rgba(0,0,0,0.03);
        letter-spacing: 2px;
    }

    /* 4. 功能卡片：皇家對齊感 */
    .feature-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 25px;
        margin-bottom: 35px;
    }
    .feature-card {
        background-color: #FFFFFF;
        border-radius: 25px;
        padding: 35px;
        text-align: center;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
        transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
        border: 1px solid #F4F4ED;
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .feature-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 45px rgba(154, 122, 56, 0.12);
        border-color: #9A7A38;
    }
    .feature-icon { font-size: 50px; margin-bottom: 20px; filter: drop-shadow(0 4px 6px rgba(0,0,0,0.1)); }
    .feature-title { font-size: 26px; font-weight: 900; color: #3E3A39; margin-bottom: 15px; letter-spacing: 1px; }
    .feature-desc { font-size: 17px; color: #666; line-height: 1.8; margin-bottom: 30px; }

    /* 5. 三大經典卡片：精緻感 */
    .classic-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
        gap: 25px;
    }
    .classic-card {
        background-color: #FFFFFF;
        padding: 30px;
        border-radius: 22px;
        border: 1px solid #F4F4ED;
        box-shadow: 0 8px 20px rgba(0,0,0,0.03);
        transition: all 0.3s ease;
    }
    .classic-card:hover { border-color: #9A7A38; }
    .classic-header { color: #9A7A38; font-weight: 900; font-size: 21px; margin-bottom: 15px; border-bottom: 1px solid #F4F4ED; padding-bottom: 10px; }
    .classic-point { background: #F4F4ED; color: #9A7A38; padding: 6px 15px; border-radius: 10px; font-weight: 800; display: inline-block; margin-top: 15px; }

    /* 6. 按鈕樣式：尊榮感金色 */
    .stButton > button {
        height: 56px !important;
        border-radius: 18px !important;
        font-weight: 900 !important;
        font-size: 19px !important;
        background: linear-gradient(135deg, #9A7A38, #B38E45) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 8px 20px rgba(154, 122, 56, 0.25) !important;
        transition: all 0.4s ease !important;
        width: 100% !important;
        letter-spacing: 2px;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #B38E45, #9A7A38) !important;
        box-shadow: 0 12px 30px rgba(154, 122, 56, 0.35) !important;
        transform: translateY(-3px) !important;
    }

    /* 8. LOGO 控制 */
    .logo-box { text-align: center; margin-bottom: 25px; }
    .logo-img { max-width: 180px; height: auto; }
    @media (max-width: 600px) {
        .logo-img { max-width: 130px; }
        .feature-grid { grid-template-columns: 1fr; }
        .stButton > button { width: 100% !important; }
    }

    /* 金色重點 */
    .gold { color: #9A7A38; font-weight: 900; }

    /* --- UI 淨化：隱藏官方元素與導航 --- */
    #MainMenu {visibility: hidden !important;} 
    header {visibility: hidden !important;} 
    footer {visibility: hidden !important;} 
    .stAppDeployButton, .stAppShareButton, .stActionButton, .viewerBadge_container__1QS1n {display: none !important;} 
    [data-testid="stSidebarNav"] {display: none !important;} 
</style> 
""", unsafe_allow_html=True)

def get_ziwei_data(birth_year, birth_month, birth_day, birth_hour):
    """
    使用 iztro 引擎獲取紫微斗數星曜數據
    """
    # 將小時轉換為 0-11 索引格式（ziwei_engine 需要）
    if birth_hour not in range(12):
        birth_hour = birth_hour // 2 % 12
    
    # 使用新的 ziwei_engine 獲取數據
    return calculate_ziwei(birth_year, birth_month, birth_day, birth_hour)

def render_ziwei_chart(ziwei_data, user_info=None):
    if not ziwei_data or 'palaces' not in ziwei_data:
        return ""
    
    # 將 CSS 樣式直接包裹在函數內，確保渲染時能正確加載
    ziwei_css = """
    <style>
    .ziwei-container {
        width: 100%;
        overflow-x: auto;
        padding: 20px 0;
        display: flex;
        justify-content: center;
        background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
    }
    .ziwei-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        grid-template-rows: repeat(4, 1fr);
        gap: 8px;
        width: 100%;
        max-width: 650px;
        aspect-ratio: 1 / 1;
        background: linear-gradient(145deg, #1e1e1e, #2a2a2a);
        border: 3px solid #d4af37;
        border-radius: 32px;
        padding: 12px;
        box-sizing: border-box;
        box-shadow: 0 32px 100px rgba(0, 0, 0, 0.5), inset 0 0 50px rgba(212, 175, 55, 0.05);
    }
    .ziwei-cell {
        background: linear-gradient(145deg, #2c2c2c, #1f1f1f);
        border: 1px solid rgba(212, 175, 55, 0.3);
        padding: 12px 12px 10px 12px;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        position: relative;
        box-sizing: border-box;
        overflow: hidden;
        box-shadow: 0 8px 25px rgba(0, 0, 0, 0.3), inset 0 0 20px rgba(255, 215, 150, 0.02);
        border-radius: 20px;
    }
    .ziwei-center {
        grid-column: 2 / 4;
        grid-row: 2 / 4;
        background: radial-gradient(circle at center, rgba(212, 175, 55, 0.1), #1a1a1a);
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        padding: 24px 16px;
        font-weight: 900;
        color: #f5e8c0;
        border: 2px solid #d4af37;
        box-sizing: border-box;
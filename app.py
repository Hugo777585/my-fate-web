import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import google.genai as genai
from google.genai import types
import datetime
import time
import os
import gspread
import re
import json
import csv
import base64
import hashlib
import uuid
from ziwei_engine import calculate_ziwei
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from lunar_python import Lunar, Solar
from tone_engine import analyze_tone_strategy
from fpdf import FPDF
from data_logger import log_site_visit, append_user_submission, ensure_worksheet

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

def render_ziwei_chart(ziwei_data):
    if not ziwei_data: return ""
    
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
        border-radius: 50%;
        position: relative;
        box-shadow: 0 12px 40px rgba(212, 175, 55, 0.2), inset 0 0 30px rgba(255, 215, 150, 0.05);
    }
    .ziwei-center::before {
        content: 'HUGO 天命智庫';
        position: absolute;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%);
        font-size: 14px;
        color: rgba(255, 215, 150, 0.15);
        letter-spacing: 0.2em;
        font-weight: 900;
        pointer-events: none;
        user-select: none;
        text-align: center;
        line-height: 1.2;
    }
    .ziwei-center-content {
        position: relative;
        z-index: 1;
    }
    .ziwei-center-title {
        font-size: 16px;
        margin-bottom: 6px;
        letter-spacing: 1px;
        color: #d4af37;
    }
    .ziwei-center-meta {
        font-size: 11px;
        color: rgba(245, 232, 192, 0.9);
        line-height: 1.4;
    }
    .palace-name {
        position: absolute;
        bottom: 10px;
        right: 10px;
        font-weight: 900;
        color: #1d1005;
        font-size: 10px;
        letter-spacing: 0.5px;
        background: linear-gradient(135deg, #d4af37, #b8860b);
        padding: 3px 8px;
        border-radius: 12px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    }
    .dz-name {
        position: absolute;
        bottom: 10px;
        left: 10px;
        color: rgba(255, 255, 255, 0.8);
        font-size: 9px;
        font-family: serif;
        background: rgba(0, 0, 0, 0.4);
        padding: 2px 5px;
        border-radius: 10px;
    }
    .star-list {
        display: flex;
        flex-direction: column;
        gap: 5px;
        color: #f7d097;
        font-weight: 900;
        font-size: 12px;
        line-height: 1.2;
        align-items: flex-start;
    }
    .star-list span {
        display: block;
        color: #ffb84d;
        font-weight: 900;
        text-shadow: 0 0 10px rgba(255, 183, 77, 0.4);
    }
    @media (max-width: 480px) {
        .ziwei-grid { gap: 4px; padding: 6px; }
        .palace-name { font-size: 8px; right: 4px; bottom: 4px; padding: 2px 6px; }
        .dz-name { font-size: 7px; left: 4px; bottom: 4px; padding: 1px 4px; }
        .star-list { font-size: 10px; }
        .ziwei-center { padding: 18px 12px; }
        .ziwei-center-title { font-size: 14px; }
        .ziwei-center-meta { font-size: 10px; }
    }
    </style>
    """
    
    palaces = ziwei_data["palaces"]
    # 紫微 4x4 宮位順序 (地支對應 Grid 位置)
    grid_map = {
        "巳": "grid-area: 1 / 1;", "午": "grid-area: 1 / 2;", "未": "grid-area: 1 / 3;", "申": "grid-area: 1 / 4;",
        "辰": "grid-area: 2 / 1;", "酉": "grid-area: 2 / 4;",
        "卯": "grid-area: 3 / 1;", "戌": "grid-area: 3 / 4;",
        "寅": "grid-area: 4 / 1;", "丑": "grid-area: 4 / 2;", "子": "grid-area: 4 / 3;", "亥": "grid-area: 4 / 4;"
    }
    
    cells_html = ""
    for dz, pos in grid_map.items():
        p_info = palaces.get(dz, {"name": "", "stars": []})
        stars_html = "".join([f"<span>{s}</span>" for s in p_info["stars"]])
        cells_html += f"""
        <div class="ziwei-cell" style="{pos}">
            <div class="star-list">{stars_html}</div>
            <div class="dz-name">{dz}</div>
            <div class="palace-name">{p_info["name"]}</div>
        </div>
        """
        
    info = ziwei_data["basic_info"]
    center_html = f"""
    <div class="ziwei-center">
        <div class="ziwei-center-content">
            <div class="ziwei-center-title">HUGO 天命智庫</div>
            <div class="ziwei-center-meta">
                {info['year']}年 {info['month']}月 {info['day']}日<br>
                {info['hour']}時生
            </div>
        </div>
    </div>
    """
    
    # 回傳純粹 HTML 字串，不包含 Markdown code fence
    chart_html = (
        f'<div class="ziwei-container">'
        f'<div class="ziwei-grid">{cells_html}{center_html}</div>'
        f'</div>'
    )
    full_html = ziwei_css + chart_html
    # 清除任何潛在 Markdown code fence，確保純 HTML 呈現
    sanitized_html = full_html.replace('```html', '').replace('```css', '').replace('```', '')
    return sanitized_html

def ai_reply(prompt, is_master=False):
    system_role = "你是一位精通《淵海子平》、《三命通會》與《滴天髓》的命理大師 Hugo。語氣沉穩、睿智，必須深入探討干支生剋與格局，拒絕罐頭回覆。你必須具備時效性，能看清當下的歲運流轉。"
    if is_master:
        prompt = "【大師模式：性格、事業、財運、感情這四個面向，每個面向必須產出至少 250 字的深度論述】" + prompt
    try:
        response = genai_client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
            config=types.GenerateContentConfig(system_instruction=system_role)
        )
        return response.text
    except Exception as e:
        return f"AI 連線失敗：{str(e)}"

def ai_love_consult_reply(context_prompt, is_master=False):
    # 使用標準半形符號重新定義 system_role
    system_role = "你是一位結合命理分析,感情心理諮詢與關係策略的顧問。請用沉穩,理性,具同理心的方式分析。"
    if is_master:
        permission_instruction = "【大師模式：完整分析】"
    else:
        permission_instruction = "【一般模式：初步引導】"
    full_prompt = f"{system_role}\n\n{year_context}\n\n{context_prompt}\n{permission_instruction}"
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_role}, {"role": "user", "content": full_prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 諮詢失敗：{str(e)}"

def get_wuxing_color(char):
    if not char: return "#FFFFFF"
    char = char[0]
    wuxing_map = {
        '甲': '#C8E6C9', '乙': '#C8E6C9', '寅': '#C8E6C9', '卯': '#C8E6C9',
        '丙': '#FFCDD2', '丁': '#FFCDD2', '巳': '#FFCDD2', '午': '#FFCDD2',
        '戊': '#FFF9C4', '己': '#FFF9C4', '辰': '#FFF9C4', '戌': '#FFF9C4', '丑': '#FFF9C4', '未': '#FFF9C4',
        '庚': '#F5F5F5', '辛': '#F5F5F5', '申': '#F5F5F5', '酉': '#F5F5F5',
        '壬': '#BBDEFB', '癸': '#BBDEFB', '亥': '#BBDEFB', '子': '#BBDEFB',
    }
    return wuxing_map.get(char, "#FFFFFF")

def render_bazi_table(bazi):
    if not bazi: return ""
    y_color = get_wuxing_color(bazi['year_dz'])
    m_color = get_wuxing_color(bazi['month_dz'])
    d_color = get_wuxing_color(bazi['day_dz'])
    h_color = get_wuxing_color(bazi['hour_dz'])
    html = f"""
    <div style="overflow-x: auto; margin-bottom: 20px;">
        <table style="width: 100%; border-collapse: collapse; text-align: center; border: 2px solid #9A7A38;">
            <tr style="background-color: #9A7A38; color: white;">
                <th>四柱</th><th>天干</th><th>十神</th><th>地支</th><th>藏干</th>
            </tr>
            <tr style="background-color: {y_color};"><td>年柱</td><td>{bazi['year_tg']}</td><td>{bazi['year_ss']}</td><td>{bazi['year_dz']}</td><td>{bazi['year_hide']}</td></tr>
            <tr style="background-color: {m_color};"><td>月柱</td><td>{bazi['month_tg']}</td><td>{bazi['month_ss']}</td><td>{bazi['month_dz']}</td><td>{bazi['month_hide']}</td></tr>
            <tr style="background-color: {d_color};"><td>日柱</td><td>{bazi['day_tg']}</td><td>日主</td><td>{bazi['day_dz']}</td><td>{bazi['day_hide']}</td></tr>
            <tr style="background-color: {h_color};"><td>時柱</td><td>{bazi['hour_tg']}</td><td>{bazi['hour_ss']}</td><td>{bazi['hour_dz']}</td><td>{bazi['hour_hide']}</td></tr>
        </table>
    </div>
    """
    return html

def calculate_bazi(y, m, d, h, minute):
    try:
        solar = Solar.fromYmdHms(int(y), int(m), int(d), int(h), int(minute), 0)
        lunar = solar.getLunar()
        eight_char = lunar.getEightChar()
        return {
            'year_tg': eight_char.getYearGan(), 'year_dz': eight_char.getYearZhi(), 'year_ss': eight_char.getYearShiShenGan(), 'year_hide': "".join(eight_char.getYearHideGan()),
            'month_tg': eight_char.getMonthGan(), 'month_dz': eight_char.getMonthZhi(), 'month_ss': eight_char.getMonthShiShenGan(), 'month_hide': "".join(eight_char.getMonthHideGan()),
            'day_tg': eight_char.getDayGan(), 'day_dz': eight_char.getDayZhi(), 'day_ss': '日主', 'day_hide': "".join(eight_char.getDayHideGan()),
            'hour_tg': eight_char.getTimeGan(), 'hour_dz': eight_char.getTimeZhi(), 'hour_ss': eight_char.getTimeShiShenGan(), 'hour_hide': "".join(eight_char.getTimeHideGan()),
            'full': {'year': eight_char.getYear(), 'month': eight_char.getMonth(), 'day': eight_char.getDay(), 'hour': eight_char.getTime()}
        }
    except Exception as e:
        return None

def render_partner_input():
    """封裝對象資料輸入介面"""
    st.subheader("💞 對象資料")
    c1, c2, c3 = st.columns(3)
    name2 = c1.text_input("對象姓名/暱稱", key="p_name")
    p_gender = c2.selectbox("對象性別", ["男", "女"], key="p_gender")
    relation_type = c3.selectbox("關係類型", ["情侶/夫妻", "合作夥伴", "暗戀/曖昧", "其他"], key="p_relation")
    
    st.markdown("#### 📅 對象出生時間 (國曆)")
    pc1, pc2, pc3, pc4, pc5 = st.columns(5)
    p_year = pc1.selectbox("年", range(1930, 2027), index=50, key="p_year")
    p_month = pc2.selectbox("月", range(1, 13), key="p_month")
    p_day = pc3.selectbox("日", range(1, 32), key="p_day")
    p_hour = pc4.selectbox("時", range(0, 24), index=12, key="p_hour")
    p_min = pc5.selectbox("分", range(0, 60), key="p_min")
    
    return name2, p_gender, relation_type, p_year, p_month, p_day, p_hour, p_min

# --- 初始化 Session State ---
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'visited_pages' not in st.session_state:
    st.session_state.visited_pages = set()

# --- 大師模式全域判斷 ---
is_master = False
# 優先檢查網址入口與管理中心的輸入
admin_input = st.session_state.get("admin_gate_input", "")
if admin_input.strip().upper() == st.secrets.get("MASTER_PASSWORD", "1234").upper():
    is_master = True

# --- 側邊欄 (Sidebar) ---
with st.sidebar:
    st.markdown("### 🔮 HUGO 天命智庫")
    if os.path.exists("logo.JPG"):
        st.image("logo.JPG", width='stretch')
    
    st.markdown("---")
    # 讀取訪客人數
    v_count = 0
    if os.path.exists("visitor_count.txt"):
        with open("visitor_count.txt", "r") as f:
            try: v_count = int(f.read())
            except: v_count = 0
    st.metric("📊 累計解盤人數", f"{v_count} 人")
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Powered by GPT-4o & HUGO Engine")

# --- 1. 頂部 Hero 區 (包含 Logo 與 標題) ---
logo_html = ""
if os.path.exists("logo.JPG"):
    with open("logo.JPG", "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()
    logo_html = f'<div class="logo-box"><img src="data:image/jpeg;base64,{logo_base64}" class="logo-img"></div>'
else:
    logo_html = '<div class="logo-box"><h1 style="color:#9A7A38; margin:0;">HUGO 天命智庫</h1></div>'

if 'analysis_mode' not in st.session_state:
    # 訪客人數 +1
    if 'visited_home' not in st.session_state:
        st.session_state.visited_home = True
        try:
            count_file = "visitor_count.txt"
            if os.path.exists(count_file):
                with open(count_file, "r") as f:
                    count = int(f.read().strip())
            else:
                count = 1000 # 初始值
            count += 1
            with open(count_file, "w") as f:
                f.write(str(count))
        except:
            pass
            
    log_site_visit("home")
    st.markdown(f"""
    <div class="main-card" style="margin-top: 0; padding-top: 20px; padding-bottom: 25px;">
        {logo_html}
        <div style="display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 30px;">
            <div style="flex: 1; min-width: 300px;">
                <h1 style="font-size: 32px; font-weight: 900; color: #2F2F2F; margin-bottom: 15px; line-height: 1.2;">你不是不順，是你還沒看懂自己的命盤。</h1>
                <h3 style="font-size: 18px; color: #444; margin-bottom: 15px; line-height: 1.4;">當感情卡住、人生停滯、選擇變得困難——<br>不是你不夠努力，而是你還沒看懂「局」。</h3>
                <p style="font-size: 15px; line-height: 1.6; color: #555;">
                    HUGO 天命智庫結合傳統命理經典與現代 AI 大數據分析，協助你看清人生方向、關係狀態與下一步選擇。
                </p>
            </div>
            <div style="flex: 0 0 220px; text-align: center;">
                <div style="width: 180px; height: 180px; background: #E2E2CC; border-radius: 50%; margin: 0 auto; display: flex; align-items: center; justify-content: center; border: 4px solid #9A7A38; box-shadow: 0 10px 25px rgba(0,0,0,0.1);">
                    <span style="font-size: 60px;">🔮</span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("📖 關於 HUGO 天命智庫：核心優勢與學理準則"):
        st.markdown(""" 
        ### 🌟 我們的優勢 
        結合頂尖 AI 運算模型與深厚的傳統命理底蘊，剔除人為情緒干擾，提供**精準、客觀、具備商業與人生決策價值**的深度分析。 

        ### 📚 核心學理依據 (三大古籍準則) 
        本系統之演算法與判斷邏輯，皆嚴格考證自命理三大經典，拒絕毫無根據的鐵口直斷： 
        1. **《淵海子平》**：建構八字基礎格局與日主強弱判定。 
        2. **《三命通會》**：統攝萬物類象、神煞吉凶與流年大運之交互影響。 
        3. **《滴天髓》**：精微解析五行生剋制化、通關調候與用神取法。 
        
        ### 📊 網站簡報與架構 
        *(大師請注意：若有簡報圖片，後續可在此處放入 `st.image("簡報檔名.jpg")`)* 
        """)

    # --- 2. 四大功能入口 (2x2) ---
    st.markdown('<div class="section-bar" style="margin-top: 0;">四大核心功能入口</div>', unsafe_allow_html=True)
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        st.markdown('<div class="feature-card"><div><div class="feature-icon">📜</div><div class="feature-title">八字命理分析</div><div class="feature-desc">解析你的先天性格、事業走向、財運基礎與感情模式。</div></div></div>', unsafe_allow_html=True)
        if st.button("開始八字分析", key="nav_bazi"): st.session_state.analysis_mode = "八字命理分析"; st.rerun()
        st.markdown('<div class="feature-card"><div><div class="feature-icon">♾️</div><div class="feature-title">八字 × 紫微交叉分析</div><div class="feature-desc">將兩套命理系統交叉比對，提升判斷深度與準確度。</div></div></div>', unsafe_allow_html=True)
        if st.button("啟動交叉分析", key="nav_cross"): st.session_state.analysis_mode = "八字 × 紫微交叉分析"; st.rerun()
    with col_f2:
        st.markdown('<div class="feature-card"><div><div class="feature-icon">✨</div><div class="feature-title">紫微斗數分析</div><div class="feature-desc">從命宮、夫妻宮、財帛宮與事業宮，看見人生不同面向的細節。</div></div></div>', unsafe_allow_html=True)
        if st.button("開始紫微分析", key="nav_ziwei"): st.session_state.analysis_mode = "紫微斗數分析"; st.rerun()
        st.markdown('<div class="feature-card"><div><div class="feature-icon">👩‍❤️‍👨</div><div class="feature-title">兩人合盤分析</div><div class="feature-desc">分析你與對象、伴侶或配偶的吸引力、衝突點與相處方式。</div></div></div>', unsafe_allow_html=True)
        if st.button("開始合盤分析", key="nav_dual"): st.session_state.analysis_mode = "兩人合盤分析"; st.session_state.enable_dual = True; st.rerun()

    # --- 3. 三大命理經典 ---
    st.markdown('<div class="section-bar">系統推算依據｜三大命理核心經典</div>', unsafe_allow_html=True)
    st.markdown("""<div class="main-card"><div class="classic-grid">
        <div class="classic-card"><div class="classic-header">1. 三命通會</div><p>命格結構、十神關係、事業財運。<b>重點：看人生基本設定。</b></p></div>
        <div class="classic-card"><div class="classic-header">2. 滴天髓</div><p>五行流動、旺衰平衡、運勢轉折。<b>重點：看起伏與卡點。</b></p></div>
        <div class="classic-card"><div class="classic-header">3. 淵海子平</div><p>日主強弱、月令格局、五行生剋。<b>重點：精準實戰判斷。</b></p></div>
    </div></div>""", unsafe_allow_html=True)

    # --- 4. 兩人合盤重點區 ---
    st.markdown('<div class="section-bar">兩人關係深度解析｜最受歡迎功能</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-card"><h4>不只是看「合不合」，而是幫你看懂「該怎麼做」。</h4><p>透過雙方命盤交叉比對，解析吸引力、衝突點與相處節奏。</p></div>', unsafe_allow_html=True)
    if st.button("【立即開始兩人合盤分析】", key="cta_dual"): st.session_state.analysis_mode = "合盤"; st.session_state.enable_dual = True; st.rerun()

    # --- 5. 第二層感情心理諮詢入口 ---
    st.markdown('<div class="section-bar">兩性情感心理諮詢</div>', unsafe_allow_html=True)
    if st.button("【進入感情心理分析】", key="cta_love"): st.switch_page("pages/02_love_analysis.py")

    st.stop()

# --- 後端邏輯區 (當選擇模式後) ---
if 'analysis_mode' in st.session_state:
    mode = st.session_state.analysis_mode
    if mode == "八字命理分析": log_site_visit("bazi")
    elif mode == "紫微斗數分析": log_site_visit("ziwei")
    elif mode == "八字 × 紫微交叉分析": log_site_visit("cross")
    elif mode == "兩人合盤分析": log_site_visit("couple")
    
    st.markdown(f"### 📋 填寫資料 - {mode}模式")
    if st.button("⬅️ 返回首頁"): del st.session_state.analysis_mode; st.rerun()
    
    col1, col2, col3 = st.columns(3)
    name = col1.text_input("姓名/暱稱")
    gender = col2.selectbox("性別", ["男", "女"])
    occupation = col3.text_input("職業/狀態")
    
    st.markdown("#### 📅 出生時間 (國曆)")
    c1, c2, c3, c4, c5 = st.columns(5)
    b_year = c1.selectbox("年", range(1930, 2027), index=50)
    b_month = c2.selectbox("月", range(1, 13))
    b_day = c3.selectbox("日", range(1, 32))
    b_hour = c4.selectbox("時", range(0, 24), index=12)
    b_min = c5.selectbox("分", range(0, 60))
    
    # --- 兩人合盤邏輯 ---
    name2 = ""
    relation_type = ""
    p_year, p_month, p_day, p_hour, p_min = 1980, 1, 1, 12, 0
    p_gender = "女"
    
    # 判斷是否為合盤模式
    is_couple_mode = (mode == "兩人合盤分析" or st.session_state.get('enable_dual', False))
    
    enable_dual = False
    if is_couple_mode:
        enable_dual = True
        name2, p_gender, relation_type, p_year, p_month, p_day, p_hour, p_min = render_partner_input()
    else:
        enable_dual = st.toggle("💑 啟用雙人合盤", value=False)
        if enable_dual:
            name2, p_gender, relation_type, p_year, p_month, p_day, p_hour, p_min = render_partner_input()
    
    question = st.text_area("您的問題", placeholder="例如：這段感情還有救嗎？或未來的事業發展？")
    
    if st.button("🚀 開始 AI 命理分析"):
        # 防錯機制：檢查必要欄位
        if not name:
            st.error("請輸入您的姓名/暱稱。")
        elif enable_dual and not name2:
            st.error("請輸入對象的姓名/暱稱。")
        elif not question:
            st.warning("建議輸入具體問題，大師能為您提供更精確的指引。")
            # 即使沒填問題也允許分析，但給予警告
        
        if name and (not enable_dual or name2):
            # 收集資料準備紀錄
            submission_data = {
                "user_name": name,
                "gender": gender,
                "job_status": occupation,
                "birth_year": b_year,
                "birth_month": b_month,
                "birth_day": b_day,
                "birth_hour": b_hour,
                "birth_minute": b_min,
                "analysis_mode": mode,
                "question": question,
                "is_couple_mode": enable_dual,
                "partner_name": name2 if enable_dual else "",
                "partner_gender": p_gender if enable_dual else "",
                "partner_birth_year": p_year if enable_dual else "", 
                "partner_birth_month": p_month if enable_dual else "",
                "partner_birth_day": p_day if enable_dual else "",
                "partner_birth_hour": p_hour if enable_dual else "",
                "partner_birth_minute": p_min if enable_dual else ""
            }
            append_user_submission(submission_data)

            with st.spinner("🔮 大師正在觀星測算中..."):
                mode = st.session_state.analysis_mode
            
            # 1. 基礎資料準備
            bazi = calculate_bazi(b_year, b_month, b_day, b_hour, b_min)
            
            if not bazi:
                st.error("排盤失敗，請檢查輸入的出生時間。")
            else:
                # 2. 根據模式執行不同的渲染與分析
                if mode == "紫微斗數分析":
                    # 紫微模式：顯示 4x4 星盤
                    ziwei_data = calculate_ziwei(b_year, b_month, b_day, b_hour)
                    st.markdown("### 🔮 紫微斗數命盤")
                    st.markdown(render_ziwei_chart(ziwei_data), unsafe_allow_html=True)
                    
                    # 專屬紫微 System Prompt
                    ziwei_system_role = "你是一位精通紫微斗數的大師。請嚴格遵守紫微斗數的邏輯（星曜、宮位、四化）來解盤，絕對禁止混入八字術語（如：十神、日主、五行強弱）。"
                    
                    prompt = f"{year_context}\n\n請針對以下紫微斗數命盤數據進行深度分析：\nJSON數據：{json.dumps(ziwei_data, ensure_ascii=False)}\n用戶問題：{question}\n\n請詳細分析命宮、夫妻宮、財帛宮與事業宮的特質，並針對用戶問題給予具體建議。"
                    
                    try:
                        response = genai_client.models.generate_content(
                            model='gemini-flash-latest',
                            contents=prompt,
                            config=types.GenerateContentConfig(system_instruction=ziwei_system_role)
                        )
                        result = response.text
                    except Exception as e:
                        result = f"AI 紫微分析失敗：{str(e)}"
                        
                    st.markdown(f'<div class="main-card">{result}</div>', unsafe_allow_html=True)
                
                elif mode == "八字命理分析":
                    # 八字模式：僅顯示八字盤 (隱藏紫微)
                    st.markdown("### 📜 八字命盤基礎")
                    st.markdown(render_bazi_table(bazi), unsafe_allow_html=True)
                    
                    prompt = f"{year_context}\n\n你是一位專業命理大師。請針對以下八字命盤進行深度分析：\n姓名：{name}\n性別：{gender}\n出生時間：{b_year}/{b_month}/{b_day} {b_hour}:{b_min}\n職業：{occupation}\n問題：{question}\n命盤數據：{bazi['full']}\n\n請分析性格、事業、財運與感情建議。"
                    result = ai_reply(prompt, is_master=is_master)
                    st.markdown(f'<div class="main-card">{result}</div>', unsafe_allow_html=True)
                
                elif mode == "八字 × 紫微交叉分析":
                    # 交叉分析：顯示八字盤，並由 AI 結合紫微邏輯
                    st.markdown("### 📜 八字命盤基礎")
                    st.markdown(render_bazi_table(bazi), unsafe_allow_html=True)
                    st.info("💡 系統正結合紫微斗數星曜分佈進行交叉判斷。")
                    
                    prompt = f"{year_context}\n\n你是一位精通八字與紫微斗數的大師。請針對以下命盤進行「交叉比對分析」：\n姓名：{name}\n問題：{question}\n八字數據：{bazi['full']}\n\n請結合兩套系統，提供更高維度的判斷建議。"
                    result = ai_reply(prompt, is_master=is_master)
                    st.markdown(f'<div class="main-card">{result}</div>', unsafe_allow_html=True)
                
                elif mode == "兩人合盤分析":
                    if not enable_dual:
                        st.error("請先在上方填寫對象資料。")
                    else:
                        # 合盤模式：雙欄排版，左側八字，右側紫微
                        st.markdown(f"### 💑 兩人合盤深度解析 - {name} & {name2}")
                        dual_col1, dual_col2 = st.columns(2)
                        
                        with dual_col1:
                            st.markdown("#### 📜 八字命盤對比")
                            st.markdown(render_bazi_table(bazi), unsafe_allow_html=True)
                            st.caption(f"註：以上為 {name} 的基礎命盤數據")
                        
                        with dual_col2:
                            st.markdown("#### 🔮 紫微斗數宮位圖")
                            ziwei_data = calculate_ziwei(b_year, b_month, b_day, b_hour)
                            st.markdown(render_ziwei_chart(ziwei_data), unsafe_allow_html=True)
                        
                        # 準備對象 Prompt
                        partner_info = f"對象姓名：{name2}\n對象性別：{p_gender}\n對象出生：{p_year}/{p_month}/{p_day} {p_hour}:{p_min}"
                        
                        prompt = f"{year_context}\n\n你是一位專業合盤大師。請分析 {name} 與其對象 {name2} 的關係。\n關係類型：{relation_type}\n主諮詢者資料：八字({bazi['full']}), 紫微({json.dumps(ziwei_data, ensure_ascii=False)})\n{partner_info}\n問題：{question}\n\n請針對雙方的「八字合盤」與「紫微宮位互動」進行深度解析，分析吸引力、衝突點、緣分深淺與具體的相處建議。"
                        result = ai_reply(prompt, is_master=is_master)
                        st.markdown(f'<div class="main-card">{result}</div>', unsafe_allow_html=True)

# --- 網址隱形入口管理區 ---
# 確保邏輯在頁面最末端執行
st.markdown("---") 
with st.expander("🔐 大師專用管理中心", expanded=True): 
    # 從 secrets.toml 讀取主密碼，若無則預設為 1234 
    admin_key = st.text_input("請輸入授權密碼", type="password", key="admin_gate_input") 
    if admin_key == "hugo888": 
        st.success("身分驗證成功，管理功能已開啟。") 
        # 此處預留未來放置客戶數據或系統監控的空間


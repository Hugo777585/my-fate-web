import streamlit as st
import google.generativeai as genai
import datetime
import time
import os
import gspread
import re
import json
import csv
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from lunar_python import Lunar, Solar
from tone_engine import analyze_tone_strategy
from fpdf import FPDF

# --- PDF 報告產生器 ---
class ReportPDF(FPDF):
    def footer(self):
        # 頁尾
        self.set_y(-15)
        try:
            self.set_font("CJK", size=9)
        except:
            self.set_font("Helvetica", size=9)
        self.cell(0, 10, "雨果大師命理 AI - 執此命書，願你洞悉天機，行穩致遠。", align="C")

def _find_cjk_font():
    # 支援 Windows 與 Linux (Streamlit Cloud) 的常見字體路徑
    candidates = [
        r"C:\Windows\Fonts\msjh.ttc",    # Windows 微軟正黑
        r"C:\Windows\Fonts\msyh.ttc",    # Windows 雅黑
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", # Linux Noto CJK
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSerifCJK-Regular.ttc",
        "/usr/share/fonts/fonts-noto-cjk/NotoSansCJK.ttc"
    ]
    for p in candidates:
        if os.path.exists(p): return p
    return None

def create_pdf(user_name, body):
    pdf = ReportPDF()
    font_path = _find_cjk_font()
    
    if font_path:
        pdf.add_font("CJK", "", font_path, uni=True)
        pdf.set_font("CJK", size=16)
    else:
        pdf.set_font("Helvetica", size=16)
    
    pdf.add_page()
    pdf.cell(0, 10, f"{user_name} - 命理 AI 分析報告", ln=True, align="C")
    pdf.ln(10)
    
    if font_path:
        pdf.set_font("CJK", size=11)
    else:
        pdf.set_font("Helvetica", size=11)
    
    # 移除 Markdown 語法 (簡單處理)
    clean_body = body.replace("**", "").replace("### ", "").replace("## ", "").replace("# ", "")
    pdf.multi_cell(0, 8, clean_body)
    
    return bytes(pdf.output())

# 載入環境變數 (Local 開發用)
load_dotenv()

# --- 初始化付款狀態 ---
if 'payment_status' not in st.session_state:
    st.session_state.payment_status = "free"
if 'order_data' not in st.session_state:
    st.session_state.order_data = None

# --- 訂單處理邏輯 ---
def save_order_to_csv(order_info):
    file_exists = os.path.isfile('orders.csv')
    with open('orders.csv', mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['order_id', 'created_at', 'name', 'contact', 'phone', 'birth_date', 'birth_time', 'gender', 'question', 'plan', 'payment_status'])
        writer.writerow([
            order_info['order_id'],
            order_info['created_at'],
            order_info['name'],
            order_info['contact'],
            order_info['phone'],
            order_info['birth_date'],
            order_info['birth_time'],
            order_info['gender'],
            order_info['question'],
            order_info['plan'],
            order_info['payment_status']
        ])

# --- Google Sheets 連線設定 ---
def init_gsheets():
    client_email = "未知"
    service_account_info = None
    max_retries = 3
    retry_delay = 2 # 秒
    
    for attempt in range(max_retries):
        try:
            # 定義存取範圍
            scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
            
            # 1. 優先嘗試讀取本地 hugo-key.json
            key_file_path = "hugo-key.json"
            if os.path.exists(key_file_path):
                try:
                    with open(key_file_path, "r", encoding="utf-8") as f:
                        service_account_info = json.load(f)
                except Exception as e:
                    return None, client_email, f"🔑 鑰匙格式錯誤 (JSON 毀損)：{str(e)}"
            
            # 2. 如果本地檔案不存在，則嘗試讀取 Streamlit Secrets (雲端環境)
            if not service_account_info:
                if "gcp_service_account" in st.secrets:
                    service_account_info = st.secrets["gcp_service_account"]
                else:
                    return None, client_email, "🚫 找不到連線憑證：本地無 hugo-key.json，且雲端 Secrets 未設定 [gcp_service_account]。"
                
            client_email = service_account_info.get("client_email", "未知")
            
            # 3. 建立憑證與授權
            creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
            client = gspread.authorize(creds)
            
            # 4. 開啟試算表
            sheet_url = st.secrets.get("gsheets_url")
            sheet_name = "雨果天命智庫客戶紀錄"
            
            if sheet_url:
                spreadsheet = client.open_by_url(sheet_url)
            else:
                spreadsheet = client.open(sheet_name)
            
            sheet = spreadsheet.sheet1
            return sheet, client_email, None

        except (gspread.exceptions.SpreadsheetNotFound, gspread.exceptions.NoValidUrlKeyFound):
            return None, client_email, f"📂 試算表找不到：請確認名稱為 '{sheet_name}' 或 URL 正確。"
        except gspread.exceptions.APIError as e:
            if "Permission denied" in str(e):
                return None, client_email, "📂 權限不足：請確保已將試算表「共用」給服務帳號 Email。"
            return None, client_email, f"⚠️ Google API 錯誤：{str(e)}"
        except Exception as e:
            # 針對網路或 DNS 錯誤進行重試
            err_str = str(e)
            if "NameResolutionError" in err_str or "connection" in err_str.lower() or "timeout" in err_str.lower():
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
                return None, client_email, f"🌐 網路連線或 DNS 解析失敗：{err_str}。請檢查雲端環境網路狀態。"
            return None, client_email, f"🚨 連線系統錯誤：{err_str}"
            
    return None, client_email, "🚨 連線失敗：已達最大重試次數。"

# 初始化試算表物件
sheet, current_client_email, gs_error = init_gsheets()

with st.sidebar:
    st.header("📊 資料庫連線")
    if gs_error:
        st.error(gs_error)
        st.warning(f"💡 請將試算表共用給：\n`{current_client_email}`")
    elif sheet:
        st.success(f"✅ 已連線：{sheet.spreadsheet.title}")
        st.info(f"📧 服務帳號：`{current_client_email}`")

    st.markdown("---")
    if st.button("🧠 AI感情心理分析"):
        st.switch_page("pages/02_love_analysis.py")

def get_wuxing_color(char):
    """根據干支字元回傳對應的五行背景顏色"""
    if not char: return "#FFFFFF"
    char = char[0] # 取第一個字
    wuxing_map = {
        # 木
        '甲': '#C8E6C9', '乙': '#C8E6C9', '寅': '#C8E6C9', '卯': '#C8E6C9',
        # 火
        '丙': '#FFCDD2', '丁': '#FFCDD2', '巳': '#FFCDD2', '午': '#FFCDD2',
        # 土
        '戊': '#FFF9C4', '己': '#FFF9C4', '辰': '#FFF9C4', '戌': '#FFF9C4', '丑': '#FFF9C4', '未': '#FFF9C4',
        # 金
        '庚': '#F5F5F5', '辛': '#F5F5F5', '申': '#F5F5F5', '酉': '#F5F5F5',
        # 水
        '壬': '#BBDEFB', '癸': '#BBDEFB', '亥': '#BBDEFB', '子': '#BBDEFB',
    }
    return wuxing_map.get(char, "#FFFFFF")

def render_bazi_table(bazi):
    """產生彩色五行排盤 HTML 表格"""
    if not bazi: return ""
    
    # 取得各柱顏色
    y_color = get_wuxing_color(bazi['year_dz'])
    m_color = get_wuxing_color(bazi['month_dz'])
    d_color = get_wuxing_color(bazi['day_dz'])
    h_color = get_wuxing_color(bazi['hour_dz'])
    
    # 使用媒體查詢 (Media Query) 或相對單位來優化手機顯示
    html = f"""
    <div style="overflow-x: auto; -webkit-overflow-scrolling: touch; margin-bottom: 20px;">
        <style>
            .bazi-table {{
                border-collapse: collapse; 
                width: 100%; 
                min-width: 450px; /* 確保在手機上不會縮到看不見 */
                font-size: 18px; 
                font-weight: bold; 
                text-align: center; 
                border: 2px solid #6C3483;
            }}
            @media (max-width: 600px) {{
                .bazi-table {{
                    font-size: 14px; /* 手機版字體調小 */
                }}
                .bazi-table td, .bazi-table th {{
                    padding: 6px !important;
                }}
            }}
        </style>
        <table class="bazi-table" border="1">
            <tr style="background-color: #6C3483; color: white;">
                <th style="padding: 10px;">四柱</th>
                <th style="padding: 10px;">天干</th>
                <th style="padding: 10px;">十神</th>
                <th style="padding: 10px;">地支</th>
                <th style="padding: 10px;">藏干</th>
            </tr>
            <tr style="background-color: {y_color}; color: #1A1A1A; font-weight: 600;">
                <td style="padding: 10px; border: 1px solid #6C3483;">年柱</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['year_tg']}</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['year_ss']}</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['year_dz']}</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['year_hide']}</td>
            </tr>
            <tr style="background-color: {m_color}; color: #1A1A1A; font-weight: 600;">
                <td style="padding: 10px; border: 1px solid #6C3483;">月柱</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['month_tg']}</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['month_ss']}</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['month_dz']}</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['month_hide']}</td>
            </tr>
            <tr style="background-color: {d_color}; color: #1A1A1A; font-weight: 600;">
                <td style="padding: 10px; border: 1px solid #6C3483;">日柱 (日主)</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['day_tg']}【日主】</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">日主</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['day_dz']}</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['day_hide']}</td>
            </tr>
            <tr style="background-color: {h_color}; color: #1A1A1A; font-weight: 600;">
                <td style="padding: 10px; border: 1px solid #6C3483;">時柱</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['hour_tg']}</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['hour_ss']}</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['hour_dz']}</td>
                <td style="padding: 10px; border: 1px solid #6C3483;">{bazi['hour_hide']}</td>
            </tr>
        </table>
    </div>
    """
    return html

def calculate_bazi(y, m, d, h, minute):
    try:
        # 使用 Solar 類來處理國曆日期與時間，確保節氣轉換精準
        solar = Solar.fromYmdHms(int(y), int(m), int(d), int(h), int(minute), 0)
        lunar = solar.getLunar()
        eight_char = lunar.getEightChar()
        
        # 取得八字四柱 (年、月、日、時)
        year_pillar = eight_char.getYear()
        month_pillar = eight_char.getMonth()
        day_pillar = eight_char.getDay()
        hour_pillar = eight_char.getTime()

        # 取得藏干
        year_hide = "".join(eight_char.getYearHideGan())
        month_hide = "".join(eight_char.getMonthHideGan())
        day_hide = "".join(eight_char.getDayHideGan())
        hour_hide = "".join(eight_char.getTimeHideGan())

        # 取得十神 (以日主為中心)
        year_shishen = eight_char.getYearShiShenGan()
        month_shishen = eight_char.getMonthShiShenGan()
        hour_shishen = eight_char.getTimeShiShenGan()

        return {
            'year_tg': year_pillar[:1], 'year_dz': year_pillar[1:2], 'year_ss': year_shishen, 'year_hide': year_hide,
            'month_tg': month_pillar[:1], 'month_dz': month_pillar[1:2], 'month_ss': month_shishen, 'month_hide': month_hide,
            'day_tg': day_pillar[:1], 'day_dz': day_pillar[1:2], 'day_ss': '日主', 'day_hide': day_hide,
            'hour_tg': hour_pillar[:1], 'hour_dz': hour_pillar[1:2], 'hour_ss': hour_shishen, 'hour_hide': hour_hide,
            'full': {
                'year': year_pillar,
                'month': month_pillar,
                'day': day_pillar,
                'hour': hour_pillar
            }
        }
    except Exception as e:
        st.error(f"命盤計算發生系統錯誤：{e}")
        return None

st.set_page_config(page_title="雨果大師｜命理 AI", page_icon="🔮", layout="wide")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

# CSS 注入：美化介面並隱藏 Streamlit 預設元素
st.markdown("""
<style>
    .main-title {
        font-size: 2.8em;
        font-weight: 800;
        color: #6C3483;
        text-align: center;
        margin-bottom: 0.1em;
        text-shadow: 2px 2px 4px rgba(108, 52, 131, 0.2);
    }
    .sub-title {
        font-size: 1.1em;
        color: #7D3C98;
        text-align: center;
        margin-bottom: 2em;
        font-style: italic;
    }
    .result-card {
        background: linear-gradient(135deg, #F9F0FF 0%, #E8DAEF 100%);
        border: 2px solid #A569BD;
        border-radius: 16px;
        padding: 28px;
        margin-top: 20px;
        box-shadow: 0 8px 32px rgba(165, 105, 189, 0.25);
    }
    .result-header {
        font-size: 1.4em;
        color: #6C3483;
        font-weight: 700;
        margin-bottom: 15px;
        border-bottom: 2px solid #D7BDE2;
        padding-bottom: 8px;
    }
    .stButton>button {
        background: linear-gradient(135deg, #8E44AD, #A569BD);
        color: white;
        font-weight: 700;
        font-size: 1.1em;
        padding: 0.6em 2em;
        border-radius: 12px;
        border: none;
        box-shadow: 0 4px 15px rgba(142, 68, 173, 0.4);
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #9B59B6, #BB8FCE);
        box-shadow: 0 6px 20px rgba(142, 68, 173, 0.5);
        transform: translateY(-2px);
    }
    .master-zone {
        background-color: #f4f0ff;
        border: 1px dashed #8e44ad;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    /* 多步驟表單過場動畫 */
    .st-step-container {
        animation: fadeIn 0.5s ease-in-out;
    }
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .step-btn-active {
        background-color: #6C3483 !important;
        color: white !important;
    }
    /* 進階服務區塊 CTA 樣式 */
    .cta-container {
        background: linear-gradient(135deg, #FFF4E6 0%, #FFF9F0 100%);
        border: 2px dashed #E67E22;
        border-radius: 16px;
        padding: 25px;
        margin-top: 30px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(230, 126, 34, 0.15);
    }
    .cta-title {
        font-size: 1.3em;
        font-weight: 700;
        color: #D35400;
        margin-bottom: 10px;
    }
    .cta-text {
        font-size: 0.95em;
        color: #A04000;
        margin-bottom: 20px;
    }
    /* 新增首頁排版樣式 */
    .hero-section {
        text-align: center;
        padding: 40px 20px;
        background-color: #000000;
        color: #D4AF37; /* 金色 */
        border-radius: 20px;
        margin-bottom: 40px;
    }
    .hero-title {
        font-size: 3.5em;
        font-weight: 900;
        margin-bottom: 10px;
        color: #D4AF37;
    }
    .hero-subtitle {
        font-size: 1.5em;
        margin-bottom: 20px;
        color: #FFFFFF;
    }
    .hero-copy {
        font-size: 1.2em;
        margin-bottom: 30px;
        color: #CCCCCC;
    }
    .section-container {
        padding: 60px 20px;
        margin-bottom: 40px;
        border-radius: 20px;
    }
    .pain-points-section {
        background-color: #F8F9FA;
    }
    .pain-point-item {
        font-size: 1.2em;
        margin-bottom: 15px;
        padding-left: 20px;
        border-left: 4px solid #6C3483;
    }
    .plan-card {
        background: white;
        border: 2px solid #E0E0E0;
        border-radius: 20px;
        padding: 30px;
        text-align: center;
        transition: all 0.3s ease;
        height: 100%;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .plan-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 30px rgba(108, 52, 131, 0.15);
    }
    .plan-card.popular {
        border: 3px solid #A569BD;
        background: linear-gradient(180deg, #FFFFFF 0%, #F5EEF8 100%);
        position: relative;
    }
    .popular-badge {
        position: absolute;
        top: -15px;
        left: 50%;
        transform: translateX(-50%);
        background: #A569BD;
        color: white;
        padding: 4px 15px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: 700;
        letter-spacing: 1px;
        z-index: 10;
    }
    .plan-title {
        font-size: 1.5em;
        font-weight: 800;
        color: #4A235A;
        margin-bottom: 10px;
    }
    .plan-price {
        font-size: 2.2em;
        font-weight: 900;
        color: #6C3483;
        margin-bottom: 20px;
    }
    .plan-price span {
        font-size: 0.5em;
        color: #7B7B7B;
        font-weight: 400;
    }
    .plan-features {
        text-align: left;
        margin-bottom: 25px;
        list-style: none;
        padding: 0;
    }
    .plan-features li {
        margin-bottom: 12px;
        color: #4D5656;
        font-size: 0.95em;
        display: flex;
        align-items: center;
    }
    .plan-features li:before {
        content: "✅";
        margin-right: 10px;
        font-size: 0.8em;
    }
    .plan-features li.locked {
        color: #ABB2B9;
    }
    .plan-features li.locked:before {
        content: "🔒";
    }
    
    /* 結尾解鎖區塊樣式 */
    .locked-preview {
        background: #F4F6F7;
        border-radius: 12px;
        padding: 25px;
        margin-top: 25px;
        position: relative;
        overflow: hidden;
        border: 1px solid #D7BDE2;
    }
    .locked-preview-blur {
        filter: blur(5px);
        opacity: 0.5;
        user-select: none;
    }
    .locked-overlay {
        position: absolute;
        top: 0; left: 0; right: 0; bottom: 0;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        background: rgba(255, 255, 255, 0.5);
        z-index: 10;
    }
    .locked-text {
        background: white;
        padding: 12px 30px;
        border-radius: 50px;
        box-shadow: 0 4px 20px rgba(108, 52, 131, 0.2);
        font-weight: 800;
        color: #6C3483;
        border: 2px solid #6C3483;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        gap: 8px;
    }
    .trust-section {
        background-color: #F0E6FF;
        padding: 40px;
        border-radius: 20px;
    }
    .final-cta {
        background: linear-gradient(135deg, #6C3483, #8E44AD);
        color: white;
        text-align: center;
        padding: 60px 20px;
        border-radius: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. Hero 主視覺 ---
if st.session_state.get('scroll_to_analysis'):
    st.markdown('<script>window.parent.document.getElementById("analysis_section").scrollIntoView({behavior: "smooth"});</script>', unsafe_allow_html=True)
    st.session_state.scroll_to_analysis = False

st.markdown('<h1 class="main-title">HUGO 天命智庫</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">八字命理 × AI分析 × 感情諮詢</p>', unsafe_allow_html=True)

# 2. 管理員密碼鎖 (大師盤)
MASTER_CODE = "HUGO888"
is_master = False

with st.sidebar:
    st.header("🔐 系統授權")
    auth_code_input = st.text_input("大師專用授權碼", type="password", key="auth_code_input")
    
    # 強制比對邏輯：去空格、轉大寫
    if auth_code_input.strip().upper() == MASTER_CODE:
        is_master = True
        st.success("✅ 大師模式已開啟")
        
        st.markdown("---")
        st.subheader("📊 資料庫連線狀態")
        
        if sheet:
            st.info(f"📁 已連線至：{sheet.spreadsheet.title}")
            if st.button("🔍 執行連線測試"):
                try:
                    # 測試讀取標題
                    headers = sheet.row_values(1)
                    st.write("✅ 讀取測試成功！")
                    st.write(f"📋 標題列：{', '.join(headers[:5])}...")
                except Exception as e:
                    st.error(f"❌ 讀取失敗：{e}")
        else:
            st.error("❌ 試算表連線失敗")
            st.markdown("""
            **檢查清單：**
            1. Secrets 是否已正確設定 `gcp_service_account`？
            2. 試算表名稱是否為 `雨果天命智庫客戶紀錄`？
            3. 是否已分享權限給服務帳號 Email？
            """)
    elif auth_code_input != "":
        st.error("❌ 授權碼錯誤")

# 3. API 設定
SYSTEM_INSTRUCTION = """你是一個專業且具備心理學同理心的命理分析大師。
請嚴格遵守以下指令進行分析：

【核心法則：70/30 命運法則】
1. 禁止鐵口直斷：絕對禁止使用『絕對』、『一定會』、『命中註定逃不掉』等極端字眼。所有分析應視為『機率』與『趨勢』。
2. 70/30 結構化分析：
   - 70% 命理趨勢：分析先天命盤特質、五行喜忌與當前流年環境的客觀引導。
   - 30% 自由意志：提出後天可以採取的具體行動、心態轉變或應對策略。
3. 賦權用戶：結論必須強調八字只是人生的天氣預報，那 30% 的選擇權才是決定最終結局的關鍵。語氣應讓人感到『充滿力量』與『希望』，而非恐懼。

【⚙️ Hugo 命理系統：紅色警戒模式 (高危險感情模式)】
當分析使用者（或其伴侶）的命盤時，若偵測到以下特定結構，請強制啟動【紅色警戒模式】，並輸出對應的行為預測與實戰警告：

🔴 警戒點一：【破壞性掠奪與雙面人設】
- 觸發條件 (八字)：命局中「劫財」過旺（兩個以上），且日支（夫妻宮）遭遇嚴重「地支相沖」（如寅申沖、子午沖、卯酉沖、辰戌沖）。
- 行為預測：此盤帶有極強隱蔽性與破壞力。表面看似有原則或重感情，骨子裡「劫財」心性極端自我中心。親密關係地基（夫妻宮）隨時會崩塌。
- 警告語：⚠️ 【系統警告：高度感情耗損風險】 注意！此盤主的感情防線極度不穩定。極易出現「多線發展」、「滿口謊言」或「利益掠奪」。對方可能將「分手」當作操控籌碼，並在斷聯後用小恩小惠或未來承諾進行情緒勒索。請「聽其言，更要觀其行」，切勿被表面人設蒙蔽，必須嚴格設定停損點！

🔴 警戒點二：【缺乏界線與情緒反咬】
- 觸發條件 (八字)：1. 八字日主極弱且官殺壓迫（殺重身輕）。2. 命盤見「傷官見官」或「梟印奪食」等情緒劇烈波動結構。
- 行為預測：內心是填不滿的情緒黑洞。因能量太弱渴望溫暖，初期交往毫無界線。一旦感到壓力或理虧心虛，負面能量爆發，會用刻薄、顛倒是非的言語攻擊伴侶。
- 警告語：⚠️ 【系統警告：吸血型依附與惡意重構風險】 注意！此盤主極度缺乏安全感與人際界線。初期展現脆弱引發您的「拯救慾」。但這是單向消耗的關係。當對方無法處理自身情緒，會啟動防禦機制，用言語踐踏您的付出。請停止「過度承擔」，不要試圖拯救對方！

🔴 警戒點三：【宿命吸引：拯救者陷阱】（合盤互動警示）
- 觸發條件 (雙人合盤)：客人盤帶強烈「庇護/照顧」特質（如丙火日主、印星極旺、日主能量強且具備包容力），且詢問上述警戒點對象。
- 警告語：🚨 【系統最高警告：拯救者消耗迴圈】 您的命格自帶強大溫暖，宛如「心靈急診室」，極易吸引到情緒黑洞對象。這不是正緣，是能量考驗！您無法用個人善意填平對方的業力。請立刻收回您的「庇護能量」，將重心放回自己身上。談戀愛不是做慈善，請果斷物理切割！

【輸出要求】
1. 只能輸出 Markdown 格式，禁止任何無意義的開場白。
"""

try:
    # 優先順序：Streamlit Secrets > .env 檔案 > 環境變數
    gemini_key = st.secrets.get("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    
    if not gemini_key:
        # 嘗試從已讀取的 service_account_info 中抓取 (如果有的話)
        # 或者從其它檔案讀取，但通常 GEMINI_API_KEY 應該獨立於 GCP 帳號
        st.error("API 金鑰讀取失敗：請在 Streamlit Secrets 中設定 `GEMINI_API_KEY`。")
        st.stop()
        
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel(
        "gemini-flash-latest", # 使用相容性最高且穩定的 Flash 最新版
        system_instruction=SYSTEM_INSTRUCTION
    )
except Exception as e:
    st.error(f"API 設定發生錯誤：{e}")
    st.stop()

# 4. 功能模式選擇
st.markdown("### 🎯 選擇分析模式")
analysis_mode = st.radio(
    "請選擇命理分析模式",
    ["【八字精論】"],
    horizontal=True,
    label_visibility="collapsed"
)
st.markdown("---")

# 5. 基礎輸入介面 (大眾版與大師盤通用)
with st.container():
    st.markdown("### 📋 填寫基本資料")
    col1, col2, col3 = st.columns(3)
    with col1:
        name = st.text_input("姓名/暱稱", placeholder="如何稱呼您？")
    with col2:
        gender = st.selectbox("性別", ["男", "女"])
    with col3:
        occupation = st.selectbox(
            "目前狀態/職業",
            ["學生", "上班族", "受聘", "自營商", "合夥公司", "待業", "家管", "退休", "更生人", "身障"]
        )

    st.markdown("#### 📅 出生時間 (國曆)")
    
    # 判斷是否為手機版排版 (Streamlit 寬度小於某值時會自動堆疊，但我們主動優化)
    col_date1, col_date2, col_date3 = st.columns(3)
    with col_date1:
        years = list(range(1930, 2027))
        b_year = st.selectbox("年", options=years, index=years.index(1980))
    with col_date2:
        months = list(range(1, 13))
        b_month = st.selectbox("月", options=months, index=0)
    with col_date3:
        days = list(range(1, 32))
        b_day = st.selectbox("日", options=days, index=0)
    
    col_time1, col_time2, col_spacer = st.columns([1, 1, 1])
    with col_time1:
        hours = list(range(0, 24))
        b_hour = st.selectbox("時", options=hours, index=12)
    with col_time2:
        mins = list(range(0, 60))
        b_min = st.selectbox("分", options=mins, index=0)
    with col_spacer:
        st.write("") # 佔位符，讓時分在手機版看起來更平衡

    # --- 引導式多步驟表單 (Multi-step Form) ---
    st.markdown("#### 💬 告訴大師您的困惑")
    
    if 'form_step' not in st.session_state:
        st.session_state.form_step = 1
    if 'main_cat' not in st.session_state:
        st.session_state.main_cat = None
    if 'sub_cat' not in st.session_state:
        st.session_state.sub_cat = None
    if 'detail_text' not in st.session_state:
        st.session_state.detail_text = ""
    if 'trigger_analysis' not in st.session_state:
        st.session_state.trigger_analysis = False

    form_container = st.container()
    
    with form_container:
        st.markdown('<div class="st-step-container">', unsafe_allow_html=True)
        
        # 0. 大分類選擇 (始終顯示，滿足隨時切換需求)
        st.write("✨ **請選擇諮詢分類：**")
        col_cat1, col_cat2 = st.columns(2)
        with col_cat1:
            # 增加 key 確保狀態穩定，並在點擊時強制重置相關狀態
            if st.button("💘 感情婚姻", use_container_width=True, key="main_cat_love"):
                st.session_state.main_cat = "感情"
                st.session_state.form_step = 2  # 切換後進入該分類的第二步
                st.rerun()
        with col_cat2:
            if st.button("💼 事業財運", use_container_width=True, key="main_cat_job"):
                st.session_state.main_cat = "事業"
                st.session_state.form_step = 2
                st.rerun()
        
        st.markdown("---")

        # 步驟一：引導（如果尚未選擇）
        if st.session_state.form_step == 1:
            st.info("💡 請點選上方按鈕選擇諮詢分類")
        
        # 步驟二：次級狀態選擇
        elif st.session_state.form_step == 2:
            st.write(f"✨ **第二步：關於「{st.session_state.main_cat}」，目前的具體狀態是？**")
            
            if st.session_state.main_cat == "感情":
                options = ["曖昧中", "面臨分手", "懷疑欺瞞", "單身求緣", "婚姻危機", "其他"]
            else:
                options = ["想換工作", "創業諮詢", "財運不佳", "職場人際", "升遷機會", "其他"]
            
            # 使用按鈕矩陣呈現
            cols = st.columns(3)
            for i, opt in enumerate(options):
                with cols[i % 3]:
                    if st.button(opt, use_container_width=True):
                        st.session_state.sub_cat = opt
                        st.session_state.form_step = 3
                        st.rerun()
            
            if st.button("⬅️ 返回上一步"):
                st.session_state.form_step = 1
                st.rerun()

        # 步驟三：細節描述
        elif st.session_state.form_step == 3:
            st.write(f"✨ **第三步：描述一下「{st.session_state.sub_cat}」具體發生了什麼事？**")
            
            placeholder_text = "描述對方具體做了什麼讓你最在意的事？" if st.session_state.main_cat == "感情" else "請描述目前事業或財運上遇到的具體困難..."
            
            st.session_state.detail_text = st.text_area(
                "詳細描述", 
                value=st.session_state.detail_text,
                placeholder=placeholder_text,
                height=150,
                label_visibility="collapsed"
            )
            
            col_f1, col_f2 = st.columns([1, 1])
            with col_f1:
                if st.button("⬅️ 返回上一步", use_container_width=True):
                    st.session_state.form_step = 2
                    st.rerun()
            with col_f2:
                if st.button("✅ 確認並開始分析", use_container_width=True):
                    # 確認後直接觸發分析
                    st.session_state.trigger_analysis = True
                    st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

    # 整合最終提問字串
    if st.session_state.main_cat and st.session_state.sub_cat:
        question = f"【諮詢類別：{st.session_state.main_cat} - {st.session_state.sub_cat}】\n{st.session_state.detail_text}"
    else:
        question = ""

# 5. 大師進階分析區 (僅在密碼正確時顯示)
advanced_params = {}
if is_master:
    with st.expander("🔮 大師進階分析區", expanded=True):
        st.markdown('<div class="master-zone">', unsafe_allow_html=True)
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            advanced_params['focus'] = st.multiselect(
                "加強分析維度",
                ["流年流月運勢", "神煞精論", "格局細分", "十神深論", "調候用神詳解"],
                default=["流年流月運勢"]
            )
        with col_m2:
            advanced_params['theory'] = st.radio(
                "核心學理偏好",
                ["平衡中和", "氣勢從格", "調候優先"],
                horizontal=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

# 6. 雙人合盤功能 (保留原本的邏輯)
# 任務一：動態隱藏對象
# 當使用者狀態為「單身」或「個人工作/事業」時，完全隱藏第二位對象的輸入區塊
is_personal = (st.session_state.sub_cat == "單身求緣") or (st.session_state.main_cat == "事業")

enable_dual = False
if not is_personal:
    enable_dual = st.checkbox("💞 啟用雙人合盤 (感情/合夥)")

# 初始化對象變數，避免未啟用時報錯
name2 = "無"
b_year2, b_month2, b_day2, b_hour2, b_min2 = 1980, 1, 1, 12, 0
relation_type = "無"

if enable_dual and not is_personal:
    st.subheader("💞 第二位對象資料")
    col_p2_name, col_p2_gender = st.columns(2)
    with col_p2_name:
        name2 = st.text_input("對象姓名/暱稱", placeholder="如何稱呼對方？", key="name2")
    with col_p2_gender:
        gender2 = st.selectbox("對象性別", ["男", "女"], key="gender2")
        
    col_p2_1, col_p2_2, col_p2_3, col_p2_4, col_p2_5 = st.columns(5)
    with col_p2_1:
        years = list(range(1930, 2027))
        b_year2 = st.selectbox("年", options=years, index=years.index(1980), key="b_year2")
    with col_p2_2:
        months = list(range(1, 13))
        b_month2 = st.selectbox("月", options=months, index=0, key="b_month2")
    with col_p2_3:
        days = list(range(1, 32))
        b_day2 = st.selectbox("日", options=days, index=0, key="b_day2")
    with col_p2_4:
        hours = list(range(0, 24))
        b_hour2 = st.selectbox("時", options=hours, index=12, key="b_hour2")
    with col_p2_5:
        mins = list(range(0, 60))
        b_min2 = st.selectbox("分", options=mins, index=0, key="b_min2")
    relation_type = st.selectbox("雙方關係", ["情侶/夫妻", "事業合夥", "家人/朋友"])

st.markdown("---")

# 任務一-3：新增提問區
st.markdown("#### 🚀 核心卡關問題")
user_detailed_question = st.text_area(
    "您目前遇到最大的卡關是什麼？或有什麼具體想問的問題？（描述越詳細，大師解析越精準）",
    placeholder="例如：這段感情還有救嗎？對方對我是認真的嗎？我該不該換工作？",
    height=150
)

# 任務一：動態送出按鈕 (已移動至最下方)
st.markdown("---")
col_btn_left, col_btn_right, col_btn_end = st.columns([1, 2, 1])
with col_btn_right:
    if enable_dual and not is_personal:
        btn_label = "💞 進行兩人合盤解說"
    else:
        btn_label = "✨ 開始個人深度流年解析"
    
    if is_master:
        btn_label = "🔮 大師深度發功"
    
    main_btn_clicked = st.button(btn_label, use_container_width=True)
    
    if main_btn_clicked or st.session_state.trigger_analysis:
        st.session_state.trigger_analysis = False
        
        if not question:
            st.warning("請簡單填寫一下您想問的問題，大師才能為您指點迷津喔！")
        else:
            start_time = time.time()
            with st.spinner("大師正在排盤與分析中，請稍候..."):
                bazi = calculate_bazi(b_year, b_month, b_day, b_hour, b_min)
                bazi_shishen = []
                if bazi:
                    bazi_shishen = [bazi['year_ss'], bazi['month_ss'], bazi['hour_ss']]
                
                tone_strategy = analyze_tone_strategy(question, bazi_shishen)
                tone_instruction = f"\n\n【當前對話語氣指引】：\n{tone_strategy['system_prompt']}\n請確保在回覆中完美融入此語氣。"

                if bazi:
                    pillar_info = f"""
【萬年曆精算命盤】：
年柱：{bazi['full']['year']}
月柱：{bazi['full']['month']}
日柱：{bazi['full']['day']} (日主：{bazi['day_tg']})
時柱：{bazi['full']['hour']}
"""
                else:
                    pillar_info = "（命盤計算失敗，請檢查輸入日期）"

                base_info = f"姓名：{name}，性別：{gender}，生日：{b_year}/{b_month}/{b_day} {b_hour}:{b_min}，職業：{occupation}，提問：{question}，具體卡關：{user_detailed_question}"

                current_year = datetime.datetime.now().year
                next_year = current_year + 1
                
                # 任務二：Finn 大腦升級 (Prompt)
                # 使用使用者提供的完整架構替換
                prompt = f"""
現在是 {current_year} 年。你是一位名為 Finn 的專業八字命理大師。
這是系統的第一層「基礎命理分析」。核心任務是：運用【三本八字經典】邏輯，進行精準解析，建立信任感。
【嚴格限制】：只能點出「為什麼會發生」，【絕對不可】給出心理學解方、應對策略或下一步建議。

請依以下架構輸出（600-800字）：
### 1. 【四柱八字排盤】
(若有對象資料，務必畫出雙方四柱對照表；若無則只畫命主)。請用簡單表格呈現天干地支。
### 2. 【命格底蘊與流年掃描】
結合經典邏輯，精準點出命主在 {current_year} 年面臨的核心關卡，解釋現狀成因。
### 3. 【關係合盤與狀態解析】
(若有對方資料)：對比雙方八字五行互補與摩擦點。
(若無)：精準分析命主近期的感情或人際卡關狀態。
### 4. 【大師結語與引導】
(針對客戶提問的卡關點：{question} 進行一句話的同理共鳴，接著強制換行並輸出以下引流文案)
---
### 💡 大師點評：為什麼你會感覺「卡住了」？
這份初步分析，是為了幫你看清楚「為什麼會發生目前的狀況」。命盤顯示你最近的困擾，往往來自於流年磁場的波動，讓你感覺：
👉 人際關係不太單純，容易被誤解
👉 做決定時總有一種「看不清前方」的阻礙感
👉 表面平穩，但背後壓力與競爭正在醞釀

⚠️ **但這一段分析，只是告訴你：為什麼會發生。**

真正的結果，取決於接下來的行動。這份報告還沒有揭露：
❌ 哪幾個關鍵月份你該全力出擊，或徹底收手？
❌ 哪些人是你必須立刻拉開距離的「能量黑洞」？
❌ 如果衝突爆發，你該用什麼策略才能反敗為勝？

這部分，才是「真正改變結果」的關鍵。

---
### 🔮 選擇適合您的轉運方案：

#### 【💸 299 深度分析：釐清局勢】
適合想「避開地雷」的你。我將為您補上：
✔ 關鍵流年月份提醒
✔ 目前困境的深層原因拆解
✔ 基礎的應對行動方向

#### 【🔥 699 完整分析：主導結果】
適合「已經遇到問題」或「不允許自己再走錯」的你。我們將直接進入實戰：
✔ 核心人際 / 感情卡關的「斷點」分析
✔ 具體告訴你：該進、該退，還是觀察？
✔ 給予下一步的對話策略與具體化解行動（絕非模糊建議）

---
🎯 **大師建議：**
如果您不確定自己適合哪種深度，可以直接將您的具體狀況傳送給我，我會親自為您判斷最合適的解析方式。
👇 請點擊下方【🧠 AI感情心理分析】開始您的改變。
"""
                
                # 附加原始資料與盤位資訊供 AI 參考，但不強制 AI 輸出格式（由上面的架構要求決定）
                prompt += f"\n\n【參考資料】\n命主資料：{name}, {gender}, {b_year}/{b_month}/{b_day} {b_hour}:{b_min}, 職業:{occupation}\n提問：{question}\n詳細卡關：{user_detailed_question}\n{pillar_info}"
                
                if enable_dual:
                    bazi2 = calculate_bazi(b_year2, b_month2, b_day2, b_hour2, b_min2)
                    if bazi2:
                        prompt += f"\n對象資料：{name2}, {gender2}, {b_year2}/{b_month2}/{b_day2} {b_hour2}:{b_min2}, 關係:{relation_type}"

                try:
                    response = model.generate_content(prompt)
                    elapsed = time.time() - start_time
                    result_text = response.text
                    result_text = result_text.replace('恩，你好！', '').replace('恩，', '').replace('哈囉，', '').replace('你好，', '').replace('您好，', '').replace('首先，', '').replace('首先呢', '').replace('恩，好', '').strip()

                    result_title = f"📜 八字精論｜{'大師深度解析' if is_master else '溫馨命理建議'}"

                    st.markdown('<div class="result-card">', unsafe_allow_html=True)
                    st.markdown(f'<p class="result-header">{result_title}</p>', unsafe_allow_html=True)
                    
                    if tone_strategy['mode'] != "Neutral":
                        st.info(f"🔮 **大師私房建議 ({tone_strategy['mode']})**：\n\n{tone_strategy['action_advice']}")

                    bazi_table_html = render_bazi_table(bazi)
                    st.markdown(bazi_table_html, unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    st.markdown(result_text, unsafe_allow_html=True)
                    
                    if st.session_state.payment_status == "free":
                        st.markdown(f"""
                        <div class="locked-preview">
                            <div class="locked-preview-blur">
                                <h3>🔮 深度解析預覽：您的專屬行動建議</h3>
                                <p>根據您的日主 {bazi['day_tg']} 與流年感應，在接下來的三個月內，您最需要注意的一個關鍵轉折點在於...</p>
                                <p>針對您提問的「{question[:20]}...」，具體的破解步驟建議如下：第一步是調整您的... 第二步則是在關鍵時刻選擇...</p>
                            </div>
                            <div class="locked-overlay">
                                <div class="locked-text">
                                    🔓 解鎖完整深度報告與行動指引
                                </div>
                                <p style="margin-top:10px; color:#6C3483; font-size:0.9em; font-weight:600;">
                                    Hugo：這份報告將為你揭示隱藏的轉機。
                                </p>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                    st.markdown('</div>', unsafe_allow_html=True)
                    
                    # --- 付費解鎖架構 ---
                    st.markdown("---")
                    st.subheader("🚀 升級您的解析報告")
                    
                    col_plan1, col_plan2, col_plan3 = st.columns(3)
                    
                    with col_plan1:
                        st.markdown("""
                        <div class="plan-card">
                            <div class="plan-title">🥉 免費版</div>
                            <div class="plan-price">NT$ 0</div>
                            <ul class="plan-features">
                                <li>基礎命理分析</li>
                                <li class="locked">流年行動指引</li>
                                <li class="locked">感情/事業深度建議</li>
                                <li class="locked">PDF 完整報告</li>
                                <li class="locked">3 次提問權限</li>
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.session_state.payment_status == "free":
                            st.button("目前方案", disabled=True, key="btn_free")
                        else:
                            if st.button("切換回免費版", key="btn_switch_free"):
                                st.session_state.payment_status = "free"
                                st.rerun()
                                
                    with col_plan2:
                        st.markdown("""
                        <div class="plan-card popular">
                            <div class="popular-badge">MOST POPULAR</div>
                            <div class="plan-title">🥈 299 深度版</div>
                            <div class="plan-price">NT$ 299 <span>/ 案</span></div>
                            <ul class="plan-features">
                                <li>基礎命理分析</li>
                                <li><b>流年行動指引</b></li>
                                <li><b>感情/事業深度建議</b></li>
                                <li class="locked">PDF 完整報告</li>
                                <li class="locked">3 次提問權限</li>
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.session_state.payment_status == "paid_299":
                            st.button("✅ 已解鎖", disabled=True, key="btn_299_active")
                        elif st.session_state.payment_status == "paid_699":
                            st.info("✨ 已包含在完整版")
                        else:
                            if st.button("🔓 解鎖 299 深度版", key="btn_unlock_299"):
                                st.session_state.temp_pay_plan = "paid_299"
                                st.rerun()

                    with col_plan3:
                        st.markdown("""
                        <div class="plan-card">
                            <div class="plan-title">🥇 699 完整版</div>
                            <div class="plan-price">NT$ 699 <span>/ 案</span></div>
                            <ul class="plan-features">
                                <li>299 版所有內容</li>
                                <li><b>完整 PDF 深度報告</b></li>
                                <li><b>3 次追問權限 (Hugo 親回)</b></li>
                                <li>專屬開運建議</li>
                            </ul>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.session_state.payment_status == "paid_699":
                            st.button("✅ 已解鎖", disabled=True, key="btn_699_active")
                        else:
                            if st.button("🔓 解鎖 699 完整版", key="btn_unlock_699"):
                                st.session_state.temp_pay_plan = "paid_699"
                                st.rerun()

                    if 'temp_pay_plan' in st.session_state:
                        selected_plan_val = 299 if st.session_state.temp_pay_plan == "paid_299" else 699
                        st.subheader(f"📝 建立訂單（{selected_plan_val} 方案）")
                        o_name = st.text_input("姓名", value=name)
                        o_contact = st.text_input("LINE ID 或 Email")
                        o_phone = st.text_input("手機 (選填)")
                        
                        try:
                            default_date = datetime.date(int(b_year), int(b_month), int(b_day))
                        except:
                            default_date = datetime.date.today()
                            
                        o_birth_date = st.date_input("出生年月日", value=default_date)
                        o_birth_time = st.text_input("出生時間（例：08:20）", value=f"{b_hour}:{b_min}")
                        o_gender = st.selectbox("性別", options=["男", "女"], index=0 if gender == "男" else 1)
                        o_question = st.text_area("想諮詢的問題", value=question)
                        
                        if st.button("建立訂單"):
                            if not o_name or not o_contact:
                                st.error("請填寫姓名與聯絡資訊")
                            else:
                                order_id = f"HUGO_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
                                order_info = {
                                    'order_id': order_id,
                                    'created_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    'name': o_name,
                                    'contact': o_contact,
                                    'phone': o_phone,
                                    'birth_date': str(o_birth_date),
                                    'birth_time': o_birth_time,
                                    'gender': o_gender,
                                    'question': o_question,
                                    'plan': selected_plan_val,
                                    'payment_status': 'unpaid'
                                }
                                st.session_state.order_data = order_info
                                save_order_to_csv(order_info)
                                st.success("訂單已建立！請加入LINE完成付款與分析")
                                st.json(st.session_state.order_data)

                        if st.session_state.order_data:
                            st.info("💳 **目前為測試模式**")
                            col_pay1, col_pay2 = st.columns(2)
                            with col_pay1:
                                if st.button("✅ 確認付款完成並解鎖", type="primary"):
                                    st.session_state.order_data['payment_status'] = 'test_paid'
                                    save_order_to_csv(st.session_state.order_data)
                                    st.session_state.payment_status = st.session_state.temp_pay_plan
                                    del st.session_state.temp_pay_plan
                                    st.success(f"🎉 付款成功！訂單編號 {st.session_state.order_data['order_id']} 已解鎖。")
                                    st.rerun()
                            with col_pay2:
                                if st.button("❌ 取消"):
                                    del st.session_state.temp_pay_plan
                                    st.session_state.order_data = None
                                    st.rerun()

                    if st.session_state.payment_status in ["paid_299", "paid_699"]:
                        st.markdown("---")
                        st.markdown("## 🌟 進階解鎖內容")
                        if st.session_state.order_data:
                            st.caption(f"📄 訂單編號：{st.session_state.order_data['order_id']}")
                        
                        st.markdown("### 📍 流年行動指引 & 建議")
                        st.success(f"【{st.session_state.main_cat if 'main_cat' in st.session_state else '整體'}建議】根據您的命盤，今年應以『穩』為主，適合學習與內省，不宜大動作投資。")
                        
                        if st.session_state.payment_status == "paid_699":
                            st.markdown("### 📘 完整深度報告")
                            st.write("這裡顯示更完整的深度分析內容，包含大運流年的細部拆解與五行補運建議。")
                            try:
                                pdf_bytes = create_pdf(name, result_text)
                                st.download_button(
                                    label="📥 下載完整命理報告 (PDF)",
                                    data=pdf_bytes,
                                    file_name=f"雨果大師_{name}_命理報告.pdf",
                                    mime="application/pdf",
                                    use_container_width=True
                                )
                            except Exception as pdf_err:
                                st.error(f"PDF 產生失敗：{pdf_err}")
                        else:
                            if st.button("升級至 699 完整版"):
                                st.session_state.temp_pay_plan = "paid_699"
                                st.rerun()
                    else:
                        st.info("🔒 付費解鎖後即可查看進階行動指引與下載 PDF 報告")

                    st.caption(f"⏱️ 分析耗時：{elapsed:.1f} 秒")

                    if sheet is not None:
                        try:
                            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            birth_datetime_str = f"{b_year}-{b_month:02d}-{b_day:02d} {b_hour:02d}:{b_min:02d}"
                            if enable_dual:
                                occ_info = f"{occupation} (對象: {name2}/{relation_type})"
                                partner_dob_str = f"{b_year2}-{b_month2:02d}-{b_day2:02d}"
                            else:
                                occ_info = occupation
                                partner_dob_str = "無"
                            
                            safe_result_text = result_text[:30000] if result_text else ""
                            row_data = [now_str, name, birth_datetime_str, occ_info, partner_dob_str, gender, safe_result_text]
                            sheet.append_row(row_data)
                        except Exception as gs_err:
                            st.sidebar.warning(f"⚠️ 紀錄存檔失敗：{gs_err}")

                except Exception as e:
                    st.error(f"發生錯誤：{e}")

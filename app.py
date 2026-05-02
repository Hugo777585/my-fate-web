import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
import datetime
import time
import os
import gspread
import re
import json
import csv
import base64
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from lunar_python import Lunar, Solar
from tone_engine import analyze_tone_strategy
from fpdf import FPDF

load_dotenv()
openai_key = st.secrets.get("OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")

if not openai_key:
    st.error("尚未設定 OPENAI_API_KEY，請先到 Streamlit Cloud Secrets 加入金鑰。")
    st.stop()

client = OpenAI(api_key=openai_key)

# --- 護眼淺灰色：Hugo 大師版背景 --- 
st.markdown(""" 
<style> 
    /* 整體底層改為溫和淺灰，降低亮度不刺眼 */ 
    .stApp { 
        background-color: #e6e9ef; 
        color: #2d3436; 
    } 
    
    /* 側邊欄維持白色或極淺灰，增加層次感 */ 
    [data-testid="stSidebar"] { 
        background-color: #f8f9fa; 
        border-right: 1px solid #dcdde1; 
    } 

    /* 調整內容區塊的間距 */ 
    .block-container { 
        padding-top: 2rem; 
        padding-bottom: 2rem; 
    } 

    /* 讓輸入區塊與卡片有淡淡的陰影，看起來更立體 */ 
    div[data-testid="stVerticalBlock"] > div { 
        background-color: white; 
        padding: 10px; 
        border-radius: 10px; 
        box-shadow: 0 2px 5px rgba(0,0,0,0.05); 
        margin-bottom: 5px; 
    } 

    div[data-testid="stMarkdownContainer"], 
    div[data-testid="stTable"], 
    div.element-container { 
        background-color: #ffffff; border-radius: 16px; padding: 15px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.05); margin-bottom: 15px; 
    } 
    h1, h2, h3 { color: #2d3436 !important; border-left: 6px solid #6c5ce7; padding-left: 15px; } 
    table { border-collapse: collapse; width: 100%; } 
    th { background-color: #f0f4ff !important; color: #6c5ce7 !important; font-weight: 900 !important; font-size: 18px !important; } 
    td { font-size: 16px !important; text-align: center !important; } 
</style> 
""", unsafe_allow_html=True)

def ai_reply(prompt):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return response.output[0].content[0].text

def ai_love_consult_reply(context_prompt, is_master=False):
    """
    第二層 AI 感情心理諮詢回覆函數 (優化轉單版)
    """
    system_role = """你是一位結合命理分析、感情心理諮詢與關係策略的顧問。請用沉穩、理性、具同理心的方式分析，像是在理解人、有洞察力。不要鐵口直斷，不要恐嚇使用者。"""
    
    # 根據權限調整輸出要求
    if is_master:
        permission_instruction = """
【大師模式：完整分析】
請提供完整深度分析，不限制字數，包含：
1. 對方目前真實心理狀態
2. 目前關係的核心卡點
3. 使用者內心真正不安的核心
4. 具體建議採取的做法（實戰策略）
5. 絕對不建議做的事
6. 潛在風險提醒
7. 明確的下一步行動建議
"""
    else:
        permission_instruction = """
【一般模式：初步引導】
請嚴格遵守以下三段式結構，字數約 300～500 字：
1. ① 對方心理：描述對方的心理狀態，要準確且有畫面感。
2. ② 關係卡點：點出關係中讓使用者產生共鳴的阻礙。
3. ③ 方向指引：給予一點點處理方向，但務必保留「關鍵沒說破」，創造好奇感。

❌ 禁止出現「購買」、「方案」、「價格」等商業字眼。
"""

    full_prompt = f"{system_role}\n\n{context_prompt}\n{permission_instruction}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": full_prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 諮詢暫時無法連線：{str(e)}"

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
    # 在側邊欄顯示您的 logo.JPG 
    st.sidebar.image("logo.JPG", use_column_width=True)
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

# --- 基礎 UI 隱藏樣式 ---
st.markdown("""
<style>
    /* 隱藏 Streamlit 預設元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    [data-testid="stHeader"] {display: none;}
</style>
""", unsafe_allow_html=True)

# --- 0. 頂部動態橫幅與音樂 ---
# 1. 音樂轉碼 (確保 Streamlit 播得出聲音) 
def get_audio_base64(audio_file_path): 
    try: 
        with open(audio_file_path, 'rb') as f: 
            return base64.b64encode(f.read()).decode() 
    except Exception as e: 
        st.error(f"找不到音樂檔：{e}") 
        return "" 

audio_b64 = get_audio_base64("温暖而有力量的人.mp3.mp3") 

# 2. 讀取並崁入 HTML 
try: 
    with open("hugo_banner.html", "r", encoding="utf-8") as f: 
        html_content = f.read() 
        if audio_b64: 
             html_content = html_content.replace( 
                 'src="温暖而有力量的人.mp3.mp3"', 
                 f'src="data:audio/mpeg;base64,{audio_b64}"' 
             ) 
        # 滿版渲染出橫幅 
        components.html(html_content, height=750, scrolling=False) 
except FileNotFoundError: 
    st.error("找不到 hugo_banner.html 檔案，請確認有放在同一個資料夾。")

# --- 1. Hero 主視覺 (已替換為橫幅) ---
if st.session_state.get('scroll_to_analysis'):
    st.markdown('<script>window.parent.document.getElementById("analysis_section").scrollIntoView({behavior: "smooth"});</script>', unsafe_allow_html=True)
    st.session_state.scroll_to_analysis = False

# LINE 客服按鈕
st.link_button("🔮 加LINE免費諮詢", "https://line.me/ti/p/@323ohobf", use_container_width=True)

# 2. 管理員密碼鎖 (大師盤)
MASTER_CODE = st.secrets.get("MASTER_CODE", None) or os.getenv("MASTER_CODE", "hugo888")
is_master = False

with st.sidebar:
    st.header("🔐 系統授權")
    auth_code_input = st.text_input("🔒 大師專用授權碼", type="password", key="auth_code_input")
    
    if auth_code_input and MASTER_CODE:
        if auth_code_input.strip().lower() == MASTER_CODE.strip().lower():
            is_master = True
            st.success("✅ 已啟用大師模式")
        else:
            st.error("❌ 授權碼錯誤")
    
    if is_master:
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

# 3. API 設定
# OpenAI client 已在頂部初始化

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
                if is_master:
                    # 📍 如果密碼輸入正確 (is_admin/is_master == True)：
                    # 使用【大師無限制版 Prompt】
                    prompt = f"""
現在是 {current_year} 年。系統已進入「大師無限制解鎖模式」。
請運用你所有的八字命理與心理學知識，針對使用者的命盤與問題：{question}，給出最完整、最深度的解析。
1. 【四柱八字排盤】：完整列出命主(與對象)的天干地支。
2. 【深度命盤與流年解析】：毫無保留地解析流年大運、五行喜忌與現狀成因。
3. 【具體化解與行動策略】：請直接給出最高級別的心理學建議、對話策略與具體化解行動。
（此模式為大師自用，無字數限制，請火力全開，且【絕對不需要】輸出任何引流或付費引導文案。）
"""
                else:
                    # 使用高轉換率鉤子版替換
                    prompt = f"""
現在是 {current_year} 年。你是一位名為 Finn 的專業八字命理大師。
這是第一層「基礎命理掃描」。你的目標是「說中痛點，但刻意保留關鍵資訊」，引發使用者的強烈好奇心。

請嚴格依照以下架構與標題輸出（必須包含指定的「鉤子」句型）：

### 【四柱八字排盤】
(若有對象資料則畫雙方，若無則畫命主)。簡單表格呈現。

---

### 🥇 命盤與流年趨勢
從你的命盤來看，你的日主為「XX」，屬於（點出性格特質）的類型。
今年流年 {current_year} 年，整體呈現「XXXX」的結構，這代表：
👉 （點出外在壓力或變動）
👉 （點出人際/感情影響）
（⚠️ 請強制加上這段鉤子）：
這不是單純運氣不好，而是「命盤本身的結構被引動」。但關鍵在於——不是每個月都一樣嚴重。有些月份只是壓力，但有幾個特定月份是「真正會出事的點」。

### 🥈 現況解析與深層原因
(結合客戶提問：{question} 進行共鳴)
這也對應到你目前的狀況：
👉 （點出現狀痛點 1）
👉 （點出現狀痛點 2）
（⚠️ 請強制加上這段鉤子）：
但實際上，問題並不是你做錯。這背後其實有更深一層的原因，跟你本命盤的某個隱藏特質有關。但這個我在免費版不會講太細，因為這會直接影響你接下來的決策。

### 💥 【關鍵：卡點與決策】
如果這種狀況沒有調整，很容易陷入惡性循環。
目前這份分析，只幫你看清楚「為什麼會發生」，還沒有告訴你：
❃ 哪幾個月份是「真正需要防的」？
❃ 對方真實的心態到底是什麼？
❃ 妳現在該進、退、還是觀察？

⚠️ 很多人都是在事情發生之後才來問，但那時候，已經來不及調整了。

👉 如果妳看到這裡，已經有 3 個以上對應到，那我會很直接跟妳說——
👉 現在這個狀態，不處理一定會出事。
而免費這邊，我不會講到「怎麼避開」與「決策層」。
"""
                
                # 附加原始資料與盤位資訊供 AI 參考，但不強制 AI 輸出格式（由上面的架構要求決定）
                prompt += f"\n\n【參考資料】\n命主資料：{name}, {gender}, {b_year}/{b_month}/{b_day} {b_hour}:{b_min}, 職業:{occupation}\n提問：{question}\n詳細卡關：{user_detailed_question}\n{pillar_info}"
                
                if enable_dual:
                    bazi2 = calculate_bazi(b_year2, b_month2, b_day2, b_hour2, b_min2)
                    if bazi2:
                        prompt += f"\n對象資料：{name2}, {gender2}, {b_year2}/{b_month2}/{b_day2} {b_hour2}:{b_min2}, 關係:{relation_type}"

                try:
                    result_text = ai_reply(prompt)
                    elapsed = time.time() - start_time
                    result_text = result_text.replace('恩，你好！', '').replace('恩，', '').replace('哈囉，', '').replace('你好，', '').replace('您好，', '').replace('首先，', '').replace('首先呢', '').replace('恩，好', '').strip()

                    result_title = f"📜 八字精論｜{'大師深度解析' if is_master else '溫馨命理建議'}"

                    st.markdown('<div class="result-card">', unsafe_allow_html=True)
                    st.markdown(f'<p class="result-header">{result_title}</p>', unsafe_allow_html=True)
                    
                    if tone_strategy['mode'] != "Neutral":
                        st.info(f"🔮 **大師私房建議 ({tone_strategy['mode']})**：\n\n{tone_strategy['action_advice']}")

                    bazi_table_html = render_bazi_table(bazi)
                    st.markdown(bazi_table_html, unsafe_allow_html=True)
                    st.markdown("<br>", unsafe_allow_html=True)
                    
                    if is_master:
                        st.write("🔥 大師完整版分析啟動")
                        st.markdown(result_text, unsafe_allow_html=True)
                    else:
                        st.write("👉 以上為您的初步命理分析報告")
                        # 基礎分析可能只顯示前段或特定內容，這裡先保留原本顯示 result_text 的邏輯
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
                    
                    # LINE 完整分析按鈕
                    st.link_button("👉 加LINE看完整分析", "https://line.me/ti/p/@323ohobf", use_container_width=True)
                    
                    # --- 第二層｜AI感情心理諮詢師 (高轉換引導版) ---
                    st.markdown("---")
                    st.markdown("""
                    ### � 延伸分析｜感情心理解析 
                    
                    很多時候，真正讓人放不下的， 
                    不是發生了什麼， 
                    而是你始終看不懂「對方現在到底在想什麼」。 
                    
                    你可能會開始反覆想： 
                    👉 他現在對我是認認真真的，還是只是剛好有人陪？ 
                    👉 這段關係，還有沒有機會走下去？ 
                    👉 我現在該主動，還是該慢慢退？ 
                    
                    有些答案，其實你心裡已經隱約知道， 
                    只是還沒有被看清楚。 
                    
                    **HUGO 天命智庫會透過：**
                    **八字命盤 × 關係互動 × 心理狀態** 
                    
                    幫你把「現在這段關係的真實狀態」拆開來看。 
                    
                    學理上不是告訴你一個結果， 
                    而是讓你知道： 
                    
                    👉 **對方現在的情緒位置** 
                    👉 **你們之間的關係落差** 
                    👉 **以及你下一步做什麼，結果會開始改變** 
                    
                    💗 **如果你準備好看清楚這段關係** 
                    
                    👉 **請點擊下方，進入 AI 感情心理解析** 
                    """)
                    
                    if st.button("🚀 進入 AI 感情心理解析", use_container_width=True, type="primary"):
                        st.switch_page("pages/02_love_analysis.py")
                    
                    # 移除舊有的付費解鎖架構 (已隱藏)
                    if is_master:
                        st.markdown("---")
                        st.subheader("� 大師後台管理")
                        # 這裡可以保留一些大師才看的到的數據或功能

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

import streamlit as st
import google.generativeai as genai
import datetime
import time
import os
import gspread
import re
import json
from google.oauth2.service_account import Credentials
from lunar_python import Lunar, Solar
from tone_engine import analyze_tone_strategy

# --- Google Sheets 連線設定 ---
def init_gsheets():
    client_email = "未知"
    service_account_info = None
    
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
                # 注意：Streamlit Secrets 本身就是 Dict，不需 json.load
                service_account_info = st.secrets["gcp_service_account"]
            else:
                return None, client_email, "🚫 找不到連線憑證：本地無 hugo-key.json，且雲端 Secrets 未設定 [gcp_service_account]。"
            
        client_email = service_account_info.get("client_email", "未知")
        
        # 3. 驗證金鑰內容是否完整
        required_fields = ["project_id", "private_key", "client_email"]
        if not all(field in service_account_info for field in required_fields):
            return None, client_email, "🔑 鑰匙格式錯誤：JSON 內容遺漏必要欄位 (project_id, private_key 或 client_email)。"

        # 建立憑證
        creds = Credentials.from_service_account_info(service_account_info, scopes=scopes)
        
        # 授權並開啟試算表
        client = gspread.authorize(creds)
        
        # 4. 開啟試算表
        sheet_url = st.secrets.get("gsheets_url")
        sheet_name = "雨果天命智庫客戶紀錄"
        
        try:
            if sheet_url:
                spreadsheet = client.open_by_url(sheet_url)
            else:
                spreadsheet = client.open(sheet_name)
            
            sheet = spreadsheet.sheet1
            return sheet, client_email, None
        except gspread.exceptions.SpreadsheetNotFound:
            return None, client_email, f"📂 試算表權限沒開：找不到名為 '{sheet_name}' 的檔案，請確認名稱正確。"
        except gspread.exceptions.APIError as e:
            if "Permission denied" in str(e):
                return None, client_email, "📂 試算表權限沒開：請確保已將試算表「共用」給下方的服務帳號 Email。"
            return None, client_email, f"⚠️ Google API 錯誤：{str(e)}"
            
    except Exception as e:
        return None, client_email, f"🚨 連線系統錯誤：{str(e)}"

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
    
    html = f"""
    <div style="overflow-x: auto;">
        <table border="1" style="border-collapse: collapse; width: 100%; font-size: 22px; font-weight: bold; text-align: center; border: 2px solid #6C3483;">
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
    #MainMenu {display: none !important;}
    footer {display: none !important;}
    header {display: none !important;}
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
</style>
""", unsafe_allow_html=True)

# 1. Logo 置頂
st.markdown('<p class="main-title">🔮 雨果大師</p>', unsafe_allow_html=True)
col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
with col_logo2:
    logo_path = "logo.JPG" if os.path.exists("logo.JPG") else "logo.jpg"
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
st.markdown('<p class="sub-title">古典命理與 AI 的深度對話｜專業八字・紫微斗數・人生指引</p>', unsafe_allow_html=True)

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

【高危險感情模式：紅色警戒】
當分析命盤時，若偵測到以下結構，請強制啟動【紅色警戒模式】：

🔴 警戒點一：【破壞性掠奪與雙面人設】
- 觸發：命局中「劫財」過旺（高於兩個以上），且日支（夫妻宮）遭遇嚴重的「地支相沖」（如寅申沖、子午沖、卯酉沖、辰戌沖）。
- 警告語：⚠️ 【系統警告：高度感情耗損風險】 注意！此盤主的感情防線極度不穩定。在實際相處中，極容易出現「多線發展」、「滿口謊言」或「利益掠奪」的行為。對方可能會將「分手」當作操控籌碼，並在斷聯後用小恩小惠或未來的承諾進行情緒勒索。請「聽其言，更要觀其行」，必須嚴格設定停損點！

🔴 警戒點二：【缺乏界線與情緒反咬】
- 觸發：1. 八字日主極弱且官殺極度壓迫。2. 紫微命宮逢地空地劫，且夫妻宮見巨門化權或化忌。
- 警告語：⚠️ 【系統警告：吸血型依附與惡意重構風險】 注意！此盤主極度缺乏安全感與人際界線。這是一段單向消耗的關係。當對方無法處理自身情緒，會啟動防禦機制，用言語踐踏您的付出（例如：嗆你沒資格、拿前任來貶低你）。請停止「過度承擔」，不要試圖拯救對方！

🔴 警戒點三：【宿命吸引：拯救者陷阱】
- 觸發：雙人合盤時，若一方帶有強烈「庇護/照顧」特質（如丙火、印旺），另一方符合上述警戒點。
- 警告語：🚨 【系統最高警告：拯救者消耗迴圈】 您的命格自帶強大溫暖，極易吸引到情緒黑洞對象。這不是正緣，是能量考驗！您無法用善意填平對方的業力。請立刻收回您的「庇護能量」，將重心放回自己身上。請果斷物理切割！

【輸出要求】
1. 只能輸出 Markdown 格式，禁止任何無意義的開場白（如：你好、恩等）。
"""

try:
    # 優先從 st.secrets 讀取，若失敗則嘗試從本地環境變數或檔案讀取 (雖然主要在雲端運行)
    gemini_key = st.secrets.get("GEMINI_API_KEY")
    
    if not gemini_key:
        # 嘗試從已讀取的 service_account_info 中抓取 (如果有的話)
        # 或者從其它檔案讀取，但通常 GEMINI_API_KEY 應該獨立於 GCP 帳號
        st.error("API 金鑰讀取失敗：請在 Streamlit Secrets 中設定 `GEMINI_API_KEY`。")
        st.stop()
        
    genai.configure(api_key=gemini_key)
    model = genai.GenerativeModel(
        "gemini-1.5-flash", # 精準指定 1.5-flash 模型
        system_instruction=SYSTEM_INSTRUCTION
    )
except Exception as e:
    st.error(f"API 設定發生錯誤：{e}")
    st.stop()

# 4. 功能模式選擇
st.markdown("### 🎯 選擇分析模式")
analysis_mode = st.radio(
    "請選擇命理分析模式",
    ["【八字精論】", "【紫微斗數分析】", "【八紫交叉比對】"],
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
    col4, col5, col6, col7, col8 = st.columns(5)
    with col4:
        b_year = st.number_input("年", min_value=1900, max_value=2030, value=1980)
    with col5:
        b_month = st.number_input("月", min_value=1, max_value=12, value=1)
    with col6:
        b_day = st.number_input("日", min_value=1, max_value=31, value=1)
    with col7:
        b_hour = st.number_input("時", min_value=0, max_value=23, value=12)
    with col8:
        b_min = st.number_input("分", min_value=0, max_value=59, value=0)

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

    form_container = st.container()
    
    with form_container:
        st.markdown('<div class="st-step-container">', unsafe_allow_html=True)
        
        # 步驟一：大分類選擇
        if st.session_state.form_step == 1:
            st.write("✨ **第一步：您想諮詢哪方面的問題？**")
            col_cat1, col_cat2 = st.columns(2)
            with col_cat1:
                if st.button("💘 感情婚姻", use_container_width=True):
                    st.session_state.main_cat = "感情"
                    st.session_state.form_step = 2
                    st.rerun()
            with col_cat2:
                if st.button("💼 事業財運", use_container_width=True):
                    st.session_state.main_cat = "事業"
                    st.session_state.form_step = 2
                    st.rerun()
        
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
                if st.button("✅ 確認輸入", use_container_width=True):
                    # 確認後留在這一步，但顯示已確認
                    st.success("資料已暫存，請點擊下方「大師發功」按鈕開始分析。")
        
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
enable_dual = st.checkbox("💞 啟用雙人合盤 (感情/合夥)")
if enable_dual:
    st.subheader("💞 第二位對象資料")
    col_p2_1, col_p2_2, col_p2_3, col_p2_4, col_p2_5, col_p2_6 = st.columns([1, 1, 1, 1, 1, 1])
    with col_p2_1:
        gender2 = st.selectbox("對象性別", ["男", "女"], key="gender2")
    with col_p2_2:
        b_year2 = st.number_input("年", min_value=1900, max_value=2030, value=1980, key="b_year2")
    with col_p2_3:
        b_month2 = st.number_input("月", min_value=1, max_value=12, value=1, key="b_month2")
    with col_p2_4:
        b_day2 = st.number_input("日", min_value=1, max_value=31, value=1, key="b_day2")
    with col_p2_5:
        b_hour2 = st.number_input("時", min_value=0, max_value=23, value=12, key="b_hour2")
    with col_p2_6:
        b_min2 = st.number_input("分", min_value=0, max_value=59, value=0, key="b_min2")
    relation_type = st.selectbox("雙方關係", ["情侶/夫妻", "事業合夥", "家人/朋友"])

st.markdown("---")

# 7. 試算按鈕與 Prompt 邏輯
col_btn_left, col_btn_right, col_btn_end = st.columns([1, 2, 1])
with col_btn_right:
    btn_label = "✨ 大師深度發功" if is_master else "✨ 開始溫馨試算"
    if st.button(btn_label, use_container_width=True):
        if not question:
            st.warning("請簡單填寫一下您想問的問題，大師才能為您指點迷津喔！")
        else:
            start_time = time.time()
            with st.spinner("大師正在排盤與分析中，請稍候..."):
                bazi = calculate_bazi(b_year, b_month, b_day, b_hour, b_min)
                
                # --- 動態語氣分析 ---
                bazi_shishen = []
                if bazi:
                    # 收集八字中的十神，用於語氣引擎判斷
                    bazi_shishen = [bazi['year_ss'], bazi['month_ss'], bazi['hour_ss']]
                
                tone_strategy = analyze_tone_strategy(question, bazi_shishen)
                tone_instruction = f"\n\n【當前對話語氣指引】：\n{tone_strategy['system_prompt']}\n請確保在回覆中完美融入此語氣。"

                # 準備精確的四柱數據字串，供 Prompt 使用
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

                base_info = f"姓名：{name}，性別：{gender}，生日：{b_year}/{b_month}/{b_day} {b_hour}:{b_min}，職業：{occupation}，提問：{question}"

                if is_master:
                    if analysis_mode == "【八字精論】":
                        prompt = f"""請以此經由萬年曆精算出的正確命盤為【絕對依據】，進行『70/30 命運法則』深度分析：
{pillar_info}

客人資料：{base_info}
加強維度：{', '.join(advanced_params.get('focus', []))}
學理偏好：{advanced_params.get('theory', '標準')}

【輸出架構要求】：
1. 『 【70% 命運趨勢】 』：嚴格依據《三命通會》、《滴天髓》等古籍，分析先天格局、五行喜忌與當前流年走勢。
2. 『 【30% 自由意志】 』：針對客人的職業【{occupation}】與提問，提供後天可優化的具體建議與行動。
3. 『 【大師賦權結語】 』：強調 30% 的主動權，給予溫暖且有力量的總結。
4. 禁止輸出重複的排盤表格。
{tone_instruction}
"""
                    elif analysis_mode == "【紫微斗數分析】":
                        prompt = f"""請輔助參考八字命盤進行『70/30 命運法則』之紫微斗數分析：
{pillar_info}

客人資料：{base_info}
加強維度：{', '.join(advanced_params.get('focus', []))}
學理偏好：{advanced_params.get('theory', '標準')}

【輸出架構要求】：
1. 『 【70% 紫微趨勢】 』：分析命宮主星、四化飛星等先天配置。
2. 『 【30% 自由意志】 』：後天心態調整與行動指引。
3. 『 【大師賦權結語】 』：賦予希望與行動力的總結。
{tone_instruction}
"""
                    else:
                        prompt = f"""請進行『70/30 命運法則』之八紫交叉比對分析：
{pillar_info}

客人資料：{base_info}
加強維度：{', '.join(advanced_params.get('focus', []))}
學理偏好：{advanced_params.get('theory', '標準')}

【輸出架構要求】：
1. 『 【70% 交叉趨勢結論】 』：綜合分析八字喜忌與紫微流年。
2. 『 【30% 自由意志】 』：跨學理的具體改善方案。
3. 『 【大師賦權結語】 』：充滿力量的人生指引。
{tone_instruction}
"""
                else:
                    if analysis_mode == "【八字精論】":
                        prompt = f"""請根據『70/30 命運法則』對以下命盤進行親切解析：
{pillar_info}
客人資料：{base_info}
請劃分『 【70% 命運趨勢】 』、『 【30% 自由意志】 』與『 【溫馨賦權結語】 』。
{tone_instruction}"""
                    elif analysis_mode == "【紫微斗數分析】":
                        prompt = f"""請根據『70/30 命運法則』進行紫微斗數分析：
{pillar_info}
客人資料：{base_info}
請劃分『 【70% 紫微趨勢】 』、『 【30% 自由意志】 』與『 【溫馨賦權結語】 』。
{tone_instruction}"""
                    else:
                        prompt = f"""請根據『70/30 命運法則』進行八紫交叉比對分析：
{pillar_info}
客人資料：{base_info}
請劃分『 【70% 綜合趨勢】 』、『 【30% 自由意志】 』與『 【溫馨賦權結語】 』。
{tone_instruction}"""

                if enable_dual:
                    bazi2 = calculate_bazi(b_year2, b_month2, b_day2, b_hour2, b_min2)
                    if bazi2:
                        prompt += f"\n\n雙人合盤：對象八字【{bazi2['full']['year']} {bazi2['full']['month']} {bazi2['full']['day']} {bazi2['full']['hour']}】，關係：{relation_type}"
                    else:
                        prompt += f"\n\n雙人合盤：對象生日：{b_year2}/{b_month2}/{b_day2} {b_hour2}:{b_min2}，關係：{relation_type}"

                try:
                    response = model.generate_content(prompt)
                    elapsed = time.time() - start_time
                    result_text = response.text
                    result_text = result_text.replace('恩，你好！', '').replace('恩，', '').replace('哈囉，', '').replace('你好，', '').replace('您好，', '').replace('首先，', '').replace('首先呢', '').replace('恩，好', '').strip()

                    mode_display = {
                        "【八字精論】": "八字精論",
                        "【紫微斗數分析】": "紫微斗數分析",
                        "【八紫交叉比對】": "八紫交叉比對"
                    }
                    result_title = f"📜 {mode_display[analysis_mode]}｜{'大師深度解析' if is_master else '溫馨命理建議'}"

                    st.markdown('<div class="result-card">', unsafe_allow_html=True)
                    st.markdown(f'<p class="result-header">{result_title}</p>', unsafe_allow_html=True)
                    
                    # --- 顯示大師私房建議 (僅在觸發特定語氣模式時) ---
                    if tone_strategy['mode'] != "Neutral":
                        st.info(f"🔮 **大師私房建議 ({tone_strategy['mode']})**：\n\n{tone_strategy['action_advice']}")

                    # 在八字模式下，先顯示 Python 產生的彩色表格
                    if "八字" in analysis_mode or analysis_mode == "【八紫交叉比對】":
                        bazi_table_html = render_bazi_table(bazi)
                        st.markdown(bazi_table_html, unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                    
                    st.markdown(result_text, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.caption(f"⏱️ 分析耗時：{elapsed:.1f} 秒")

                    # --- 8. 進階服務區塊 (Call to Action) ---
                    st.markdown("""
                    <div class="cta-container">
                        <p class="cta-title">🚀 想要更深層的改運指引嗎？</p>
                        <p class="cta-text">免費建議只是開始，精準的行動指南能幫助您避開流月波折，或由大師親自為您撥雲見日。</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    col_cta1, col_cta2 = st.columns(2)
                    with col_cta1:
                        if st.button("🔓 解鎖進階流月行動指南 (付費)", use_container_width=True):
                            st.toast("🔮 正在串接金流系統，即將開放...")
                    with col_cta2:
                        if st.button("💬 預約真人深度諮詢", use_container_width=True):
                            st.toast("📅 正在跳轉預約系統...")
                            st.info("💡 提示：真人諮詢目前採預約制，請洽客服人員。")

                    # --- 寫入 Google Sheets 邏輯 ---
                    if sheet is not None:
                        try:
                            # 準備要寫入的一列資料
                            # 欄位：日期時間, 西元生年, 月, 日, 時, 分, 性別, 職業, 模式, 正確日主, AI回覆
                            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            day_master = bazi['day_tg'] if bazi else "未知"
                            
                            row_data = [
                                now_str, 
                                str(b_year), 
                                str(b_month), 
                                str(b_day), 
                                str(b_hour), 
                                str(b_min), 
                                gender, 
                                occupation, 
                                analysis_mode, 
                                day_master, 
                                result_text[:5000]
                            ]
                            sheet.append_row(row_data)
                        except Exception as gs_err:
                            st.error(f"❌ 試算表寫入失敗：{gs_err}。請確認試算表權限是否已開放給服務帳號。")
                    else:
                        st.warning("⚠️ 試算表目前未連線，資料將不會被記錄。")

                except Exception as e:
                    st.error(f"發生錯誤：{e}")

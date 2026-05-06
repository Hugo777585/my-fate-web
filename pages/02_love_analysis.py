import streamlit as st
from openai import OpenAI
import datetime
import os
import json
import pandas as pd
from dotenv import load_dotenv
import uuid
from data_logger import log_site_visit, append_user_submission

load_dotenv()
# --- 初始化 Session State (如果直接從此頁進入) ---
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'visited_pages' not in st.session_state:
    st.session_state.visited_pages = set()

# 紀錄瀏覽
log_site_visit("psychology")
openai_key = st.secrets.get("OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")

if not openai_key:
    st.error("尚未設定 OPENAI_API_KEY，請先到 Streamlit Cloud Secrets 加入金鑰。")
    st.stop()

client = OpenAI(api_key=openai_key)

st.set_page_config(
    page_title="兩性情感心理諮詢｜雨果天命智庫",
    page_icon="🧠",
    layout="wide"
)

# --- CSS 注入：打造「命理 × 心理 × 關係策略分析室」風格 ---
st.markdown(""" 
<style> 
    /* 全局背景：暖米白 */ 
    .stApp { 
        background-color: #F8F6F0; 
        color: #3E3A39; 
        font-family: 'Noto Serif TC', serif;
    } 
    
    /* 隱藏預設元素 */
    #MainMenu, header, footer { visibility: hidden; display: none !important; }
    
    /* 內容區塊寬度 */
    .block-container { 
        max-width: 1000px;
        padding-top: 1rem;
    } 

    /* 高級白色卡片樣式 */ 
    .premium-card { 
        background-color: #FFFFFF; 
        padding: 30px; 
        border-radius: 20px; 
        box-shadow: 0 10px 30px rgba(0,0,0,0.05); 
        margin-bottom: 25px;
        border: 1px solid #E2E2CC;
    } 
    
    .card-title {
        font-size: 22px;
        font-weight: 800;
        color: #9A7A38;
        margin-bottom: 20px;
        border-bottom: 2px solid #F8F6F0;
        padding-bottom: 10px;
    }

    /* 功能特色小卡片 (暖米色) */
    .feature-card {
        background-color: #E2E2CC;
        padding: 20px;
        border-radius: 14px;
        height: 180px;
        text-align: center;
        border: 1px solid #D1D1B8;
        transition: all 0.3s ease;
        display: flex;
        flex-direction: column;
        justify-content: center;
        margin-bottom: 15px;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.12);
        background-color: #ECECD8;
    }
    .feature-card h4 {
        color: #9A7A38;
        margin-bottom: 10px;
        font-weight: 800;
    }
    .feature-card p {
        font-size: 0.95em;
        line-height: 1.5;
        color: #3E3A39;
    }

    /* 標題樣式 */
    h1, h2, h3 { 
        color: #3E3A39 !important; 
        font-family: 'Noto Serif TC', serif;
    }

    /* CTA 按鈕美化 */
    .stButton>button {
        height: 58px !important;
        border-radius: 16px !important;
        font-weight: 800 !important;
        font-size: 1.1em !important;
        background: linear-gradient(135deg, #9A7A38, #B38E45) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 6px 15px rgba(154, 122, 56, 0.3) !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }
    .stButton>button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 10px 25px rgba(154, 122, 56, 0.4) !important;
        background: linear-gradient(135deg, #B38E45, #9A7A38) !important;
    }

    /* 定價方案卡片 */
    .pricing-card {
        background-color: #FFFFFF;
        padding: 25px;
        border-radius: 20px;
        border: 1px solid #E2E2CC;
        text-align: center;
        margin-bottom: 20px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.02);
    }
    .pricing-price {
        font-size: 2em;
        font-weight: 900;
        color: #9A7A38;
        margin: 10px 0;
    }
    
    /* 診斷表樣式 */
    .diagnostic-table {
        width: 100%;
        border-collapse: collapse;
        background-color: #FFFFFF;
        border-radius: 12px;
        overflow: hidden;
    }
    .diagnostic-table th {
        background-color: #E2E2CC;
        padding: 12px;
        text-align: left;
        color: #3E3A39;
    }
    .diagnostic-table td {
        padding: 12px;
        border-bottom: 1px solid #F8F6F0;
        color: #3E3A39;
    }
    
    /* Logo 樣式 */
    .logo-container {
        text-align: center;
        margin-bottom: 20px;
    }
    .logo-img {
        max-width: 200px;
    }
    .subtitle {
        font-size: 1.2em;
        color: #9A7A38;
        font-style: italic;
        margin-top: 10px;
        font-family: 'Noto Serif TC', serif;
    }
</style> 
""", unsafe_allow_html=True)

# --- 一、頁頭品牌形象 ---
import base64
logo_html = ""
if os.path.exists("logo.JPG"):
    with open("logo.JPG", "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()
    logo_html = f'<div class="logo-container"><img src="data:image/jpeg;base64,{logo_base64}" class="logo-img"><div class="subtitle">跨越時空的共振，為您指點情感的迷津。</div></div>'
else:
    logo_html = '<div class="logo-container"><h1 style="color:#9A7A38; margin:0;">HUGO 天命智庫</h1><div class="subtitle">跨越時空的共振，為您指點情感的迷津。</div></div>'

st.markdown(logo_html, unsafe_allow_html=True)

st.markdown("""
<div style="text-align: center; margin-bottom: 40px;">
    <h1 style="font-size: 36px; font-weight: 900; border: none; padding: 0;">兩性情感心理諮詢</h1>
    <p style="font-size: 17px; color: #555; max-width: 800px; margin: 20px auto; line-height: 1.7;">
        當對方忽冷忽熱、訊息變少、態度模糊，很多人會開始懷疑自己是不是做錯了什麼。但感情問題往往不是單一事件，而是由依附模式、溝通方式、情緒反應與雙方關係結構共同形成。
    </p>
</div>
""", unsafe_allow_html=True)

# --- 二、核心功能區 (4張卡片) ---
col_c1, col_c2 = st.columns(2)
with col_c1:
    st.markdown("""
    <div class="feature-card">
        <h4>1. 對方心態分析</h4>
        <p>分析對方目前是靠近、觀望、逃避、冷淡，還是正在測試你的反應。</p>
    </div>
    <div class="feature-card">
        <h4>2. 關係卡點判讀</h4>
        <p>找出你們反覆爭吵、冷戰、誤會或拉扯的真正原因。</p>
    </div>
    """, unsafe_allow_html=True)
with col_c2:
    st.markdown("""
    <div class="feature-card">
        <h4>3. 溝通策略建議</h4>
        <p>依照目前局勢，提供適合主動、冷處理、收線、觀察或重新開啟對話的方式。</p>
    </div>
    <div class="feature-card">
        <h4>4. 命盤與心理交叉分析</h4>
        <p>結合雙方命盤與互動模式，判斷感情吸引力、衝突點與長期穩定度。</p>
    </div>
    """, unsafe_allow_html=True)

# --- 主 CTA 按鍵 1 ---
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🚀 開始感情心理分析"):
    st.info("正在引導至分析區...")
st.markdown("<br>", unsafe_allow_html=True)

# --- 三、關係狀態診斷表 ---
st.markdown("## 🔍 關係狀態診斷表")
diagnostic_data = {
    "分析項目": ["回訊頻率", "主動程度", "情緒反應", "身體距離", "承諾態度"],
    "觀察重點": ["變慢、變短、已讀不回", "是否主動找你、約你、關心你", "容易生氣、逃避、冷處理", "是否願意見面、靠近、互動", "是否願意討論未來"],
    "可能意義": ["關係熱度下降或對方正在退縮", "判斷投入程度", "可能存在防衛或壓力", "判斷真實吸引力", "判斷關係穩定度"]
}
st.table(pd.DataFrame(diagnostic_data))

# --- 五、表單輸入區 (心靈卡片排版) ---
st.markdown("---")

col_main1, col_main2 = st.columns(2)

with col_main1:
    st.markdown('<div class="premium-card"><div class="card-title">👤 您的本命資料</div>', unsafe_allow_html=True)
    user_name = st.text_input("您的姓名/暱稱", placeholder="如何稱呼您？")
    user_gender = st.selectbox("您的性別", ["男", "女", "其他"])
    user_job = st.text_input("您的職業/狀態", placeholder="例如：金融業、學生...")
    
    st.markdown("#### 📅 出生時間")
    uc1, uc2, uc3 = st.columns(3)
    u_year = uc1.selectbox("年", range(1930, 2027), index=50, key="u_year")
    u_month = uc2.selectbox("月", range(1, 13), key="u_month")
    u_day = uc3.selectbox("日", range(1, 32), key="u_day")
    
    uc4, uc5 = st.columns(2)
    u_hour = uc4.selectbox("時", range(0, 24), index=12, key="u_hour")
    u_min = uc5.selectbox("分", range(0, 60), key="u_min")
    st.markdown('</div>', unsafe_allow_html=True)

with col_main2:
    st.markdown('<div class="premium-card"><div class="card-title">💞 對象緣分資料</div>', unsafe_allow_html=True)
    partner_name = st.text_input("對象姓名/暱稱", placeholder="如何稱呼對方？")
    partner_gender = st.selectbox("對象性別", ["男", "女", "其他"])
    relation_type = st.selectbox("目前關係類型", ["暗戀中", "曖昧中", "交往中", "已婚", "冷戰/分手", "其他"])
    
    st.markdown("#### 📅 對象出生時間")
    pc1, pc2, pc3 = st.columns(3)
    p_year = pc1.selectbox("年", range(1930, 2027), index=50, key="p_year")
    p_month = pc2.selectbox("月", range(1, 13), key="p_month")
    p_day = pc3.selectbox("日", range(1, 32), key="p_day")
    
    pc4, pc5 = st.columns(2)
    p_hour = pc4.selectbox("時", range(0, 24), index=12, key="p_hour")
    p_min = pc5.selectbox("分", range(0, 60), key="p_min")
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="premium-card"><div class="card-title">💬 您心中的疑惑</div>', unsafe_allow_html=True)
current_status = st.text_area("描述目前的互動狀況或具體問題", placeholder="例如：對方最近回訊變慢，我們剛吵完架...", height=150)
expectation = st.selectbox("您對這段關係的期待", ["修復關係", "看清真相", "瀟灑轉身", "尋求突破", "其他"])
partner_attitude = st.selectbox("您感受到對方的目前態度", ["逃避", "忽冷忽熱", "冷淡", "熱情", "未知"])
st.markdown('</div>', unsafe_allow_html=True)

if st.button("✨ 啟動 AI 心理深度解析"):
    if not current_status or not user_name or not partner_name:
        st.warning("請填寫姓名與目前的互動狀況。")
    else:
        # 收集資料準備紀錄
        submission_data = {
            "user_name": user_name,
            "gender": user_gender,
            "job_status": user_job,
            "birth_year": u_year,
            "birth_month": u_month,
            "birth_day": u_day,
            "birth_hour": u_hour,
            "birth_minute": u_min,
            "analysis_mode": "感情心理分析",
            "question": f"互動狀況：{current_status}\n期待：{expectation}\n對方態度：{partner_attitude}",
            "is_couple_mode": True,
            "partner_name": partner_name,
            "partner_gender": partner_gender,
            "partner_birth_year": p_year,
            "partner_birth_month": p_month,
            "partner_birth_day": p_day,
            "partner_birth_hour": p_hour,
            "partner_birth_minute": p_min
        }
        append_user_submission(submission_data)
        
        with st.spinner("AI 心理分析顧問正在為您判讀局勢..."):
            st.success("分析完成！(目前為功能展示，紀錄已寫入)")
            st.info(f"您的問題已記錄：{current_status[:50]}...")

# --- 六、頁尾引流 ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("""
<div style="background-color: #E2E2CC; padding: 40px; border-radius: 20px; text-align: center;">
    <h2 style="border: none;">還在不安中反覆內耗嗎？</h2>
    <p style="font-size: 18px; margin-bottom: 25px;">讓 HUGO 天命智庫 陪你一起看清這段關係的真實樣貌，找回你的主動權。</p>
</div>
""", unsafe_allow_html=True)

st.link_button("👉 加 LINE 獲取一對一專家分析", "https://line.me/ti/p/@323ohobf", use_container_width=True)

if st.button("⬅️ 返回首頁"):
    st.switch_page("app.py")

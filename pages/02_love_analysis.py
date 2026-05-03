import streamlit as st
from openai import OpenAI
import datetime
import os
import json
import pandas as pd
from dotenv import load_dotenv
import uuid
from data_logger import log_site_visit

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
    /* 全局背景：沉穩暖灰色系 */ 
    .stApp { 
        background-color: #B3AAAA; 
        color: #2D2D2D; 
    } 
    
    /* 側邊欄：亞麻灰 */ 
    [data-testid="stSidebar"] { 
        background-color: #C9C9C2; 
        border-right: 1px solid #999; 
    } 

    /* 內容區塊寬度 */
    .block-container { 
        max-width: 1000px;
        padding-top: 2rem;
    } 

    /* 暖灰色卡片樣式 */ 
    .love-card { 
        background-color: #C9C9C2; 
        padding: 25px; 
        border-radius: 18px; 
        box-shadow: 0 6px 20px rgba(0,0,0,0.08); 
        margin-bottom: 20px;
        border: 1px solid #B3AAAA;
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
        color: #4a235a;
        margin-bottom: 10px;
        font-weight: 800;
    }
    .feature-card p {
        font-size: 0.95em;
        line-height: 1.5;
        color: #444;
    }

    /* 標題樣式 */
    h1, h2, h3 { 
        color: #2D2D2D !important; 
        border-left: 6px solid #6c5ce7; 
        padding-left: 15px; 
    }

    /* CTA 按鈕美化 */
    .stButton>button {
        height: 58px !important;
        border-radius: 16px !important;
        font-weight: 800 !important;
        font-size: 1.1em !important;
        background: linear-gradient(135deg, #6c5ce7, #a29bfe) !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 6px 15px rgba(108, 92, 231, 0.3) !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }
    .stButton>button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 10px 25px rgba(108, 92, 231, 0.4) !important;
    }

    /* 定價方案卡片 */
    .pricing-card {
        background-color: #F4F4ED;
        padding: 25px;
        border-radius: 20px;
        border: 2px solid #E2E2CC;
        text-align: center;
        margin-bottom: 20px;
    }
    .pricing-price {
        font-size: 2em;
        font-weight: 900;
        color: #6c5ce7;
        margin: 10px 0;
    }
    
    /* 診斷表樣式 */
    .diagnostic-table {
        width: 100%;
        border-collapse: collapse;
        background-color: #FDFCF9;
        border-radius: 12px;
        overflow: hidden;
    }
    .diagnostic-table th {
        background-color: #E2E2CC;
        padding: 12px;
        text-align: left;
    }
    .diagnostic-table td {
        padding: 12px;
        border-bottom: 1px solid #EEE;
    }
</style> 
""", unsafe_allow_html=True)

# --- 一、頁面主標 ---
st.markdown("""
<div style="text-align: center; margin-bottom: 40px;">
    <h1 style="font-size: 42px; font-weight: 900; border: none; padding: 0;">兩性情感心理諮詢</h1>
    <h3 style="font-size: 22px; color: #444; border: none; padding: 0; font-weight: 600;">你不是不夠好，而是還沒看懂這段關係真正卡住的地方。</h3>
    <p style="font-size: 17px; color: #555; max-width: 800px; margin: 20px auto; line-height: 1.7;">
        當對方忽冷忽熱、訊息變少、態度模糊，很多人會開始懷疑自己是不是做錯了什麼。但感情問題往往不是單一事件，而是由依附模式、溝通方式、情緒反應與雙方關係結構共同形成。
    </p>
    <div style="background-color: #E2E2CC; display: inline-block; padding: 10px 25px; border-radius: 30px; font-weight: 800; color: #4a235a;">
        八字命盤 × 關係心理 × 行為模式 × AI 交叉分析
    </div>
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

# --- 四、付費引流區 (中段) ---
st.markdown("## 💎 專業顧問服務方案")
col_p1, col_p2, col_p3 = st.columns(3)

with col_p1:
    st.markdown("""
    <div class="pricing-card">
        <h3>免費版</h3>
        <p>適合初步了解目前關係狀態</p>
        <div class="pricing-price">$0</div>
        <p style="text-align: left; font-size: 0.9em; min-height: 120px;">
        ・提供基礎方向判讀<br>
        ・協助你先看懂問題大概在哪裡
        </p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("我要做兩人關係解析", key="btn_free"):
        pass

with col_p2:
    st.markdown("""
    <div class="pricing-card" style="border-color: #6c5ce7; background-color: #F0EFFF;">
        <div style="background: #6c5ce7; color: white; border-radius: 5px; padding: 2px 10px; display: inline-block; font-size: 0.8em; margin-bottom: 10px;">熱門推薦</div>
        <h3>299 深度分析</h3>
        <p>適合正在曖昧、冷戰、分手邊緣的人</p>
        <div class="pricing-price">$299</div>
        <p style="text-align: left; font-size: 0.9em; min-height: 120px;">
        ・單一感情問題深入分析<br>
        ・提供對方心態與走向判讀<br>
        ・給予 3 種實戰行動選項<br>
        ・包含 3 次提問 (5天內有效)
        </p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("我要看對方心態", key="btn_299"):
        pass

with col_p3:
    st.markdown("""
    <div class="pricing-card">
        <h3>699 完整追蹤</h3>
        <p>適合重大感情抉擇或拉扯中</p>
        <div class="pricing-price">$699</div>
        <p style="text-align: left; font-size: 0.9em; min-height: 120px;">
        ・結合命盤、互動與心理模式<br>
        ・提供完整判斷與策略調整<br>
        ・非一次性回答，含階段追蹤<br>
        ・專屬策略報告
        </p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("查看 299 / 699 方案", key="btn_699"):
        pass

# --- 五、表單輸入區 (模擬分析流程) ---
st.markdown("---")
st.header("📋 描述目前的感情困局")
with st.container():
    col_in1, col_nav_in2 = st.columns(2)
    with col_in1:
        st.text_area("目前的互動狀況 (例如：訊息變少、冷戰中...)", height=150)
    with col_nav_in2:
        st.selectbox("你對這段關係的期待", ["修復關係", "看清真相", "瀟灑轉身", "其他"])
        st.selectbox("對方的目前態度", ["逃避", "忽冷忽熱", "冷淡", "熱情", "未知"])

st.button("✨ 啟動 AI 心理深度解析")

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

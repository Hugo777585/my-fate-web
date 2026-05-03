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
import hashlib
import uuid
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials
from lunar_python import Lunar, Solar
from tone_engine import analyze_tone_strategy
from fpdf import FPDF
from data_logger import log_site_visit, append_user_submission, ensure_worksheet

load_dotenv()
openai_key = st.secrets.get("OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")

if not openai_key:
    st.error("尚未設定 OPENAI_API_KEY，請先到 Streamlit Cloud Secrets 加入金鑰。")
    st.stop()

client = OpenAI(api_key=openai_key)

# --- Hugo 大師專屬：專業命理顧問感樣式 --- 
st.markdown(""" 
<style> 
    /* 1. 全局背景色：#B3AAAA */ 
    .stApp { 
        background-color: #B3AAAA; 
        color: #2F2F2F; 
        font-family: 'Noto Sans TC', sans-serif;
    } 

    /* 隱藏預設元素與多餘白條 */
    hr, .stDivider, div[data-testid="stDivider"], header, footer { display: none !important; }
    .block-container { 
        padding-top: 2rem; 
        padding-bottom: 2rem; 
        max-width: 1100px;
    } 
    
    /* 2. 主內容卡片背景：#C9C9C2 */
    .main-card {
        background-color: #C9C9C2;
        padding: 35px;
        border-radius: 22px;
        box-shadow: 0 12px 40px rgba(0,0,0,0.15);
        margin-bottom: 30px;
        border: 1px solid rgba(0,0,0,0.05);
    }

    /* 3. 區塊橫桿 / 標題區背景：#E2E2CC */
    .section-bar {
        background-color: #E2E2CC;
        padding: 15px 25px;
        border-radius: 18px;
        font-weight: 900;
        font-size: 24px;
        color: #2F2F2F;
        margin: 40px 0 25px 0;
        border-left: 10px solid #9A7A38;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }

    /* 4. 2x2 功能大卡片 */
    .feature-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 20px;
        margin-bottom: 30px;
    }
    .feature-card {
        background-color: #E2E2CC;
        border-radius: 20px;
        padding: 30px;
        text-align: center;
        box-shadow: 0 8px 20px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        border: 1px solid rgba(154, 122, 56, 0.2);
        height: 100%;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .feature-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 15px 35px rgba(0,0,0,0.15);
    }
    .feature-icon { font-size: 45px; margin-bottom: 15px; }
    .feature-title { font-size: 24px; font-weight: 900; color: #2F2F2F; margin-bottom: 12px; }
    .feature-desc { font-size: 16px; color: #444; line-height: 1.6; margin-bottom: 25px; }

    /* 5. 三大經典卡片 */
    .classic-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 20px;
    }
    .classic-card {
        background-color: #F4F4ED;
        padding: 25px;
        border-radius: 18px;
        border: 1px solid #E2E2CC;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .classic-header { color: #9A7A38; font-weight: 900; font-size: 19px; margin-bottom: 10px; }
    .classic-point { background: #E2E2CC; padding: 5px 12px; border-radius: 8px; font-weight: 700; display: inline-block; margin-top: 10px; }

    /* 6. 按鈕樣式：高度 48px+，重點金色 #9A7A38 */
    .stButton > button {
        height: 52px !important;
        border-radius: 15px !important;
        font-weight: 900 !important;
        font-size: 18px !important;
        background-color: #9A7A38 !important;
        color: white !important;
        border: none !important;
        box-shadow: 0 6px 15px rgba(154, 122, 56, 0.3) !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
    }
    .stButton > button:hover {
        background-color: #B38E45 !important;
        box-shadow: 0 10px 25px rgba(154, 122, 56, 0.4) !important;
        transform: translateY(-2px) !important;
    }

    /* 7. 方案卡片 */
    .price-card {
        background-color: #FDFCF9;
        padding: 30px;
        border-radius: 22px;
        text-align: center;
        border: 2px solid #E2E2CC;
        transition: all 0.3s ease;
        height: 100%;
    }
    .price-card.featured { border-color: #9A7A38; background-color: #ECECD8; }
    .price-title { font-size: 24px; font-weight: 900; color: #2F2F2F; }
    .price-val { font-size: 38px; font-weight: 900; color: #9A7A38; margin: 20px 0; }

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
</style> 
""", unsafe_allow_html=True)

def ai_reply(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 連線失敗：{str(e)}"

def ai_love_consult_reply(context_prompt, is_master=False):
    system_role = """你是一位結合命理分析、感情心理諮詢與關係策略的顧問。請用沉穩、理性、具同理心的方式分析。"""
    if is_master:
        permission_instruction = "【大師模式：完整分析】"
    else:
        permission_instruction = "【一般模式：初步引導】"
    full_prompt = f"{system_role}\n\n{context_prompt}\n{permission_instruction}"
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
            <tr style="background-color: {m_color};"><td>月柱</td><td>{bazi['month_tg']}</td><td>{bazi['month_ss']}</td><td>{bazi['year_dz']}</td><td>{bazi['month_hide']}</td></tr>
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

# --- 初始化 Session State ---
if 'session_id' not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if 'visited_pages' not in st.session_state:
    st.session_state.visited_pages = set()

st.set_page_config(page_title="HUGO 天命智庫", page_icon="🔮", layout="wide")

# --- 1. 頂部 Hero 區 (包含 Logo 與 標題) ---
logo_html = ""
if os.path.exists("logo.JPG"):
    with open("logo.JPG", "rb") as f:
        logo_base64 = base64.b64encode(f.read()).decode()
    logo_html = f'<div class="logo-box"><img src="data:image/jpeg;base64,{logo_base64}" class="logo-img"></div>'
else:
    logo_html = '<div class="logo-box"><h1 style="color:#9A7A38; margin:0;">HUGO 天命智庫</h1></div>'

if 'analysis_mode' not in st.session_state:
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

    # --- 6. 方案引流區 ---
    st.markdown('<div class="section-bar">專業諮詢方案</div>', unsafe_allow_html=True)
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1: st.markdown('<div class="price-card"><div class="price-title">免費體驗</div><div class="price-val">$0</div><p>基礎命盤解析</p></div>', unsafe_allow_html=True); st.button("開始免費分析", key="p_free")
    with col_p2: st.markdown('<div class="price-card featured"><div class="price-title">299 深度分析</div><div class="price-val">$299</div><p>單一感情問題深入分析</p></div>', unsafe_allow_html=True); st.button("了解 299 方案", key="p_299")
    with col_p3: st.markdown('<div class="price-card"><div class="price-title">699 完整追蹤</div><div class="price-val">$699</div><p>命盤+互動+心理策略</p></div>', unsafe_allow_html=True); st.button("了解 699 方案", key="p_699")

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
    enable_dual = st.toggle("💑 啟用雙人合盤", value=st.session_state.get('enable_dual', False))
    if enable_dual:
        st.subheader("💞 對象資料")
        name2 = st.text_input("對象姓名")
        relation_type = st.selectbox("關係", ["情侶/夫妻", "合作夥伴", "其他"])
        # ... (簡化對象時間輸入以節省空間)
    
    question = st.text_area("您的問題", placeholder="例如：這段感情還有救嗎？")
    
    if st.button("🚀 開始 AI 命理分析"):
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
            "partner_gender": "未知", # 原本簡化輸入沒這欄位，補上
            "partner_birth_year": "1980", 
            "partner_birth_month": "1",
            "partner_birth_day": "1",
            "partner_birth_hour": "12",
            "partner_birth_minute": "0"
        }
        append_user_submission(submission_data)

        with st.spinner("大師發功中..."):
            mode = st.session_state.analysis_mode
            
            # 1. 基礎資料準備
            bazi = calculate_bazi(b_year, b_month, b_day, b_hour, b_min)
            
            if not bazi:
                st.error("排盤失敗，請檢查輸入的出生時間。")
            else:
                # 2. 根據模式執行不同的渲染與分析
                if mode == "紫微斗數分析":
                    st.warning("🔮 紫微斗數分析模組建置中，請改用八字 × 紫微交叉分析或八字命理分析。")
                    # 這裡不顯示八字盤
                
                elif mode == "八字命理分析":
                    # 顯示八字盤
                    st.markdown(render_bazi_table(bazi), unsafe_allow_html=True)
                    
                    # 呼叫 AI 分析
                    prompt = f"你是一位專業命理大師。請針對以下八字命盤進行深度分析：\n姓名：{name}\n性別：{gender}\n出生時間：{b_year}/{b_month}/{b_day} {b_hour}:{b_min}\n職業：{occupation}\n問題：{question}\n命盤數據：{bazi['full']}\n\n請分析性格、事業、財運與感情建議。"
                    result = ai_reply(prompt)
                    st.markdown(f'<div class="main-card">{result}</div>', unsafe_allow_html=True)
                
                elif mode == "八字 × 紫微交叉分析":
                    # 顯示八字盤作為參考之一
                    st.markdown("### 📜 八字命盤基礎")
                    st.markdown(render_bazi_table(bazi), unsafe_allow_html=True)
                    
                    st.info("💡 紫微斗數詳細星盤模組建置中，目前以「八字為主，紫微邏輯為輔」進行交叉分析。")
                    
                    prompt = f"你是一位精通八字與紫微斗數的大師。請針對以下命盤進行「交叉比對分析」：\n姓名：{name}\n問題：{question}\n八字數據：{bazi['full']}\n\n請結合兩套系統，提供更高維度的判斷建議。"
                    result = ai_reply(prompt)
                    st.markdown(f'<div class="main-card">{result}</div>', unsafe_allow_html=True)
                
                elif mode == "兩人合盤分析":
                    if not enable_dual:
                        st.error("請先在上方開啟「💑 啟用雙人合盤」並填寫對象資料。")
                    else:
                        # 顯示第一人八字
                        st.markdown(f"### 📜 {name} 的命盤")
                        st.markdown(render_bazi_table(bazi), unsafe_allow_html=True)
                        
                        prompt = f"你是一位專業合盤大師。請分析 {name} 與其對象 {name2} 的關係。\n關係類型：{relation_type}\n主諮詢者八字：{bazi['full']}\n問題：{question}\n\n請分析雙方吸引力、衝突點與相處建議。"
                        result = ai_reply(prompt)
                        st.markdown(f'<div class="main-card">{result}</div>', unsafe_allow_html=True)


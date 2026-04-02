import datetime as _dt
import json
import streamlit as st
import google.generativeai as genai
from borax.calendars.lunardate import LunarDate

# ==========================================
# 1. 核心設定
# ==========================================
st.set_page_config(page_title="Hugo 乾坤命理館", layout="wide")

OCCUPATIONS = ["上班族", "創業/自由業", "學生 (未滿十八歲)", "學生 (十八歲以上)", "家管", "已退休", "更生人", "待業中"]
OCCURATION_STATUS = ["受聘上班族", "自己經營創業", "自由工作者", "目前待業中"]
RELATIONSHIP_STATUS = ["單身", "穩定交往中", "已婚", "已離婚/分居"]

# ==========================================
# 2. 計算邏輯 (找回大綱的靈魂)
# ==========================================
def get_bazi_display(d):
    try:
        ld = LunarDate.from_solar_date(d.year, d.month, d.day)
        return f"📅 **農曆生日**：{ld.year}年 {ld.month}月 {ld.day}日 \n\n 📜 **命理八字**：{ld.gz_year}年 {ld.gz_month}月 {ld.gz_day}日"
    except:
        return "資料計算中..."

# ==========================================
# 3. 側邊欄與 AI 邏輯
# ==========================================
with st.sidebar:
    st.header("⚙️ 大師後台")
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    master_code = st.text_input("大師密碼", type="password")
    is_master = (master_code == "HUGO888")

def generate_ai_text(api_key, module, payload, is_master):
    if not api_key: return "請先在左側設定 API Key。"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")
    prompt = f"你是命理大師 Hugo。模組：{module}。資料：{json.dumps(payload, ensure_ascii=False)}"
    if is_master: prompt += "（啟動宗師深度模式，針對家管/更生人給出具體破局戰術）"
    try:
        res = model.generate_content(prompt)
        return res.text
    except Exception as e: return f"解析失敗：{str(e)}"

# ==========================================
# 4. 主介面佈局 (找回消失的看板)
# ==========================================
st.title("🔮 Hugo 乾坤命理館：流年造化推演")

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.subheader("👤 主命主資料")
        name = st.text_input("姓名", value="命主A")
        u_birth = st.date_input("您的生日", value=_dt.date(1980, 1, 1), min_value=_dt.date(1940, 1, 1))
        u_time = st.time_input("出生時間", value=_dt.time(12, 0))
        occupation = st.selectbox("目前的身份/狀態：", OCCUPATIONS)
    
    # 🔥🔥🔥 這裡就是你說消失的大綱！我把它抓回來了！ 🔥🔥🔥
    st.info(get_bazi_display(u_birth))

with col2:
    with st.container(border=True):
        st.subheader("🏠 現實生活狀態")
        job_s = st.selectbox("目前職業狀態", OCCURATION_STATUS)
        rel_s = st.selectbox("感情婚姻現況", RELATIONSHIP_STATUS)
        child = st.text_input("子女狀況", placeholder="例如：1個，17歲")

st.divider()
btn_cols = st.columns(3)
module = None
if btn_cols[0].button("八字乾坤：深度能量解析"): module = "八字解析"
if btn_cols[1].button("紫微精論：人生十二宮位"): module = "紫微解析"
if btn_cols[2].button("兩人命運合盤：深度解析"): module = "兩人配對"

if module:
    payload = {"姓名": name, "身分": occupation, "生日": str(u_birth)}
    with st.spinner("大師解析中..."):
        res = generate_ai_text(api_key, module, payload, is_master)
        st.markdown(f"### 🖋️ Hugo 大師論斷：{module}")
        st.markdown(f"<div style='background-color: #1e212b; padding: 20px; border-radius: 10px;'>{res}</div>", unsafe_allow_html=True)

# 底部聯絡資訊
st.markdown("---")
st.subheader("🔮 預約 Hugo 大師親自破局")
st.markdown("### 📱 LINE 預約：https://line.me/ti/p/~en777585 ")

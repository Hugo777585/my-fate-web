import datetime as _dt
import json
import streamlit as st
import google.generativeai as genai
from borax.calendars.lunardate import LunarDate

# ==========================================
# 1. 核心常數與設定
# ==========================================
st.set_page_config(page_title="Hugo 乾坤命理館", layout="wide")

OCCUPATIONS = ["上班族", "創業/自由業", "學生 (未滿十八歲)", "學生 (十八歲以上)", "家管", "已退休", "更生人", "待業中"]
OCCURATION_STATUS = ["受聘上班族", "自己經營創業", "自由工作者", "目前待業中"]
RELATIONSHIP_STATUS = ["單身", "穩定交往中", "已婚", "已離婚/分居"]
BOOK_OPTIONS = ["滴天髓（氣勢）", "窮通寶鑒（調候）", "三命通會（格局神煞）"]

# ==========================================
# 2. AI 靈魂發動機 (包含完整 Hugo 大師指令)
# ==========================================
def generate_ai_text(api_key, module, payload, selected_books, is_master):
    if not api_key: return "請先在左側設定 API Key。"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name="gemini-2.0-flash")
    
    books_str = "、".join(selected_books) if selected_books else "（未指定）"
    
    # 這裡就是你最重視的大師紀錄與指令
    if is_master:
        system_prompt = f"""
        【核心大腦：Hu go 大師商業決策引擎 5.0】
        你是一位經歷過人生起伏、看透人性深淵的命理大師「Hu go」。
        你的任務是幫用戶看懂人性，拿回控制權。語氣沉穩、犀利、有強烈同理心。
        
        【特殊權重指令】：
        - 家管：核心在於重新找回自我價值、打破情感依賴。
        - 更生人：核心在於重建關係平權、掌握自我揭露時機、拒絕委曲求全。
        - 學生：戰略以保護、防範受傷為主。
        
        【輸出結構】：
        1. 🔮 第一層：【靈魂共振】（直擊痛點、關係風險解碼）
        2. ☯️ 第二層：【命理金箔與殘酷定位】（使用八字/紫微術語，給出情感順位評分、穩定度）
        3. 🔥 第三層：【破局戰術】（給出 3 點現在立刻該怎麼做的具體戰術，不准說廢話）
        
        學理框架：{books_str}、引用《滴天髓》分析格局、引用紫微斗數分析人性。
        """
    else:
        system_prompt = "請扮演資深命理宗師 Hugo。給出核心性格特質與 2026 命運轉折。最後加上：✨【Hugo 大師本尊深度解析】✨ 私訊預約解鎖完整天命。"

    user_prompt = f"目前模組：{module}\n客戶輸入資料：{json.dumps(payload, ensure_ascii=False)}"
    
    try:
        response = model.generate_content(system_prompt + "\n\n" + user_prompt)
        return response.text
    except Exception as e:
        return f"大師目前正在沉思中，請稍後再試：{str(e)}"

# ==========================================
# 3. 側邊欄 (管理員模式)
# ==========================================
with st.sidebar:
    st.header("⚙️ 大師後台")
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    master_code = st.text_input("大師通關密語", type="password")
    is_master = (master_code == "HUGO888")
    if is_master: st.success("✅ 宗師深度模式已啟動")

# ==========================================
# 4. 主介面
# ==========================================
st.title("🔮 Hugo 乾坤命理館：流年造化推演")

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.subheader("👤 主命主資料")
        name = st.text_input("姓名/標籤", value="命主A")
        gender = st.selectbox("性別", ["male", "female"], format_func=lambda x: "男" if x=="male" else "女")
        u_birth = st.date_input("您的生日", value=_dt.date(1980, 1, 1), min_value=_dt.date(1940, 1, 1))
        u_time = st.time_input("出生時間", value=_dt.time(12, 0))
        occupation = st.selectbox("目前的身份/狀態：", OCCUPATIONS)
    
    with st.container(border=True):
        st.subheader("🏠 現實生活狀態")
        job_s = st.selectbox("目前職業狀態", OCCURATION_STATUS)
        rel_s = st.selectbox("感情婚姻現況", RELATIONSHIP_STATUS)
        child = st.text_input("子女狀況", placeholder="例如：1個，17歲")

with col2:
    with st.container(border=True):
        st.subheader("🔮 兩人配對 (選填)")
        p_name = st.text_input("對象姓名", "")
        p_birth = st.date_input("對象生日", value=None, key="p_d", min_value=_dt.date(1940, 1, 1))
        p_time = st.selectbox("對象時辰", ["不清楚", "子時", "丑時", "寅時", "卯時", "辰時", "巳時", "午時", "未時", "申時", "酉時", "戌時", "亥時"], key="p_t")
    
    books = st.multiselect("學理框架", BOOK_OPTIONS, default=BOOK_OPTIONS)

# ==========================================
# 5. 執行分析
# ==========================================
st.divider()
btn_cols = st.columns(3)
module = None
if btn_cols[0].button("八字乾坤：深度能量解析"): module = "八字解析"
if btn_cols[1].button("紫微精論：人生十二宮位"): module = "紫微解析"
if btn_cols[2].button("兩人命運合盤：深度解析"): module = "兩人配對"

if module:
    # 準備發送給 AI 的封包
    payload = {
        "姓名": name, "生日": str(u_birth), "性別": gender, "身分": occupation, 
        "職業狀態": job_s, "感情現況": rel_s, "子女": child,
        "對象姓名": p_name, "對象生日": str(p_birth), "對象時辰": p_time
    }
    
    with st.spinner("Hugo 大師正在撥雲見日..."):
        res = generate_ai_text(api_key, module, payload, books, is_master)
        st.markdown(f"### 🖋️ Hugo 大師論斷：{module}")
        st.markdown(f"<div style='background-color: #1e212b; padding: 25px; border-radius: 12px; border: 1px solid #30363d;'>{res}</div>", unsafe_allow_html=True)

# ==========================================
# 6. 底部聯絡資訊 (隨時可見)
# ==========================================
st.markdown("---")
st.subheader("🔮 預約 Hugo 大師親自破局")
st.markdown("### 📱 LINE 預約：https://line.me/ti/p/~en777585 ")
st.info("若您的情況複雜，需要針對目前僵局制定「專屬攻略」，請直接私訊大師 Hugo。")

import datetime as _dt
import json
import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from borax.calendars.festivals2 import TermFestival
from borax.calendars.lunardate import LunarDate
from iztro_py import astro

# 選項清單
OCCUPATIONS = ["上班族", "創業/自由業", "學生 (未滿十八歲)", "學生 (十八歲以上)", "家管", "已退休", "更生人", "待業中"]
OCCURATION_STATUS = ["受聘上班族", "自己經營創業", "自由工作者", "目前待業中"]
RELATIONSHIP_STATUS = ["單身", "穩定交往中", "已婚", "已離婚/分居"]

# 基礎邏輯
def bazi_from_borax(d, t):
    ld = LunarDate.from_solar_date(d.year, d.month, d.day)
    return {"lunar": str(ld), "pillars": ld.gz_year + ld.gz_month + ld.gz_day}

def generate_ai_text(api_key, model_name, module, payload, is_master):
    if not api_key: return "請輸入 API Key"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=model_name)
    prompt = f"扮演命理大師 Hugo。身份是{payload['occupation']}。模式：{module}。資料：{payload}"
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e: return str(e)

# 介面
st.title("🔮 Hugo 乾坤命理館")
with st.sidebar:
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    master_code = st.text_input("大師密碼", type="password")
    is_master = (master_code == "HUGO888")

name = st.text_input("姓名", value="命主A")
u_birth = st.date_input("生日", value=_dt.date(1980, 1, 1))
u_time = st.time_input("出生時間")
occupation = st.selectbox("目前身分", OCCUPATIONS)

if st.button("八字乾坤：深度解析"):
    payload = {"name": name, "occupation": occupation, "birthday": str(u_birth)}
    res = generate_ai_text(api_key, "gemini-2.0-flash", "八字解析", payload, is_master)
    st.markdown(f"### 🖋️ Hugo 大師論斷\n{res}")

st.markdown("---")
st.markdown("### 📱 LINE 預約：`https://line.me/ti/p/~en777585` ")

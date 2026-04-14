import streamlit as st
import google.generativeai as genai
import datetime

st.set_page_config(page_title="Hugo 命理大師", page_icon="🔮")
st.title("🔮 Hugo 命理大師 - 專屬運勢分析")

try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash")
except Exception as e:
    st.error("API 金鑰讀取失敗，請確認 Streamlit Secrets 設定是否正確。")
    st.stop()

st.header("📋 填寫基本資料")
col1, col2, col3 = st.columns(3)

with col1:
    gender = st.selectbox("性別", ["男", "女"])
with col2:
    birth_date = st.date_input("出生日期 (國曆)", min_value=datetime.date(1930, 1, 1))
with col3:
    birth_time = st.time_input("出生時間")

occupation = st.selectbox(
    "目前狀態/職業",
    ["學生", "上班族", "受聘", "自營商", "合夥公司", "公務人員", "軍警", "八大行業", "待業", "家管", "退休", "更生人", "身障"]
)

question = st.text_area("有什麼特別想問的問題嗎？（例如：想問下半年的財運、適不適合換工作等）", placeholder="請簡述您的問題...")

if st.button("✨ 開始發功試算"):
    if not question:
        st.warning("請簡單填寫一下您想問的問題，大師才能為您指點迷津喔！")
    else:
        with st.spinner("大師正在排盤與分析中，請稍候..."):
            prompt = f"""
            你是一位擁有近 30 年經驗的專業命理大師。
            現在有一位客人來找你算命，以下是他的基本資料與現況：
            - 性別：{gender}
            - 出生日期：{birth_date}
            - 出生時間：{birth_time}
            - 職業/目前狀態：{occupation}
            - 他特別想問的問題：{question}

            請根據以上資料，執行以下分析任務：
            1. 請根據他的職業與狀態（{occupation}）給予符合現況的精準分析。例如：自營商/合夥側重財運與合作；受聘/公務人員/軍警側重事業官運；八大行業側重桃花人緣與身心提醒；更生人/身障/待業給予轉機與心理支撐。
            2. 針對他提問的問題（{question}），以傳統命理（八字或紫微）的角度，給出具體、專業且具同理心的建議。
            3. 語氣請保持專業、沉穩且溫暖，全篇請使用繁體中文，排版要清晰易讀。
            """

            try:
                response = model.generate_content(prompt)
                st.success("分析完成！")
                st.markdown("### 📜 大師解析")
                st.write(response.text)
            except Exception as e:
                st.error(f"發生錯誤：{e}")

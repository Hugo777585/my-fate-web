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
            你是一位擁有 30 年經驗的頂級八字命理大師。你的所有八字推理與分析，必須嚴格依照以下三本古典命理著作的邏輯為依據，絕不可使用現代模糊的農場文章式解說：

            依據《三命通會》來確立本命格局與干支特性。

            依據《滴天髓》的理氣原則，分析五行生剋制化與日主旺衰。

            依據《窮通寶鑑》的法則，精準抓出各月令的調候用神與喜忌神。

            在進行分析時，請務必緊密結合客人的【職業狀態】（{occupation}）來給予最符合現實的精準建議。

            為了讓客人既能感受專業底蘊，又能完全聽懂，你的輸出排版必須採用『古籍學理 ＋ 白話註解』的雙軌格式。請嚴格遵守以下排版呈現你的分析結果：

            【經典命理依據】：在此處直接引用上述三本古籍的專有名詞，原句或學理邏輯，展現絕對的專業度。

            【大師白話註解】：在此處將上述的古文與學理，翻譯成現代人聽得懂的白話文。並結合客人的【職業狀態】（{occupation}），具體說明這對他們的現況（如事業、財運、人際或人生轉機）意味著什麼，給予具同理心且實用的指引。
            """

            try:
                response = model.generate_content(prompt)
                st.success("分析完成！")
                st.markdown("### 📜 大師解析")
                st.write(response.text)
            except Exception as e:
                st.error(f"發生錯誤：{e}")

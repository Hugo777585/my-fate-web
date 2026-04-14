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

st.divider()
st.header("⚙️ 進階設定")

version = st.radio(
    "選擇測算深度版本：",
    ["🟢 簡易大眾版 (白話易懂)", "🟣 大師深度版 (古籍引經據典)"],
    captions=["親切輕鬆，實用生活建議", "專業嚴謹，三大古籍學理依據"]
)

enable_dual = st.checkbox("💞 啟用雙人合盤 (感情/合夥)")

person2_data = None
if enable_dual:
    st.subheader("💞 第二位對象資料")
    col_p2_1, col_p2_2, col_p2_3 = st.columns(3)
    with col_p2_1:
        gender2 = st.selectbox("對象性別", ["男", "女"], key="gender2")
    with col_p2_2:
        birth_date2 = st.date_input("對象出生日期", min_value=datetime.date(1930, 1, 1), key="birth_date2")
    with col_p2_3:
        birth_time2 = st.time_input("對象出生時間", key="birth_time2")
    
    relation_type = st.selectbox(
        "雙方關係",
        ["情侶/夫妻", "事業合夥", "家人/朋友"]
    )

if st.button("✨ 開始發功試算"):
    if not question:
        st.warning("請簡單填寫一下您想問的問題，大師才能為您指點迷津喔！")
    else:
        with st.spinner("大師正在排盤與分析中，請稍候..."):
            if version == "🟢 簡易大眾版 (白話易懂)":
                prompt = f"""
                你是一位親切温暖的運勢顧問，擅長用輕鬆、白話、正向鼓勵的方式幫助客人了解自己的運勢。
                
                現在有一位客人來找你諮詢，以下是他的基本資料：
                - 性別：{gender}
                - 出生日期：{birth_date}
                - 出生時間：{birth_time}
                - 職業/目前狀態：{occupation}
                - 他特別想問的問題：{question}
                
                請用淺顯易懂、輕鬆正向的語氣，直接給出實用的生活建議。不要引經據典，用白話文回答就好。
                語氣要像朋友間的深度對話，帶有溫暖與同理心，讓人感受到希望與力量。
                """
                
                if enable_dual and relation_type and birth_date2 and birth_time2:
                    prompt += f"""
                    
                    此外，這位客人想要進行雙人合盤分析！
                    - 第二位對象性別：{gender2}
                    - 第二位對象出生日期：{birth_date2}
                    - 第二位對象出生時間：{birth_time2}
                    - 雙方關係：{relation_type}
                    
                    請用輕鬆易懂的方式，分析這段關係的互補與潛在挑戰，並給出促進關係和諧的實用建議。
                    """
            else:
                prompt = f"""
                你是一位擁有 30 年經驗的頂級八字命理大師。你的所有八字推理與分析，必須嚴格依照以下三本古典命理著作的邏輯為依據，絕不可使用現代模糊的農場文章式解說：

                依據《三命通會》來確立本命格局與干支特性。

                依據《滴天髓》的理氣原則，分析五行生剋制化與日主旺衰。

                依據《窮通寶鑑》的法則，精準抓出各月令的調候用神與喜忌神。

                在進行分析時，請務必緊密結合客人的【職業狀態】（{occupation}）來給予最符合現實的精準建議。

                為了讓客人既能感受專業底蘊，又能完全聽懂，你的輸出排版必須採用『古籍學理 ＋ 白話註解』的雙軌格式。請嚴格遵守以下排版呈現你的分析結果：

                【經典命理依據】：在此處直接引用上述三本古籍的專有名詞，原句或學理邏輯，展現絕對的專業度。

                【大師白話註解】：在此處將上述的古文與學理，翻譯成現代人聽得懂的白話文。並結合客人的【職業狀態】（{occupation}），具體說明這對他們的現況（如事業、財運，人際或人生轉機）意味著什麼，給予具同理心且實用的指引。
                """
                
                if enable_dual and relation_type and birth_date2 and birth_time2:
                    prompt += f"""
                    
                    此外，這位客人想要進行雙人合盤分析！
                    - 第二位對象性別：{gender2}
                    - 第二位對象出生日期：{birth_date2}
                    - 第二位對象出生時間：{birth_time2}
                    - 雙方關係：{relation_type}
                    
                    請立即啟動『雙人合盤模式』，嚴格依據《三命通會》、《滴天髓》、《窮通寶鑑》的學理，分析：
                    1. 兩人的八字五行生剋制化與日主旺衰
                    2. 雙方性格的互補與衝突點
                    3. 針對【{relation_type}】給予具體的相處與發展建議
                    4. 採用『古籍學理 ＋ 大師白話註解』的雙軌格式輸出
                    """

            try:
                response = model.generate_content(prompt)
                st.success("分析完成！")
                st.markdown("### 📜 大師解析")
                st.write(response.text)
            except Exception as e:
                st.error(f"發生錯誤：{e}")

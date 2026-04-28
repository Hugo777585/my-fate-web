import streamlit as st

st.set_page_config(
    page_title="AI感情心理分析",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 AI感情心理分析")
st.write("這裡是 AI 感情心理分析頁面")

st.info("系統建置中")

if st.button("⬅️ 回到首頁"):
    st.switch_page("app.py")
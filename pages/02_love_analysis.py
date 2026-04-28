import streamlit as st

st.set_page_config(
    page_title="AI感情心理分析",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 AI感情心理分析")
st.caption("感情互動、關係卡關、訊息解讀與心理攻防分析")

st.markdown("""
### 這裡是第二層功能：AI感情心理分析

可提供：
- 對方心理想法分析
- 訊息對話解讀
- 曖昧／分手／復合卡關分析
- 兩人僵持不下的溝通建議
- 情緒整理與自我安定建議
""")

st.info("功能建置中，正式版即將開放。")

if st.button("回到首頁"):
    st.switch_page("app.py")
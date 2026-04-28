import streamlit as st

st.set_page_config(page_title="AI感情心理分析", page_icon="🧠")

st.title("🧠 AI 感情心理分析")
st.markdown("這是第二層感情心理分析測試頁。")

st.info("目前為測試版，先確認頁面能正常開啟。")

nickname = st.text_input("你的暱稱")
relationship = st.selectbox("目前關係狀態", ["曖昧", "交往中", "冷淡中", "分手後", "不確定"])
chat_text = st.text_area("請貼上對話內容", height=180)

if st.button("開始測試分析"):
    if not chat_text:
        st.warning("請先貼上對話內容")
    else:
        st.success("測試成功：第二層頁面可以正常運作。")
        st.markdown("""
        ### 基礎分析示範
        目前這段互動看起來，對方可能有情緒反應，但還需要更多脈絡才能判斷。

        若要進一步分析，可以升級深度方案。
        """)
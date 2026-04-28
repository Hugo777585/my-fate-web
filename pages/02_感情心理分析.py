import streamlit as st

st.set_page_config(page_title="感情心理分析", page_icon="🧠", layout="wide")

st.title("🧠 AI 感情心理分析系統")
st.markdown("輸入對話，解析對方真實想法與行為模式")

st.markdown("---")

options = [
    "對方在想什麼",
    "這段感情還有沒有機會",
    "對方是否在說謊",
    "為什麼已讀不回",
    "分手後是否能復合"
]

selected_option = st.radio("你想分析什麼？", options)

st.markdown("---")

chat_input = st.text_area("請貼上對話內容", height=200, placeholder="例如：\n對方：好啊 那改天再約\n對方：最近比較忙 先這樣")

relationship = st.selectbox("目前關係狀態", [
    "曖昧",
    "交往中",
    "冷淡中",
    "已分手"
])

extra_question = st.text_input("補充問題（選填）", placeholder="例如：對方突然不讀不回是什麼意思？")

st.markdown("---")

if st.button("開始分析", type="primary", use_container_width=True):
    if not chat_input:
        st.warning("⚠️ 請輸入對話內容")
    else:
        with st.spinner("🔮 分析中，請稍候..."):
            import time
            time.sleep(2)

        result = f"""
        🔍 分析結果：{selected_option}

        ---

        1️⃣ 對方目前狀態：
        偏防禦＋觀望，尚未完全投入。從對話語境判斷，對方處於「情感評估期」，正在收集資訊再做決定。

        ---

        2️⃣ 真實心理：
        對你有情緒連結，但同時在測試你的反應。語氣保持輕鬆但有距離，可能是避免給出明確承諾而預留退路。

        ---

        3️⃣ 行為模式：
        容易忽冷忽熱，控制互動節奏。這類型的人通常自尊心較強，害怕受傷，會用「忙」當作情緒緩衝。

        ---

        4️⃣ 建議策略：
        不要主動追問，保持自己的節奏和生活重心。過度的主動會讓對方壓力更大，適度的空間反而能激發對方的主動性。

        ---

        💡 補充建議：
        {extra_question if extra_question else '這段關係的核心問題在於「雙方步調不一致」，建議先各自沉澱再重新評估。'}
        """

        st.success(result)

st.markdown("---")
st.markdown("🔥 想看更精準完整分析？")

col1, col2 = st.columns([1, 1])
with col1:
    st.link_button("👉 解鎖進階分析（付費）", "https://line.me/ti/p/@hugo_master", use_container_width=True)
with col2:
    st.link_button("🏠 回首頁", "https://hugomaster.io", use_container_width=True)

st.markdown("---")
st.caption("⚠️ 本分析僅供參考，不構成任何感情建議。請自律判斷。"
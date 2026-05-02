import streamlit as st
from openai import OpenAI
import datetime
import os
import json
from dotenv import load_dotenv

load_dotenv()
openai_key = st.secrets.get("OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")

if not openai_key:
    st.error("尚未設定 OPENAI_API_KEY，請先到 Streamlit Cloud Secrets 加入金鑰。")
    st.stop()

client = OpenAI(api_key=openai_key)

def ai_love_consult_reply(context_prompt):
    """
    優化後的 AI 感情心理諮詢回覆函數 (測量表專用版)
    """
    system_role = """你是一位結合兩性關係心理學與實戰策略的資深顧問。
請根據使用者的測量表分數指標（依附強度、對方投入、關係風險）以及文字描述，進行精準的深度分析。

分析要求：
1. 語氣：沉穩、具備洞察力、有同理心，但不過度感性，要點出核心問題。
2. 結構：
   - 【關係類型】：定義目前這段互動屬於哪種心理狀態。
   - 【對方可能心理】：分析對方的行為動機與潛在心態。
   - 【關係卡點】：點出目前雙方最核心的矛盾或阻礙。
   - 【風險預測】：預測若維持現狀，未來的走向與潛在危機。
   - 【核心卡住點】：針對使用者個人，分析他目前在心理上真正過不去的地方。
   - 【下一步行動暗示】：給予一個方向性的引導，但不直接給完整執行清單。

❌ 禁止鐵口直斷，禁止出現商業或引流字眼。
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": context_prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 諮詢暫時無法連線：{str(e)}"

st.set_page_config(
    page_title="兩性關係心理測量｜雨果天命智庫",
    page_icon="🧠",
    layout="wide"
)

# CSS 注入 (大師護眼風格)
st.markdown("""
<style>
    .stApp { background-color: #e6e9ef; color: #2d3436; }
    [data-testid="stSidebar"] { background-color: #f8f9fa; border-right: 1px solid #dcdde1; }
    div[data-testid="stVerticalBlock"] > div {
        background-color: white; padding: 20px; border-radius: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px;
    }
    h1, h2, h3 { color: #2d3436 !important; border-left: 6px solid #6c5ce7; padding-left: 15px; }
    .stRadio > label { font-weight: 600; font-size: 1.1em; color: #4a235a; margin-bottom: 10px; }
    .stButton>button {
        background: linear-gradient(135deg, #8E44AD, #A569BD);
        color: white; font-weight: 700; border-radius: 12px; border: none;
        padding: 0.8em 2em; width: 100%; box-shadow: 0 4px 15px rgba(142, 68, 173, 0.4);
    }
</style>
""", unsafe_allow_html=True)

st.title("🧠 兩性關係心理測量表")
st.write("請根據您與對方目前的真實互動狀況，選擇最符合的程度（1分：完全不符合 ～ 5分：完全符合）")

# --- 測量表問題定義 ---
questions = [
    # A 情感依附
    {"cat": "A", "q": "1. 我會頻繁地檢查對方的社群動態或最後上線時間。"},
    {"cat": "A", "q": "2. 當對方沒有即時回覆訊息時，我會感到非常焦慮或不安。"},
    {"cat": "A", "q": "3. 我覺得我的人生中心目前大多圍繞在對方身上。"},
    {"cat": "A", "q": "4. 我很難想像失去這段關係後的生活會是什麼樣子。"},
    {"cat": "A", "q": "5. 我願意為了迎合對方的喜好而改變自己的行為或計畫。"},
    # B 對方投入
    {"cat": "B", "q": "6. 對方會主動安排兩人的約會或見面行程。"},
    {"cat": "B", "q": "7. 對方在忙碌之餘也會撥出時間主動聯繫我。"},
    {"cat": "B", "q": "8. 對方願意跟我分享他生活中的細節或內心的感受。"},
    {"cat": "B", "q": "9. 對方會主動關心我的情緒變化或生活狀況。"},
    {"cat": "B", "q": "10. 在這段關係中，我覺得對方付出的心力跟我差不多。"},
    # C 穩定度
    {"cat": "C", "q": "11. 我們的互動頻率非常穩定，不會突然消失或斷聯。"},
    {"cat": "C", "q": "12. 我們對於未來的規劃或想法有一定的共識。"},
    {"cat": "C", "q": "13. 我們遇到衝突時，能冷靜溝通並達成共識。"},
    {"cat": "C", "q": "14. 我覺得這段關係給我很強的安全感與信任感。"},
    {"cat": "C", "q": "15. 我們的關係狀態非常明確，身邊的人都知道我們的關係。"},
    # D 失衡
    {"cat": "D", "q": "16. 我覺得在這段關係中，我總是那個主動退讓或遷就的人。"},
    {"cat": "D", "q": "17. 當我表達不滿時，對方往往會避而不談或指責我太敏感。"},
    {"cat": "D", "q": "18. 我覺得我在這段關係中的情緒價值大多來自於對方的回應。"},
    {"cat": "D", "q": "19. 我覺得我比對方更害怕這段關係結束。"},
    {"cat": "D", "q": "20. 對方在做決定時，很少會先考慮到我的感受。"},
    # E 曖昧風險
    {"cat": "E", "q": "21. 我們的關係目前還沒有明確的定義（如：還在曖昧期）。"},
    {"cat": "E", "q": "22. 我不確定對方身邊是否還有其他曖昧對象。"},
    {"cat": "E", "q": "23. 對方偶爾會說出一些承諾，但很少實際做到。"},
    {"cat": "E", "q": "24. 當我試圖確認關係時，對方會採取模糊或逃避的態度。"},
    {"cat": "E", "q": "25. 我們雖然有親密互動，但感覺不到長期的承諾。"},
    # F 拉扯動態
    {"cat": "F", "q": "26. 我們目前的互動像是一場心理博弈，誰先主動誰就輸了。"},
    {"cat": "F", "q": "27. 我會刻意晚一點回訊息，好讓自己看起來沒那麼在意。"},
    {"cat": "F", "q": "28. 我們的互動節奏忽冷忽熱，充滿了試探。"},
    {"cat": "F", "q": "29. 我覺得我需要透過某些行為（如：發動態）來引起對方的注意。"},
    {"cat": "F", "q": "30. 我們的關係中存在著一種「誰比較在乎誰」權力拉扯。"}
]

# --- 渲染測量表 ---
scores = {}
with st.form("relationship_scale"):
    for item in questions:
        scores[item['q']] = {
            "cat": item['cat'],
            "val": st.radio(item['q'], [1, 2, 3, 4, 5], horizontal=True, index=2)
        }
    
    st.markdown("### 📝 感情現況描述")
    user_description = st.text_area(
        "請描述你目前的感情狀況、最近發生的事、最在意的點、最想知道的問題",
        placeholder="例如：我們最近冷戰了一週，對方突然不讀不回，我很擔心他是不是想分手...",
        height=200
    )
    
    submit_btn = st.form_submit_button("✨ 開始 AI 感情心理分析")

# --- 分析邏輯 ---
if submit_btn:
    if not user_description.strip():
        st.warning("⚠️ 請填寫「感情現況描述」，大師才能為您進行精準分析喔！")
    else:
        # 1. 計算指標
        sum_A = sum(v['val'] for v in scores.values() if v['cat'] == 'A')
        sum_B = sum(v['val'] for v in scores.values() if v['cat'] == 'B')
        sum_C = sum(v['val'] for v in scores.values() if v['cat'] == 'C')
        sum_D = sum(v['val'] for v in scores.values() if v['cat'] == 'D')
        sum_E = sum(v['val'] for v in scores.values() if v['cat'] == 'E')
        sum_F = sum(v['val'] for v in scores.values() if v['cat'] == 'F')
        
        # 指標計算
        attachment_strength = sum_A
        partner_investment = sum_B + sum_C
        relationship_risk = sum_D + sum_E + sum_F
        
        with st.spinner("正在進行深度心理剖析..."):
            # 2. 構建 Prompt
            context_prompt = f"""
【測量表指標結果】
- 依附強度 (A)：{attachment_strength} / 25
- 對方投入 (B+C)：{partner_investment} / 50
- 關係風險 (D+E+F)：{relationship_risk} / 75

【使用者文字描述】
{user_description}
"""
            # 3. 呼叫 AI
            result = ai_love_consult_reply(context_prompt)
            
            # 4. 顯示結果
            st.markdown("---")
            st.markdown(result)
            
            # 5. 自然引導與 CTA
            st.markdown("""
---
### 🔮 延伸建議

如果你想知道接下來該**主動、等待，還是收回**，我可以再幫你往下拆完整策略。

👇 這一步，會決定這段關係接下來的走向
""")
            st.link_button("👉 加 LINE 直接看完整分析", "https://line.me/ti/p/@323ohobf", use_container_width=True)

if st.button("⬅️ 回到首頁"):
    st.switch_page("app.py")

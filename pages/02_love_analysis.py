import streamlit as st
from openai import OpenAI
import datetime
import os
import json
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
openai_key = st.secrets.get("OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")

if not openai_key:
    st.error("尚未設定 OPENAI_API_KEY，請先到 Streamlit Cloud Secrets 加入金鑰。")
    st.stop()

client = OpenAI(api_key=openai_key)

def generate_free_reply(event, wish, attitude):
    return f"""
### 📜 AI 感情初步掃描（免費版）

從你描述的狀況來看，這段關係目前不是單純的「有沒有感情」可以判斷，而是已經進入一種比較微妙的拉扯狀態。

你在意的是「{wish}」，而對方目前呈現出來的態度是「{attitude}」。這代表你感受到的不是單一事件的問題，而是對方的回應方式、距離感與情緒節奏，開始讓你產生不確定感。這種不確定，往往比直接拒絕更消耗人，因為它會讓你一直想確認、一直想找線索。

目前比較值得注意的是，你們之間可能已經出現「一方想靠近，一方卻沒有穩定接住」的狀態。對方不一定完全沒有感覺，但他的反應未必能給你足夠安全感。這也是為什麼你會反覆想知道：他到底是在觀察、試探、退後，還是只是享受被在意的感覺。

真正讓你卡住的，可能不是這件事本身，而是你還沒辦法確定下一步該怎麼做。太主動，怕自己失去位置；太冷淡，又怕錯過可能性。所以你現在最需要的不是立刻下結論，而是先看清楚這段互動裡，哪一部分是對方造成的，哪一部分是你被不安牽著走。

免費版先幫你看到這裡：這段關係目前的核心，不是單純追或不追，而是「你下一步怎麼回應，會直接影響對方後面的態度」。

如果你想知道接下來怎麼做比較不會把關係推遠，我可以再幫你往下拆。
"""

def ai_love_consult_reply(context_prompt):
    system_role = """你是一位結合兩性關係心理學與實戰策略的資深顧問。
請根據使用者的測量表分數指標以及文字描述，進行精準的深度分析。
分析要求：語氣沉穩、具備洞察力、有同理心，點出核心問題。
結構：關係類型、對方可能心理、關係卡點、風險預測、核心卡住點、下一步行動暗示。
❌ 禁止鐵口直斷，禁止出現商業或引流字眼。"""
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
    page_title="兩性情感心理諮詢｜雨果天命智庫",
    page_icon="🧠",
    layout="wide"
)

# --- 初始化狀態 ---
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'show_report' not in st.session_state:
    st.session_state.show_report = False

# CSS 注入 (優化手機版與高級感)
st.markdown("""
<style>
    .stApp { background-color: #e6e9ef; color: #2d3436; }
    
    /* 頂部主視覺卡片 */
    .hero-card {
        background: linear-gradient(135deg, #fce4ec 0%, #f3e5f5 100%);
        padding: 40px 20px;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.05);
    }
    .hero-title { color: #4a235a; font-size: 2.2em; font-weight: 800; margin-bottom: 10px; }
    .hero-subtitle { color: #6c5ce7; font-size: 1.2em; font-weight: 600; margin-bottom: 20px; }
    .hero-text { color: #2d3436; font-size: 1.1em; line-height: 1.6; max-width: 800px; margin: 0 auto; }

    /* 通用卡片樣式 */
    div[data-testid="stVerticalBlock"] > div {
        background-color: white; padding: 20px; border-radius: 16px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05); margin-bottom: 20px;
    }
    
    /* 標題樣式 */
    h1, h2, h3 { color: #2d3436 !important; border-left: 6px solid #6c5ce7; padding-left: 15px; }

    /* 按鈕優化 */
    .stButton>button {
        background: linear-gradient(135deg, #8E44AD, #A569BD);
        color: white; font-weight: 700; border-radius: 12px; border: none;
        padding: 1em 2em; width: 100%; font-size: 1.1em;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(142, 68, 173, 0.4); }

    /* 手機版適應 */
    @media (max-width: 600px) {
        .hero-title { font-size: 1.6em; }
        .hero-text { font-size: 1em; }
        div[data-testid="column"] { margin-bottom: 15px; }
    }

    /* 鎖定區塊樣式 */
    .locked-card {
        background: #f1f2f6; border: 2px dashed #6c5ce7; padding: 25px;
        border-radius: 16px; text-align: center; color: #2d3436;
    }
    
    /* 表格滑動優化 */
    .stTable { overflow-x: auto; display: block; }
</style>
""", unsafe_allow_html=True)

# --- 一、頂部動態導引 (Slides) ---
slides = [ 
    { 
        "title": "你現在卡住的，不是感情", 
        "desc": "而是你不知道\n他到底在想什麼", 
        "color": "#6C5CE7" 
    },           { 
        "title": "你是不是也這樣？", 
        "desc": "忽冷忽熱、已讀不回\n越想越亂、越做越錯", 
        "color": "#A29BFE" 
    },             { 
        "title": "多數人會做錯的事", 
        "desc": "拼命問、情緒爆、想確認關係\n結果反而把人推走", 
        "color": "#FD79A8" 
    },          { 
        "title": "這裡不只是聊天", 
        "desc": "我們用三個維度分析\n命盤 × 行為 × 心理", 
        "color": "#00B894" 
    },          { 
        "title": "你會看到的是", 
        "desc": "關係數據分析\n心理模型判讀\n行動策略建議", 
        "color": "#0984E3" 
    },         { 
        "title": "不是算命，是決策", 
        "desc": "看清關係\n再決定你要不要繼續", 
        "color": "#2D3436" 
    } 
]

if "slide_index" not in st.session_state: 
    st.session_state.slide_index = 0 

slide = slides[st.session_state.slide_index] 

st.markdown(f""" 
<div style=" 
background: {slide['color']}; 
padding: 40px; 
border-radius: 20px; 
text-align: center; 
color: white; 
min-height: 220px; 
display: flex; 
flex-direction: column; 
justify-content: center; 
box-shadow: 0 10px 30px rgba(0,0,0,0.1);
margin-bottom: 20px;
"> 
    <h2 style="color: white !important; border: none !important; padding: 0 !important;">{slide['title']}</h2> 
    <p style="font-size:18px; white-space: pre-line;"> 
    {slide['desc']} 
    </p> 
</div> 
""", unsafe_allow_html=True) 

col_nav1, col_nav2, col_nav3 = st.columns([1,2,1]) 

with col_nav1: 
    if st.button("⬅️", use_container_width=True): 
        st.session_state.slide_index = max(0, st.session_state.slide_index - 1) 
        st.rerun()

with col_nav3: 
    if st.button("➡️", use_container_width=True): 
        st.session_state.slide_index = min(len(slides)-1, st.session_state.slide_index + 1)
        st.rerun()

st.markdown("### 👇 開始你的感情心理分析")
st.link_button("👉 加 LINE 免費諮詢", "https://line.me/ti/p/@323ohobf", use_container_width=True)

# --- 二、分析模型說明區 ---
st.markdown("### 🛡️ 分析模型說明")
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.info("**命盤結構**\n長期關係模式、感情慣性、吸引與衝突點")
with col_m2:
    st.info("**互動行為**\n訊息反應、冷熱變化、關係主導權")
with col_m3:
    st.info("**心理狀態**\n依附類型、防禦模式、真實投入程度")

st.markdown("---")

# --- 三、表單區 ---
st.header("� 描述目前感情狀況")
with st.container():
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        event = st.text_area("1. 目前發生什麼事？", placeholder="請簡述目前的狀況...", height=150)
        key_events = st.text_area("2. 關鍵事件補充", placeholder="是否有什麼特別的轉折點或事件？", height=100)
    with col_f2:
        wish = st.selectbox("3. 你最想知道的是？", [
            "對方在想什麼", "這段關係還有沒有機會", "我現在該怎麼做", "要不要繼續這段關係"
        ])
        attitude = st.selectbox("4. 對方目前態度？", [
            "熱情", "冷淡", "忽冷忽熱", "逃避", "曖昧不明"
        ])
    
    user_question = st.text_area(
        "5. 請輸入你想進一步追問的感情問題",
        placeholder="例如：他為什麼突然不讀不回？我該主動傳訊息給他嗎？",
        height=150
    )

    if st.button("✨ 產生感情心理分析報告", use_container_width=True):
        if not user_question.strip():
            st.warning("⚠️ 請先輸入想分析的感情問題")
        else:
            with st.spinner("正在生成深度心理分析報告..."):
                # 模擬 AI 文字分析
                context_prompt = f"狀況：{event}\n願望：{wish}\n態度：{attitude}\n追問：{user_question}"
                st.session_state.analysis_result = generate_free_reply(event, wish, attitude)
                st.session_state.show_report = True
                st.rerun()

# --- 四、分析報表區 ( st.button 執行後顯示 ) ---
if st.session_state.show_report:
    st.markdown("---")
    st.header("📊 關係核心數據儀表板")
    
    # 五、關係核心數據
    col_d1, col_d2, col_d3, col_d4 = st.columns(4)
    with col_d1:
        st.metric("💗 關係穩定度", "65%", "較上週 +5%")
        st.progress(0.65)
    with col_d2:
        st.metric("🔥 對方投入度", "40%", "-2%", delta_color="inverse")
        st.progress(0.40)
    with col_d3:
        st.metric("⚖️ 互動失衡指數", "78%", "高危", delta_color="inverse")
        st.progress(0.78)
    with col_d4:
        st.metric("💬 溝通順暢度", "52%", "+10%")
        st.progress(0.52)

    # 六、關係類型判定
    st.markdown("### 🔍 關係類型判定")
    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        st.success("**依附關係**\n焦慮拉扯型")
    with col_t2:
        st.success("**關係階段**\n曖昧觀察期")
    with col_t3:
        st.success("**衝突風格**\n壓抑累積型")
    st.write("> 這代表目前關係不是完全沒有情感，而是進入「不確定與防禦並存」階段。")

    # 七、戀愛週期圖
    st.markdown("### � 戀愛週期走勢")
    chart_data = pd.DataFrame({
        "階段": ["甜蜜期", "磨合期", "衝突期", "冷淡期", "修復期"],
        "情感強度": [90, 70, 50, 35, 60]
    }).set_index("階段")
    st.line_chart(chart_data)
    st.caption("這張圖用來判斷目前關係大概落在哪個階段，並不是絕對結果，而是輔助使用者理解互動變化。")

    # 八、依附類型分析
    st.markdown("### 🧬 依附類型分析")
    col_a1, col_a2 = st.columns([2, 1])
    with col_a1:
        st.write("安全型 (30%)")
        st.progress(0.30)
        st.write("焦慮型 (45%)")
        st.progress(0.45)
        st.write("逃避型 (25%)")
        st.progress(0.25)
    with col_a2:
        st.info("目前使用者較容易在不確定中放大情緒，而對方可能透過退後、觀察或冷處理來保護自己。")

    # 九、行動影響對照表
    st.markdown("### 🧭 行動策略對照表")
    strategy_data = {
        "你的行動": ["主動追問", "暫停聯絡", "輕鬆互動", "情緒攤牌"],
        "可能結果": ["對方壓力上升", "對方開始觀察", "關係回溫機率提高", "容易造成防禦"],
        "建議程度": ["🚫 不建議", "⚠️ 可觀察", "✅ 建議", "🚨 高風險"]
    }
    st.table(pd.DataFrame(strategy_data))

    # 十、風險雷區
    st.markdown("### ⚠️ 目前最需要避開的雷區")
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.error("**過度追問**\n會讓對方覺得壓力變大")
    with col_r2:
        st.error("**情緒施壓**\n容易造成冷處理或逃避")
    with col_r3:
        st.error("**太快確認關係**\n會破壞目前微妙平衡")

    # 十一、AI文字分析區
    st.markdown("### 🧠 AI 初步心理判讀")
    st.markdown(st.session_state.analysis_result)

    # 十二、進階內容鎖定區
    st.markdown(f"""
<div class="locked-card">
    <h3>🔒 以下關鍵分析已鎖定</h3>
    <p>・對方真正沒有說出口的想法</p>
    <p>・這段關係是否還有機會</p>
    <p>・你下一步最適合的做法</p>
    <p>・如果做錯，可能造成什麼後果</p>
    <p>・適合主動、等待，還是收回</p>
    <br>
    <p>免費版會協助你看見目前狀態。如果你想知道「下一步怎麼做」，建議進一步分析。</p>
</div>
""", unsafe_allow_html=True)

    # 十三、LINE引流區
    st.markdown("---")
    st.subheader("📩 不想只靠 AI 判斷？")
    st.markdown("""
你可以加 LINE，讓我親自幫你看完整狀況。  
**適合：**  
✔ 想知道對方真實想法 | ✔ 想知道該不該主動  
✔ 想挽回但怕做錯 | ✔ 想確認這段關係還有沒有機會
""")
    st.link_button("👉 加 LINE 免費諮詢", "https://line.me/ti/p/@323ohobf", use_container_width=True)

    # 十四、回訪機制
    st.warning("""
**📌 建議 3 天後再回來重新分析**  
因為感情狀態會隨著互動改變，不同時間點的判斷也會不同。
""")

if st.button("⬅️ 回到首頁"):
    st.switch_page("app.py")

import streamlit as st
from openai import OpenAI
import datetime
import os
import csv
from dotenv import load_dotenv

load_dotenv()
openai_key = st.secrets.get("OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")

if not openai_key:
    st.error("尚未設定 OPENAI_API_KEY，請先到 Streamlit Cloud Secrets 加入金鑰。")
    st.stop()

client = OpenAI(api_key=openai_key)

def ai_love_consult_reply(context_prompt, is_master=False):
    """
    第二層 AI 感情心理諮詢回覆函數 (優化轉單版)
    """
    system_role = """你是一位結合命理分析、感情心理諮詢與關係策略的顧問。請用沉穩、理性、具同理心的方式分析，像是在理解人、有洞察力。不要鐵口直斷，不要恐嚇使用者。"""
    
    # 根據權限調整輸出要求
    if is_master:
        permission_instruction = """
【大師模式：完整分析】
請提供完整深度分析，不限制字數，包含：
1. 對方目前真實心理狀態
2. 目前關係的核心卡點
3. 使用者內心真正不安的核心
4. 具體建議採取的做法（實戰策略）
5. 絕對不建議做的事
6. 潛在風險提醒
7. 明確的下一步行動建議
"""
    else:
        permission_instruction = """
【一般模式：初步引導】
請嚴格遵守以下三段式結構，字數約 300～500 字：
1. ① 對方心理：描述對方的心理狀態，要準確且有畫面感。
2. ② 關係卡點：點出關係中讓使用者產生共鳴的阻礙。
3. ③ 方向指引：給予一點點處理方向，但務必保留「關鍵沒說破」，創造好奇感。

❌ 禁止出現「購買」、「方案」、「價格」等商業字眼。
"""

    full_prompt = f"{system_role}\n\n{context_prompt}\n{permission_instruction}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": full_prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 諮詢暫時無法連線：{str(e)}"

st.set_page_config(
    page_title="AI感情心理分析",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 AI感情心理分析")

# CSS 注入 (與 app.py 同步)
st.markdown("""
<style>
    .plan-card {
        background: white;
        border: 2px solid #E0E0E0;
        border-radius: 20px;
        padding: 30px;
        text-align: center;
        transition: all 0.3s ease;
        height: 100%;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }
    .plan-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 12px 30px rgba(108, 52, 131, 0.15);
    }
    .plan-card.popular {
        border: 3px solid #A569BD;
        background: linear-gradient(180deg, #FFFFFF 0%, #F5EEF8 100%);
        position: relative;
    }
    .popular-badge {
        position: absolute;
        top: -15px;
        left: 50%;
        transform: translateX(-50%);
        background: #A569BD;
        color: white;
        padding: 4px 15px;
        border-radius: 20px;
        font-size: 0.8em;
        font-weight: 700;
        letter-spacing: 1px;
        z-index: 10;
    }
    .plan-title {
        font-size: 1.5em;
        font-weight: 800;
        color: #4A235A;
        margin-bottom: 10px;
    }
    .plan-price {
        font-size: 2.2em;
        font-weight: 900;
        color: #6C3483;
        margin-bottom: 20px;
    }
    .plan-price span {
        font-size: 0.5em;
        color: #7B7B7B;
        font-weight: 400;
    }
    .plan-features {
        text-align: left;
        margin-bottom: 25px;
        list-style: none;
        padding: 0;
    }
    .plan-features li {
        margin-bottom: 12px;
        color: #4D5656;
        font-size: 0.95em;
        display: flex;
        align-items: center;
    }
    .plan-features li:before {
        content: "✅";
        margin-right: 10px;
        font-size: 0.8em;
    }
    .plan-features li.locked {
        color: #ABB2B9;
    }
    .plan-features li.locked:before {
        content: "🔒";
    }
    .stButton>button {
        background: linear-gradient(135deg, #8E44AD, #A569BD);
        color: white;
        font-weight: 700;
        font-size: 1.1em;
        padding: 0.6em 2em;
        border-radius: 12px;
        border: none;
        box-shadow: 0 4px 15px rgba(142, 68, 173, 0.4);
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #9B59B6, #BB8FCE);
        box-shadow: 0 6px 20px rgba(142, 68, 173, 0.5);
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

# --- 初始化狀態 ---
if 'payment_status' not in st.session_state:
    st.session_state.payment_status = "free"
if 'order_data' not in st.session_state:
    st.session_state.order_data = None
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None

# --- 模擬 AI 回覆生成函數 ---
def generate_free_reply(event, wish, attitude):
    return f"""
    ### 📜 AI 感情初步掃描 (免費版)
    
    「從你描述的狀況來看，這段關係目前比較像是**互動節奏失衡**。
    你在意的是『{wish}』，但對方目前表現出的『{attitude}』態度，代表他可能正在退後或觀察。
    這裡如果處理錯，容易變成你越追，對方越冷。」
    
    ---
    「今年在感情與人際上會出現變動， 
    特別是在某些月份容易產生誤解或衝突。」 
    """
    

def generate_299_reply(event, wish, attitude):
    return f"""
    ### 📜 AI 感情深度分析 (299 深度版)
    
    **1. 對方目前可能心態：**
    對方的『{attitude}』並非完全無情，而是處於一種「心理防禦」狀態。他可能在擔心這段關係發展太快會導致失控。
    
    **2. 你們目前卡住的核心原因：**
    核心在於「信任厚度」不足。當你試圖確認『{wish}』時，會觸發對方的逃避機制。
    
    **3. 你現在的位置：**
    目前處於「觀察期」。如果能在接下來的 5 天內保持情緒穩定，局勢將會好轉。
    
    **4. 基本應對方向：**
    建議採取「後撤一步，增加神秘感」的策略。不要主動確認關係，而是引導對方主動聯繫。
    
    ---
    📌 **服務資訊：**
    - 剩餘提問次數：3 次
    - 有效期限：5 天
    """

def generate_699_reply(event, wish, attitude):
    return f"""
    ### 📜 AI 感情完整決策報告 (699 完整版)
    
    **1. 對方心態完整解析：**
    對方表現出的『{attitude}』其實是「試探」。他內心深處對你有 75% 的好感，但其本命盤中的某個隱藏特質（如：偏印奪食）讓他習慣性地在靠近時推開他人。
    
    **2. 關係未來走向：**
    若按照目前「越追越冷」的慣性，三個月內關係會徹底進入冰點。但若能調整互動節奏，下個月將迎來「合盤感應期」，是升溫的關鍵點。
    
    **3. 你現在該進、退、停、觀察：**
    **【退】。** 立刻停止一切詢問式、索取式對話。
    
    **4. 下一步具體做法：**
    三天內不要傳訊息。第四天晚上 8 點左右，傳送一則與感情無關、僅分享生活趣事的訊息。
    
    **5. 可使用的對話建議：**
    「今天路過那家店發現...，突然想到你上次說過的...，感覺蠻有趣的。」
    
    ---
    📌 **服務資訊：**
    - 剩餘提問次數：5 次
    - 有效期限：6 天
    - **大師服務：** Hugo 大師已接收您的資料，將針對您的狀況親自回覆。
    """

# --- 訂單處理邏輯 (與 app.py 同步) ---
def save_order_to_csv(order_info):
    file_exists = os.path.isfile('orders.csv')
    with open('orders.csv', mode='a', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['order_id', 'created_at', 'name', 'contact', 'phone', 'birth_date', 'birth_time', 'gender', 'question', 'plan', 'payment_status'])
        writer.writerow([
            order_info['order_id'],
            order_info['created_at'],
            order_info['name'],
            order_info['contact'],
            order_info['phone'],
            order_info['birth_date'],
            order_info['birth_time'],
            order_info['gender'],
            order_info['question'],
            order_info['plan'],
            order_info['payment_status']
        ])

# --- 感情狀況輸入區 ---
st.header("💞 描述您的感情狀況")

with st.container():
    col_input1, col_input2 = st.columns(2)
    with col_input1:
        event_happening = st.text_area("1. 目前發生什麼事？", placeholder="請簡述目前的狀況...", height=150)
        key_events = st.text_area("2. 關鍵事件補充", placeholder="是否有什麼特別的轉折點或事件？", height=100)
    
    with col_input2:
        wish_to_know = st.selectbox("3. 你最想知道的是？", [
            "對方在想什麼", 
            "這段關係還有沒有機會", 
            "我現在該怎麼做", 
            "要不要繼續這段關係"
        ])
        partner_attitude = st.selectbox("4. 對方目前態度？", [
            "熱情", 
            "冷淡", 
            "忽冷忽熱", 
            "逃避", 
            "曖昧不明"
        ])

# --- 分析執行邏輯 ---
st.markdown("<br>", unsafe_allow_html=True)

love_question = st.text_area(
    "請輸入你想進一步追問的感情問題",
    placeholder="例如：他為什麼突然不讀不回？我該主動傳訊息給他嗎？",
    key="love_question"
)

if st.button("✨ 開始 AI 感情心理分析", use_container_width=True):
    if not love_question.strip():
        st.warning("請先輸入想分析的感情問題")
    elif not event_happening:
        st.warning("⚠️ 請先填寫「目前發生什麼事」，大師才能為您分析喔！")
    else:
        with st.spinner("正在進行感情心理分析..."):
            try:
                # 建立 AI 分析用的 Prompt
                context_prompt = f"""
【使用者描述的現況】
1. 目前發生什麼事：{event_happening}
2. 關鍵事件補充：{key_events}
3. 使用者最想知道的是：{wish_to_know}
4. 對方目前的態度：{partner_attitude}
5. 針對此狀況的具體追問：{love_question}
"""
                # 目前統一使用一般模式，或根據需求調整
                is_master = False 
                
                # 呼叫 AI 函數
                result = ai_love_consult_reply(context_prompt, is_master)
                
                # 儲存結果到 session_state 以便持久顯示
                st.session_state.analysis_result = result
                st.rerun()

            except Exception as e:
                st.error(f"AI 分析失敗：{e}")

# --- 顯示分析結果 (持久化) ---
if st.session_state.analysis_result:
    st.markdown("---")
    st.markdown(st.session_state.analysis_result)

    # --- 加入自然引導文案 ---
    st.markdown("""
### 🔮 延伸分析｜感情心理解析 

很多時候，真正讓人放不下的， 
不是發生了什麼， 
而是你始終看不懂「對方現在到底在想什麼」。 

你可能會開始反覆想： 

👉 他現在對我是認真的，還是只是剛好有人陪？ 
👉 這段關係，還有沒有機會走下去？ 
👉 我現在該主動，還是該慢慢退？ 

HUGO 天命智庫會透過： 

**八字命盤 × 關係互動 × 心理狀態** 

幫你把「現在這段關係的真實狀態」拆開來看。 

👉 如果你想進一步看清這段關係，可以加 LINE 做完整分析。 
""")
    st.link_button("👉 加 LINE 進一步諮詢", "https://line.me/ti/p/@323ohobf", use_container_width=True)

if st.button("⬅️ 回到首頁"):
    st.switch_page("app.py")
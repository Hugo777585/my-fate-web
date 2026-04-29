import streamlit as st
import datetime
import os
import csv

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
    ⚠️ **以上為初步情緒與狀況理解。**
    目前的分析只幫你看清楚了「卡在哪裡」，但還沒有揭露對方的真實心態與具體做法。
    
    💡 **建議：** 若想主導結果，建議參考下方的 **299 深度解說** 或 **699 完整決策分析**。
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
        analysis_scheme = st.radio("5. 選擇分析方案：", [
            "免費初步分析", 
            "299 深度分析", 
            "699 完整分析"
        ], horizontal=True)

# --- 分析執行邏輯 ---
st.markdown("<br>", unsafe_allow_html=True)
if st.button("✨ 開始 AI 感情心理分析", use_container_width=True):
    if not event_happening:
        st.warning("⚠️ 請先填寫「目前發生什麼事」，大師才能為您分析喔！")
    else:
        try:
            if analysis_scheme == "免費初步分析":
                st.session_state.analysis_result = generate_free_reply(event_happening, wish_to_know, partner_attitude)
                st.session_state.payment_status = "free"
            
            elif analysis_scheme == "299 深度分析":
                # 檢查是否已付費
                if st.session_state.payment_status == "paid_299" or st.session_state.payment_status == "paid_699":
                    st.session_state.analysis_result = generate_299_reply(event_happening, wish_to_know, partner_attitude)
                else:
                    st.session_state.temp_pay_plan_love = "paid_299"
                    st.session_state.analysis_result = None # 先不顯示結果
                    st.info("💡 您選擇了 299 深度分析，請先完成下方訂單以解鎖內容。")

            elif analysis_scheme == "699 完整分析":
                # 檢查是否已付費
                if st.session_state.payment_status == "paid_699":
                    st.session_state.analysis_result = generate_699_reply(event_happening, wish_to_know, partner_attitude)
                else:
                    st.session_state.temp_pay_plan_love = "paid_699"
                    st.session_state.analysis_result = None # 先不顯示結果
                    st.info("💡 您選擇了 699 完整分析，請先完成下方訂單以解鎖內容。")
        except Exception as e:
            st.error(f"❌ 執行分析時發生錯誤：{e}")

# --- 顯示分析結果 ---
if st.session_state.analysis_result:
    st.markdown("---")
    st.markdown('<div style="background-color: #FDFEFE; padding: 25px; border-radius: 15px; border-left: 5px solid #8E44AD; box-shadow: 0 4px 10px rgba(0,0,0,0.05);">', unsafe_allow_html=True)
    st.markdown(st.session_state.analysis_result)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # 免費版顯示付費引導
    if st.session_state.payment_status == "free":
        st.markdown("<br>", unsafe_allow_html=True)
        st.info("🔒 以上為初步分析。解鎖 299 或 699 方案可獲得更具體的對象心態與行動策略。")

# --- 方案展示與訂單區 ---
st.markdown("---")
st.subheader("🚀 選擇適合您的轉運方案")

# 這裡接續原本的方案展示卡片
col_plan1, col_plan2 = st.columns(2)

with col_plan1:
    st.markdown("""
    <div class="plan-card">
        <div class="plan-title">🥈 299 深度解說</div>
        <div class="plan-price">NT$ 299</div>
        <ul class="plan-features">
            <li>深入解析流年＋本命盤交互影響</li>
            <li>精準分析目前遇到的人與問題</li>
            <li>給予明確方向，解決目前困境的專屬解說</li>
        </ul>
        <p style="color: #6C3483; font-size: 0.9em; font-weight: 600; margin-top: 10px;">
            適合對象：「已經遇到問題，需要大師指引方向與解方的人」
        </p>
    </div>
    """, unsafe_allow_html=True)
    if st.session_state.payment_status == "paid_299":
        st.button("✅ 已解鎖", disabled=True, key="love_btn_299_active")
    elif st.session_state.payment_status == "paid_699":
        st.info("✨ 已包含在完整版")
    else:
        if st.button("🔓 解鎖 299 深度解說", key="love_btn_unlock_299"):
            st.session_state.temp_pay_plan_love = "paid_299"
            st.rerun()

with col_plan2:
    st.markdown("""
    <div class="plan-card popular">
        <div class="popular-badge">熱門推薦</div>
        <div class="plan-title">🥇 699 完整決策分析</div>
        <div class="plan-price">NT$ 699</div>
        <ul class="plan-features">
            <li>包含 299 所有深度解析內容</li>
            <li>不只解析，直接「幫您判斷與決策」</li>
            <li>結合命盤＋兩性心理 → 看透對方真實心態與局勢</li>
            <li>提供具體做法（給予明確的下一步行動策略）</li>
            <li><b>📌 可提問 3 次（由 Hugo 大師親自針對您的狀況回覆解答）</b></li>
        </ul>
        <p style="color: #6C3483; font-size: 0.9em; font-weight: 600; margin-top: 10px;">
            適合對象：「卡關混亂、想要明確答案，且需要大師親自為您解惑的人」
        </p>
    </div>
    """, unsafe_allow_html=True)
    if st.session_state.payment_status == "paid_699":
        st.button("✅ 已解鎖", disabled=True, key="love_btn_699_active")
    else:
        if st.button("🔓 解鎖 699 完整決策分析", key="love_btn_unlock_699"):
            st.session_state.temp_pay_plan_love = "paid_699"
            st.rerun()

# 模擬付款邏輯
if 'temp_pay_plan_love' in st.session_state:
    selected_plan_val = 299 if st.session_state.temp_pay_plan_love == "paid_299" else 699
    st.subheader(f"📝 建立訂單（{selected_plan_val} 方案）")
    
    lo_name = st.text_input("姓名")
    lo_contact = st.text_input("LINE ID 或 Email")
    lo_phone = st.text_input("手機 (選填)")
    lo_birth_date = st.date_input("出生年月日", value=datetime.date.today())
    lo_birth_time = st.text_input("出生時間 (例：08:20)")
    lo_gender = st.selectbox("性別", options=["男", "女"])
    lo_question = st.text_area("想諮詢的感情問題")
    
    if st.button("建立訂單", key="btn_create_order_love"):
        if not lo_name or not lo_contact:
            st.error("請填寫姓名與聯絡資訊")
        else:
            order_id = f"HUGO_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            order_info = {
                'order_id': order_id,
                'created_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'name': lo_name,
                'contact': lo_contact,
                'phone': lo_phone,
                'birth_date': str(lo_birth_date),
                'birth_time': lo_birth_time,
                'gender': lo_gender,
                'question': lo_question,
                'plan': selected_plan_val,
                'payment_status': 'unpaid'
            }
            st.session_state.order_data = order_info
            save_order_to_csv(order_info)
            st.success("訂單已建立！請加入LINE完成付款與分析")
            st.image(r"G:\AI下載\頭像\ChatGPT Image 2026年4月28日 下午11_50_51.png", use_container_width=True)
            st.json(st.session_state.order_data)

if st.session_state.order_data and st.session_state.order_data.get('payment_status') == 'unpaid':
    st.info("💳 **目前為測試模式**")
    st.write(f"您選擇了：{st.session_state.order_data['plan']} 方案")
    if st.button("✅ 確認付款完成並解鎖 (測試)", type="primary"):
        st.session_state.order_data['payment_status'] = 'test_paid'
        save_order_to_csv(st.session_state.order_data)
        
        st.session_state.payment_status = st.session_state.temp_pay_plan_love
        del st.session_state.temp_pay_plan_love
        st.success(f"🎉 付款成功！訂單編號 {st.session_state.order_data['order_id']} 已解鎖。")
        st.rerun()

# --- 顯示已付款內容 ---
if st.session_state.payment_status in ["paid_299", "paid_699"] and st.session_state.analysis_result:
    # 這裡的 analysis_result 已經在上面 generate 了
    pass
else:
    if st.session_state.payment_status == "free":
        pass
    else:
        st.info("🔒 付費解鎖後即可查看深度想法解析與行動建議")
        st.link_button(
            "👉 加入LINE解鎖完整分析",
            "https://line.me/ti/p/@258hnnao"
        )

if st.button("⬅️ 回到首頁"):
    st.switch_page("app.py")
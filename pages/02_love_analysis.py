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

# --- 初始化付款狀態 ---
if 'payment_status' not in st.session_state:
    st.session_state.payment_status = "free"
if 'order_data' not in st.session_state:
    st.session_state.order_data = None

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

st.write("這裡是 AI 感情心理分析頁面")

# 模擬分析按鈕
if st.button("開始 AI 模擬分析"):
    st.info("分析中...")
    st.success("分析完成！")
    
    st.markdown("---")
    st.subheader("🚀 升級您的感情解析報告")
    
    # 方案顯示
    col_plan1, col_plan2, col_plan3 = st.columns(3)
    
    with col_plan1:
        st.markdown("""
        <div class="plan-card">
            <div class="plan-title">🥉 免費版</div>
            <div class="plan-price">NT$ 0</div>
            <ul class="plan-features">
                <li>基礎感情分析</li>
                <li class="locked">對方真實想法解析</li>
                <li class="locked">具體行動建議指引</li>
                <li class="locked">PDF 完整報告</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.payment_status == "free":
            st.button("目前方案", disabled=True, key="love_btn_free")
        else:
            if st.button("切換回免費版", key="love_btn_switch_free"):
                st.session_state.payment_status = "free"
                st.rerun()

    with col_plan2:
        st.markdown("""
        <div class="plan-card popular">
            <div class="popular-badge">熱門推薦</div>
            <div class="plan-title">🥈 299 深度版</div>
            <div class="plan-price">NT$ 299</div>
            <ul class="plan-features">
                <li>基礎感情分析</li>
                <li><b>對方真實想法解析</b></li>
                <li><b>具體行動建議指引</b></li>
                <li class="locked">PDF 下載權限</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.payment_status == "paid_299":
            st.button("✅ 已解鎖", disabled=True, key="love_btn_299_active")
        elif st.session_state.payment_status == "paid_699":
            st.info("✨ 已包含在完整版")
        else:
            if st.button("🔓 解鎖 299 深度版", key="love_btn_unlock_299"):
                st.session_state.temp_pay_plan_love = "paid_299"
                st.rerun()

    with col_plan3:
        st.markdown("""
        <div class="plan-card">
            <div class="plan-title">🥇 699 完整版</div>
            <div class="plan-price">NT$ 699</div>
            <ul class="plan-features">
                <li>299 版所有內容</li>
                <li><b>完整對話拆解報告</b></li>
                <li><b>PDF 下載權限</b></li>
                <li><b>3 次提問權限 (Hugo 親回)</b></li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.payment_status == "paid_699":
            st.button("✅ 已解鎖", disabled=True, key="love_btn_699_active")
        else:
            if st.button("🔓 解鎖 699 完整版", key="love_btn_unlock_699"):
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

        if st.session_state.order_data:
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
    if st.session_state.payment_status in ["paid_299", "paid_699"]:
        st.markdown("---")
        st.markdown("## 🌟 感情深度解析內容")
        if st.session_state.order_data:
            st.caption(f"📄 訂單編號：{st.session_state.order_data['order_id']}")
        st.success("對方目前對你的好感度約為 75%，建議在接下來的三天內主動發起一次輕鬆的話題互動。")
        
        if st.session_state.payment_status == "paid_699":
            st.markdown("### 📘 完整對話拆解與 PDF")
            st.write("這裡會顯示完整的對話心理拆解。")
            st.button("📥 下載 PDF 報告 (模擬)")
        else:
            st.warning("🔒 完整報告與 PDF 下載僅限「699 完整版」")
    else:
        st.info("🔒 付費解鎖後即可查看深度想法解析與行動建議")
        st.link_button(
            "👉 加入LINE解鎖完整分析",
            "https://line.me/ti/p/@258hnnao"
        )

st.info("系統建置中")

if st.button("⬅️ 回到首頁"):
    st.switch_page("app.py")
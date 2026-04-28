import streamlit as st

st.set_page_config(
    page_title="AI感情心理分析",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 AI感情心理分析")

# --- 初始化付款狀態 ---
if 'payment_status' not in st.session_state:
    st.session_state.payment_status = "free"

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
        st.markdown("### 🥉 免費版")
        st.write("✅ 基礎感情分析")
        if st.session_state.payment_status == "free":
            st.button("目前方案", disabled=True, key="love_btn_free")
        else:
            if st.button("切換回免費版", key="love_btn_switch_free"):
                st.session_state.payment_status = "free"
                st.rerun()

    with col_plan2:
        st.markdown("### 🥈 299 深度版")
        st.write("✅ 基礎感情分析")
        st.write("✅ 對方真實想法解析")
        st.write("✅ 行動建議指引")
        if st.session_state.payment_status == "paid_299":
            st.button("✅ 已解鎖", disabled=True, key="love_btn_299_active")
        elif st.session_state.payment_status == "paid_699":
            st.write("✨ 已包含在完整版")
        else:
            if st.button("🔓 解鎖 299 深度版", key="love_btn_unlock_299"):
                st.session_state.temp_pay_plan_love = "paid_299"
                st.rerun()

    with col_plan3:
        st.markdown("### 🥇 699 完整版")
        st.write("✅ 299 版所有內容")
        st.write("✅ 完整對話拆解報告")
        st.write("✅ PDF 下載權限")
        st.write("✅ 3 次線上提問權限")
        if st.session_state.payment_status == "paid_699":
            st.button("✅ 已解鎖", disabled=True, key="love_btn_699_active")
        else:
            if st.button("🔓 解鎖 699 完整版", key="love_btn_unlock_699"):
                st.session_state.temp_pay_plan_love = "paid_699"
                st.rerun()

    # 模擬付款邏輯
    if 'temp_pay_plan_love' in st.session_state:
        st.info("💳 **目前為測試模式**")
        st.write(f"您選擇了：{'299 深度版' if st.session_state.temp_pay_plan_love == 'paid_299' else '699 完整版'}")
        if st.button("✅ 確認付款完成 (測試)", type="primary"):
            st.session_state.payment_status = st.session_state.temp_pay_plan_love
            del st.session_state.temp_pay_plan_love
            st.success("🎉 付款成功！內容已解鎖。")
            st.rerun()

    # --- 顯示已付款內容 ---
    if st.session_state.payment_status in ["paid_299", "paid_699"]:
        st.markdown("---")
        st.markdown("## 🌟 感情深度解析內容")
        st.success("對方目前對你的好感度約為 75%，建議在接下來的三天內主動發起一次輕鬆的話題互動。")
        
        if st.session_state.payment_status == "paid_699":
            st.markdown("### 📘 完整對話拆解與 PDF")
            st.write("這裡會顯示完整的對話心理拆解。")
            st.button("📥 下載 PDF 報告 (模擬)")
        else:
            st.warning("🔒 完整報告與 PDF 下載僅限「699 完整版」")
    else:
        st.info("🔒 付費解鎖後即可查看深度想法解析與行動建議")

st.info("系統建置中")

if st.button("⬅️ 回到首頁"):
    st.switch_page("app.py")
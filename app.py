import streamlit as st
import google.generativeai as genai
import datetime
import time
import os

st.set_page_config(page_title="雨果大師｜命理 AI", page_icon="🔮", layout="wide")

# CSS 注入：美化介面並隱藏 Streamlit 預設元素
st.markdown("""
<style>
    .main-title {
        font-size: 2.8em;
        font-weight: 800;
        color: #6C3483;
        text-align: center;
        margin-bottom: 0.1em;
        text-shadow: 2px 2px 4px rgba(108, 52, 131, 0.2);
    }
    .sub-title {
        font-size: 1.1em;
        color: #7D3C98;
        text-align: center;
        margin-bottom: 2em;
        font-style: italic;
    }
    .result-card {
        background: linear-gradient(135deg, #F9F0FF 0%, #E8DAEF 100%);
        border: 2px solid #A569BD;
        border-radius: 16px;
        padding: 28px;
        margin-top: 20px;
        box-shadow: 0 8px 32px rgba(165, 105, 189, 0.25);
    }
    .result-header {
        font-size: 1.4em;
        color: #6C3483;
        font-weight: 700;
        margin-bottom: 15px;
        border-bottom: 2px solid #D7BDE2;
        padding-bottom: 8px;
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
    #MainMenu {display: none !important;}
    footer {display: none !important;}
    header {display: none !important;}
    .master-zone {
        background-color: #f4f0ff;
        border: 1px dashed #8e44ad;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# 1. Logo 置頂
st.markdown('<p class="main-title">🔮 雨果大師</p>', unsafe_allow_html=True)
col_logo1, col_logo2, col_logo3 = st.columns([1, 2, 1])
with col_logo2:
    logo_path = "logo.JPG" if os.path.exists("logo.JPG") else "logo.jpg"
    if os.path.exists(logo_path):
        st.image(logo_path, use_container_width=True)
st.markdown('<p class="sub-title">古典命理與 AI 的深度對話｜專業八字・紫微斗數・人生指引</p>', unsafe_allow_html=True)

# 2. 管理員密碼鎖 (大師盤)
MASTER_CODE = "16888"
is_master = False

with st.sidebar:
    st.header("🔐 系統授權")
    auth_code = st.text_input("大師專用授權碼", type="password")
    if auth_code == MASTER_CODE:
        is_master = True
        st.success("✅ 大師模式已開啟")
    elif auth_code != "":
        st.error("❌ 授權碼錯誤")

# 3. API 設定
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel("gemini-2.5-flash")
except Exception as e:
    st.error("API 金鑰讀取失敗，請確認 Streamlit Secrets 設定是否正確。")
    st.stop()

# 4. 功能模式選擇
st.markdown("### 🎯 選擇分析模式")
analysis_mode = st.radio(
    "請選擇命理分析模式",
    ["【八字精論】", "【紫微斗數分析】", "【八紫交叉比對】"],
    horizontal=True,
    label_visibility="collapsed"
)
st.markdown("---")

# 5. 基礎輸入介面 (大眾版與大師盤通用)
with st.container():
    st.markdown("### 📋 填寫基本資料")
    col1, col2, col3 = st.columns(3)
    with col1:
        name = st.text_input("姓名/暱稱", placeholder="如何稱呼您？")
    with col2:
        gender = st.selectbox("性別", ["男", "女"])
    with col3:
        occupation = st.selectbox(
            "目前狀態/職業",
            ["學生", "上班族", "受聘", "自營商", "合夥公司", "待業", "家管", "退休", "更生人", "身障"]
        )

    col4, col5 = st.columns(2)
    with col4:
        birth_date = st.date_input("出生日期 (國曆)", min_value=datetime.date(1930, 1, 1))
    with col5:
        birth_time = st.time_input("出生時間")

    question = st.text_area("有什麼特別想問的問題嗎？", placeholder="請簡述您的問題...", height=100)

# 5. 大師進階分析區 (僅在密碼正確時顯示)
advanced_params = {}
if is_master:
    with st.expander("🔮 大師進階分析區", expanded=True):
        st.markdown('<div class="master-zone">', unsafe_allow_html=True)
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            advanced_params['focus'] = st.multiselect(
                "加強分析維度",
                ["流年流月運勢", "神煞精論", "格局細分", "十神深論", "調候用神詳解"],
                default=["流年流月運勢"]
            )
        with col_m2:
            advanced_params['theory'] = st.radio(
                "核心學理偏好",
                ["平衡中和", "氣勢從格", "調候優先"],
                horizontal=True
            )
        st.markdown('</div>', unsafe_allow_html=True)

# 6. 雙人合盤功能 (保留原本的邏輯)
enable_dual = st.checkbox("💞 啟用雙人合盤 (感情/合夥)")
if enable_dual:
    st.subheader("💞 第二位對象資料")
    col_p2_1, col_p2_2, col_p2_3 = st.columns(3)
    with col_p2_1:
        gender2 = st.selectbox("對象性別", ["男", "女"], key="gender2")
    with col_p2_2:
        birth_date2 = st.date_input("對象出生日期", min_value=datetime.date(1930, 1, 1), key="birth_date2")
    with col_p2_3:
        birth_time2 = st.time_input("對象出生時間", key="birth_time2")
    relation_type = st.selectbox("雙方關係", ["情侶/夫妻", "事業合夥", "家人/朋友"])

st.markdown("---")

# 7. 試算按鈕與 Prompt 邏輯
col_btn_left, col_btn_right, col_btn_end = st.columns([1, 2, 1])
with col_btn_right:
    btn_label = "✨ 大師深度發功" if is_master else "✨ 開始溫馨試算"
    if st.button(btn_label, use_container_width=True):
        if not question:
            st.warning("請簡單填寫一下您想問的問題，大師才能為您指點迷津喔！")
        else:
            start_time = time.time()
            with st.spinner("大師正在排盤與分析中，請稍候..."):
                base_info = f"""
                【客人資料】：
                - 姓名：{name}
                - 性別：{gender}
                - 生日：{birth_date} {birth_time}
                - 職業：{occupation}
                - 提問：{question}
                """

                if is_master:
                    if analysis_mode == "【八字精論】":
                        prompt = f"""
                        你是一位擁有 30 年經驗的頂級八字命理大師。
                        請根據以下客人資料，嚴格依據《三命通會》、《滴天髓》、《窮通寶鑑》進行深度推理。
                        {base_info}
                        - 大師加強維度：{', '.join(advanced_params.get('focus', []))}
                        - 核心學理偏好：{advanced_params.get('theory', '標準')}
                        
                        【輸出要求】（請嚴格按照以下四個硬性框架表格輸出，不准省略、不准只用聊天口吻）：
                        
                        ═══════════════════════════════════════════════════════════
                        一、【四柱命盤實盤】
                        ═══════════════════════════════════════════════════════════
                        請用以下表格格式，填入實際命盤數據：
                        
                        ┌────────────┬──────────┬──────────┬──────────┬──────────┐
                        │ 四柱       │ 天干     │ 十神     │ 地支     │ 藏干/十神│
                        ├────────────┼──────────┼──────────┼──────────┼──────────┤
                        │ 年柱       │ (填入)   │ (填入)   │ (填入)   │ (填入)   │
                        ├────────────┼──────────┼──────────┼──────────┼──────────┤
                        │ 月柱       │ (填入)   │ (填入)   │ (填入)   │ (填入)   │
                        ├────────────┼──────────┼──────────┼──────────┼──────────┤
                        │ 日柱 日主  │ (填入)   │ (日主)   │ (填入)   │ (填入)   │
                        ├────────────┼──────────┼──────────┼──────────┼──────────┤
                        │ 時柱       │ (填入)   │ (填入)   │ (填入)   │ (填入)   │
                        └────────────┴──────────┴──────────┴──────────┴──────────┘
                        
                        ═══════════════════════════════════════════════════════════
                        二、【五行能量權重】
                        ═══════════════════════════════════════════════════════════
                        請用以下表格格式，計算五行能量：
                        
                        ┌────────┬──────────────┬──────────────┬──────────────┐
                        │ 五行   │ 狀態(旺相休囚死)│ 天干數量     │ 總權重百分比  │
                        ├────────┼──────────────┼──────────────┼──────────────┤
                        │ 金     │ (填入)       │ (填入)       │ (填入)%      │
                        ├────────┼──────────────┼──────────────┼──────────────┤
                        │ 木     │ (填入)       │ (填入)       │ (填入)%      │
                        ├────────┼──────────────┼──────────────┼──────────────┤
                        │ 水     │ (填入)       │ (填入)       │ (填入)%      │
                        ├────────┼──────────────┼──────────────┼──────────────┤
                        │ 火     │ (填入)       │ (填入)       │ (填入)%      │
                        ├────────┼──────────────┼──────────────┼──────────────┤
                        │ 土     │ (填入)       │ (填入)       │ (填入)%      │
                        └────────┴──────────────┴──────────────┴──────────────┘
                        
                        ═══════════════════════════════════════════════════════════
                        三、【格局喜忌與身強弱判斷】
                        ═══════════════════════════════════════════════════════════
                        本命格局：(例如：食神生財格、官印相生格、專旺格等)
                        日元強度：(例如：身強 / 身弱 / 中和)
                        喜用五行：(例如：水、木 - 對日主最有利的五行)
                        忌諱五行：(例如：土、火 - 對日主不利的五行)
                        調候用神：(如需特別調候，依《窮通寶鑑》標示)
                        
                        ═══════════════════════════════════════════════════════════
                        四、【十神坐基與具體斷語】
                        ═══════════════════════════════════════════════════════════
                        請列出年、月、日、時柱中，主要十神的坐基含義與斷語：
                        - 年柱十神：X坐X → 具體斷語（例如：正財坐偏印代表...）
                        - 月柱十神：X坐X → 具體斷語
                        - 日主坐基：X坐X → 具體斷語（代表本人的核心特質）
                        - 時柱十神：X坐X → 具體斷語（例如：食神坐傷官代表...）
                        
                        ═══════════════════════════════════════════════════════════
                        最後：【大師白話註解】
                        ═══════════════════════════════════════════════════════════
                        依據上述四個框架表格的數據，引用《三命通會》、《滴天髓》、《窮通寶鑑》：
                        - 給予結合職業背景【{occupation}】的白話註解
                        - 針對使用者的【職業狀態】（自營商、更生人、身障等）給予具同理心的實務建議
                        - 提供趨吉避凶的具體方向
                        - 針對大師指定的加強維度【{', '.join(advanced_params.get('focus', []))}】進行深入建議
                        """
                    elif analysis_mode == "【紫微斗數分析】":
                        prompt = f"""
                        你是一位擁有 30 年經驗的頂級紫微斗數命理大師。
                        請根據以下客人資料，嚴格依據《紫微斗數全書》之學理進行深度推理。
                        {base_info}
                        - 大師加強維度：{', '.join(advanced_params.get('focus', []))}
                        - 核心學理偏好：{advanced_params.get('theory', '標準')}
                        
                        【輸出結構】（請嚴格按照以下順序）：
                        
                        第一部分：【星曜乾坤：紫微命盤】
                        - 請排出命宮、身宮所在宮位
                        - 列出主要星曜配置（紫微、天機、太陽、武曲等）
                        - 標示四化飛星（化祿、化權、化科、化忌）
                        - 列出十二宮位（命宮、兄弟宮、夫妻宮、子女宮、財帛宮、疾厄宮、遷移宮、奴僕宮、事業宮、田宅宮、福德宮、父母宮）
                        
                        第二部分：【經典命理依據】
                        - 必須精準引用《紫微斗數全書》原文
                        - 依據星曜性質、格局、四化飛星、宮位象義進行推理
                        - 分析命宮主星強弱、事业运势、財富運勢
                        
                        第三部分：【大師白話註解】
                        - 將學理翻譯成現代人聽得懂的解說
                        - 緊密結合職業背景【{occupation}】給予精準建議
                        - 針對使用者的【職業狀態】（自營商、更生人、身障等）給予具同理心的指引
                        - 針對大師指定的加強維度進行深入推演
                        - 語氣專業、權威且具備極高的洞察力
                        """
                    else:
                        prompt = f"""
                        你是一位擁有 30 年經驗的頂級命理大師，兼具八字與紫微斗數深厚造詣。
                        請根據以下客人資料，同時排出八字命盤與紫微命盤，並依據以下學理進行交叉比對：
                        - 八字部分：嚴格依據《三命通會》、《滴天髓》、《窮通寶鑑》。
                        - 紫微部分：嚴格依據《紫微斗數全書》。
                        
                        {base_info}
                        - 大師加強維度：{', '.join(advanced_params.get('focus', []))}
                        - 核心學理偏好：{advanced_params.get('theory', '標準')}
                        
                        【輸出結構】（請嚴格按照以下順序）：
                        
                        第一部分：【命盤乾坤：雙盤排盤】
                        【八字四柱】
                        - 用表格排出年柱、月柱、日柱、時柱（含天干地支）
                        - 標註日主（日元）
                        - 列出地支藏干
                        
                        【紫微星曜】
                        - 命宮、身宮及主要星曜配置
                        - 四化飛星（化祿、化權、化科、化忌）
                        - 十二宮位簡表
                        
                        第二部分：【經典命理依據】
                        - 八字部分：引用《三命通會》、《滴天髓》、《窮通寶鑑》進行喜忌判斷
                        - 紫微部分：引用《紫微斗數全書》進行星曜宮位分析
                        - 針對兩者的喜忌進行對照
                        
                        第三部分：【八紫交叉結論】
                        - 若兩者結論一致（如：八字走喜神運且紫微流年化祿），加強肯定建議，指出黃金時期
                        - 若結論有異（如：八字用神得令但紫微流年沖煞），給予風險提醒與化解方向
                        
                        第四部分：【大師白話註解】
                        - 將學理翻譯成現代人聽得懂的解說
                        - 緊密結合職業背景【{occupation}】給予精準建議
                        - 針對使用者的【職業狀態】（自營商、更生人、身障等）給予具同理心的指引
                        - 語氣專業、權威且具備極高的洞察力
                        """
                else:
                    if analysis_mode == "【八字精論】":
                        prompt = f"""
                        你是一位親切溫馨的八字命理顧問。
                        請根據以下客人資料提供白話、正向且具同理心的八字運勢分析。
                        {base_info}
                        
                        【輸出結構】：
                        第一部分：【四柱命盤】：排出年柱、月柱、日柱、時柱（天干地支），標註日主
                        第二部分：【命理分析】：結合命盤給予白話解析
                        
                        【解析要求】：
                        1. 先用簡單易懂的方式說明四柱排列
                        2. 語氣要現代、親切，像朋友般的對話
                        3. 結合客人的職業背景【{occupation}】給予實用的指引
                        4. 針對使用者的【職業狀態】（自營商、更生人、身障等）給予具同理心的指引
                        """
                    elif analysis_mode == "【紫微斗數分析】":
                        prompt = f"""
                        你是一位親切溫馨的紫微斗數命理顧問。
                        請根據以下客人資料提供白話、正向且具同理心的紫微斗數運勢分析。
                        {base_info}
                        
                        【輸出結構】：
                        第一部分：【紫微命盤】：排出命宮主星與主要星曜配置（淺顯易懂的方式）
                        第二部分：【命理分析】：結合命盤給予白話解析
                        
                        【解析要求】：
                        1. 先用簡單易懂的方式說明星曜與宮位配置
                        2. 語氣要現代、親切，像朋友般的對話
                        3. 結合客人的職業背景【{occupation}】給予實用的指引
                        4. 針對使用者的【職業狀態】（自營商、更生人、身障等）給予具同理心的指引
                        """
                    else:
                        prompt = f"""
                        你是一位親切溫馨的命理顧問，兼具八字與紫微斗數知識。
                        請根據以下客人資料，同時排出八字命盤與紫微命盤，針對兩者的喜忌進行對照分析。
                        {base_info}
                        
                        【輸出結構】：
                        第一部分：【雙盤排盤】：八字四柱 + 紫微星曜（淺顯易懂）
                        第二部分：【交叉分析】：兩者結論對照
                        第三部分：【白話建議】：溫馨實用的指引
                        
                        【交叉比對邏輯】：
                        1. 若兩者結論一致，請加強肯定建議
                        2. 若結論有異，請給予風險提醒與化解方向
                        3. 語氣要現代、親切，像朋友般的對話
                        4. 結合客人的職業背景【{occupation}】給予實用的指引
                        5. 針對使用者的【職業狀態】（自營商、更生人、身障等）給予具同理心的指引
                        """

                if enable_dual:
                    prompt += f"\n\n此外，請啟動雙人合盤模式，分析與對象（性別：{gender2}，生日：{birth_date2} {birth_time2}）的【{relation_type}】關係。"

                try:
                    response = model.generate_content(prompt)
                    elapsed = time.time() - start_time

                    mode_display = {
                        "【八字精論】": "八字精論",
                        "【紫微斗數分析】": "紫微斗數分析",
                        "【八紫交叉比對】": "八紫交叉比對"
                    }
                    result_title = f"📜 {mode_display[analysis_mode]}｜{'大師深度解析' if is_master else '溫馨命理建議'}"

                    st.markdown('<div class="result-card">', unsafe_allow_html=True)
                    st.markdown(f'<p class="result-header">{result_title}</p>', unsafe_allow_html=True)
                    st.markdown(response.text)
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.caption(f"⏱️ 分析耗時：{elapsed:.1f} 秒")

                except Exception as e:
                    st.error(f"發生錯誤：{e}")

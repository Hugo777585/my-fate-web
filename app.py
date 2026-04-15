import streamlit as st
import google.generativeai as genai
import datetime
import time
import os
from lunar_python import Lunar, Solar

def calculate_bazi(birth_date, birth_time):
    try:
        # 1. 強制轉為整數
        y = int(birth_date.year)
        m = int(birth_date.month)
        d = int(birth_date.day)
        h = int(birth_time.hour)
        minute = int(birth_time.minute)

        # 2. 生成八字
        solar = Solar.fromYmdHms(y, m, d, h, minute, 0)
        lunar = solar.getLunar()
        eight_char = lunar.getEightChar()
        
        # 取得八字四柱 (年、月、日、時)
        year_pillar = eight_char.getYear()
        month_pillar = eight_char.getMonth()
        day_pillar = eight_char.getDay()
        hour_pillar = eight_char.getTime()

        # 取得藏干
        year_hide = "".join(eight_char.getYearHideGan())
        month_hide = "".join(eight_char.getMonthHideGan())
        day_hide = "".join(eight_char.getDayHideGan())
        hour_hide = "".join(eight_char.getTimeHideGan())

        # 取得十神 (以日主為中心)
        year_shishen = eight_char.getYearShiShenGan()
        month_shishen = eight_char.getMonthShiShenGan()
        hour_shishen = eight_char.getTimeShiShenGan()

        return {
            'year_tg': year_pillar[:1], 'year_dz': year_pillar[1:2], 'year_ss': year_shishen, 'year_hide': year_hide,
            'month_tg': month_pillar[:1], 'month_dz': month_pillar[1:2], 'month_ss': month_shishen, 'month_hide': month_hide,
            'day_tg': day_pillar[:1], 'day_dz': day_pillar[1:2], 'day_ss': '日主', 'day_hide': day_hide,
            'hour_tg': hour_pillar[:1], 'hour_dz': hour_pillar[1:2], 'hour_ss': hour_shishen, 'hour_hide': hour_hide,
            'full': {
                'year': year_pillar,
                'month': month_pillar,
                'day': day_pillar,
                'hour': hour_pillar
            }
        }
    except Exception as e:
        st.error(f"日期轉換或命盤計算發生系統錯誤：{e}")
        return None

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
SYSTEM_INSTRUCTION = "你是一個沒有感情的命理排盤伺服器。絕對禁止使用任何問候語（如：恩、你好、哈囉）。你只能輸出 Markdown 表格（使用 |---| 語法）與專業的古籍解析，禁止任何開場白。"
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    model = genai.GenerativeModel(
        "gemini-2.5-flash",
        system_instruction=SYSTEM_INSTRUCTION
    )
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
                bazi = calculate_bazi(birth_date, birth_time)
                
                # 準備精確的四柱數據字串，供 Prompt 使用
                if bazi:
                    pillar_info = f"""
【萬年曆精算命盤】：
年柱：{bazi['full']['year']}
月柱：{bazi['full']['month']}
日柱：{bazi['full']['day']} (日主：{bazi['day_tg']})
時柱：{bazi['full']['hour']}
"""
                else:
                    pillar_info = "（命盤計算失敗，請檢查輸入日期）"

                base_info = f"姓名：{name}，性別：{gender}，生日：{birth_date} {birth_time}，職業：{occupation}，提問：{question}"

                if is_master:
                    if analysis_mode == "【八字精論】":
                        prompt = f"""請以此經由萬年曆精算出的正確命盤為【絕對依據】，禁止自行推算：
{pillar_info}

客人資料：{base_info}
加強維度：{', '.join(advanced_params.get('focus', []))}
學理偏好：{advanced_params.get('theory', '標準')}

【輸出要求】：必須使用 HTML 表格呈現四柱排盤。表格字體加粗加大，確保清晰易讀。
請根據每一柱「地支」的五行屬性，為該行加上背景底色。

一、【命盤乾坤：四柱排盤】（HTML 彩色表格）
<table border="2" cellpadding="8" cellspacing="2" style="border-collapse: collapse; width: 100%; font-size: 20px; font-weight: bold; text-align: center;">
<tr style="background-color: #6C3483; color: white;">
<th>四柱</th><th>天干</th><th>十神</th><th>地支</th><th>藏干</th>
</tr>
<tr style="background-color: (根據地支【{bazi['year_dz'] if bazi else ''}】的五行填入顏色);"><td>年柱</td><td>{bazi['year_tg'] if bazi else ''}</td><td>{bazi['year_ss'] if bazi else ''}</td><td>{bazi['year_dz'] if bazi else ''}</td><td>{bazi['year_hide'] if bazi else ''}</td></tr>
<tr style="background-color: (根據地支【{bazi['month_dz'] if bazi else ''}】的五行填入顏色);"><td>月柱</td><td>{bazi['month_tg'] if bazi else ''}</td><td>{bazi['month_ss'] if bazi else ''}</td><td>{bazi['month_dz'] if bazi else ''}</td><td>{bazi['month_hide'] if bazi else ''}</td></tr>
<tr style="background-color: (根據地支【{bazi['day_dz'] if bazi else ''}】的五行填入顏色);"><td>日柱日主</td><td>{bazi['day_tg'] if bazi else ''}【日主】</td><td>(日主)</td><td>{bazi['day_dz'] if bazi else ''}</td><td>{bazi['day_hide'] if bazi else ''}</td></tr>
<tr style="background-color: (根據地支【{bazi['hour_dz'] if bazi else ''}】的五行填入顏色);"><td>時柱</td><td>{bazi['hour_tg'] if bazi else ''}</td><td>{bazi['hour_ss'] if bazi else ''}</td><td>{bazi['hour_dz'] if bazi else ''}</td><td>{bazi['hour_hide'] if bazi else ''}</td></tr>
</table>

【五行配色規則】：
- 木 (甲乙寅卯)：#e8f5e9 (淺綠)
- 火 (丙丁巳午)：#ffebee (淺紅)
- 土 (戊己辰戌丑未)：#fff3e0 (淺黃)
- 金 (庚辛申酉)：#f5f5f5 (淺灰)
- 水 (壬癸亥子)：#e3f2fd (淺藍)

二、【五行能量與喜忌】
依據《三命通會》、《滴天髓》、《窮通寶鑑》分析五行強弱，判定本命格局、日元強弱、喜用五行、忌諱五行。

三、【經典命理依據】
嚴格依據《三命通會》、《滴天髓》、《窮通寶鑑》進行深度解析。

四、【大師白話註解】
針對客人職業狀態【{occupation}】給予專業且具同理心的建議與趨吉避凶指引。
"""
                    elif analysis_mode == "【紫微斗數分析】":
                        prompt = f"""請以此經由萬年曆精算出的正確八字命盤輔助參考：
{pillar_info}

客人資料：{base_info}
加強維度：{', '.join(advanced_params.get('focus', []))}
學理偏好：{advanced_params.get('theory', '標準')}

一、【紫微命盤】
（請排出紫微斗數命盤表格）

二、【格局與喜忌】
命宮主星、四化飛星、事業/財富分析。

三、【古籍學理與大師白話指引】
依據《紫微斗數全書》進行解析，針對職業狀態【{occupation}】給予建議。"""
                    else:
                        prompt = f"""請以此經由萬年曆精算出的正確八字命盤為分析依據：
{pillar_info}

客人資料：{base_info}
加強維度：{', '.join(advanced_params.get('focus', []))}
學理偏好：{advanced_params.get('theory', '標準')}

一、【八字與紫微雙盤排盤】
（請同時顯示八字四柱與紫微命盤簡表）

二、【交叉比對結論】
針對八字喜忌與紫微流年進行對照分析。

三、【古籍學理與大師白話指引】
綜合《三命通會》、《滴天髓》、《窮通寶鑑》與《紫微斗數全書》進行解析，禁止廢話。"""
                else:
                    if analysis_mode == "【八字精論】":
                        prompt = f"""請根據以下經由萬年曆精算出的正確八字命盤進行分析，禁止自行推算：
{pillar_info}

客人資料：{base_info}
請用簡潔的 Markdown 格式（含表格）提供溫馨建議，並結合客人的職業背景【{occupation}】。"""
                    elif analysis_mode == "【紫微斗數分析】":
                        prompt = f"""請根據以下經由萬年曆精算出的正確八字命盤輔助參考，進行紫微斗數分析：
{pillar_info}

客人資料：{base_info}
請提供專業的紫微斗數解析與溫馨建議。"""
                    else:
                        prompt = f"""請根據以下經由萬年曆精算出的正確八字命盤進行交叉比對分析：
{pillar_info}

客人資料：{base_info}
同時提供八字與紫微的綜合解析。"""

                if enable_dual:
                    prompt += f"\n\n雙人合盤：對象性別：{gender2}，生日：{birth_date2} {birth_time2}，關係：{relation_type}"

                try:
                    response = model.generate_content(prompt)
                    elapsed = time.time() - start_time
                    result_text = response.text
                    result_text = result_text.replace('恩，你好！', '').replace('恩，', '').replace('哈囉，', '').replace('你好，', '').replace('您好，', '').replace('首先，', '').replace('首先呢', '').replace('恩，好', '').strip()

                    mode_display = {
                        "【八字精論】": "八字精論",
                        "【紫微斗數分析】": "紫微斗數分析",
                        "【八紫交叉比對】": "八紫交叉比對"
                    }
                    result_title = f"📜 {mode_display[analysis_mode]}｜{'大師深度解析' if is_master else '溫馨命理建議'}"

                    st.markdown('<div class="result-card">', unsafe_allow_html=True)
                    st.markdown(f'<p class="result-header">{result_title}</p>', unsafe_allow_html=True)
                    st.markdown(result_text, unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                    st.caption(f"⏱️ 分析耗時：{elapsed:.1f} 秒")

                except Exception as e:
                    st.error(f"發生錯誤：{e}")

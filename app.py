import sys
import datetime as _dt
import hashlib
import calendar
import os
import json
import base64
from dataclasses import dataclass
from typing import Any

import streamlit as st

# ==========================================
# Streamlit 配置 (必須是第一個 Streamlit 指令)
# ==========================================
st.set_page_config(page_title="Hugo 乾坤命理館：流年造化推演", layout="wide")

import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from fpdf import FPDF
from borax.calendars.festivals2 import TermFestival
from borax.calendars.lunardate import LunarDate
from iztro_py import astro

# ==========================================
# 全域變數與 AI 設定 (集中管理模型版本)
# ==========================================
GEMINI_MODEL = 'gemini-2.5-flash'
# ==========================================
# 基礎常數與資料
# ==========================================
GAN = ["甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸"]
ZHI = ["子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥"]
GAN_YANG = {0, 2, 4, 6, 8}

GAN_ELEMENT = {
    "甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
    "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水",
}

ZHI_ELEMENT = {
    "子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
    "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水",
}

LIUHE = {
    ("子", "丑"): "合土", ("寅", "亥"): "合木", ("卯", "戌"): "合火",
    ("辰", "酉"): "合金", ("巳", "申"): "合水", ("午", "未"): "合土",
}

CHONG = {
    ("子", "午"), ("丑", "未"), ("寅", "申"), ("卯", "酉"), ("辰", "戌"), ("巳", "亥"),
}

SANHE = {
    frozenset({"申", "子", "辰"}): "水",
    frozenset({"寅", "午", "戌"}): "火",
    frozenset({"亥", "卯", "未"}): "木",
    frozenset({"巳", "酉", "丑"}): "金",
}

XING_GROUPS = [
    frozenset({"子", "卯"}), frozenset({"寅", "巳", "申"}), frozenset({"丑", "戌", "未"}),
    frozenset({"辰"}), frozenset({"午"}), frozenset({"酉"}), frozenset({"亥"}),
]

PALACE_BRANCHES = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]
ZIWEI_PALACES = ["命宮", "兄弟", "夫妻", "子女", "財帛", "疾厄", "遷移", "仆役", "官祿", "田宅", "福德", "父母"]

OCCUPATIONS = [
    "上班族",
    "創業/自由業",
    "學生 (未滿十八歲)",
    "學生 (十八歲以上)",
    "家管",
    "已退休",
    "更生人",
    "待業中"
]

BOOK_OPTIONS = [
    ("di", "滴天髓（氣勢）"),
    ("qiong", "窮通寶鑒（調候）"),
    ("san", "三命通會（格局神煞）"),
]

BORAX_TERMS = [
    "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨", "立夏", "小满",
    "芒种", "夏至", "小暑", "大暑", "立秋", "处暑", "白露", "秋分", "寒露", "霜降",
    "立冬", "小雪", "大雪", "冬至",
]

# ==========================================
# 來客人數統計系統
# ==========================================
def get_visitor_count():
    count_file = "visitor_count.txt"
    if "visited" not in st.session_state:
        st.session_state.visited = True
        try:
            if os.path.exists(count_file):
                with open(count_file, "r") as f:
                    count = int(f.read().strip())
            else:
                count = 888 
            count += 1
            with open(count_file, "w") as f:
                f.write(str(count))
        except:
            count = 889
        st.session_state.v_count = count
    else:
        try:
            with open(count_file, "r") as f:
                count = int(f.read().strip())
        except:
            count = st.session_state.get("v_count", 889)
    return count

# ==========================================
# Google Sheets 寫入功能
# ==========================================
def save_to_google_sheet(row_data: list):
    """將解析紀錄寫入 Google 試算表"""
    try:
        if "GCP_SERVICE_ACCOUNT" not in st.secrets:
            return
            
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scopes)
        client = gspread.authorize(creds)
        
        # 開啟試算表
        sh = client.open("Hugo 命理館：客戶紀錄總表")
        worksheet = sh.worksheet("工作表1")
        worksheet.append_row(row_data)
    except Exception as e:
        print(f"Google Sheets 寫入失敗: {e}")

# ==========================================
# 核心資料結構與計算
# ==========================================
@dataclass(frozen=True)
class GZ:
    tg: int
    dz: int
    @property
    def text(self) -> str: return f"{GAN[self.tg]}{ZHI[self.dz]}"
    @property
    def gan(self) -> str: return GAN[self.tg]
    @property
    def zhi(self) -> str: return ZHI[self.dz]

@dataclass(frozen=True)
class Person:
    name: str
    date: _dt.date
    time: _dt.time
    gender: str
    occupation: str
    hour_unknown: bool
    has_children: str = "無"
    children_count: int = 0

def _parse_gz(gz: str) -> GZ:
    tg = GAN.index(gz[0]); dz = ZHI.index(gz[1])
    return GZ(tg=tg, dz=dz)

def _hour_branch_index(hour: int) -> int:
    hour %= 24
    if hour == 23: return 0
    return ((hour + 1) // 2) % 12

def _hour_gz(day_gan_index: int, hour: int) -> GZ:
    zi_base_by_day_gan = {0:0, 5:0, 1:2, 6:2, 2:4, 7:4, 3:6, 8:6, 4:8, 9:8}
    base = zi_base_by_day_gan[int(day_gan_index)]
    dz = _hour_branch_index(int(hour))
    tg = (base + dz) % 10
    return GZ(tg=tg, dz=dz)

def _term_date(year: int, name: str) -> _dt.date:
    return TermFestival(name).at(year=year)

def _year_gz_by_lichun(solar_date: _dt.date) -> GZ:
    lichun = _term_date(solar_date.year, "立春")
    ref_year = solar_date.year if solar_date >= lichun else (solar_date.year - 1)
    ld = LunarDate.from_solar_date(ref_year, 7, 1)
    return _parse_gz(ld.gz_year)

def _find_adjacent_term(birth_dt: _dt.datetime, forward: bool) -> tuple[str, _dt.datetime]:
    candidates = []
    for y in (birth_dt.year - 1, birth_dt.year, birth_dt.year + 1):
        for name in BORAX_TERMS:
            d = _term_date(y, name)
            candidates.append((_dt.datetime.combine(d, _dt.time(0, 0)), name))
    if forward:
        after = [(t, n) for (t, n) in candidates if t > birth_dt]
        t, n = min(after, key=lambda x: x[0])
        return n, t
    else:
        before = [(t, n) for (t, n) in candidates if t < birth_dt]
        t, n = max(before, key=lambda x: x[0])
        return n, t

def bazi_from_borax(date: _dt.date, time: _dt.time) -> dict[str, Any]:
    birth_dt = _dt.datetime.combine(date, time)
    ld = LunarDate.from_solar_date(date.year, date.month, date.day)
    year_gz = _year_gz_by_lichun(date)
    month_gz = _parse_gz(ld.gz_month)
    day_gz = _parse_gz(ld.gz_day)
    hour_gz = _hour_gz(day_gz.tg, int(time.hour))
    return {
        "birth_dt": birth_dt,
        "lunar": {"year": int(ld.year), "month": int(ld.month), "day": int(ld.day), "leap": bool(getattr(ld, "leap", False))},
        "pillars": {"year": year_gz, "month": month_gz, "day": day_gz, "hour": hour_gz},
    }

def calc_dayun(birth_dt: _dt.datetime, year_gz: GZ, month_gz: GZ, gender: str) -> dict[str, Any]:
    g = gender.lower().strip()
    forward = (g == "male" and year_gz.tg in GAN_YANG) or (g == "female" and year_gz.tg not in GAN_YANG)
    jq_name, jq_dt = _find_adjacent_term(birth_dt, forward)
    delta_days = abs((jq_dt - birth_dt).total_seconds()) / 86400.0
    start_years = delta_days / 3.0
    step = 1 if forward else -1
    items = []
    for i in range(8):
        gz = GZ((month_gz.tg + step * (i + 1)) % 10, (month_gz.dz + step * (i + 1)) % 12)
        items.append({"index": i + 1, "gz": gz, "start_age_years": start_years + i * 10, "end_age_years": start_years + (i + 1) * 10})
    return {"direction": "forward" if forward else "backward", "start_age_years": start_years, "items": items, "ref_term": {"name": jq_name}}

def calc_liunian(from_year: int, years: int) -> list[dict[str, Any]]:
    return [{"year": y, "gz": _year_gz_by_lichun(_dt.date(y, 7, 1))} for y in range(from_year, from_year + years)]

def five_element_counts(pillars: dict[str, GZ]) -> dict[str, int]:
    counts = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for gz in pillars.values():
        counts[GAN_ELEMENT[gz.gan]] += 1
        counts[ZHI_ELEMENT[gz.zhi]] += 1
    return counts

def branch_pair_relation(a: str, b: str) -> tuple[bool, bool, bool, bool]:
    p, q = (a, b), (b, a)
    return (p in LIUHE or q in LIUHE, any(a in g and b in g for g in SANHE.keys()), p in CHONG or q in CHONG, any(a in g and b in g for g in XING_GROUPS))

def shensha(pillars: dict[str, GZ]) -> dict[str, Any]:
    day_gan, year_zhi, day_zhi = pillars["day"].gan, pillars["year"].zhi, pillars["day"].zhi
    branches = {p.zhi for p in pillars.values()}
    tianyi_map = {"甲":{"丑","未"}, "戊":{"丑","未"}, "庚":{"丑","未"}, "乙":{"子","申"}, "己":{"子","申"}, "丙":{"亥","酉"}, "丁":{"亥","酉"}, "壬":{"卯","巳"}, "癸":{"卯","巳"}, "辛":{"寅","午"}}
    tianyi = sorted(branches.intersection(tianyi_map.get(day_gan, set())))
    def _group_key(z: str): return "申子辰" if z in {"申","子","辰"} else "寅午戌" if z in {"寅","午","戌"} else "亥卯未" if z in {"亥","卯","未"} else "巳酉丑"
    tm, ym = {"申子辰":"酉", "寅午戌":"卯", "亥卯未":"子", "巳酉丑":"午"}, {"申子辰":"寅", "寅午戌":"申", "亥卯未":"巳", "巳酉丑":"亥"}
    tk, yk = _group_key(year_zhi), _group_key(day_zhi)
    return {"tianyi": tianyi, "taohua": {"by_year": tm[tk], "hit_by_year": tm[tk] in branches, "by_day": tm[yk], "hit_by_day": tm[yk] in branches}, "yima": {"by_year": ym[tk], "hit_by_year": ym[tk] in branches, "by_day": ym[yk], "hit_by_day": ym[yk] in branches}}

def _hour_to_iztro_index(hour: int) -> int:
    """將小時轉換為 iztro-py 的時辰索引 (0-12)"""
    if hour == 0: return 0   # 早子時
    if hour == 23: return 12 # 晚子時
    return (hour + 1) // 2

def _ziwei_chart_from_iztro(person: Person) -> dict[str, Any] | None:
    gender = "男" if person.gender == "male" else "女"
    try:
        # iztro-py 的 time_index 是 0-12
        time_idx = _hour_to_iztro_index(int(person.time.hour))
        chart = astro.by_solar(person.date.isoformat(), time_idx, gender, language="zh-TW")
        palaces = []
        for p in chart.palaces:
            palaces.append({
                "name": p.translate_name("zh-TW"),
                "major_stars": [s.translate_name("zh-TW") for s in p.major_stars],
                "minor_stars": [s.translate_name("zh-TW") for s in p.minor_stars],
            })
        return {"palaces": palaces, "soul_palace": chart.get_soul_palace().translate_name("zh-TW")}
    except Exception as e:
        print(f"Ziwei chart error: {e}")
        return None

def build_person_report(p: Person) -> dict[str, Any]:
    base = bazi_from_borax(p.date, p.time)
    pillars = base["pillars"]
    lunar = base["lunar"]
    dayun = calc_dayun(base["birth_dt"], pillars["year"], pillars["month"], p.gender)
    age = (_dt.datetime.now() - base["birth_dt"]).total_seconds() / (365.2425 * 86400.0)
    current = next((it for it in dayun["items"] if it["start_age_years"] <= age < it["end_age_years"]), None)
    return {
        "person": p, 
        "has_children": p.has_children,
        "children_count": p.children_count,
        "pillars": pillars, "lunar": lunar, "counts": five_element_counts(pillars),
        "dayun": dayun, "current_dayun": current, "liunian": calc_liunian(_dt.date.today().year, 5),
        "shensha": shensha(pillars), "ziwei_chart": _ziwei_chart_from_iztro(p)
    }

# ==========================================
# AI 邏輯 (大師靈魂)
# ==========================================
def get_bazi_analysis(prompt, api_key, model_name=GEMINI_MODEL):
    """🔥 終極穩定版：使用 google-generativeai SDK"""
    
    # 將使用者選擇的模型放在第一位，之後接備援模型 (統一使用 gemini-2.5-flash)
    models_to_try = [
        model_name, 
        "gemini-2.5-flash"
    ]
    # 移除重複的模型名，並過濾掉 None
    models_to_try = list(dict.fromkeys([m for m in models_to_try if m]))
    
    # 設置 API Key
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"🚨 API Key 設定失敗：{e}")
        return None

    # 模型參數設定 (符合 2026 最新規格)
    generation_config = {
        "temperature": 0.7,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    for m in models_to_try:
        placeholder = st.empty()
        try:
            model = genai.GenerativeModel(
                model_name=m,
                generation_config=generation_config
            )
            placeholder.info(f"🔮 大師正在運用【{m}】進行深度推演...")
            
            response = model.generate_content(prompt)
            # 檢查是否有內容產出，有些 model 可能因為安全過濾返回空結果
            if response and response.text:
                placeholder.empty() # 成功後清除提示
                return response.text
            else:
                placeholder.warning(f"⚠️ 模型 {m} 未能產出有效建議，嘗試切換模型...")
            
        except Exception as e:
            placeholder.empty()
            if m == models_to_try[-1]: # 如果最後一個也失敗
                st.error(f"🚨 所有模型都無法連線。錯誤：{e}")
            else:
                st.warning(f"⚠️ 模型 {m} 暫時無法使用，正在嘗試切換備援模型...")
            continue
    return None

def generate_ai_text(api_key: str, model_name: str, module_name: str, payload: dict, selected_books: list[str], is_master: bool = False) -> str:
    # 優先從傳入的 api_key 獲取，否則從 st.secrets 獲取
    target_key = api_key
    if not target_key:
        if "GOOGLE_API_KEY" in st.secrets:
            target_key = st.secrets["GOOGLE_API_KEY"]
        elif "GEMINI_API_KEY" in st.secrets:
            target_key = st.secrets["GEMINI_API_KEY"]
    
    if not target_key:
        return "NO_API_KEY"
    
    # 取得當前台灣時間 (UTC+8)
    now_tw = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")

    def json_serial(obj):
        if hasattr(obj, 'isoformat'): return obj.isoformat()
        if hasattr(obj, 'text'): return obj.text
        return str(obj)

    star_info = ""
    if "main_person" in payload and payload["main_person"].get("ziwei_chart"):
        star_info += "【主命主星曜】\n" + "\n".join([f"{p['name']}主星={'、'.join(p['major_stars'])}" for p in payload["main_person"]["ziwei_chart"].get('palaces', [])]) + "\n"
    if "partner_person" in payload and payload["partner_person"].get("ziwei_chart"):
        star_info += "【對象星曜】\n" + "\n".join([f"{p['name']}主星={'、'.join(p['major_stars'])}" for p in payload["partner_person"]["ziwei_chart"].get('palaces', [])]) + "\n"

    # 判斷是否為雙人合盤
    is_pairing = "partner_person" in payload
    
    if not is_master:
        # 【新版白話文＋八字用神大綱】
        partner_info = ""
        if is_pairing:
            p2 = payload["partner_person"]["person"]
            p2_pillars = payload["partner_person"]["pillars"]
            partner_info = f"""
        【配對對象資料】：
        - [對象姓名]: {p2.name}
        - [對象八字]: {p2_pillars["year"].text}, {p2_pillars["month"].text}, {p2_pillars["day"].text}, {p2_pillars["hour"].text}
        """

        prompt = f"""
        你現在是一位親切、直白且專業的現代命理分析師。
        請根據這份【專屬生命地圖解析】大綱，產出一份白話文風格的測算結果。
        {"如果是雙人合盤，請特別分析兩人的靈魂契合度與相處建議。" if is_pairing else ""}
        
        【系統資訊】：
        - [登錄時間]: {now_tw}
        
        【客人資料】：
        - [客人姓名]: {payload["main_person"]["person"].name}
        - [八字命盤]: 
            - 年柱: {payload["main_person"]["pillars"]["year"].text}
            - 月柱: {payload["main_person"]["pillars"]["month"].text}
            - 日柱: {payload["main_person"]["pillars"]["day"].text}
            - 時柱: {payload["main_person"]["pillars"]["hour"].text}
        {partner_info}
        
        【解析要求】：
        1. 語氣要現代、口語化，像是朋友間的深度對話，禁止使用「汝」、「吾」、「汝的內在驅動力」或「見父母宮」等文言文詞彙。
        2. 請根據命盤推算出客人的 [八字用神]，並針對該用神提供 [八字用神專屬建議內容]。
        3. ### 【天命密碼】：用白話點出客人的性格核心優勢與潛在挑戰。
        {"4. ### 【情緣鑑定】：分析兩人的契合點、潛在摩擦點，以及如何讓感情更穩定的具體建議。" if is_pairing else "4. ### 【命運預告】：針對 2026 年提供一個具體的轉折點預告（不給具體月份與解法，引導後續諮詢）。"}
        5. ### 【用神建議】：詳細說明 [八字用神] 對客人的重要性，並給出具體的「用神補強建議」。
        6. 最後強制加上：✨ **【想解鎖完整的「破局戰術」與「運勢攻略」？】** ✨ 請截圖此畫面並點擊下方 LINE 連結預約大師！
        """
    else:
        books = "、".join(selected_books) if selected_books else "（未指定）"
        # 【大師深度模式 - 也要改為白話專業風格】
        prompt = f"""
        你是一位頂級命理分析師。模組：{module_name}。
        請給出包含靈魂共振、命理金箔、破局戰術的深度解析。
        請使用現代、直白且富有洞見的語氣，禁止使用陳舊文言文（如「汝」、「吾」）。
        參考學理：{books}。
        
        【系統資訊】：
        - [登錄時間]: {now_tw}
        
        【客人資料】：
        - [客人姓名]: {payload["main_person"]["person"].name}
        - [八字命盤]: {payload["main_person"]["pillars"]["year"].text}, {payload["main_person"]["pillars"]["month"].text}, {payload["main_person"]["pillars"]["day"].text}, {payload["main_person"]["pillars"]["hour"].text}
        {star_info}
        """

    result = get_bazi_analysis(prompt, api_key=target_key, model_name=model_name)
    return result if result else "🚨 大師目前閉關中，請稍後再試。"

# ==========================================
# PDF 匯出
# ==========================================
class ReportPDF(FPDF):
    def footer(self):
        self.set_y(-15); self.set_font("Helvetica", size=9)
        self.cell(0, 10, "執此命書，願你洞悉天機，行穩致遠。", align="C")

def _find_cjk_font() -> str:
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\msjh.ttc",
        r"C:\Windows\Fonts\simsun.ttc", r"C:\Windows\Fonts\simhei.ttf",
    ]
    for p in candidates:
        if os.path.exists(p): return p
    return ""

def create_pdf(user_name: str, body: str):
    pdf = ReportPDF()
    font_path = _find_cjk_font()
    if font_path:
        pdf.add_font("CJK", "", font_path)
        pdf.add_font("CJK", "B", font_path)
        pdf.set_font("CJK", size=16)
    else:
        pdf.set_font("Helvetica", size=16)
    
    pdf.add_page()
    pdf.cell(0, 10, f"{user_name} - 人生宿命乾坤論斷", ln=True, align="C")
    
    if font_path: pdf.set_font("CJK", size=12)
    else: pdf.set_font("Helvetica", size=12)
    
    clean_body = body.replace("**", "")
    pdf.multi_cell(0, 8, clean_body)
    return pdf.output()

# ==========================================
# UI 樣式
# ==========================================
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; background-color: #262730; border: 1px solid #4a4a4a; }
    .report-card { background-color: #1e212b; padding: 25px; border-radius: 12px; border: 1px solid #30363d; font-size: 1.1em; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

st.title("🔮 Hugo 乾坤命理館：流年造化推演")

with st.sidebar:
    st.header("⚙️ 設定")
    # 優先從 st.secrets 讀取 GEMINI_API_KEY 或 GOOGLE_API_KEY
    api_key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
    
    # 如果 secrets 中沒有，才顯示側邊欄輸入框
    if not api_key:
        api_key = st.text_input("Gemini API Key", type="password")
    else:
        st.success("✅ 已自動載入系統 API Key")
    
    # 【關鍵修正】：統一使用 gemini-2.5-flash
    model_name = st.selectbox("模型版本", [
        "gemini-2.5-flash"
    ])
    st.info("已鎖定大師靈魂提示詞，強制輸出權威斷言。")

    # 🧪 驗證用最小測試
    if st.button("🧪 測試 AI 連線"):
        if not api_key:
            st.warning("⚠️ 請先輸入 API Key 才能進行測試！")
        else:
            try:
                genai.configure(api_key=api_key)
                # 測試也使用標準參數
                test_model = genai.GenerativeModel(
                    model_name="gemini-2.5-flash",
                    generation_config={"temperature": 0.7}
                )
                r = test_model.generate_content("請說一句：『AI 連線測試成功！』")
                st.success(r.text)
            except Exception as e:
                st.error(f"❌ 測試失敗：{e}")
    
    st.markdown("---")
    master_code = st.text_input("大師通關密語 (選填)", type="password")
    is_master_mode = (master_code.upper() == "HUGO888")
    if is_master_mode:
        st.success("✅ 已解鎖：宗師深度模式")
    elif master_code:
        st.error("❌ 密語錯誤：啟動公眾引流模式")
    else:
        st.caption("輸入正確密語以解鎖深度流年分析")

    st.sidebar.markdown("---")
    v_count = get_visitor_count()
    st.sidebar.metric("📊 累計解盤人數", f"{v_count} 人")
    st.sidebar.caption(f"Powered by {GEMINI_MODEL} & Borax")

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.subheader("👤 主命主資料")
        name = st.text_input("姓名/標籤", value="命主A")
        gender = st.selectbox("性別", ["male", "female"], format_func=lambda x: "男" if x=="male" else "女")
        bday = st.date_input("出生日期", value=_dt.date(1980, 1, 1))
        btime = st.time_input("出生時間", value=_dt.time(12, 0))
        occ = st.selectbox("職業屬性", OCCUPATIONS)
        unknown = st.checkbox("不確定出生時辰")
        
        # 新增小孩資訊
        has_children = st.radio("是否有小孩？", ["無", "有"], horizontal=True)
        children_count = 0
        if has_children == "有":
            children_count = st.number_input("請問有幾個小孩？", min_value=1, max_value=10, value=1)

    with st.container(border=True):
        st.subheader("💞 感情合盤 / 配對對象")
        enable_partner = st.checkbox("啟用雙人合盤分析")
        
        p2_name = ""
        p2_gender = "female"
        p2_bday = _dt.date.today()
        p2_btime = _dt.time(12, 0)
        
        if enable_partner:
            if is_master_mode:
                match_with_hugo = st.checkbox("🔮 直接與大師本人(士恩)合盤", help="自動載入 1977/12/06 資料")
            else:
                match_with_hugo = False
                
            if match_with_hugo:
                p2_name = "Hugo 大師 (士恩)"
                p2_gender = "male"
                p2_bday = _dt.date(1977, 12, 6)
                p2_btime = _dt.time(12, 0)
                st.success("✅ 已自動載入大師本命盤 (1977/12/06 屬蛇)")
            else:
                p2_name = st.text_input("對象姓名/標籤", value="對象B")
                p2_gender = st.selectbox("對象性別", ["female", "male"], format_func=lambda x: "女" if x=="female" else "男")
                p2_bday = st.date_input("對象出生日期", value=_dt.date(1985, 1, 1))
                p2_btime = st.time_input("對象出生時間", value=_dt.time(12, 0))

with col2:
    with st.container(border=True):
        st.subheader("📚 解盤框架")
        books = st.multiselect("學理框架", [b[1] for b in BOOK_OPTIONS], default=[b[1] for b in BOOK_OPTIONS])

st.divider()

btn_cols = st.columns(4)
module_name = None
if btn_cols[0].button("八字乾坤：深度解析"): module_name = "八字乾坤：深度能量解析"
if btn_cols[1].button("紫微精論：十二宮位"): module_name = "紫微精論：人生十二宮位"
if btn_cols[2].button("命理大滿貫：旗艦合參"): module_name = "命理大滿貫：八字紫微合參"

if module_name:
    if not api_key:
        st.error("🚨 老闆，你忘了在左邊輸入 Gemini API Key 啦！沒有鑰匙，大師無法開工喔！")
    else:
        try:
            # 建立主命主資料
            p1 = Person(name, bday, btime, gender, occ, unknown, has_children, children_count)
            report1 = build_person_report(p1)
            payload = {"main_person": report1}
            
            # 處理雙人合盤資料
            if enable_partner:
                try:
                    p2_name_val = p2_name if p2_name else "對象B"
                    p2 = Person(p2_name_val, p2_bday, p2_btime, p2_gender, "未知", False)
                    report2 = build_person_report(p2)
                    payload["partner_person"] = report2
                    module_name += " (💖 雙人情感合盤)"
                except Exception as e_partner:
                    st.warning(f"⚠️ 配對對象資料解析異常，將僅進行個人分析。錯誤：{e_partner}")
            
            with st.spinner(f"大師正在解析【{module_name}】..."):
                result = generate_ai_text(api_key, model_name, module_name, payload, books, is_master=is_master_mode)
                
                if result == "NO_API_KEY":
                    st.error("🚨 系統錯誤：偵測不到 API Key。")
                else:
                    now_tw_display = (_dt.datetime.now(_dt.timezone.utc) + _dt.timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
                    st.info(f"🕒 測算登錄時間：{now_tw_display}")
                    st.markdown(f"### 🖋️ 大師論斷：{module_name}")
                    st.markdown(f"<div class='report-card'>{result}</div>", unsafe_allow_html=True)
                    
                    # --- 寫入 Google Sheets ---
                    save_to_google_sheet([
                        now_tw_display,                      # A: 推算時間
                        name,                                # B: 客戶姓名
                        str(bday),                           # C: 出生日期
                        str(btime),                          # D: 出生時間
                        occ,                                 # E: 職業屬性
                        p2_name if enable_partner else "",   # F: 對象姓名
                        str(p2_bday) if enable_partner else "", # G: 對象生日
                        "解析成功",                          # H: 解析結果
                        "大師深度模式" if is_master_mode else "公眾引流模式" # I: 解盤模式
                    ])

                    try:
                        pdf_bytes = create_pdf(name, result)
                        col_dl1, col_dl2 = st.columns(2)
                        col_dl1.download_button("📥 下載 PDF 版", data=pdf_bytes, file_name=f"{module_name}.pdf", mime="application/pdf")
                        col_dl2.download_button("📥 下載純文字版", data=result.encode("utf-8"), file_name=f"{module_name}.txt")
                    except Exception as e_pdf:
                        st.warning("⚠️ 雲端伺服器缺少中文字型，暫停 PDF 下載功能，請先截圖或複製上方文字！")
                        st.download_button("📥 下載純文字版", data=result.encode("utf-8"), file_name=f"{module_name}.txt")
        except Exception as e_main:
            st.error(f"🚨 系統解析失敗，請檢查輸入資料是否正確。錯誤訊息：{e_main}")

st.markdown("---")
st.subheader("🔮 預約 Hugo 大師親自破局")
st.markdown("### 📱 LINE 預約：https://line.me/ti/p/~en777585 ")

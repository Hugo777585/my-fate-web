import datetime as _dt
import hashlib
import calendar
import os
import json
import base64
from dataclasses import dataclass
from typing import Any

import streamlit as st
import google.generativeai as genai
import gspread
from google.oauth2.service_account import Credentials
from borax.calendars.festivals2 import TermFestival
from borax.calendars.lunardate import LunarDate
from iztro_py import astro

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
    "穩定型 (固定薪水/內勤)",
    "開創型 (業務/接案/論件計酬)",
    "特殊波動型 (高風險/八大/偏門)",
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

def _ziwei_chart_from_iztro(person: Person) -> dict[str, Any] | None:
    gender = "男" if person.gender == "male" else "女"
    try:
        chart = astro.by_solar(person.date.isoformat(), int(person.time.hour), gender, language="zh-TW")
        palaces = []
        for p in chart.palaces:
            palaces.append({
                "name": p.translate_name("zh-TW"),
                "major_stars": [s.translate_name("zh-TW") for s in p.major_stars],
                "minor_stars": [s.translate_name("zh-TW") for s in p.minor_stars],
            })
        return {"palaces": palaces, "soul_palace": chart.get_soul_palace().translate_name("zh-TW")}
    except: return None

def build_person_report(p: Person) -> dict[str, Any]:
    base = bazi_from_borax(p.date, p.time)
    pillars = base["pillars"]
    lunar = base["lunar"]
    dayun = calc_dayun(base["birth_dt"], pillars["year"], pillars["month"], p.gender)
    age = (_dt.datetime.now() - base["birth_dt"]).total_seconds() / (365.2425 * 86400.0)
    current = next((it for it in dayun["items"] if it["start_age_years"] <= age < it["end_age_years"]), None)
    return {
        "person": p, "pillars": pillars, "lunar": lunar, "counts": five_element_counts(pillars),
        "dayun": dayun, "current_dayun": current, "liunian": calc_liunian(_dt.date.today().year, 5),
        "shensha": shensha(pillars), "ziwei_chart": _ziwei_chart_from_iztro(p)
    }

# ==========================================
# AI 邏輯 (大師靈魂)
# ==========================================
def _ai_system_prompt(selected_books: list[str], module_name: str) -> str:
    books = "、".join(selected_books) if selected_books else "（未指定）"
    return (
        "請扮演資深命理大師 Hugo。你的語氣要氣勢磅礴、直指人心，同時帶著對命主的深刻理解。請使用一般大眾能懂的日常比喻（如天氣、航海等，絕不可使用餐飲比喻）。\n\n"
        "【排版與輸出格式嚴格要求】：\n"
        "1. 必須分段落，並使用大標題（例如：### 【事業與財富軌跡】）。\n"
        "2. 每個大標題下，『必須使用條列式（*）與粗體』來標示專業術語，接著緊跟白話解釋與比喻。\n"
        "格式範例：\n"
        "* **《滴天髓》論日主（丙火）**：你就像是一盞溫暖的燈火，根據氣勢強弱... \n"
        "* **命宮巨門陀羅**：這代表你心思細膩，但在處理事情時容易...\n\n"
        "【必須主動解析的五大段落】：\n"
        "1. ### 【命格本質與內心深處】：條列出核心的八字與紫微特徵，點出外表與內心的落差。此段落必須明確引用《滴天髓》分析日主氣勢清濁，以及引用《窮通寶鑑》指出月令調候用神。\n"
        "2. ### 【事業格局與財富流向】：條列出事業星曜與五行喜忌，解析天賦與盲點。此段落必須明確引用《三命通會》論述關鍵神煞或特殊格局。\n"
        "3. ### 【感情羈絆與姻緣課題】：條列出夫妻宮與桃花狀況，點出感情觀與考驗。\n"
        "4. ### 【2026 丙午年：流月深度拆解】：此段落為本次解析核心，請針對 2026 丙午年進行極度詳細的分析：\n"
        "   - **上半年（春夏季：寅、卯、辰、巳、午、未月）**：點出關鍵轉折月份、氣勢起伏，以及在事業或感情上的具體機會。\n"
        "   - **下半年（秋冬季：申、酉、戌、亥、子、丑月）**：點出潛在危機、需要守成或變革的月份，並給予明確的預警。\n"
        "   - 必須使用條列式，並針對特定月份給出「大師叮嚀」。\n"
        "5. ### 【Hugo 大師專屬轉運處方】：給出 3 個具體能立刻執行的生活行動建議。\n\n"
        "【Hugo 大師重點懶人包】：\n"
        "在報告的最末端，請提供一個 200 字以內的精煉總結，用最具氣勢且溫暖的文字，概括命主 2026 年的整體運勢與最終建議。\n\n"
        "【學理引述強制要求】：\n"
        "- 必須將以下古籍理論自然揉合在「粗體術語」解釋中：\n"
        "  1. 引用《滴天髓》：分析日主氣勢強弱與格局清濁。\n"
        "  2. 引用《窮通寶鑑》：根據月令明確指出「調候」用神。\n"
        "  3. 引用《三命通會》：點出關鍵神煞或特殊格局組合。\n\n"
        "【輸出規範】：\n"
        "- 絕對不可使用 Markdown 表格。\n"
        "- 必須善用 Markdown 的『粗體』與『條列』來增強閱讀的層次感。\n"
        f"- 必須參考學理框架：{books}。\n"
        f"- 目前解析模組：{module_name}。"
    )

def _ziwei_star_table_text(chart: dict | None) -> str:
    if not chart or not chart.get("palaces"): return ""
    return "\n".join([f"{p['name']}：主星={'、'.join(p['major_stars']) or '無'}；輔星={'、'.join(p['minor_stars'][:5]) or '無'}" for p in chart["palaces"]])

def generate_ai_text(api_key: str, model_name: str, module_name: str, payload: dict, selected_books: list[str]) -> str:
    if not api_key: return "請先在左側輸入 API Key。"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=model_name, system_instruction=_ai_system_prompt(selected_books, module_name))
    star_info = f"\n\n【紫微斗數星曜總表】\n{_ziwei_star_table_text(payload.get('ziwei_chart'))}\n" if "紫微" in module_name else ""
    
    # 確保 payload 中的內容可以被 JSON 序列化（將無法識別的物件轉為字串）
    def json_serial(obj):
        if hasattr(obj, 'isoformat'): return obj.isoformat()
        if hasattr(obj, 'text'): return obj.text # 處理 GZ 等物件
        return str(obj)

    safe_payload_json = json.dumps(payload, default=json_serial, ensure_ascii=False, indent=2)
    user_prompt = f"【模組】{module_name}\n【資料】\n{safe_payload_json}{star_info}"
    try:
        response = model.generate_content(user_prompt, generation_config=genai.types.GenerationConfig(temperature=0.7))
        # 防呆處理：嘗試讀取 response.text，若 AI 詞窮或報錯則回傳自定義訊息
        try:
            text = (response.text or "").strip()
            if not text:
                return "大師目前正在沉思中，請再按一次分析按鈕，或調整一下輸入的資料。"
        except Exception:
            return "大師目前正在沉思中，請再按一次分析按鈕，或調整一下輸入的資料。"

        if "未填" in text and "紫微" in module_name:
            text = text.replace("未填", f"【系統強制修正】\n{_ziwei_star_table_text(payload.get('ziwei_chart'))}")
        return text
    except Exception as e:
        return f"API 呼叫失敗：{str(e)}"

def extract_summary(text: str) -> str:
    """從 AI 回傳文字中擷取懶人包內容"""
    marker = "【Hugo 大師重點懶人包】："
    if marker in text:
        parts = text.split(marker)
        return parts[-1].strip()
    return "（未產出懶人包）"

def save_to_google_sheet(person: Person, summary: str):
    """將資料非同步寫入 Google Sheet"""
    try:
        # 從 st.secrets 讀取 GCP Service Account 資料
        # 預期格式為 st.secrets["GCP_SERVICE_ACCOUNT"] (一個 dict)
        if "GCP_SERVICE_ACCOUNT" not in st.secrets:
            print("無法存檔：st.secrets 中找不到 GCP_SERVICE_ACCOUNT 設定。")
            return

        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["GCP_SERVICE_ACCOUNT"], scopes=scopes)
        client = gspread.authorize(creds)
        
        # 開啟試算表
        sheet_name = "Hugo 命理館：客戶紀錄總表"
        sh = client.open(sheet_name)
        worksheet = sh.get_worksheet(0) # 第一個工作表
        
        # 準備資料行 (台北時間)
        now_tw = (_dt.datetime.utcnow() + _dt.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        row = [
            now_tw,
            person.name,
            "男" if person.gender == "male" else "女",
            person.date.isoformat(),
            person.time.strftime("%H:%M"),
            person.occupation,
            summary
        ]
        
        worksheet.append_row(row)
        print(f"成功存檔至 Google Sheet: {person.name}")
    except Exception as e:
        # 靜默失敗，僅在後台列印
        print(f"Google Sheet 存檔失敗：{str(e)}")

# ==========================================
# Streamlit UI
# ==========================================
st.set_page_config(page_title="My Fate Web - Hugo 大師版", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; background-color: #262730; border: 1px solid #4a4a4a; }
    .report-card { background-color: #1e212b; padding: 25px; border-radius: 12px; border: 1px solid #30363d; font-size: 1.1em; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

st.title("🔮 My Fate Web: Hugo 大師命理系統")

with st.sidebar:
    st.header("⚙️ 設定")
    # 直接讀取 secrets 裡的 GEMINI_API_KEY
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError:
        api_key = ""
        st.warning("⚠️ 找不到 GEMINI_API_KEY。請在 .streamlit/secrets.toml 中設定。")
    
    model_name = st.selectbox("模型版本", ["gemini-2.5-flash", "gemini-2.0-flash"])
    st.info("已鎖定 Hugo 大師靈魂提示詞，提供溫暖且犀利的洞察。")
    st.sidebar.markdown("---")
    st.sidebar.caption("Powered by Gemini 2.5 Flash & Borax")

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

with col2:
    with st.container(border=True):
        st.subheader("📚 解盤框架")
        books = st.multiselect("學理框架", [b[1] for b in BOOK_OPTIONS], default=[b[1] for b in BOOK_OPTIONS])
        st.subheader("📅 行事曆設定")
        cal_date = st.date_input("查詢月份", value=_dt.date.today())

st.divider()

# 按鈕區
btn_cols = st.columns(3)
module = None
if btn_cols[0].button("八字乾坤：深度解析"): module = "八字乾坤：深度能量解析"
if btn_cols[1].button("紫微精論：十二宮位"): module = "紫微精論：人生十二宮位"
if btn_cols[2].button("命理大滿貫：旗艦合參"): module = "命理大滿貫：八字紫微合參"

if module:
    p = Person(name, bday, btime, gender, occ, unknown)
    report = build_person_report(p)
    
    with st.spinner(f"Hugo 大師正在為您解析【{module}】..."):
        result = generate_ai_text(api_key, model_name, module, report, books)
        st.markdown(f"### 🖋️ Hugo 大師論斷：{module}")
        st.markdown(f"<div class='report-card'>{result}</div>", unsafe_allow_html=True)
        st.download_button("📥 下載此段論斷 (TXT)", data=result.encode("utf-8"), file_name=f"{module}.txt")
        
        # 存檔至 Google Sheet (非同步效果：即使失敗也不影響 UI)
        summary = extract_summary(result)
        save_to_google_sheet(p, summary)
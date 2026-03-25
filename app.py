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
from fpdf import FPDF
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
        "你是一位隱居多年、看破紅塵的命理玄學老手。你擁有極高的氣場與智慧，說話字字珠璣，能一眼看穿命盤背後的宿命真相。\n"
        "你必須嚴格遵守以下輸出規範：\n"
        "1) 【語氣要求】：極度自信、鐵口直斷、一針見血、徹底拒絕廢話。文字要有老手傅當面指點的氣場與溫度，充滿威嚴感。\n"
        "2) 【排版要求】：直接切入命盤核心痛點與解法。文字要自然流暢，減少生硬的條列式排版，標題必須加粗。\n"
        "3) 【核心禁令（違者視為嚴重錯誤）】：絕對禁止輸出以下 AI 常用罐頭廢話：\n"
        "   - 「這是一盤相當有意思的緣分」\n   - 「本命書由AI協作生成」\n   - 「矛盾與潛力」\n   - 「僅供參考」\n   - 「你要靠規則」\n"
        "4) 重要關鍵字（如 忌、喜、命門、轉折、格局）必須用 **...** 標示。\n"
        "5) 禁止輸出「未填」「未知」；如資料不足，請明確說明缺少哪個欄位。\n"
        f"6) 學理框架：{books}。請在解說時明確採用這些框架的專業術語。\n"
        f"7) 本次輸出模組：{module_name}。\n"
        "8) 【核心禁令】：絕對禁止在不同章節或宮位使用相同的結語模板或重複的文案！\n"
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
        text = (response.text or "").strip()
        if "未填" in text and "紫微" in module_name:
            text = text.replace("未填", f"【系統強制修正】\n{_ziwei_star_table_text(payload.get('ziwei_chart'))}")
        return text
    except Exception as e:
        return f"API 呼叫失敗：{str(e)}"

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
# Streamlit UI
# ==========================================
st.set_page_config(page_title="My Fate Web - 大師靈魂版", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: #ffffff; }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; background-color: #262730; border: 1px solid #4a4a4a; }
    .report-card { background-color: #1e212b; padding: 25px; border-radius: 12px; border: 1px solid #30363d; font-size: 1.1em; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

st.title("🔮 My Fate Web: 大師靈魂命理系統")

with st.sidebar:
    st.header("⚙️ 設定")
    api_key = st.text_input("Gemini API Key", type="password")
    model_name = st.selectbox("模型版本", ["gemini-2.5-flash", "gemini-2.0-flash"])
    st.info("已鎖定大師靈魂提示詞，強制輸出權威斷言。")
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
btn_cols = st.columns(4)
module = None
if btn_cols[0].button("八字乾坤：深度解析"): module = "八字乾坤：深度能量解析"
if btn_cols[1].button("紫微精論：十二宮位"): module = "紫微精論：人生十二宮位"
if btn_cols[2].button("命理大滿貫：旗艦合參"): module = "命理大滿貫：八字紫微合參"
if btn_cols[3].button("匯出 PDF 命書"): module = "PDF_EXPORT"

if module:
    p = Person(name, bday, btime, gender, occ, unknown)
    report = build_person_report(p)
    
    if module == "PDF_EXPORT":
        with st.spinner("正在撰寫大師命書..."):
            full_body = generate_ai_text(api_key, model_name, "一般版命書", report, books)
            pdf_bytes = create_pdf(name, full_body)
            st.success("命書已撰寫完成！")
            st.download_button("📥 下載 PDF 命書", data=pdf_bytes, file_name=f"{name}_Fate.pdf", mime="application/pdf")
    else:
        with st.spinner(f"大師正在解析【{module}】..."):
            result = generate_ai_text(api_key, model_name, module, report, books)
            st.markdown(f"### 🖋️ 大師論斷：{module}")
            st.markdown(f"<div class='report-card'>{result}</div>", unsafe_allow_html=True)
            
            pdf_bytes = create_pdf(name, result)
            col_dl1, col_dl2 = st.columns(2)
            col_dl1.download_button("📥 下載 PDF 版", data=pdf_bytes, file_name=f"{module}.pdf", mime="application/pdf")
            col_dl2.download_button("📥 下載純文字版", data=result.encode("utf-8"), file_name=f"{module}.txt")
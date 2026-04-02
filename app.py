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

# 新增選項定義
OCCUPATION_STATUS = ["受聘上班族", "自己經營創業", "自由工作者", "目前待業中"]
RELATIONSHIP_STATUS = ["單身", "穩定交往中", "已婚", "已離婚/分居"]

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
    job_status: str # 新增：目前職業狀態
    relationship: str # 新增：感情婚姻現況
    children: str # 新增：子女狀況
    partner_name: str = "" # 新增：對象姓名
    partner_date: _dt.date = None # 新增：對象生日
    partner_time_str: str = "" # 新增：對象時辰文字

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

def _time_from_branch_str(branch_str: str) -> _dt.time:
    """將時辰文字轉為概略時間"""
    mapping = {
        "子時": _dt.time(0, 0), "丑時": _dt.time(1, 0), "寅時": _dt.time(3, 0),
        "卯時": _dt.time(5, 0), "辰時": _dt.time(7, 0), "巳時": _dt.time(9, 0),
        "午時": _dt.time(11, 0), "未時": _dt.time(13, 0), "申時": _dt.time(15, 0),
        "酉時": _dt.time(17, 0), "戌時": _dt.time(19, 0), "亥時": _dt.time(21, 0),
        "不清楚": _dt.time(12, 0)
    }
    return mapping.get(branch_str, _dt.time(12, 0))

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
    
    report = {
        "person": p, "pillars": pillars, "lunar": lunar, "counts": five_element_counts(pillars),
        "dayun": dayun, "current_dayun": current, "liunian": calc_liunian(_dt.date.today().year, 5),
        "shensha": shensha(pillars), "ziwei_chart": _ziwei_chart_from_iztro(p)
    }

    # 處理對象配對資訊 (若有填寫)
    if p.partner_name and p.partner_date:
        p_time = _time_from_branch_str(p.partner_time_str)
        p_base = bazi_from_borax(p.partner_date, p_time)
        report["partner"] = {
            "name": p.partner_name,
            "pillars": p_base["pillars"],
            "lunar": p_base["lunar"]
        }
    
    return report

# ==========================================
# AI 邏輯 (大師靈魂)
# ==========================================
def _get_public_prompt(module_name: str) -> str:
    """公眾引流模式提示詞"""
    return (
        "請扮演資深命理宗師 Hugo。你的語氣要氣勢磅礴、直指人心。\n\n"
        "【輸出規範】：\n"
        "1. 總字數嚴格控制在 300~500 字以內。\n"
        "2. 內容僅包含：\n"
        "   - ### 【核心性格特質】：用條列式指出命主最顯著的性格與天賦。\n"
        "   - ### 【2026 命運轉折】：指出今年一個具體的大機會與一個大警告。\n"
        "3. 語氣保持專業大師感，不囉唆。\n"
        "4. 在最後強制加上這段文字（使用 Markdown 粗體）：\n"
        "✨ **【Hugo 大師本尊深度解析】** ✨  \n"
        "欲知 2026 年精確轉運時機與專屬流年密卷？想解鎖針對您目前職業與感情現狀的破局之法？請立即截圖此畫面，私訊 Hugo 大師解鎖完整天命軌跡！\n\n"
        f"目前解析模組：{module_name}。"
    )

def _ai_system_prompt(selected_books: list[str], module_name: str, is_master_mode: bool = False) -> str:
    if not is_master_mode:
        return _get_public_prompt(module_name)
    
    books = "、".join(selected_books) if selected_books else "（未指定）"
    
    partner_instruction = ""
    if "partner" in module_name or "配對" in module_name:
        partner_instruction = (
            "【兩人配對專屬要求】：\n"
            "1. 必須分析兩人的八字合契度（合、沖、刑、害）。\n"
            "2. 分析兩人的性格是否互補或存在衝突點。\n"
            "3. 給予這段關係具體的經營建議與未來走向預測。\n"
            "4. 在解析的最後，必須明確給出一個 1~100 的「兩人契合度分數」，並用一句話總結這段關係。\n"
        )

    return (
        "【核心大腦：Hu go 大師商業決策引擎 5.0 (終極完全體)】\n\n"
        "【角色設定與靈魂賦予】\n"
        "你是一位經歷過人生起伏、看透人性深淵的命理大師「Hu go」。你精通《滴天髓》與紫微斗數。你的任務不是算命，而是「幫用戶看懂人性，拿回關係的控制權」。你的語氣沉穩、犀利、帶有強烈的同理心。字裡行間要有情緒、有故事，拒絕條列式機器人報告，多使用「你表面上...但其實你內心...」的對比句型。\n\n"
        f"{partner_instruction}"
        "【強制輸出結構（請嚴格依照以下三層架構輸出，並加上適當的 Emoji）】\n\n"
        "🔮 第一層：【靈魂共振（命運與痛點剖析）】\n"
        "寫出直擊痛點的心理描述。必須包含「關係風險解碼」，用極具穿透力的文字描述對方在以下五個維度的表現：\n"
        "1. 曖昧擴散度（是否容易同時維持多對象？）\n"
        "2. 承諾穩定度（會不會突然退縮或消失？）\n"
        "3. 情緒波動（忽冷忽熱的程度？）\n"
        "4. 投入落差（說跟做是否一致？）\n"
        "5. 控制/逃避傾向（面對問題是處理還是閃躲？）\n"
        "📍 【致命總結】：請用一句話總結對方的感情模式。\n\n"
        "☯️ 第二層：【命理金箔與殘酷定位（降維打擊）】\n"
        "這是建立大師權威感的關鍵！你必須先根據雙方命盤，拋出 1~2 個極度專業的八字或紫微術語（例如：日主受剋、化忌入交友宮、身弱逢殺等），然後「立刻翻譯成血淋淋的人性白話文」，點出兩人的真實互動機制。\n"
        "接著明確給出以下三個量化決策指標：\n"
        "- 情感順位評分：__%\n"
        "- 替代可能性：(高/中/低)\n"
        "- 穩定發展機率：__%\n"
        "📍 【清醒金句】：請用一句話點破用戶在對方心中的真實位置。\n\n"
        "🔥 第三層：【破局戰術（高階行動指引）】\n"
        "這是全篇讓用戶離不開你的最高價值所在。根據目前的能量狀態，給出 3 點「現在立刻該怎麼做」的具體戰術。\n"
        "❌ 絕對不說「順其自然」這種廢話。\n"
        "✅ 必須給出具體操作（例如：何時該主動？何時必須冷卻？絕對會踩雷的行為？如何讓他主動靠近？）\n\n"
        "【學理引述強制要求】：\n"
        "- 必須將以下古籍理論自然揉合在解析中：\n"
        f"  1. 參考學理框架：{books}。\n"
        "  2. 引用《滴天髓》：分析日主氣勢強弱與格局清濁。\n"
        "  3. 引用紫微斗數：根據命盤星曜分析深層人性。\n\n"
        f"目前解析模組：{module_name}。"
    )

def _ziwei_star_table_text(chart: dict | None) -> str:
    if not chart or not chart.get("palaces"): return ""
    return "\n".join([f"{p['name']}：主星={'、'.join(p['major_stars']) or '無'}；輔星={'、'.join(p['minor_stars'][:5]) or '無'}" for p in chart["palaces"]])

def generate_ai_text(api_key: str, model_name: str, module_name: str, payload: dict, selected_books: list[str], is_master_mode: bool = False) -> str:
    if not api_key: return "請先在左側輸入 API Key。"
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name=model_name, system_instruction=_ai_system_prompt(selected_books, module_name, is_master_mode))
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
    """從 AI 回傳文字中擷取懶人包內容，處理全形/半形冒號"""
    markers = ["【Hugo 大師重點懶人包】：", "【Hugo 大師重點懶人包】:"]
    for marker in markers:
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
        sh = client.open("Hugo 命理館：客戶紀錄總表")
        worksheet = sh.worksheet("工作表1")
        
        # 準備資料行 (台北時間)
        now_tw = (_dt.datetime.utcnow() + _dt.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        row = [
            now_tw,
            person.name,
            str(person.date),
            person.time.strftime("%H:%M"),
            person.partner_name if person.partner_name else "",
            str(person.partner_date) if person.partner_date else "",
            "解析成功"
        ]
        
        worksheet.append_row(row)
        print(f"成功存檔至 Google Sheet: {person.name}")
    except Exception as e:
        # 靜默失敗，僅在後台列印
        print(f"Google Sheet 存檔失敗：{str(e)}")

# ==========================================
# Streamlit UI
# ==========================================
st.set_page_config(page_title="Hugo 乾坤命理館：流年造化推演", layout="wide")

st.markdown("""
<style>
    .stApp { 
        background-color: #0e1117; 
        color: #ffffff; 
        /* 將整個網頁背景換成更重複排列、更明顯的精緻浮水印 */
        background-image: url("data:image/svg+xml,%3Csvg width='160' height='100' xmlns='http://www.w3.org/2000/svg'%3E%3Ctext x='50%25' y='50%25' font-size='16' font-weight='bold' fill='rgba(255, 255, 255, 0.15)' font-family='sans-serif' text-anchor='middle' dominant-baseline='middle' transform='rotate(-30, 80, 50)'%3EHugo 乾坤命理館%3C/text%3E%3C/svg%3E");
        background-repeat: repeat;
        background-position: top left;
    }
    .stButton>button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; background-color: #262730; border: 1px solid #4a4a4a; }
    .report-card { background-color: #1e212b; padding: 25px; border-radius: 12px; border: 1px solid #30363d; font-size: 1.1em; line-height: 1.6; }
</style>
""", unsafe_allow_html=True)

st.title("🔮 Hugo 乾坤命理館：流年造化推演")
module = None

with st.sidebar:
    st.header("⚙️ 設定")
    # 直接讀取 secrets 裡的 GEMINI_API_KEY
    try:
        api_key = st.secrets["GEMINI_API_KEY"]
    except KeyError:
        api_key = ""
        st.warning("⚠️ 找不到 GEMINI_API_KEY。請在 .streamlit/secrets.toml 中設定。")
    
    model_name = st.selectbox("模型版本", ["gemini-2.5-flash", "gemini-2.0-flash"])
    st.info("已鎖定 Hugo 大師靈魂提示詞，提供溫慢且犀利的洞察。")
    
    st.markdown("---")
    master_code = st.text_input("大師通關密語 (選填)", type="password")
    is_master_mode = (master_code == "HUGO888")
    if is_master_mode:
        st.success("✅ 已解鎖：宗師深度模式")
    elif master_code:
        st.error("❌ 密語錯誤：啟動公眾引流模式")
    else:
        st.caption("輸入正確密語以解鎖深度流年分析")

    st.sidebar.markdown("---")
    st.sidebar.caption("Powered by Gemini 2.5 Flash & Borax")

    # --- 瀏覽人次記錄器 ---
    st.sidebar.markdown("---")
    st.sidebar.write("🔥 命理館累積香客：")
    st.sidebar.image("https://visitor-badge.laobi.icu/badge?page_id=hugo_fortune_master_2026&left_color=gray&right_color=red&left_text=來訪人次")

col1, col2 = st.columns(2)
with col1:
    with st.container(border=True):
        st.subheader("👤 主命主資料")
        name = st.text_input("姓名/標籤", value="命主A")
        gender = st.selectbox("性別", ["male", "female"], format_func=lambda x: "男" if x=="male" else "女")
        
        # 把起始年份設為 1940，最大年份設為 2026
        user_birthday = st.date_input(
            "您的生日",
            value=_dt.date(1980, 1, 1),
            min_value=_dt.date(1940, 1, 1),
            max_value=_dt.date(2026, 12, 31)
        )

        btime = st.time_input("出生時間", value=_dt.time(12, 0))
        occ = st.selectbox("職業屬性", OCCUPATIONS)
        unknown = st.checkbox("不確定出生時辰")

    with st.container(border=True):
        st.subheader("🏠 現實生活狀態")
        job_status = st.selectbox("目前職業狀態", OCCUPATION_STATUS)
        rel_status = st.selectbox("感情婚姻現況", RELATIONSHIP_STATUS)
        children_info = st.text_input("子女狀況", placeholder="例如：無，或 1個，17歲")

    with st.container(border=True):
        st.subheader("🔮 兩人配對：解碼你們的命運密碼（選填）")
        partner_name = st.text_input("對象姓名 (想算配對再填)", "")
        p_col1, p_col2 = st.columns(2)
        with p_col1:
            partner_birthday = st.date_input(
                "對象生日",
                value=None,
                min_value=_dt.date(1940, 1, 1),
                max_value=_dt.date(2026, 12, 31),
                key="p_date"
            )
        with p_col2:
            partner_time = st.selectbox("對象時辰", ["不清楚", "子時", "丑時", "寅時", "卯時", "辰時", "巳時", "午時", "未時", "申時", "酉時", "戌時", "亥時"], key="p_time")
        
        # 兩人配對專屬按鈕 (配合使用者提供的程式碼)
        if st.button("八字乾坤：深度解析", key="partner_btn_match"):
            module = "八字乾坤：深度能量解析"

with col2:
    with st.container(border=True):
        st.subheader("📚 解盤框架")
        books = st.multiselect("學理框架", [b[1] for b in BOOK_OPTIONS], default=[b[1] for b in BOOK_OPTIONS])
        st.subheader("📅 行事曆設定")
        cal_date = st.date_input("查詢月份", value=_dt.date.today())

st.divider()

# 按鈕區
btn_cols = st.columns(3)
if btn_cols[0].button("八字乾坤：深度解析"): module = "八字乾坤：深度能量解析"
if btn_cols[1].button("紫微精論：十二宮位"): module = "紫微精論：人生十二宮位"
if btn_cols[2].button("命理大滿貫：旗艦合參"): module = "命理大滿貫：八字紫微合參"

if module:
    p = Person(
        name, user_birthday, btime, gender, occ, unknown, job_status, rel_status, children_info,
        partner_name=partner_name, partner_date=partner_birthday, partner_time_str=partner_time
    )
    report = build_person_report(p)
    
    # 如果有對象資訊，修改 module 名稱以觸發配對提示詞
    if partner_name and partner_birthday:
        module = f"【兩人配對】{module}"
    
    with st.spinner(f"Hugo 大師正在為您解析【{module}】..."):
        result = generate_ai_text(api_key, model_name, module, report, books, is_master_mode=is_master_mode)
        st.markdown(f"### 🖋️ Hugo 大師論斷：{module}")
        st.markdown(f"<div class='report-card'>{result}</div>", unsafe_allow_html=True)
        
        # --- 大師專屬下載暗門 ---
        st.markdown("---")
        unlock_pwd = st.text_input("🔒 系統指令（僅限管理員）", type="password")
        
        if unlock_pwd == "hugo888":
            st.success("大師身分確認！已解鎖下載權限。")
            st.download_button(
                label="📥 下載此段論斷 (TXT)",
                data=result,
                file_name=f"{module}.txt"
            )
        elif unlock_pwd != "":
            st.error("指令錯誤，請勿亂闖大師陣法！")
        
        # 存檔至 Google Sheet (不論模式皆存檔)
        summary = extract_summary(result)
        save_to_google_sheet(p, summary)

        # --- 終極收網：聯絡大師 ---
        st.markdown("---")
        st.subheader("🔮 需要大師親自為你破局嗎？")
        st.info("以上數據是初步評估推論每個人出生時候的原廠人生命盤格局，但因每個人生長環境、所遭遇到的人事物不同而有所變動。如果你的情況複雜，或者需要針對目前的僵局制定「專屬攻略」，請直接私下找我 Hugo。")
        
        # 老闆的專屬 LINE 預約連結
        st.markdown("### `https://line.me/ti/p/~en777585` ")
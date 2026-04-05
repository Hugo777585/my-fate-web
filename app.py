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
        "person": p, 
        "has_children": p.has_children,
        "children_count": p.children_count,
        "pillars": pillars, "lunar": lunar, "counts": five_element_counts(pillars),
        "dayun": dayun, "current_dayun": current, "liunian": calc_liunian

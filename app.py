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
GAN_ELEMENT = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土", "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
ZHI_ELEMENT = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火", "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
LIUHE = {("子", "丑"): "合土", ("寅", "亥"): "合木", ("卯", "戌"): "合火", ("辰", "酉"): "合金", ("巳", "申"): "合水", ("午", "未"): "合土"}
CHONG = {("子", "午"), ("丑", "未"), ("寅", "申"), ("卯", "酉"), ("辰", "戌"), ("巳", "亥")}
SANHE = {frozenset({"申", "子", "辰"}): "水", frozenset({"寅", "午", "戌"}): "火", frozenset({"亥", "卯", "未"}): "木", frozenset({"巳", "酉", "丑"}): "金"}
XING_GROUPS = [frozenset({"子", "卯"}), frozenset({"寅", "巳", "申"}), frozenset({"丑", "戌", "未"}), frozenset({"辰"}), frozenset({"午"}), frozenset({"酉"}), frozenset({"亥"})]
PALACE_BRANCHES = ["寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥", "子", "丑"]
ZIWEI_PALACES = ["命宮", "兄弟", "夫妻", "子女", "財帛", "疾厄", "遷移", "仆役", "官祿", "田宅", "福德", "父母"]

# --- 選項清單 ---
OCCUPATIONS = ["上班族", "創業/自由業", "學生 (未滿十八歲)", "學生 (十八歲以上)", "家管", "已退休", "更生人", "待業中"]
OCCURATION_STATUS = ["受聘上班族", "自己經營創業", "自由工作者", "目前待業中"]
RELATIONSHIP_STATUS = ["單身", "穩定交往中", "已婚", "已離婚/分居"]
BOOK_OPTIONS = [("di", "滴天髓（氣勢）"), ("qiong", "窮通寶鑒（調候）"), ("san", "三命通會（格局神煞）")]
BORAX_TERMS = ["小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨", "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋", "处暑", "白露", "秋分", "寒露", "霜降", "立冬", "小雪", "大雪", "冬至"]

# ==========================================
# 核心計算邏輯
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
    name: str; date: _dt.date; time: _dt.time; gender: str; occupation: str; hour_unknown: bool; job_status: str; relationship: str; children: str; partner_name: str = ""; partner_date: _dt.date = None; partner_time_str: str = ""

def _parse_gz(gz: str) -> GZ:
    tg = GAN.index(gz[0]); dz = ZHI.index(gz[1]); return GZ(tg=tg, dz=dz)
def _hour_branch_index(hour: int) -> int:
    hour %= 24; return 0 if hour == 23 else ((hour + 1) // 2) % 12
def _hour_gz(day_gan_index: int, hour: int) -> GZ:
    zi_base = {0:0, 5:0, 1:2, 6:2, 2:4, 7:4, 3:6, 8:6, 4:8, 9:8}
    base = zi_base[int(day_gan_index)]; dz = _hour_branch_index(int(hour)); tg = (base + dz) % 10; return GZ(tg=tg, dz=dz)
def _time_from_branch_str(s: str) -> _dt.time:
    m = {"子時": _dt.time(0, 0), "丑時": _dt.time(1, 0), "寅時": _dt.time(3, 0), "卯時": _dt.time(5, 0), "辰時": _dt.time(7, 0), "巳時": _dt.time(9, 0), "午時": _dt.time(11, 0), "未時": _dt.time(13, 0), "申時": _dt.time(15, 0), "酉時": _dt.time(17, 0), "戌時": _dt.time(19, 0), "亥時": _dt.time(21, 0)}
    return m.get(s, _dt.time(12, 0))
def _term_date(y: int, n: str) -> _dt.date: return TermFestival(n).at(year=y)
def _year_gz_by_lichun(sd: _dt.date) -> GZ:
    lc = _term_date(sd.year, "立春"); ry = sd.year if sd >= lc else (sd.year - 1); ld = LunarDate.from_solar_date(ry, 7, 1); return _parse_gz(ld.gz_year)
def _find_adjacent_term(bdt: _dt.datetime, fwd: bool) -> tuple[str, _dt.datetime]:
    cands = []
    for y in (bdt.year - 1, bdt.year, bdt.year + 1):
        for n in BORAX_TERMS: d = _term_date(y, n); cands.append((_dt.datetime.combine(d, _dt.time(0, 0)), n))
    if fwd:
        t, n = min([(t, n) for (t, n) in cands if t > bdt], key=lambda x: x[0]); return n, t
    t, n = max([(t, n) for (t, n) in cands if t < bdt], key=lambda x: x[0]); return n, t
def bazi_from_borax(d: _dt.date, t: _dt.time) -> dict:
    bdt = _dt.datetime.combine(d, t); ld = LunarDate.from_solar_date(d.year, d.month, d.day); yg = _year_gz_by_lichun(d); mg = _parse_gz(ld.gz_month); dg = _parse_gz(ld.gz_day); hg = _hour_gz(dg.tg, int(t.hour))
    return {"birth_dt": bdt, "lunar": {"year": int(ld.year), "month": int(ld.month), "day": int(ld.day)}, "pillars": {"year": yg, "month": mg, "day": dg, "hour": hg}}
def build_person_report(p: Person) -> dict:
    base = bazi_from_borax(p.date, p.time); pillars = base["pillars"]
    report = {"person": p, "pillars": pillars, "lunar": base["lunar"]}
    if p.partner_name and p.partner_date:
        pt = _time_from_branch_str(p.partner_time_str); pb = bazi_from_borax(p.partner_date, pt); report["partner"] = {"name": p.partner_name, "pillars": pb["pillars"]}
    return report

# ==========================================
# AI 提示詞與執行
# ==========================================
def _ai_system_prompt(books: list, module: str, is_master: bool) -> str:
    books_str = "、".join(books) if books else "（未指定）"
    if not is_master:
        return f"請扮演命理宗師 Hugo。### 【核心性格】：條列式指出天賦。### 【2026 命運轉折】：具體機會與警告。✨ **【Hugo 大師本尊深度解析】** ✨ 私訊 Hugo 預約解鎖完整天命！模組：{module}"
    return (
        "【核心大腦：Hu go 大師商業決策引擎 5.0】\n"
        "你是一位看透人性的命理大師「Hu go」。用語犀利、沉穩、帶有強共同理心。針對不同身分給出權重：\n"
        "1. 家管：重塑個人魅力。2. 更生人：重建關係平權與掌握自我揭露時機。3. 學生：專注自我成長。\n"
        "輸出三層結構：🔮靈魂共振、☯️命理金箔與殘酷定位、🔥破局戰術（3點具體戰術）。\n"
        f"學理：{books_str}、滴天髓、紫微斗數。模組：{module}"
    )

def generate_ai_text(api_key: str, model_name: str, module: str, payload: dict, books: list, is_master: bool) -> str:

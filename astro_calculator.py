#!/usr/bin/env python3
"""
星命師 v2 - 占星計算層
輸入：占星之門盤面 Markdown
輸出：結構化解盤事實報告（供 Gemini 星命師 Gem 使用）

使用方式：
    python3 astro_calculator.py 盤面.md
    或
    python3 astro_calculator.py 盤面.md --theme 婚姻
"""

import re
import sys
import json
import argparse
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────
# 資料表（來自 01_core_tables.json + 02_dignity_engine.json）
# ─────────────────────────────────────────────

SIGN_NUM = {
    "牡羊": 1, "金牛": 2, "雙子": 3, "巨蟹": 4,
    "獅子": 5, "處女": 6, "天秤": 7, "天蠍": 8,
    "射手": 9, "魔羯": 10, "水瓶": 11, "雙魚": 12
}
NUM_SIGN = {v: k for k, v in SIGN_NUM.items()}

SIGN_EN = {
    "牡羊": "aries", "金牛": "taurus", "雙子": "gemini", "巨蟹": "cancer",
    "獅子": "leo", "處女": "virgo", "天秤": "libra", "天蠍": "scorpio",
    "射手": "sagittarius", "魔羯": "capricorn", "水瓶": "aquarius", "雙魚": "pisces"
}

PLANET_ZH = {
    "sun": "太陽", "moon": "月亮", "mercury": "水星", "venus": "金星",
    "mars": "火星", "jupiter": "木星", "saturn": "土星"
}
ZH_PLANET = {v: k for k, v in PLANET_ZH.items()}

DIGNITY_SCORES = {
    "domicile": 5, "exaltation": 4, "triplicity": 3,
    "term": 2, "face": 1, "peregrine": 0, "detriment": -5, "fall": -4
}

DIGNITY_LOOKUP = {
    "saturn":  {"domicile": ["aquarius","capricorn"], "exaltation": ["libra"],
                "detriment": ["leo","cancer"], "fall": ["aries"],
                "triplicity_day": ["gemini","libra","aquarius"],
                "triplicity_night": ["gemini","libra","aquarius"]},
    "jupiter": {"domicile": ["sagittarius","pisces"], "exaltation": ["cancer"],
                "detriment": ["gemini","virgo"], "fall": ["capricorn"],
                "triplicity_day": ["aries","leo","sagittarius"],
                "triplicity_night": ["aries","leo","sagittarius"]},
    "mars":    {"domicile": ["aries","scorpio"], "exaltation": ["capricorn"],
                "detriment": ["taurus","libra"], "fall": ["cancer"],
                "triplicity_day": ["cancer","scorpio","pisces"],
                "triplicity_night": ["cancer","scorpio","pisces"]},
    "sun":     {"domicile": ["leo"], "exaltation": ["aries"],
                "detriment": ["aquarius"], "fall": ["libra"],
                "triplicity_day": ["aries","leo","sagittarius"], "triplicity_night": []},
    "venus":   {"domicile": ["taurus","libra"], "exaltation": ["pisces"],
                "detriment": ["aries","scorpio"], "fall": ["virgo"],
                "triplicity_day": ["taurus","virgo","capricorn"],
                "triplicity_night": ["taurus","virgo","capricorn"]},
    "mercury": {"domicile": ["gemini","virgo"], "exaltation": ["virgo"],
                "detriment": ["sagittarius","pisces"], "fall": ["pisces"],
                "triplicity_day": ["gemini","libra","aquarius"],
                "triplicity_night": ["gemini","libra","aquarius"]},
    "moon":    {"domicile": ["cancer"], "exaltation": ["taurus"],
                "detriment": ["capricorn"], "fall": ["scorpio"],
                "triplicity_day": [], "triplicity_night": ["taurus","virgo","capricorn"]}
}

HOUSE_STRENGTH = {1:4, 2:2, 3:1, 4:4, 5:2, 6:1, 7:4, 8:2, 9:1, 10:4, 11:2, 12:1}
HOUSE_TYPE = {1:"angular", 2:"succedent", 3:"cadent", 4:"angular",
              5:"succedent", 6:"cadent", 7:"angular", 8:"succedent",
              9:"cadent", 10:"angular", 11:"succedent", 12:"cadent"}

SOLAR_PHASE_MODIFIER = {
    "偕日升": 2, "焦傷": -2, "在日光下": -1,
    "東出": 1, "西入": -1
}

SPEED_MODIFIER = {"逆行": -1, "停滯": 1, "快": 1, "慢": -1, "平均": 0}

PTOLEMY_ASPECTS = {0: "合相", 60: "六分相", 90: "四分相", 120: "三分相", 180: "對分相"}
MODERN_ASPECTS = {30: "十二分相", 45: "半四分相", 135: "八分之三相", 150: "十二分之五相"}

ASPECT_HARMONY = {
    "合相": "fusion", "六分相": "harmonious", "三分相": "harmonious",
    "四分相": "discordant", "對分相": "discordant",
    "十二分相": "minor_neutral", "半四分相": "minor_tension",
    "八分之三相": "minor_tension", "十二分之五相": "minor_neutral"
}

PLANET_NATURE = {
    "sun": "neutral", "moon": "neutral",
    "jupiter": "benefic", "venus": "benefic",
    "saturn": "malefic", "mars": "malefic",
    "mercury": "neutral"
}

HOUSE_TOPICS = {
    "personality":   [1, 3, 10],
    "wealth":        [2, 8, 11],
    "health":        [1, 6, 8],
    "marriage":      [7, 5, 11],
    "children":      [5, 11, 4],
    "career_status": [10, 1, 11],
    "travel":        [9, 3, 12],
    "lifespan":      [1, 8, 4],
    "death_quality": [8, 4, 12],
}

THEME_ZH = {
    "personality": "性格/個人特質",
    "wealth": "財富",
    "health": "健康",
    "marriage": "婚姻/伴侶",
    "children": "子女",
    "career_status": "事業/社會地位",
    "travel": "旅行/移居",
    "lifespan": "壽命能量",
    "death_quality": "死亡品質",
}

# ─────────────────────────────────────────────
# 資料結構
# ─────────────────────────────────────────────

@dataclass
class Planet:
    name_zh: str
    name_en: str
    sign_zh: str
    sign_en: str
    degree: float
    house: int
    retrograde: bool = False
    speed: str = "平均"
    solar_phase: str = ""
    # 本體之力（從占星之門讀取）
    has_domicile: bool = False
    has_exaltation: bool = False
    has_triplicity: bool = False
    triplicity_order: int = 0
    has_term: bool = False
    has_face: bool = False
    has_detriment: bool = False
    has_fall: bool = False
    is_peregrine: bool = False
    # 計算結果
    dignity_score: int = 0
    strength_label: str = ""

@dataclass
class Aspect:
    planet_a: str
    planet_b: str
    aspect_zh: str
    degrees: int
    orb: float
    is_ptolemy: bool
    harmony: str
    weight: float = 0.0

@dataclass
class HouseCusp:
    house: int
    sign_zh: str
    sign_en: str
    degree: float
    lord_zh: str
    lord_en: str

@dataclass
class Reception:
    planet_a: str
    planet_b: str
    reception_type: str  # "廟宮互容" / "廟旺互容" 等

@dataclass
class Chart:
    planets: dict = field(default_factory=dict)  # en_name -> Planet
    houses: dict = field(default_factory=dict)   # house_num -> HouseCusp
    aspects: list = field(default_factory=list)
    receptions: list = field(default_factory=list)
    is_diurnal: bool = True
    part_of_fortune_house: int = 0
    part_of_fortune_sign: str = ""

# ─────────────────────────────────────────────
# 解析器
# ─────────────────────────────────────────────

def parse_degree(deg_str: str) -> float:
    """解析度數字串，例如 '7°24'' -> 7.4"""
    deg_str = deg_str.strip()
    m = re.search(r"(\d+)[°度]\s*(\d+)?[′'分]?", deg_str)
    if m:
        d = int(m.group(1))
        mi = int(m.group(2)) if m.group(2) else 0
        return round(d + mi / 60, 2)
    try:
        return float(re.search(r"[\d.]+", deg_str).group())
    except:
        return 0.0

def parse_sign_degree(text: str):
    """從 '金牛座 7°24'' 解析星座與度數"""
    for sign_zh in SIGN_NUM:
        if sign_zh in text:
            deg_part = text.replace(sign_zh + "座", "").strip()
            return sign_zh, SIGN_EN[sign_zh], parse_degree(deg_part)
    return None, None, 0.0

def parse_planets(md: str) -> dict:
    """解析行星區段——占星之門格式：每欄獨立一行，中間有空行"""
    planets = {}
    PLANET_NAMES = ["太陽", "月亮", "水星", "金星", "火星", "木星", "土星"]

    # 只處理「星位：行星的星座與宮位」區段
    section = md
    if "## 星位" in md and "## 宮位" in md:
        start = md.index("## 星位")
        end = md.index("## 宮位")
        section = md[start:end]

    lines = section.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 找到行星名稱行（包含連結格式或純文字）
        for zh_name in PLANET_NAMES:
            if zh_name in line:
                retrograde = "℞" in line or (i > 0 and "℞" in lines[i-1])
                sign_zh, sign_en, deg = None, None, 0.0
                house = 0

                # 向下最多找10行
                for j in range(i+1, min(i+12, len(lines))):
                    l = lines[j].strip()
                    if not l:
                        continue
                    if not sign_zh:
                        s, se, d = parse_sign_degree(l)
                        if s:
                            sign_zh, sign_en, deg = s, se, d
                            continue
                    if not house:
                        hm = re.search(r"第(\d+)宮", l)
                        if hm:
                            house = int(hm.group(1))
                    # 若下一個行星名出現則停止
                    if any(p in l for p in PLANET_NAMES) and l != line:
                        break
                    if sign_zh and house:
                        break

                if sign_zh and house:
                    en_name = ZH_PLANET.get(zh_name, "")
                    if en_name and en_name not in planets:
                        planets[en_name] = Planet(
                            name_zh=zh_name, name_en=en_name,
                            sign_zh=sign_zh, sign_en=sign_en,
                            degree=deg, house=house, retrograde=retrograde
                        )
                break  # 同一行只匹配一個行星
        i += 1
    return planets

def parse_houses(md: str) -> dict:
    """解析宮位區段——占星之門格式：第N宮、宮始點、宮主星各自獨立一行"""
    houses = {}

    # 擷取宮位區段
    if "## 宮位" in md and "## 相位" in md:
        start = md.index("## 宮位")
        end = md.index("## 相位")
        section = md[start:end]
    else:
        section = md

    lines = section.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        hm = re.search(r"第(\d+)宮", line)
        if hm and "宮始點" not in line and "宮主星" not in line and "宮神星" not in line:
            house_num = int(hm.group(1))
            sign_zh, sign_en, deg = None, None, 0.0
            lord_zh = ""

            for j in range(i+1, min(i+10, len(lines))):
                l = lines[j].strip()
                if not l:
                    continue
                if not sign_zh:
                    s, se, d = parse_sign_degree(l)
                    if s:
                        sign_zh, sign_en, deg = s, se, d
                        continue
                if not lord_zh:
                    for p in ["太陽", "月亮", "水星", "金星", "火星", "木星", "土星"]:
                        if p in l:
                            lord_zh = p
                            break
                if sign_zh and lord_zh:
                    break

            if sign_zh and lord_zh and house_num not in houses:
                lord_en = ZH_PLANET.get(lord_zh, "")
                houses[house_num] = HouseCusp(
                    house=house_num, sign_zh=sign_zh, sign_en=sign_en,
                    degree=deg, lord_zh=lord_zh, lord_en=lord_en
                )
        i += 1
    return houses

def parse_aspects(md: str) -> list:
    """解析相位區段——占星之門格式：行星A、行星B、相位、容許度各自獨立一行"""
    aspects = []
    ASPECT_DEG_MAP = {
        "合相": 0, "六分相": 60, "四分相": 90, "三分相": 120,
        "二分相": 180, "對分相": 180, "180°": 180,
        "十二分相": 30, "半四分相": 45,
        "八分之三相": 135, "十二分之五相": 150
    }
    # 標準化名稱：二分相 → 對分相
    ASPECT_NORMALIZE = {"二分相": "對分相"}
    PLANET_NAMES = ["太陽", "月亮", "水星", "金星", "火星", "木星", "土星"]

    if "## 相位" in md:
        if "## 小行星" in md:
            end_marker = "## 小行星"
        elif "## 宮位" in md and md.index("## 宮位") > md.index("## 相位"):
            end_marker = None
        else:
            end_marker = None

        start = md.index("## 相位")
        section = md[start:md.index(end_marker) if end_marker and end_marker in md else start+5000]
    else:
        section = md

    lines = section.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        # 找到第一顆行星行
        planet_a = None
        for p in PLANET_NAMES:
            if p in line and "(" not in line.replace("(", ""):
                planet_a = p
                break
        if not planet_a:
            # 嘗試連結格式
            m = re.search(r"\[([太陽月亮水星金星火星木星土星]+)\]", line)
            if m and m.group(1) in PLANET_NAMES:
                planet_a = m.group(1)

        if planet_a:
            planet_b = None
            aspect_name = None
            orb = 0.0

            for j in range(i+1, min(i+8, len(lines))):
                l = lines[j].strip()
                if not l:
                    continue
                # 找行星B
                if not planet_b:
                    for p in PLANET_NAMES:
                        if p in l:
                            planet_b = p
                            break
                    if not planet_b:
                        m2 = re.search(r"\[([太陽月亮水星金星火星木星土星]+)\]", l)
                        if m2:
                            planet_b = m2.group(1)
                # 找相位名稱
                if not aspect_name:
                    for name in ASPECT_DEG_MAP:
                        if name in l:
                            aspect_name = name
                            break
                # 找容許度
                if not orb:
                    om = re.search(r"([\d.]+)°", l)
                    if om and aspect_name:
                        orb = float(om.group(1))

                if planet_b and aspect_name and orb:
                    break

            if planet_b and aspect_name:
                deg = ASPECT_DEG_MAP[aspect_name]
                aspect_name = ASPECT_NORMALIZE.get(aspect_name, aspect_name)
                is_ptolemy = deg in PTOLEMY_ASPECTS
                harmony = ASPECT_HARMONY.get(aspect_name, "neutral")
                en_a = ZH_PLANET.get(planet_a, planet_a)
                en_b = ZH_PLANET.get(planet_b, planet_b)

                # 避免重複
                exists = any(
                    (a.planet_a == en_a and a.planet_b == en_b and a.aspect_zh == aspect_name)
                    for a in aspects
                )
                if not exists:
                    aspects.append(Aspect(
                        planet_a=en_a, planet_b=en_b,
                        aspect_zh=aspect_name, degrees=deg, orb=orb,
                        is_ptolemy=is_ptolemy, harmony=harmony
                    ))
        i += 1
    return aspects

def parse_dignity_table(md: str, planets: dict):
    """解析本體之力表——占星之門格式的古占判斷區段"""
    PLANET_NAMES = ["太陽", "月亮", "水星", "金星", "火星", "木星", "土星"]

    # 擷取古占區段
    if "行星的本體之力" in md:
        start = md.index("行星的本體之力")
        section = md[start:start+2000]
    else:
        section = md

    lines = section.split("\n")

    # 找到表格行：行星名稱後跟廟旺三分界外觀陷弱的標記
    for i, line in enumerate(lines):
        for zh in PLANET_NAMES:
            en = ZH_PLANET.get(zh, "")
            if en not in planets:
                continue

            if zh in line:
                # 讀取接下來幾行作為這顆行星的尊貴列
                # 格式：行星名 / - 或 廟 / - 或 旺 / 三分標記 / - 或 界 / - 或 外觀 / - 或 陷 / - 或 弱
                context_lines = lines[i:i+20]
                context = " ".join(l.strip() for l in context_lines if l.strip())

                # 廟：下一個非空行若包含行星本身縮寫(如"廟")
                # 直接掃描該行後的幾行
                p = planets[en]
                for k, cl in enumerate(context_lines[1:], 1):
                    cl = cl.strip()
                    if not cl or cl == "-" or cl == "\\-":
                        continue
                    # 找廟旺三分等標記
                    if "廟" in cl and not any(other in cl for other in ["旺","三","界","觀","陷","弱"]):
                        p.has_domicile = True
                    if "旺" in cl and not any(other in cl for other in ["廟","三","界","觀","陷","弱"]):
                        p.has_exaltation = True
                    if "三分" in cl or re.search(zh + r"\d", cl):
                        p.has_triplicity = True
                        m = re.search(r"(\d)", cl)
                        if m:
                            p.triplicity_order = int(m.group(1))
                    if "界" in cl and "外" not in cl:
                        p.has_term = True
                    if "外觀" in cl or ("外" in cl and "觀" in cl):
                        p.has_face = True
                    if "陷" in cl:
                        p.has_detriment = True
                    if ("弱" in cl or "落" in cl) and "強弱" not in cl:
                        p.has_fall = True
                    # 遇到下一顆行星就停
                    if any(other in cl for other in PLANET_NAMES if other != zh) and k > 2:
                        break

    # 補充：用占星之門已計算好的表格文字做快速掃描
    # 格式示例：「月 旺 月2」、「金 界 金陷」
    for i, line in enumerate(lines):
        for zh in PLANET_NAMES:
            en = ZH_PLANET.get(zh, "")
            if en not in planets:
                continue
            p = planets[en]
            if zh in line:
                # 同行有廟旺等標記
                if "廟" in line: p.has_domicile = True
                if "旺" in line: p.has_exaltation = True
                if "陷" in line: p.has_detriment = True
                if "弱" in line or "落" in line: p.has_fall = True
                # 三分：格式 "月2" 或 "木2"
                short = zh[0]  # 取第一個字
                if re.search(short + r"\d", line):
                    p.has_triplicity = True

def parse_solar_status(md: str, planets: dict):
    """解析東出/西入/焦傷/逆行/速度狀態——從占星之門的古占判斷表"""
    PLANET_NAMES = ["太陽", "月亮", "水星", "金星", "火星", "木星", "土星"]

    # 找「星體的更多判斷」區段
    if "星體的更多判斷" in md:
        start = md.index("星體的更多判斷")
        section = md[start:start+2000]
    else:
        section = md

    lines = section.split("\n")

    # 每顆行星的狀態跨多行，格式：
    # [行星名]
    # [速度]
    # [距日狀態]
    # [東/西]
    for i, line in enumerate(lines):
        for zh in PLANET_NAMES:
            en = ZH_PLANET.get(zh, "")
            if en not in planets:
                continue
            if zh in line:
                p = planets[en]
                # 讀後面幾行
                for k in range(1, 8):
                    if i+k >= len(lines):
                        break
                    cl = lines[i+k].strip()
                    if not cl or cl == "-" or cl == "\\-":
                        continue
                    # 速度
                    if any(s in cl for s in ["逆行", "快", "慢", "平均", "停滯"]):
                        for s in ["逆行", "快", "慢", "平均", "停滯"]:
                            if s in cl:
                                p.speed = s
                                if s == "逆行":
                                    p.retrograde = True
                                break
                    # 距日
                    if "焦傷" in cl: p.solar_phase = "焦傷"
                    elif "偕日升" in cl: p.solar_phase = "偕日升"
                    elif "在日光下" in cl: p.solar_phase = "在日光下"
                    # 東西
                    if "東出" in cl and not p.solar_phase:
                        p.solar_phase = "東出"
                    elif "西入" in cl and not p.solar_phase:
                        p.solar_phase = "西入"
                    # 遇到下一顆行星停
                    if any(other in cl for other in PLANET_NAMES if other != zh) and k > 3:
                        break

def parse_receptions(md: str) -> list:
    """解析廟旺互容"""
    receptions = []
    PLANET_NAMES = ["太陽", "月亮", "水星", "金星", "火星", "木星", "土星"]
    RECEPTION_TYPES = ["廟宮互容", "廟旺互容", "旺宮互容", "互容"]

    if "廟旺互容" in md or "互容" in md:
        if "廟旺互容" in md:
            start = md.index("廟旺互容")
        else:
            start = md.index("互容")
        section = md[start:start+500]
    else:
        return receptions

    lines = section.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        for rtype in RECEPTION_TYPES:
            if rtype in line:
                # 找同行或前後行的兩顆行星
                all_lines = lines[max(0,i-3):i+3]
                found_planets = []
                for l in all_lines:
                    for p in PLANET_NAMES:
                        if p in l and p not in found_planets:
                            found_planets.append(p)
                if len(found_planets) >= 2:
                    receptions.append(Reception(
                        planet_a=ZH_PLANET.get(found_planets[0], found_planets[0]),
                        planet_b=ZH_PLANET.get(found_planets[1], found_planets[1]),
                        reception_type=rtype
                    ))
        i += 1
    return receptions

def determine_sect(planets: dict) -> bool:
    """判斷日間盤/夜間盤（太陽在7-12宮為晝生）"""
    sun = planets.get("sun")
    if sun:
        return sun.house in [7, 8, 9, 10, 11, 12]
    return True

# ─────────────────────────────────────────────
# 計算引擎
# ─────────────────────────────────────────────

def compute_dignity_score(planet: Planet, is_diurnal: bool) -> tuple[int, str]:
    """計算行星綜合尊貴分數——以 DIGNITY_LOOKUP 為主，解析旗標為輔"""
    score = 0
    en = planet.name_en
    sign_en = planet.sign_en
    dl = DIGNITY_LOOKUP.get(en, {})

    # ── 廟（Domicile）：查表優先 ──
    if sign_en in dl.get("domicile", []):
        planet.has_domicile = True
        planet.has_detriment = False
    # ── 陷（Detriment）：查表優先 ──
    if sign_en in dl.get("detriment", []):
        planet.has_detriment = True
        planet.has_domicile = False

    # ── 旺（Exaltation）：查表優先 ──
    if sign_en in dl.get("exaltation", []):
        planet.has_exaltation = True
        planet.has_fall = False
    # ── 落（Fall）：查表優先 ──
    if sign_en in dl.get("fall", []):
        planet.has_fall = True
        planet.has_exaltation = False

    # ── 三分性（Triplicity）：查表優先 ──
    triplicity_key = "triplicity_day" if is_diurnal else "triplicity_night"
    if sign_en in dl.get(triplicity_key, []):
        planet.has_triplicity = True

    # 計分
    if planet.has_domicile:
        score += DIGNITY_SCORES["domicile"]
    elif planet.has_exaltation:
        score += DIGNITY_SCORES["exaltation"]

    if planet.has_detriment:
        score += DIGNITY_SCORES["detriment"]
    elif planet.has_fall:
        score += DIGNITY_SCORES["fall"]

    if planet.has_triplicity:
        score += DIGNITY_SCORES["triplicity"]
    if planet.has_term:
        score += DIGNITY_SCORES["term"]
    if planet.has_face:
        score += DIGNITY_SCORES["face"]

    # 外來
    if not any([planet.has_domicile, planet.has_exaltation, planet.has_triplicity,
                planet.has_term, planet.has_face, planet.has_detriment, planet.has_fall]):
        planet.is_peregrine = True

    # 宮位強度
    score += HOUSE_STRENGTH.get(planet.house, 1)

    # 太陽距離修正
    score += SOLAR_PHASE_MODIFIER.get(planet.solar_phase, 0)

    # 速度修正
    score += SPEED_MODIFIER.get(planet.speed, 0)

    # 逆行額外扣分（已在 speed modifier 裡，但 speed 欄可能顯示「逆行」）
    if planet.retrograde and planet.speed not in SPEED_MODIFIER:
        score += SPEED_MODIFIER.get("逆行", -1)

    # 分類
    if score >= 8:
        label = "至強"
    elif score >= 5:
        label = "強力"
    elif score >= 2:
        label = "中等"
    elif score >= 0:
        label = "中性"
    else:
        label = "衰弱"

    return score, label

def compute_aspect_weights(aspects: list, planets: dict) -> list:
    """計算每個相位的加權效力，並去除重複"""
    WEIGHT_TABLE = {
        ("benefic","benefic","harmonious"): 5,
        ("benefic","benefic","fusion"):     4,
        ("benefic","malefic","harmonious"): 1,
        ("benefic","malefic","discordant"): -2,
        ("malefic","malefic","discordant"): -4,
        ("malefic","malefic","harmonious"): 1,
        ("benefic","neutral","harmonious"): 2,
        ("malefic","neutral","discordant"): -2,
        ("neutral","neutral","harmonious"): 1,
        ("neutral","neutral","discordant"): -1,
    }

    seen = set()
    unique_aspects = []

    for asp in aspects:
        # 去重：用排序後的行星對+相位名作為key
        key = tuple(sorted([asp.planet_a, asp.planet_b])) + (asp.aspect_zh,)
        if key in seen:
            continue
        seen.add(key)

        na = PLANET_NATURE.get(asp.planet_a, "neutral")
        nb = PLANET_NATURE.get(asp.planet_b, "neutral")
        h = asp.harmony

        # 嘗試各種key組合
        key1 = tuple(sorted([na, nb])) + (h,)
        key2 = (na, nb, h)
        key3 = (nb, na, h)
        weight = WEIGHT_TABLE.get(key1) or WEIGHT_TABLE.get(key2) or WEIGHT_TABLE.get(key3) or 0

        # 現代相位權重減半
        if not asp.is_ptolemy:
            weight = weight * 0.5

        # 容許度修正
        if asp.orb < 1:
            weight *= 1.3
        elif asp.orb > 8:
            weight *= 0.6
        elif asp.orb > 5:
            weight *= 0.8

        asp.weight = round(weight, 1)
        unique_aspects.append(asp)

    return unique_aspects

def track_flystar(houses: dict, planets: dict) -> dict:
    """飛星追蹤：每個宮位的廟主星落在哪個宮"""
    flystar = {}
    for house_num, cusp in houses.items():
        lord_en = cusp.lord_en
        if lord_en in planets:
            lord_planet = planets[lord_en]
            flystar[house_num] = {
                "lord": cusp.lord_zh,
                "lord_en": lord_en,
                "flies_to_house": lord_planet.house,
                "flies_to_sign": lord_planet.sign_zh,
                "lord_strength": lord_planet.strength_label,
                "lord_score": lord_planet.dignity_score
            }
    return flystar

def collect_theme_factors(theme: str, planets: dict, houses: dict,
                           aspects: list, flystar: dict, is_diurnal: bool) -> dict:
    """收集特定主題的所有相關因子"""
    relevant_houses = HOUSE_TOPICS.get(theme, [])
    factors = {
        "theme": theme,
        "theme_zh": THEME_ZH.get(theme, theme),
        "relevant_houses": relevant_houses,
        "house_analysis": {},
        "key_planets": {},
        "relevant_aspects": [],
        "flystar_connections": [],
        "receptions_involved": [],
        "overall_score": 0,
        "scenario_type": ""
    }

    positive_score = 0
    negative_score = 0

    def dignity_only_score(p: Planet) -> int:
        """只計算尊貴分數，不含宮位/速度/距日等修正"""
        s = 0
        if p.has_domicile: s += DIGNITY_SCORES["domicile"]
        elif p.has_exaltation: s += DIGNITY_SCORES["exaltation"]
        if p.has_detriment: s += DIGNITY_SCORES["detriment"]
        elif p.has_fall: s += DIGNITY_SCORES["fall"]
        if p.has_triplicity: s += DIGNITY_SCORES["triplicity"]
        if p.has_term: s += DIGNITY_SCORES["term"]
        if p.has_face: s += DIGNITY_SCORES["face"]
        if p.retrograde: s -= 1
        if p.solar_phase == "焦傷": s -= 2
        return s

    # 分析相關宮位
    for h in relevant_houses:
        house_info = {}
        cusp = houses.get(h, {})
        if cusp:
            house_info["cusp_sign"] = cusp.sign_zh if hasattr(cusp, 'sign_zh') else ""
            house_info["lord"] = cusp.lord_zh if hasattr(cusp, 'lord_zh') else ""
            lord_en = cusp.lord_en if hasattr(cusp, 'lord_en') else ""
            if lord_en and lord_en in planets:
                lp = planets[lord_en]
                house_info["lord_score"] = lp.dignity_score
                house_info["lord_strength"] = lp.strength_label
                house_info["lord_in_house"] = lp.house
                house_info["lord_in_sign"] = lp.sign_zh
                ds = dignity_only_score(lp)
                if ds > 0:
                    positive_score += ds
                elif ds < 0:
                    negative_score += abs(ds)

        # 宮內行星
        planets_in_house = [p for p in planets.values() if p.house == h]
        house_info["planets_in_house"] = []
        for p in planets_in_house:
            pinfo = {
                "planet": p.name_zh,
                "sign": p.sign_zh,
                "score": p.dignity_score,
                "strength": p.strength_label,
                "nature": PLANET_NATURE.get(p.name_en, "neutral"),
                "retrograde": p.retrograde
            }
            house_info["planets_in_house"].append(pinfo)
            nature = PLANET_NATURE.get(p.name_en, "neutral")
            ds = dignity_only_score(p)
            if nature == "benefic":
                if ds > 0: positive_score += ds
                elif ds < 0: negative_score += abs(ds)
            elif nature == "malefic":
                if ds < 0: negative_score += abs(ds) + 1
                else: negative_score += 1  # 凶星即使外來也有基礎壓力

        factors["house_analysis"][f"house_{h}"] = house_info

        # 飛星
        if h in flystar:
            fs = flystar[h]
            factors["flystar_connections"].append({
                "from_house": h,
                "lord": fs["lord"],
                "flies_to": fs["flies_to_house"],
                "lord_strength": fs["lord_strength"]
            })

    # 相關相位（只取與主題行星相關的）
    theme_planet_names = set()
    for h in relevant_houses:
        cusp = houses.get(h)
        if cusp and hasattr(cusp, 'lord_en'):
            theme_planet_names.add(cusp.lord_en)
        for p in planets.values():
            if p.house == h:
                theme_planet_names.add(p.name_en)

    for asp in aspects:
        if asp.planet_a in theme_planet_names or asp.planet_b in theme_planet_names:
            factors["relevant_aspects"].append({
                "a": PLANET_ZH.get(asp.planet_a, asp.planet_a),
                "b": PLANET_ZH.get(asp.planet_b, asp.planet_b),
                "aspect": asp.aspect_zh,
                "orb": asp.orb,
                "is_ptolemy": asp.is_ptolemy,
                "harmony": asp.harmony,
                "weight": asp.weight
            })
            if asp.weight > 0:
                positive_score += asp.weight
            else:
                negative_score += abs(asp.weight)

    # 整體評分與場景類型
    net = positive_score - negative_score
    factors["overall_score"] = round(net, 1)
    factors["positive_score"] = round(positive_score, 1)
    factors["negative_score"] = round(negative_score, 1)

    if net >= 5:
        factors["scenario_type"] = "順遂"
    elif net <= -5:
        factors["scenario_type"] = "阻礙"
    else:
        factors["scenario_type"] = "張力"

    return factors

def compute_part_of_fortune(planets: dict, is_diurnal: bool) -> tuple[str, float]:
    """計算福點"""
    sun = planets.get("sun")
    moon = planets.get("moon")
    if not sun or not moon:
        return "", 0.0

    sun_deg = (SIGN_NUM.get(sun.sign_zh, 1) - 1) * 30 + sun.degree
    moon_deg = (SIGN_NUM.get(moon.sign_zh, 1) - 1) * 30 + moon.degree

    asc_house = 1
    asc_deg = 0.0  # 簡化，實際需要上升度數

    if is_diurnal:
        pof_deg = (asc_deg + moon_deg - sun_deg) % 360
    else:
        pof_deg = (asc_deg + sun_deg - moon_deg) % 360

    sign_num = int(pof_deg // 30) + 1
    sign_zh = NUM_SIGN.get(sign_num, "")
    return sign_zh, round(pof_deg % 30, 2)

# ─────────────────────────────────────────────
# 主程式：解析 + 計算 + 輸出報告
# ─────────────────────────────────────────────

def _parse_planets_v2(md: str) -> dict:
    """新解析器：支援單行壓縮格式（占星之門最新版）"""
    planets = {}
    full = md.replace('\n', ' ')
    SIGNS_LOCAL = list(SIGN_EN.keys())

    for zh_name in ["太陽","月亮","水星","金星","火星","木星","土星"]:
        en_name = ZH_PLANET.get(zh_name, "")
        pat = re.compile(
            re.escape(zh_name) +
            r'[^\u4e00-\u9fff]*?℞?\s*'
            r'([牡金雙巨獅處天射魔水][羊牛子蟹子女秤蠍手羯瓶魚])[座]?\s*'
            r'(\d+)[°度]\s*(\d+)?[°\'′]?\s*第(\d+)宮'
        )
        m = pat.search(full)
        if m:
            sign_raw = m.group(1)
            sign_zh = sign_raw
            for s in SIGNS_LOCAL:
                if s.startswith(sign_raw) or sign_raw == s[:2]:
                    sign_zh = s; break
            deg = float(m.group(2)) + (float(m.group(3))/60 if m.group(3) else 0)
            house = int(m.group(4))
            window = full[max(0, m.start()-8):m.start()+len(zh_name)+4]
            retro = '℞' in window
            planets[en_name] = Planet(
                name_zh=zh_name, name_en=en_name,
                sign_zh=sign_zh, sign_en=SIGN_EN.get(sign_zh, ""),
                degree=round(deg, 2), house=house, retrograde=retro
            )

    # fallback：舊版多行格式
    if not planets:
        planets = parse_planets(md)
    return planets

def _parse_houses_v2(md: str) -> dict:
    """新解析器：支援單行壓縮格式"""
    houses = {}
    full = md.replace('\n', ' ')
    SIGNS_LOCAL = list(SIGN_EN.keys())
    PLANET_LIST = ["太陽","月亮","水星","金星","火星","木星","土星"]

    for h in range(1, 13):
        pat = re.compile(
            r'第' + str(h) + r'宮\s*'
            r'([牡金雙巨獅處天射魔水][羊牛子蟹子女秤蠍手羯瓶魚])[座]?\s*'
            r'[\d°\'′\s]+\s*'
            r'([太陽月亮水星金星火星木星土星]{2})'
        )
        m = pat.search(full)
        if m:
            sign_raw = m.group(1)
            sign_zh = sign_raw
            for s in SIGNS_LOCAL:
                if s.startswith(sign_raw): sign_zh = s; break
            lord_zh = m.group(2)
            if lord_zh in ZH_PLANET:
                houses[h] = HouseCusp(
                    house=h, sign_zh=sign_zh, sign_en=SIGN_EN.get(sign_zh, ""),
                    degree=0.0, lord_zh=lord_zh, lord_en=ZH_PLANET[lord_zh]
                )

    if not houses:
        houses = parse_houses(md)
    return houses

def _parse_aspects_v2(md: str) -> list:
    """新解析器：支援單行壓縮格式"""
    aspects = []
    full = md.replace('\n', ' ')
    ASPECT_MAP = {
        '合相':0, '六分相':60, '四分相':90, '三分相':120,
        '對分相':180, '二分相':180,
        '十二分相':30, '半四分相':45, '八分之三相':135, '十二分之五相':150
    }
    PTOL = {0, 60, 90, 120, 180}
    seen = set()

    pat = re.compile(
        r'([太陽月亮水星金星火星木星土星]{2})\s+'
        r'([太陽月亮水星金星火星木星土星]{2})\s+'
        r'([^\d（(]{2,8}?)\s*[（(][^）)]*[）)]\s*([\d.]+)°'
    )
    for m in pat.finditer(full):
        pa, pb = m.group(1), m.group(2)
        asp_raw, orb = m.group(3).strip(), float(m.group(4))
        asp = None
        for name in ASPECT_MAP:
            if name in asp_raw: asp = name; break
        if not asp: continue
        if pa not in ZH_PLANET or pb not in ZH_PLANET: continue
        key = tuple(sorted([pa, pb])) + (asp,)
        if key in seen: continue
        seen.add(key)
        deg = ASPECT_MAP[asp]
        asp_name = '對分相' if asp == '二分相' else asp
        aspects.append(Aspect(
            planet_a=ZH_PLANET[pa], planet_b=ZH_PLANET[pb],
            aspect_zh=asp_name, degrees=deg, orb=orb,
            is_ptolemy=(deg in PTOL),
            harmony=ASPECT_HARMONY.get(asp_name, "neutral")
        ))

    if not aspects:
        aspects = parse_aspects(md)
    return aspects

def _parse_dignity_v2(md: str, planets: dict):
    """新解析器：本體之力表"""
    full = md.replace('\n', ' ')
    section = full
    if '行星的本體之力' in full:
        idx = full.index('行星的本體之力')
        section = full[idx:idx+800]

    ALL_ZH = ["太陽","月亮","水星","金星","火星","木星","土星"]
    for zh_name in ALL_ZH:
        en = ZH_PLANET.get(zh_name, "")
        if en not in planets: continue
        p = planets[en]

        # 找到行星那一列的內容
        others = [re.escape(z) for z in ALL_ZH if z != zh_name]
        pat = re.compile(re.escape(zh_name) + r'(.{3,150}?)(?=' + '|'.join(others) + r'|ⓘ|$)')
        m = pat.search(section)
        if not m: continue
        row = m.group(1)

        if '廟' in row: p.has_domicile = True
        if '旺' in row: p.has_exaltation = True
        if '陷' in row: p.has_detriment = True
        if '弱' in row: p.has_fall = True

        short = zh_name[0]
        tm = re.search(short + r'(\d)', row)
        if tm:
            p.has_triplicity = True
            p.triplicity_order = int(tm.group(1))

        # 界與外觀：從表格欄位判斷
        cols = [c.strip() for c in re.split(r'[\s-]+', row) if c.strip()]
        for col in cols:
            if '界' in col: p.has_term = True
            if '外' in col and ('觀' in col or len(col) <= 3): p.has_face = True

        if not any([p.has_domicile, p.has_exaltation, p.has_triplicity,
                    p.has_term, p.has_face, p.has_detriment, p.has_fall]):
            p.is_peregrine = True

def _parse_solar_v2(md: str, planets: dict):
    """新解析器：速度/距日/東西"""
    full = md.replace('\n', ' ')
    section = full
    if '星體的更多判斷' in full:
        idx = full.index('星體的更多判斷')
        section = full[idx:idx+600]

    ALL_ZH = ["太陽","月亮","水星","金星","火星","木星","土星"]
    for zh_name in ALL_ZH:
        en = ZH_PLANET.get(zh_name, "")
        if en not in planets: continue
        p = planets[en]

        others = [re.escape(z) for z in ALL_ZH if z != zh_name]
        pat = re.compile(re.escape(zh_name) + r'(.{3,120}?)(?=' + '|'.join(others) + r'|廟旺|ⓘ|$)')
        m = pat.search(section)
        if not m: continue
        row = m.group(1)

        for sp in ['逆行','快','慢','平均','停滯']:
            if sp in row:
                p.speed = sp
                if sp == '逆行': p.retrograde = True
                break

        for status in ['焦傷','偕日升','在日光下']:
            if status in row:
                p.solar_phase = status; break

        if not p.solar_phase:
            if '東出' in row: p.solar_phase = '東出'
            elif '西入' in row: p.solar_phase = '西入'

def _parse_receptions_v2(md: str) -> list:
    """新解析器：互容"""
    receptions = []
    full = md.replace('\n', ' ')
    section = ""
    if '廟旺互容' in full:
        idx = full.index('廟旺互容')
        section = full[max(0,idx-20):idx+400]
    elif '互容' in full:
        idx = full.index('互容')
        section = full[max(0,idx-20):idx+400]
    else:
        return receptions

    seen = set()
    pat = re.compile(r'([太陽月亮水星金星火星木星土星]{2})\s*([太陽月亮水星金星火星木星土星]{2})\s*(廟宮互容|廟旺互容|旺宮互容|互容)')
    for m in pat.finditer(section):
        pa, pb, rtype = m.group(1), m.group(2), m.group(3)
        if pa not in ZH_PLANET or pb not in ZH_PLANET: continue
        key = tuple(sorted([pa, pb]))
        if key in seen: continue
        seen.add(key)
        receptions.append(Reception(
            planet_a=ZH_PLANET[pa], planet_b=ZH_PLANET[pb], reception_type=rtype
        ))
    return receptions

def parse_chart(md: str) -> Chart:
    chart = Chart()

    # 使用支援單行格式的新解析器
    chart.planets = _parse_planets_v2(md)
    chart.houses = _parse_houses_v2(md)
    chart.aspects = _parse_aspects_v2(md)
    chart.receptions = _parse_receptions_v2(md)
    chart.is_diurnal = determine_sect(chart.planets)

    _parse_dignity_v2(md, chart.planets)
    _parse_solar_v2(md, chart.planets)

    # 計算分數
    for en, planet in chart.planets.items():
        score, label = compute_dignity_score(planet, chart.is_diurnal)
        planet.dignity_score = score
        planet.strength_label = label

    chart.aspects = compute_aspect_weights(chart.aspects, chart.planets)
    return chart

def generate_report(chart: Chart, theme: str = None) -> dict:
    """生成結構化解盤事實報告"""

    flystar = track_flystar(chart.houses, chart.planets)

    # 基本盤面
    sun = chart.planets.get("sun", Planet("太陽","sun","","",0,0))
    moon = chart.planets.get("moon", Planet("月亮","moon","","",0,0))
    asc_house = chart.houses.get(1)

    report = {
        "盤面基本資訊": {
            "日夜間盤": "晝生盤（日間盤）" if chart.is_diurnal else "夜生盤（夜間盤）",
            "主要吉星": "木星" if chart.is_diurnal else "金星",
            "主要凶星": "土星" if chart.is_diurnal else "火星",
            "三骨架": {
                "上升": f"{asc_house.sign_zh}座 {asc_house.degree}° / 守護星：{asc_house.lord_zh}" if asc_house else "",
                "太陽": f"{sun.sign_zh}座 {sun.degree}° / 第{sun.house}宮 / {sun.strength_label}",
                "月亮": f"{moon.sign_zh}座 {moon.degree}° / 第{moon.house}宮 / {moon.strength_label} / {'焦傷⚠️' if moon.solar_phase == '焦傷' else '正常'}"
            }
        },
        "七行星本體之力": {},
        "宮內多星分析": {},
        "托勒密相位（核心）": [],
        "現代相位（補充）": [],
        "飛星追蹤": {},
        "廟旺互容": [],
    }

    # 七行星報告
    for en in ["sun","moon","mercury","venus","mars","jupiter","saturn"]:
        p = chart.planets.get(en)
        if not p:
            continue
        report["七行星本體之力"][p.name_zh] = {
            "星座": p.sign_zh,
            "宮位": f"第{p.house}宮（{'角宮' if HOUSE_TYPE.get(p.house)=='angular' else '續宮' if HOUSE_TYPE.get(p.house)=='succedent' else '果宮'}）",
            "逆行": "是" if p.retrograde else "否",
            "太陽距離狀態": p.solar_phase or "正常",
            "速度": p.speed,
            "尊貴": {
                "廟": "✓" if p.has_domicile else "-",
                "旺": "✓" if p.has_exaltation else "-",
                "三分": "✓" if p.has_triplicity else "-",
                "界": "✓" if p.has_term else "-",
                "外觀": "✓" if p.has_face else "-",
                "陷": "✓" if p.has_detriment else "-",
                "落": "✓" if p.has_fall else "-",
                "外來": "✓" if p.is_peregrine else "-"
            },
            "綜合尊貴分數": p.dignity_score,
            "力量等級": p.strength_label
        }

    # 宮內多星分析
    for house_num in range(1, 13):
        planets_in_h = [p for p in chart.planets.values() if p.house == house_num]
        if len(planets_in_h) >= 2:
            cusp = chart.houses.get(house_num)
            sorted_planets = sorted(planets_in_h, key=lambda x: x.dignity_score, reverse=True)
            report["宮內多星分析"][f"第{house_num}宮"] = {
                "宮頭星座": cusp.sign_zh if cusp else "",
                "宮主星": cusp.lord_zh if cusp else "",
                "宮內行星（強弱排序）": [
                    {"行星": p.name_zh, "分數": p.dignity_score,
                     "強弱": p.strength_label, "吉凶性": PLANET_NATURE.get(p.name_en,"?")}
                    for p in sorted_planets
                ],
                "整合判斷": _judge_multi_planet(sorted_planets)
            }

    # 相位分類
    for asp in sorted(chart.aspects, key=lambda x: abs(x.weight), reverse=True):
        asp_dict = {
            "行星A": PLANET_ZH.get(asp.planet_a, asp.planet_a),
            "行星B": PLANET_ZH.get(asp.planet_b, asp.planet_b),
            "相位": asp.aspect_zh,
            "容許度": f"{asp.orb}°",
            "和諧性": asp.harmony,
            "效力權重": asp.weight
        }
        if asp.is_ptolemy:
            report["托勒密相位（核心）"].append(asp_dict)
        else:
            report["現代相位（補充）"].append(asp_dict)

    # 飛星
    for h, fs in flystar.items():
        report["飛星追蹤"][f"第{h}宮主宰"] = {
            "廟主星": fs["lord"],
            "飛入": f"第{fs['flies_to_house']}宮（{fs['flies_to_sign']}座）",
            "主宰星力量": f"{fs['lord_strength']}（分數：{fs['lord_score']}）"
        }

    # 互容
    for r in chart.receptions:
        report["廟旺互容"].append({
            "行星A": PLANET_ZH.get(r.planet_a, r.planet_a),
            "行星B": PLANET_ZH.get(r.planet_b, r.planet_b),
            "互容類型": r.reception_type
        })

    # 特定主題分析
    if theme:
        flystar_full = track_flystar(chart.houses, chart.planets)
        theme_factors = collect_theme_factors(
            theme, chart.planets, chart.houses,
            chart.aspects, flystar_full, chart.is_diurnal
        )
        report[f"主題分析：{THEME_ZH.get(theme, theme)}"] = theme_factors

    return report

def _judge_multi_planet(planets: list) -> str:
    """判斷多星同宮的整合性質"""
    natures = [PLANET_NATURE.get(p.name_en, "neutral") for p in planets]
    scores = [p.dignity_score for p in planets]

    benefics = [p for p in planets if PLANET_NATURE.get(p.name_en) == "benefic"]
    malefics = [p for p in planets if PLANET_NATURE.get(p.name_en) == "malefic"]

    if malefics and not benefics:
        return f"全凶組合：{'/'.join(p.name_zh for p in malefics)}同宮，主題壓力集中"
    elif benefics and not malefics:
        return f"全吉組合：{'/'.join(p.name_zh for p in benefics)}同宮，主題資源加乘"
    elif benefics and malefics:
        return f"吉凶混合：{'/'.join(p.name_zh for p in benefics)}（吉）與{'/'.join(p.name_zh for p in malefics)}（凶）同宮，存在張力場景"
    else:
        strongest = planets[0]
        return f"中性組合：以{strongest.name_zh}（{strongest.strength_label}）為主導"

# ─────────────────────────────────────────────
# CLI 入口
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="星命師 v2 計算層")
    parser.add_argument("input", help="占星之門盤面 Markdown 檔案路徑")
    parser.add_argument("--theme", help="主題分析（personality/wealth/marriage/health/career_status/children/travel/lifespan）", default=None)
    parser.add_argument("--all-themes", action="store_true", help="輸出所有主題分析")
    parser.add_argument("--output", help="輸出 JSON 檔案路徑", default=None)
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        md = f.read()

    chart = parse_chart(md)

    if args.all_themes:
        reports = {}
        for theme in HOUSE_TOPICS:
            reports[theme] = generate_report(chart, theme)
        report = reports
    else:
        report = generate_report(chart, args.theme)

    output_json = json.dumps(report, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_json)
        print(f"✅ 報告已輸出至：{args.output}")
    else:
        print(output_json)

if __name__ == "__main__":
    main()

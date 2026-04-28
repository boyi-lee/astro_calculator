import streamlit as st
import json
import sys
import os

# 引入計算引擎
sys.path.insert(0, os.path.dirname(__file__))
from astro_calculator import parse_chart, generate_report, THEME_ZH as THEME_NAMES, HOUSE_TOPICS

# ── 頁面設定 ──
st.set_page_config(
    page_title="星命師",
    page_icon="☽",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ── 樣式 ──
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Noto Serif TC', serif;
}
.block-container { max-width: 720px; padding-top: 2rem; }

/* 標題 */
.title-block {
    text-align: center;
    padding: 2rem 0 1.5rem;
    border-bottom: 1px solid rgba(184,150,46,0.3);
    margin-bottom: 2rem;
}
.title-symbol { color: #b8962e; font-size: 13px; letter-spacing: 6px; opacity: 0.7; }
.title-main { font-size: 2.8rem; font-weight: 300; letter-spacing: 10px; color: #f5f0e8; margin: 8px 0 4px; }
.title-sub { font-size: 12px; letter-spacing: 3px; color: #b8962e; opacity: 0.5; }

/* 區塊標籤 */
.section-label {
    font-size: 10px; letter-spacing: 4px; color: #b8962e;
    opacity: 0.7; text-transform: uppercase; margin-bottom: 0.5rem;
}

/* 解盤結果卡片 */
.segment-card {
    background: rgba(245,240,232,0.03);
    border: 1px solid rgba(184,150,46,0.15);
    border-left: 2px solid #b8962e;
    border-radius: 2px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}
.segment-title {
    font-size: 10px; letter-spacing: 4px; color: #b8962e;
    opacity: 0.6; text-transform: uppercase; margin-bottom: 0.5rem;
}
.segment-content {
    font-size: 15px; line-height: 2; color: rgba(245,240,232,0.85);
    font-weight: 300;
}
.segment-scene {
    font-size: 16px; line-height: 1.9; color: rgba(245,240,232,0.7);
    font-style: italic;
}

/* 場景標籤 */
.tag-good { color: #7aad84; border: 1px solid rgba(74,92,78,0.6); padding: 2px 10px; border-radius: 12px; font-size: 12px; letter-spacing: 2px; }
.tag-tension { color: #d4b254; border: 1px solid rgba(184,150,46,0.6); padding: 2px 10px; border-radius: 12px; font-size: 12px; letter-spacing: 2px; }
.tag-hard { color: #c4725f; border: 1px solid rgba(139,58,42,0.6); padding: 2px 10px; border-radius: 12px; font-size: 12px; letter-spacing: 2px; }

/* 行星表格 */
.planet-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 6px 0; border-bottom: 1px solid rgba(184,150,46,0.08);
    font-size: 13px;
}
.planet-name { color: #b8962e; width: 40px; }
.planet-pos { color: rgba(245,240,232,0.7); flex: 1; }
.planet-score { text-align: right; }
.score-strong { color: #7aad84; }
.score-medium { color: #d4b254; }
.score-weak { color: #c4725f; }

/* 相位列表 */
.aspect-row {
    font-size: 12px; padding: 4px 0;
    color: rgba(245,240,232,0.6);
    border-bottom: 1px solid rgba(184,150,46,0.06);
}
.aspect-positive { color: rgba(122,173,132,0.8); }
.aspect-negative { color: rgba(196,114,95,0.8); }
</style>
""", unsafe_allow_html=True)

# ── 標題 ──
st.markdown("""
<div class="title-block">
    <div class="title-symbol">✦ Tetrabiblos ✦</div>
    <div class="title-main">星命師</div>
    <div class="title-sub">傳統占星解盤</div>
</div>
""", unsafe_allow_html=True)

# ── Session State ──
if "chart" not in st.session_state:
    st.session_state.chart = None
if "report" not in st.session_state:
    st.session_state.report = None
if "theme" not in st.session_state:
    st.session_state.theme = "personality"
if "md_content" not in st.session_state:
    st.session_state.md_content = ""

# ── 盤面輸入 ──
st.markdown('<div class="section-label">盤面資料</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📎 上傳 .md 檔案", "📋 貼上文字"])

with tab1:
    uploaded = st.file_uploader("占星之門盤面檔案", type=["md", "txt"], label_visibility="collapsed")
    if uploaded:
        st.session_state.md_content = uploaded.read().decode("utf-8")
        st.success(f"✓ 已載入：{uploaded.name}")

with tab2:
    pasted = st.text_area(
        "貼上盤面 Markdown",
        height=200,
        placeholder="將占星之門盤面的 Markdown 內容貼在此處...",
        label_visibility="collapsed"
    )
    if pasted:
        st.session_state.md_content = pasted

# ── 主題選擇 ──
st.markdown('<div class="section-label" style="margin-top:1.5rem">解盤主題</div>', unsafe_allow_html=True)

THEME_OPTIONS = {
    "personality":   "☿ 性格特質",
    "wealth":        "☽ 財富",
    "marriage":      "♀ 婚姻伴侶",
    "career_status": "☉ 事業地位",
    "health":        "♂ 健康",
    "children":      "♃ 子女",
    "travel":        "♄ 旅行移居",
    "lifespan":      "⊕ 壽命能量",
    "death_quality": "★ 死亡品質",
}

cols = st.columns(3)
theme_keys = list(THEME_OPTIONS.keys())
for i, (key, label) in enumerate(THEME_OPTIONS.items()):
    with cols[i % 3]:
        if st.button(
            label,
            key=f"theme_{key}",
            use_container_width=True,
            type="primary" if st.session_state.theme == key else "secondary"
        ):
            st.session_state.theme = key
            st.rerun()

st.markdown(f"**目前選擇：** {THEME_OPTIONS.get(st.session_state.theme, '')}", unsafe_allow_html=False)

# ── 開始解盤 ──
st.markdown("")
if st.button("開始解盤", type="primary", use_container_width=True):
    if not st.session_state.md_content:
        st.error("請先上傳盤面檔案或貼上盤面內容")
    else:
        with st.spinner("解析盤面中…"):
            try:
                chart = parse_chart(st.session_state.md_content)
                report = generate_report(chart, st.session_state.theme)
                st.session_state.chart = chart
                st.session_state.report = report
                st.rerun()
            except Exception as e:
                st.error(f"解盤失敗：{str(e)}")

# ── 顯示結果 ──
if st.session_state.report:
    report = st.session_state.report
    chart = st.session_state.chart
    theme_zh = THEME_NAMES.get(st.session_state.theme, st.session_state.theme)

    st.markdown("---")

    # 主題標題 + 場景類型
    theme_key_result = f"主題分析：{theme_zh}"
    theme_data = report.get(theme_key_result, {})
    scenario = theme_data.get("scenario_type", "張力")

    tag_map = {"順遂": "tag-good", "張力": "tag-tension", "阻礙": "tag-hard"}
    tag_class = tag_map.get(scenario, "tag-tension")

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:1.5rem;padding-bottom:1rem;border-bottom:1px solid rgba(184,150,46,0.25)">
        <span style="font-size:11px;letter-spacing:3px;color:#b8962e;opacity:0.7;text-transform:uppercase">{theme_zh}</span>
        <span class="{tag_class}">{scenario}</span>
    </div>
    """, unsafe_allow_html=True)

    # ── 主題因子分析 ──
    if theme_data:
        positive = theme_data.get("positive_score", 0)
        negative = theme_data.get("negative_score", 0)
        net = theme_data.get("overall_score", 0)

        col1, col2, col3 = st.columns(3)
        col1.metric("正向因子", f"+{positive}")
        col2.metric("負向因子", f"-{negative}")
        col3.metric("淨分", f"{net:+.1f}")

        # 宮位分析
        house_analysis = theme_data.get("house_analysis", {})
        if house_analysis:
            st.markdown('<div class="section-label" style="margin-top:1rem">主題宮位分析</div>', unsafe_allow_html=True)
            for hkey, hdata in house_analysis.items():
                house_num = hkey.replace("house_", "第") + "宮"
                lord = hdata.get("lord", "")
                lord_strength = hdata.get("lord_strength", "")
                lord_house = hdata.get("lord_in_house", "")
                planets_in = hdata.get("planets_in_house", [])

                col_a, col_b = st.columns([1, 2])
                with col_a:
                    st.markdown(f"**{house_num}**")
                with col_b:
                    info = f"宮主 {lord} → 第{lord_house}宮 [{lord_strength}]"
                    st.markdown(info)
                    if planets_in:
                        for p in planets_in:
                            retro = " ℞" if p.get("retrograde") else ""
                            st.markdown(f"　宮內：{p['planet']} {p['sign']}{retro} [{p['strength']}]")

        # 飛星
        flystar = theme_data.get("flystar_connections", [])
        if flystar:
            st.markdown('<div class="section-label" style="margin-top:1rem">飛星連結</div>', unsafe_allow_html=True)
            for fs in flystar:
                st.markdown(f"第{fs['from_house']}宮 **{fs['lord']}** → 第{fs['flies_to']}宮 ｜ {fs['lord_strength']}")

        # 相關相位
        relevant_aspects = theme_data.get("relevant_aspects", [])
        if relevant_aspects:
            st.markdown('<div class="section-label" style="margin-top:1rem">相關相位</div>', unsafe_allow_html=True)
            for asp in relevant_aspects[:8]:
                ptol_mark = "◆" if asp["is_ptolemy"] else "◇"
                weight = asp["weight"]
                color_class = "aspect-positive" if weight > 0 else ("aspect-negative" if weight < 0 else "")
                st.markdown(
                    f'<div class="aspect-row {color_class}">{ptol_mark} {asp["a"]} {asp["aspect"]} {asp["b"]} （{asp["orb"]}°）效力：{weight:+.1f}</div>',
                    unsafe_allow_html=True
                )

    st.markdown("---")

    # ── 七行星本體之力 ──
    with st.expander("七行星本體之力", expanded=False):
        planets_data = report.get("七行星本體之力", {})
        for planet_name, pdata in planets_data.items():
            score = pdata.get("綜合尊貴分數", 0)
            strength = pdata.get("力量等級", "")
            sign = pdata.get("星座", "")
            house = pdata.get("宮位", "")
            retro = pdata.get("逆行", "否")
            solar = pdata.get("太陽距離狀態", "")

            score_class = "score-strong" if score >= 5 else ("score-weak" if score < 0 else "score-medium")
            retro_mark = " ℞" if retro == "是" else ""
            solar_mark = f" · {solar}" if solar and solar != "正常" else ""

            st.markdown(
                f'<div class="planet-row">'
                f'<span class="planet-name">{planet_name}</span>'
                f'<span class="planet-pos">{sign} {house}{retro_mark}{solar_mark}</span>'
                f'<span class="planet-score {score_class}">{strength}（{score:+d}）</span>'
                f'</div>',
                unsafe_allow_html=True
            )

    # ── 托勒密相位 ──
    with st.expander("托勒密相位（核心）", expanded=False):
        for asp in report.get("托勒密相位（核心）", []):
            weight = asp["效力權重"]
            color = "aspect-positive" if weight > 0 else ("aspect-negative" if weight < 0 else "")
            st.markdown(
                f'<div class="aspect-row {color}">'
                f'{asp["行星A"]} {asp["相位"]} {asp["行星B"]} '
                f'（{asp["容許度"]}）效力：{weight:+.1f}'
                f'</div>',
                unsafe_allow_html=True
            )

    # ── 現代相位 ──
    with st.expander("現代相位（補充）", expanded=False):
        modern = report.get("現代相位（補充）", [])
        if modern:
            for asp in modern:
                st.markdown(f'{asp["行星A"]} {asp["相位"]} {asp["行星B"]} （{asp["容許度"]}）')
        else:
            st.markdown("無現代相位")

    # ── 飛星總覽 ──
    with st.expander("飛星追蹤（全部12宮）", expanded=False):
        for hkey, fdata in report.get("飛星追蹤", {}).items():
            st.markdown(
                f"**{hkey}**：{fdata['廟主星']} → {fdata['飛入']} ｜ {fdata['主宰星力量']}"
            )

    # ── 廟旺互容 ──
    receptions = report.get("廟旺互容", [])
    if receptions:
        with st.expander("廟旺互容", expanded=False):
            for r in receptions:
                st.markdown(f"{r['行星A']} ↔ {r['行星B']} · {r['互容類型']}")

    # ── 宮內多星 ──
    multi = report.get("宮內多星分析", {})
    if multi:
        with st.expander("宮內多星分析", expanded=False):
            for hkey, hdata in multi.items():
                st.markdown(f"**{hkey}**：{hdata['整合判斷']}")
                for p in hdata.get("宮內行星（強弱排序）", []):
                    st.markdown(f"　{p['行星']} {p['分數']:+d} [{p['強弱']}] {p['吉凶性']}")

    # ── JSON 匯出（給 Gem 用）──
    st.markdown("---")
    st.markdown('<div class="section-label">匯出給星命師 Gem</div>', unsafe_allow_html=True)
    st.markdown("將下方 JSON 複製，貼給 Gemini 星命師 Gem 進行場景化解盤。")

    # 只匯出主題分析 + 基本盤面
    export_data = {
        "盤面基本資訊": report.get("盤面基本資訊", {}),
        "七行星本體之力": report.get("七行星本體之力", {}),
        "托勒密相位（核心）": report.get("托勒密相位（核心）", []),
        "現代相位（補充）": report.get("現代相位（補充）", []),
        "廟旺互容": report.get("廟旺互容", []),
        "飛星追蹤": report.get("飛星追蹤", {}),
    }
    if theme_data:
        export_data[f"主題分析：{theme_zh}"] = theme_data

    export_json = json.dumps(export_data, ensure_ascii=False, indent=2)
    st.code(export_json, language="json")
    st.download_button(
        label="下載 JSON 報告",
        data=export_json,
        file_name=f"解盤報告_{theme_zh}.json",
        mime="application/json"
    )

    # 換主題
    if st.button("← 換一個主題", use_container_width=True):
        st.session_state.report = None
        st.session_state.chart = None
        st.rerun()

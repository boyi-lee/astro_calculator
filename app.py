import streamlit as st
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from astro_calculator import parse_chart, generate_report, THEME_ZH, HOUSE_TOPICS

st.set_page_config(page_title="星命師", page_icon="☽", layout="centered")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Serif+TC:wght@300;400;600&display=swap');
html, body, [class*="css"] { font-family: 'Noto Serif TC', serif; }
.block-container { max-width: 720px; padding-top: 2rem; }
.title-block { text-align:center; padding:2rem 0 1.5rem; border-bottom:1px solid rgba(184,150,46,0.3); margin-bottom:2rem; }
.title-main { font-size:2.5rem; font-weight:300; letter-spacing:10px; color:#f5f0e8; }
.title-sub { font-size:12px; letter-spacing:3px; color:#b8962e; opacity:0.6; margin-top:6px; }
.section-label { font-size:10px; letter-spacing:4px; color:#b8962e; opacity:0.7; text-transform:uppercase; margin-bottom:0.5rem; }
.planet-row { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid rgba(184,150,46,0.08); font-size:13px; }
.strong { color:#7aad84; } .medium { color:#d4b254; } .weak { color:#c4725f; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="title-block">
    <div style="color:#b8962e;font-size:12px;letter-spacing:6px;opacity:0.7">✦ Tetrabiblos ✦</div>
    <div class="title-main">星命師</div>
    <div class="title-sub">傳統占星解盤 · 完整盤面報告</div>
</div>
""", unsafe_allow_html=True)

# ── 輸入 ──
st.markdown('<div class="section-label">盤面資料</div>', unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📎 上傳 .md 檔案", "📋 貼上文字"])
md_content = ""

with tab1:
    uploaded = st.file_uploader("占星之門盤面", type=["md","txt"], label_visibility="collapsed")
    if uploaded:
        md_content = uploaded.read().decode("utf-8")
        st.success(f"✓ 已載入：{uploaded.name}")

with tab2:
    pasted = st.text_area("貼上盤面 Markdown", height=180, placeholder="將占星之門盤面內容貼在此處...", label_visibility="collapsed")
    if pasted:
        md_content = pasted

st.markdown("")

if st.button("解析完整盤面", type="primary", use_container_width=True):
    if not md_content:
        st.error("請先上傳盤面檔案或貼上盤面內容")
    else:
        with st.spinner("計算中…"):
            try:
                chart = parse_chart(md_content)
                if not chart.planets:
                    st.error("無法解析盤面，請確認檔案格式正確（占星之門 Markdown 格式）")
                    st.stop()

                # 一次計算所有主題
                base_report = generate_report(chart)
                all_themes = {}
                for theme_key in HOUSE_TOPICS:
                    all_themes[theme_key] = generate_report(chart, theme_key).get(f"主題分析：{THEME_ZH.get(theme_key, theme_key)}", {})

                st.session_state["report"] = base_report
                st.session_state["all_themes"] = all_themes
                st.session_state["chart_ok"] = True
                st.rerun()
            except Exception as e:
                st.error(f"解析失敗：{str(e)}")
                import traceback
                st.code(traceback.format_exc())

# ── 顯示結果 ──
if st.session_state.get("chart_ok"):
    report = st.session_state["report"]
    all_themes = st.session_state["all_themes"]

    st.markdown("---")

    # 基本資訊
    info = report.get("盤面基本資訊", {})
    骨架 = info.get("三骨架", {})
    col1, col2, col3 = st.columns(3)
    col1.metric("上升", 骨架.get("上升","").split("/")[0].strip())
    col2.metric("太陽", 骨架.get("太陽","").split("/")[0].strip())
    col3.metric("日夜間盤", "☉ 晝生" if "晝" in info.get("日夜間盤","") else "☽ 夜生")

    # 七行星
    st.markdown('<div class="section-label" style="margin-top:1.5rem">七行星本體之力</div>', unsafe_allow_html=True)
    planets_data = report.get("七行星本體之力", {})
    for pname, pdata in planets_data.items():
        score = pdata.get("綜合尊貴分數", 0)
        strength = pdata.get("力量等級", "")
        sign = pdata.get("星座", "")
        house = pdata.get("宮位", "")
        retro = "℞ " if pdata.get("逆行") == "是" else ""
        solar = pdata.get("太陽距離狀態", "")
        solar_mark = f" · {solar}" if solar and solar != "正常" else ""
        css = "strong" if score >= 5 else ("weak" if score < 0 else "medium")
        dign = [k for k,v in pdata.get("尊貴",{}).items() if v == "✓"]
        dign_str = " · ".join(dign) if dign else "外來"

        st.markdown(
            f'<div class="planet-row">'
            f'<span style="color:#b8962e;width:40px">{pname}</span>'
            f'<span style="flex:1;color:rgba(245,240,232,0.7)">{retro}{sign}座 {house}{solar_mark}</span>'
            f'<span style="color:rgba(245,240,232,0.4);font-size:11px;margin-right:8px">{dign_str}</span>'
            f'<span class="{css}">{strength}（{score:+d}）</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    # 相位
    with st.expander("托勒密相位（核心）", expanded=False):
        for asp in report.get("托勒密相位（核心）", []):
            w = asp["效力權重"]
            color = "#7aad84" if w > 0 else ("#c4725f" if w < 0 else "rgba(245,240,232,0.4)")
            st.markdown(f'<span style="color:{color}">{asp["行星A"]} {asp["相位"]} {asp["行星B"]} （{asp["容許度"]}）效力：{w:+.1f}</span>', unsafe_allow_html=True)

    with st.expander("現代相位（補充）", expanded=False):
        modern = report.get("現代相位（補充）", [])
        for asp in modern:
            st.markdown(f'{asp["行星A"]} {asp["相位"]} {asp["行星B"]} （{asp["容許度"]}）')
        if not modern:
            st.markdown("無")

    # 飛星
    with st.expander("飛星追蹤（全部12宮）", expanded=False):
        for hk, fv in report.get("飛星追蹤", {}).items():
            st.markdown(f"**{hk}**：{fv['廟主星']} → {fv['飛入']} ｜ {fv['主宰星力量']}")

    # 互容
    rec = report.get("廟旺互容", [])
    if rec:
        with st.expander("廟旺互容", expanded=True):
            for r in rec:
                st.markdown(f"**{r['行星A']}** ↔ **{r['行星B']}** · {r['互容類型']}")

    # 各主題摘要
    st.markdown('<div class="section-label" style="margin-top:1.5rem">九大主題因子分析</div>', unsafe_allow_html=True)
    for theme_key, theme_data in all_themes.items():
        theme_zh = THEME_ZH.get(theme_key, theme_key)
        scenario = theme_data.get("scenario_type", "張力")
        pos = theme_data.get("positive_score", 0)
        neg = theme_data.get("negative_score", 0)
        net = theme_data.get("overall_score", 0)
        color = "#7aad84" if scenario == "順遂" else ("#c4725f" if scenario == "阻礙" else "#d4b254")
        with st.expander(f"{theme_zh}　｜　{scenario}　（{net:+.1f}）", expanded=False):
            c1, c2, c3 = st.columns(3)
            c1.metric("正向", f"+{pos}")
            c2.metric("負向", f"-{neg}")
            c3.metric("淨分", f"{net:+.1f}")

            fs = theme_data.get("flystar_connections", [])
            if fs:
                st.markdown("**飛星：**")
                for f in fs:
                    st.markdown(f"　第{f['from_house']}宮 {f['lord']} → 第{f['flies_to']}宮 [{f['lord_strength']}]")

            asps = theme_data.get("relevant_aspects", [])
            if asps:
                st.markdown("**相關相位：**")
                for a in asps[:5]:
                    w = a['weight']
                    mark = "◆" if a['is_ptolemy'] else "◇"
                    color_a = "#7aad84" if w > 0 else ("#c4725f" if w < 0 else "rgba(245,240,232,0.4)")
                    st.markdown(f'<span style="color:{color_a}">{mark} {a["a"]} {a["aspect"]} {a["b"]}（{a["orb"]}°）{w:+.1f}</span>', unsafe_allow_html=True)

    # ── 匯出 ──
    st.markdown("---")
    st.markdown('<div class="section-label">匯出給星命師 Gem</div>', unsafe_allow_html=True)
    st.markdown("下載完整 JSON 報告，上傳給 Gemini 星命師 Gem，即可開始對話式解盤。")

    export = {
        "盤面基本資訊": report.get("盤面基本資訊", {}),
        "七行星本體之力": report.get("七行星本體之力", {}),
        "托勒密相位（核心）": report.get("托勒密相位（核心）", []),
        "現代相位（補充）": report.get("現代相位（補充）", []),
        "廟旺互容": report.get("廟旺互容", []),
        "飛星追蹤": report.get("飛星追蹤", {}),
        "宮內多星分析": report.get("宮內多星分析", {}),
        "九大主題分析": all_themes
    }
    export_json = json.dumps(export, ensure_ascii=False, indent=2)

    st.download_button(
        label="⬇ 下載完整解盤報告 JSON",
        data=export_json,
        file_name="星命師_完整解盤報告.json",
        mime="application/json",
        use_container_width=True
    )

    st.markdown("")
    if st.button("← 重新上傳", use_container_width=True):
        for k in ["report","all_themes","chart_ok"]:
            st.session_state.pop(k, None)
        st.rerun()

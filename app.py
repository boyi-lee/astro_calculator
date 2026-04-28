import streamlit as st
import json
import sys
import os
from datetime import datetime

# Google Drive API 相關庫
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload

sys.path.insert(0, os.path.dirname(__file__))
from astro_calculator import parse_chart, generate_report, THEME_ZH, HOUSE_TOPICS

# ── 設定 ──
st.set_page_config(page_title="星命師", page_icon="☽", layout="centered")

# ── Google Drive 上傳函數 ──
def upload_to_drive(json_content, file_name, folder_id):
    """
    透過服務帳號將內容上傳至指定 Google Drive 資料夾
    """
    try:
        if "gcp_service_account" not in st.secrets:
            return "error", "請先設定 .streamlit/secrets.toml 檔案。"
        
        # 從 secrets 取得憑證
        info = dict(st.secrets["gcp_service_account"])
        scopes = ['https://www.googleapis.com/auth/drive.file']
        creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
        
        # 建立服務
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': file_name,
            'parents': [folder_id] if folder_id else []
        }
        
        media = MediaInMemoryUpload(json_content.encode('utf-8'), mimetype='application/json')
        
        file = service.files().create(
            body=file_metadata, 
            media_body=media, 
            fields='id'
        ).execute()
        
        return "success", file.get('id')
    except Exception as e:
        return "error", str(e)

# ── CSS 樣式 ──
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
                    st.error("無法解析盤面，請確認格式正確")
                    st.stop()

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

    # 七行星力量
    st.markdown('<div class="section-label" style="margin-top:1.5rem">七行星本體之力</div>', unsafe_allow_html=True)
    planets_data = report.get("七行星本體之力", {})
    for pname, pdata in planets_data.items():
        score = pdata.get("綜合尊貴分數", 0)
        strength = pdata.get("力量等級", "")
        sign = pdata.get("星座", "")
        house = pdata.get("宮位", "")
        retro = "℞ " if pdata.get("逆行") == "是" else ""
        css = "strong" if score >= 5 else ("weak" if score < 0 else "medium")
        st.markdown(
            f'<div class="planet-row">'
            f'<span style="color:#b8962e;width:40px">{pname}</span>'
            f'<span style="flex:1;color:rgba(245,240,232,0.7)">{retro}{sign}座 {house}</span>'
            f'<span class="{css}">{strength}（{score:+d}）</span>'
            f'</div>',
            unsafe_allow_html=True
        )

    # 九大主題摘要
    st.markdown('<div class="section-label" style="margin-top:1.5rem">主題因子分析推論</div>', unsafe_allow_html=True)
    for theme_key, theme_data in all_themes.items():
        theme_zh = THEME_ZH.get(theme_key, theme_key)
        scenario = theme_data.get("scenario_type", "張力")
        net = theme_data.get("overall_score", 0)
        with st.expander(f"{theme_zh}　｜　{scenario}　（{net:+.1f}）"):
            st.write(f"正向得分：{theme_data.get('positive_score', 0)}")
            st.write(f"負向得分：{theme_data.get('negative_score', 0)}")

    # ── 匯出與雲端備份 ──
    st.markdown("---")
    st.markdown('<div class="section-label">數據匯出與備份</div>', unsafe_allow_html=True)
    
    export = {
        "盤面基本資訊": report.get("盤面基本資訊", {}),
        "七行星本體之力": report.get("七行星本體之力", {}),
        "九大主題分析": all_themes
    }
    export_json = json.dumps(export, ensure_ascii=False, indent=2)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M")
    default_filename = f"星命師報告_{timestamp}.json"

    col_dl, col_drive = st.columns(2)
    
    with col_dl:
        st.download_button(
            label="⬇ 下載 JSON 報告",
            data=export_json,
            file_name=default_filename,
            mime="application/json",
            use_container_width=True
        )

    with col_drive:
        folder_id = st.text_input("Drive 資料夾 ID", placeholder="在此貼上資料夾 ID...", label_visibility="collapsed")
        if st.button("☁️ 儲存至 Google 雲端", use_container_width=True):
            if not folder_id:
                st.warning("請先輸入目標資料夾 ID")
            else:
                with st.spinner("雲端傳輸中..."):
                    status, msg = upload_to_drive(export_json, default_filename, folder_id)
                    if status == "success":
                        st.success(f"✓ 儲存成功！檔案 ID: {msg}")
                    else:
                        st.error(f"儲存失敗：{msg}")

    st.markdown("")
    if st.button("← 重新上傳", use_container_width=True):
        for k in ["report","all_themes","chart_ok"]:
            st.session_state.pop(k, None)
        st.rerun()
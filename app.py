"""VNFood AI — responsive dual-theme dashboard for multi-dish recognition."""
from __future__ import annotations

import io
import json
from html import escape
from PIL import Image, ImageOps, UnidentifiedImageError
import streamlit as st

from core.gemini_handler import MODEL_NAME, PROMPT_VERSION, analyze_food, normalize_result
from core.image_tools import COLORS, draw_bounding_boxes
from core.preferences import theme_from_query, theme_to_query
from core.utils import clear_cache, get_cache_key, load_cache, save_cache

st.set_page_config(page_title="VNFood | Vietnamese Cuisine", page_icon="🍜", layout="wide", initial_sidebar_state="collapsed")

if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = theme_from_query(st.query_params.get("theme"))

def persist_theme():
    """URL query params survive a full F5 / Ctrl+R browser reload."""
    st.query_params["theme"] = theme_to_query(st.session_state.ui_theme)
if "ui_language" not in st.session_state:
    st.session_state.ui_language = "Tiếng Việt"

DARK = st.session_state.ui_theme == "Tối"
VI = st.session_state.ui_language == "Tiếng Việt"

def t(vi: str, en: str) -> str:
    return vi if VI else en

palette = {
    "bg": "#0B111B", "panel": "#131D2B", "panel2": "#192638", "ink": "#EDF3F8",
    "muted": "#9EACBE", "line": "#293749", "accent": "#FF9563", "accentInk": "#231710",
    "hover": "#223247", "soft": "#272C30", "badge": "#27372E", "badgeInk": "#BAF0C9",
    "field": "#192638", "tip": "#162C3E", "tipInk": "#C8E9FD",
} if DARK else {
    "bg": "#F5F7FA", "panel": "#FFFFFF", "panel2": "#F8FAFC", "ink": "#202F3C",
    "muted": "#667889", "line": "#E1E8EF", "accent": "#C65B35", "accentInk": "#FFFFFF",
    "hover": "#F0F4F8", "soft": "#FFF0E8", "badge": "#EAF5EE", "badgeInk": "#27724C",
    "field": "#FFFFFF", "tip": "#E9F3FF", "tipInk": "#255477",
}

# Streamlit's dynamic theme cannot be changed at runtime using config.toml.
# Set variables on the app itself and explicitly theme native widgets too.
css = r"""
<style>
:root {
  --vn-bg: BG; --vn-panel: PANEL; --vn-panel2: PANEL2; --vn-ink: INK;
  --vn-muted: MUTED; --vn-line: LINE; --vn-accent: ACCENT; --vn-accentink: ACCENTINK;
  --vn-hover: HOVER; --vn-soft: SOFT; --vn-badge: BADGE; --vn-badgeink: BADGEINK;
  --vn-field: FIELD; --vn-tip: TIP; --vn-tipink: TIPINK;
}
html, body, [data-testid="stAppViewContainer"], [data-testid="stMain"], .stApp {
  background: var(--vn-bg) !important; color: var(--vn-ink) !important;
}
[data-testid="stHeader"], [data-testid="stToolbar"] { background: var(--vn-bg) !important; }
/* Streamlit header floats above the app: reserve sufficient vertical space. */
[data-testid="stMainBlockContainer"], .block-container {
  max-width: 1320px;
  padding-top: 5.25rem !important;
  padding-bottom: 3rem !important;
}
/* Keep toolbar from obscuring app controls, independent of Streamlit theme. */
[data-testid="stHeader"] { height: 3.75rem; }

[data-testid="stAppViewContainer"] p, [data-testid="stAppViewContainer"] li,
[data-testid="stAppViewContainer"] label, [data-testid="stAppViewContainer"] span,
[data-testid="stAppViewContainer"] h1, [data-testid="stAppViewContainer"] h2,
[data-testid="stAppViewContainer"] h3 { color: var(--vn-ink); }
[data-testid="stCaptionContainer"] p, [data-testid="stWidgetLabel"] p,
[data-testid="stFileUploaderDropzoneInstructions"] *, [data-testid="stMetricLabel"] p { color:var(--vn-muted) !important; }
[data-testid="stWidgetLabel"] { margin-bottom: 0.25rem; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-color:var(--vn-line) !important; }
[data-testid="stVerticalBlockBorderWrapper"] { background:var(--vn-panel) !important; border-radius:18px; }
[data-testid="stFileUploader"] { border:1.5px dashed var(--vn-line) !important; border-radius:14px; padding:9px 12px 1px; background:var(--vn-panel2); }
[data-testid="stFileUploaderDropzone"] { background:var(--vn-panel2) !important; border:0 !important; }
[data-testid="stFileUploaderDropzone"] button, [data-testid="stFileUploader"] button,
.stButton button[kind="secondary"], .stDownloadButton button {
 background:var(--vn-panel2) !important; color:var(--vn-ink) !important;
 border:1px solid var(--vn-line) !important; border-radius:10px !important;
}
.stButton button[kind="primary"] { background:var(--vn-accent) !important; border:1px solid var(--vn-accent) !important;
 color:var(--vn-accentink) !important; border-radius:10px !important; font-weight:750; }
.stButton button[kind="primary"] *, .stButton button[kind="primary"] p { color:var(--vn-accentink) !important; }
.stButton button[kind="secondary"] *, .stDownloadButton button * {color:var(--vn-ink) !important;}
.stButton button, .stDownloadButton button {min-height:42px; transition:filter .2s, transform .2s;}
.stButton button:hover, .stDownloadButton button:hover {filter:brightness(.94);}
.stButton button:disabled {opacity:.55 !important;}
[data-baseweb="select"] > div, [data-baseweb="input"] > div,
[data-baseweb="textarea"] > div {background:var(--vn-field) !important; color:var(--vn-ink) !important;
 border:1px solid var(--vn-line) !important; border-radius:10px !important;}
[data-baseweb="select"] *, [data-baseweb="input"] input,
[data-baseweb="textarea"] textarea {color:var(--vn-ink) !important;}
[data-baseweb="popover"] [role="listbox"] {background:var(--vn-panel) !important;}
[data-baseweb="popover"] [role="option"] {background:var(--vn-panel) !important; color:var(--vn-ink) !important;}
[data-baseweb="popover"] [role="option"] * {color:var(--vn-ink) !important;}
[data-baseweb="popover"] [role="option"]:hover {background:var(--vn-hover) !important;}
[data-testid="stRadio"] label, [data-testid="stToggle"] label {color:var(--vn-ink) !important;}
[data-testid="stMetric"] {background:var(--vn-panel2); border:1px solid var(--vn-line); border-radius:12px; padding:15px 18px;}
[data-testid="stMetricValue"] *, [data-testid="stMetricValue"] {color:var(--vn-ink) !important;}
[data-testid="stImage"] img {border-radius:12px;}
[data-testid="stTabs"] [role="tablist"] {border-bottom:1px solid var(--vn-line);}
[data-testid="stTabs"] button {color:var(--vn-muted) !important;}
[data-testid="stTabs"] button[aria-selected="true"] {color:var(--vn-accent) !important;}
[data-testid="stExpander"] {background:var(--vn-panel); border:1px solid var(--vn-line); border-radius:12px;}
[data-testid="stExpander"] summary, [data-testid="stExpander"] summary * {color:var(--vn-ink) !important;}
[data-testid="stAlert"] {background:var(--vn-tip) !important; border:1px solid var(--vn-line) !important;}
[data-testid="stAlert"] p, [data-testid="stAlert"] span {color:var(--vn-tipink) !important;}
[data-testid="stProgress"] {accent-color:var(--vn-accent);}
[data-testid="stDivider"] {border-color:var(--vn-line);}
/* Avoid touching all widgets with hardcoded light text; every component uses current theme tokens. */
.vn-top {display:flex; justify-content:space-between; align-items:center; gap:14px; padding:5px 0 18px; border-bottom:1px solid var(--vn-line); margin-bottom:23px;}
.vn-brand {padding-top:8px; line-height:1.5; font-weight:850; font-size:23px; letter-spacing:-.04em; color:var(--vn-ink);}
.vn-brand span {color:var(--vn-accent);}
.vn-brand small {font-size:12px; margin-left:12px; color:var(--vn-muted); font-weight:500; letter-spacing:0;}
.vn-status {font-size:12px; border-radius:999px; padding:7px 12px; color:var(--vn-badgeink); background:var(--vn-badge); font-weight:700;}
.vn-hero {border:1px solid var(--vn-line); border-radius:22px; padding:31px 35px; margin:12px 0 24px; background:var(--vn-panel);
 display:grid; grid-template-columns:minmax(0,1fr) 210px; gap:25px; align-items:center;}
.vn-kicker {font-size:11px; font-weight:800; letter-spacing:.16em; color:var(--vn-accent); margin-bottom:12px;}
.vn-hero h1 {font-size:clamp(26px,3vw,38px); line-height:1.19; letter-spacing:-.04em; margin:0 0 13px; font-weight:830; color:var(--vn-ink);}
.vn-hero p {color:var(--vn-muted) !important; font-size:14px; line-height:1.7; margin:0; max-width:770px;}
.vn-hero-graphic {height:145px; border-radius:20px; background:var(--vn-soft); display:flex; align-items:center;
 justify-content:center; font-size:74px; border:1px solid var(--vn-line);}
.vn-section {display:flex; justify-content:space-between; align-items:center; margin:17px 0 11px; gap:10px;}
.vn-section strong {font-size:17px; font-weight:800; letter-spacing:-.02em; color:var(--vn-ink);}
.vn-section small {font-size:12px; color:var(--vn-muted);}
.vn-card {background:var(--vn-panel); border:1px solid var(--vn-line); border-radius:17px; padding:19px 21px; margin-bottom:12px;}
.vn-card-title {font-size:14px; font-weight:750; color:var(--vn-ink); margin-bottom:6px;}
.vn-caption {font-size:12px; color:var(--vn-muted); line-height:1.6;}
.vn-statline {display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-top:19px;}
.vn-chip {border:1px solid var(--vn-line); background:var(--vn-panel2); padding:7px 10px;
 border-radius:9px; font-size:11px; color:var(--vn-muted); font-weight:650;}
.vn-food {border:1px solid var(--vn-line); border-radius:14px; background:var(--vn-panel2); padding:16px; margin:10px 0;}
.vn-food-name {font-weight:800; font-size:24px; line-height:1.3; color:var(--vn-ink);}
.vn-food-region {font-size:13px; color:var(--vn-muted); margin-top:7px;}
.vn-dot {display:inline-block; border-radius:5px; width:13px; height:13px; margin-right:8px; vertical-align:baseline;}
.vn-footer {margin-top:30px; padding:18px 0; text-align:center; border-top:1px solid var(--vn-line); color:var(--vn-muted); font-size:12px;}
@media(max-width:850px) {
 [data-testid="stMainBlockContainer"], .block-container {padding:5.25rem 1rem 2rem !important;}
 .vn-hero {grid-template-columns:1fr; padding:22px;}
 .vn-hero-graphic {display:none;}
 .vn-brand small {display:none;}
}
</style>
"""
for k in sorted(palette, key=len, reverse=True):
    css = css.replace(k.upper(), palette[k])
st.markdown(css, unsafe_allow_html=True)

# Real native controls with persisted Streamlit session state, no HTML faux buttons.
brand, appearance, locale = st.columns([5, 1.65, 1.55])
with brand:
    st.markdown('<div class="vn-brand">🍜 VNFood <span></span><small>Vietnamese cuisine intelligence</small></div>', unsafe_allow_html=True)
with appearance:
    st.selectbox("🌓 " + t("Giao diện", "Theme"), ["Sáng", "Tối"], key="ui_theme", label_visibility="collapsed", on_change=persist_theme)
with locale:
    st.selectbox("🌐 Language", ["Tiếng Việt", "English"], key="ui_language", label_visibility="collapsed")
st.markdown('<div class="vn-top"><span class="vn-caption">MULTI-FOOD RECOGNITION</span><span class="vn-status">● ' + t("SẴN SÀNG", "READY") + '</span></div>', unsafe_allow_html=True)

st.markdown(f'''<div class="vn-hero">
<div><div class="vn-kicker">VISION • VIETNAMESE CUISINE</div>
<h1>{escape(t("Nhận diện ẩm thực Việt Nam", "Discover Vietnamese food"))}<br>{escape(t("trong từng bức ảnh.", "in every photo."))}</h1>
<p>{escape(t("Nhận diện tối đa 8 món ăn trong một ảnh. Xem vị trí, đặc trưng vùng miền và cách chế biến ngay trên một màn hình.", "Identify up to 8 dishes in one photo. Explore each dish, its region and how to prepare it, all in one place."))}</p>
<div class="vn-statline"><span class="vn-chip">✦ Multi-food AI</span><span class="vn-chip">▣ Bounding boxes</span><span class="vn-chip">🌏 VI / EN</span></div></div>
<div class="vn-hero-graphic">🍜</div></div>''', unsafe_allow_html=True)

# Controls (all input fields are real Streamlit controls)
with st.expander("⚙️ " + t("Tùy chọn phân tích", "Analysis preferences"), expanded=False):
    opt1, opt2 = st.columns([2,1], gap="large")
    with opt1:
        region = st.selectbox(t("Vùng miền gợi ý", "Region hint"), [
            "Northern Vietnam (Miền Bắc)", "Central Vietnam (Miền Trung)",
            "Southern Vietnam (Miền Nam)",
        ], help=t("Chỉ là gợi ý, không ép AI chọn món theo vùng miền.", "Optional hint, never overrides visual evidence."))
    with opt2:
        st.caption(t("Model đang sử dụng", "Current model"))
        st.code(MODEL_NAME, language=None)

left_upload, right_action = st.columns([1.85, 1], gap="large")
with left_upload:
    st.markdown('<div class="vn-section"><strong>01 · ' + t("Tải ảnh món ăn", "Upload food photo") + '</strong><small>JPG / PNG · 12 MB max</small></div>', unsafe_allow_html=True)
    upload = st.file_uploader(t("Chọn ảnh", "Choose photo"), type=["jpg", "jpeg", "png"], label_visibility="collapsed", key="vn_upload")
with right_action:
    st.markdown('<div class="vn-section"><strong>02 · ' + t("Phân tích", "Recognize") + '</strong><small>Gemini AI</small></div>', unsafe_allow_html=True)
    analyze_clicked = st.button("✦ " + t("Nhận diện món ăn", "Recognize dishes"), type="primary", use_container_width=True, disabled=upload is None)
    retry_clicked = st.button("↻ " + t("Phân tích lại", "Analyze again"), use_container_width=True, disabled=upload is None)

if upload is None:
    st.markdown('<div class="vn-card"><div class="vn-card-title">📷 ' + t("Chưa có ảnh nào được tải lên", "No photo uploaded yet") + '</div><div class="vn-caption">' + t("Tải ảnh rõ nét để bắt đầu. Kết quả sẽ hiển thị hình ảnh có đánh dấu và thông tin từng món.", "Upload a clear food photo to see the detections and dish information here.") + '</div></div>', unsafe_allow_html=True)
else:
    if upload.size > 12 * 1024 * 1024:
        st.error(t("Tệp vượt quá giới hạn 12 MB.", "The file exceeds the 12 MB limit."))
        st.stop()
    try:
        with Image.open(io.BytesIO(upload.getvalue())) as original:
            source = ImageOps.exif_transpose(original)
            source.thumbnail((1600, 1600))
            image = source.convert("RGB")
        temp = io.BytesIO()
        image.save(temp, format="JPEG", quality=88, optimize=True)
        image_bytes = temp.getvalue()
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        st.error(t("Ảnh không hợp lệ hoặc quá lớn.", "Invalid or oversized image."))
        st.stop()

    cache_key = get_cache_key(image_bytes, region, st.session_state.ui_language, MODEL_NAME, PROMPT_VERSION)
    should_analyze = analyze_clicked or retry_clicked
    result = None
    source_label = ""
    if should_analyze:
        with st.spinner(t("Gemini đang phân tích ảnh…", "Gemini is analyzing your image…")):
            result = normalize_result(analyze_food(image_bytes, region, st.session_state.ui_language))
            if "error" not in result:
                save_cache(cache_key, result)
            st.session_state["last_analysis"] = result
            st.session_state["last_analysis_key"] = cache_key
        source_label = "live"
    else:
        if st.session_state.get("last_analysis_key") == cache_key:
            result = normalize_result(st.session_state["last_analysis"])
            source_label = "session"
        if result is None:
            cached = load_cache(cache_key)
            if cached is not None:
                result = normalize_result(cached)
                source_label = "cache"
    st.markdown('<div class="vn-section"><strong>03 · ' + t("Kết quả nhận diện", "Results") + '</strong><small>' + escape(source_label.upper()) + '</small></div>', unsafe_allow_html=True)
    if result is None:
        with st.container(border=True):
            st.image(image, use_container_width=True)
            st.info(t("Ảnh đã sẵn sàng. Nhấn Nhận diện món ăn.", "Photo ready. Select Recognize dishes."))
    elif "error" in result:
        st.error(result["error"])
        st.image(image, use_container_width=True)
    else:
        foods = result.get("foods", [])
        annotated = draw_bounding_boxes(image_bytes, foods) if foods else image
        left, right = st.columns([1.35, 1], gap="large")
        with left:
            with st.container(border=True):
                st.markdown("**🖼️ " + t("Hình ảnh phân tích", "Analyzed photo") + "**")
                show_boxes = st.toggle(t("Hiện khung nhận diện", "Show bounding boxes"), value=True, key="vn_show_boxes")
                st.image(annotated if show_boxes else image, use_container_width=True)
                a, b = st.columns(2)
                with a:
                    st.download_button("↓ " + t("Kết quả JSON", "Download JSON"), json.dumps(result, ensure_ascii=False, indent=2),
                                       file_name="vnfood-result.json", mime="application/json", use_container_width=True)
                with b:
                    out = io.BytesIO()
                    annotated.save(out, format="PNG")
                    st.download_button("↓ " + t("Ảnh đánh dấu", "Annotated image"), out.getvalue(),
                                       file_name="vnfood-boxes.png", mime="image/png", use_container_width=True)
                st.caption(t("Mức độ tin cậy và khung nhận diện là tự động ước lượng.", "Confidence and bounding boxes are automatic estimates."))
        with right:
            if not foods:
                st.warning(t("Không phát hiện được món ăn rõ ràng.", "No recognizable food detected."))
            else:
                st.metric(t("Số món ăn", "Dishes found"), len(foods))
                selected = st.selectbox(t("Xem chi tiết món", "Select a dish"), list(range(len(foods))),
                                         format_func=lambda idx: f"{idx+1:02d} · {foods[idx]['food_name']}",
                                         key="selected_" + cache_key)
                dish = foods[selected]
                name = escape(dish.get("food_name", "—"))
                location = escape(dish.get("region", "—") or "—")
                color = COLORS[selected % len(COLORS)]
                st.markdown(f'<div class="vn-food"><div class="vn-food-name"><span class="vn-dot" style="background:{color}"></span>{name}</div><div class="vn-food-region">📍 {location}</div></div>', unsafe_allow_html=True)
                confidence = max(0, min(100, float(dish.get("confidence", 0))))
                st.progress(int(confidence), text=t("Mức tin cậy ước lượng", "Estimated confidence") + f" · {confidence:.0f}/100")
                tab1, tab2, tab3 = st.tabs([t("📖 Giới thiệu", "📖 Description"), t("🍳 Cách nấu", "🍳 Recipe"), t("🥢 Cách ăn", "🥢 How to eat")])
                with tab1:
                    st.markdown("#### " + t("Tổng quan món ăn", "Dish overview"))
                    st.write(dish.get("description") or t("Chưa có thông tin.", "Not available."))
                    if dish.get("origin_note"):
                        st.markdown("#### " + t("Nguồn gốc và văn hóa", "Origins and culture"))
                        st.write(dish["origin_note"])
                    if dish.get("taste_texture"):
                        st.markdown("#### " + t("Hương vị và kết cấu", "Taste and texture"))
                        st.write(dish["taste_texture"])
                    if dish.get("variations"):
                        st.markdown("#### " + t("Biến thể phổ biến", "Popular variations"))
                        for v in dish["variations"]:
                            st.markdown("- " + escape(v))
                with tab2:
                    timings = [str(dish.get("prep_time") or "").strip(), str(dish.get("cook_time") or "").strip()]
                    if any(timings):
                        st.caption(t("Chuẩn bị", "Preparation") + ": " + (timings[0] or "—") + "  •  " + t("Chế biến", "Cooking") + ": " + (timings[1] or "—"))
                    if dish.get("ingredients"):
                        st.markdown("#### " + t("Nguyên liệu tham khảo", "Suggested ingredients"))
                        for ing in dish["ingredients"]:
                            st.markdown("- " + escape(ing))
                    if dish.get("cooking_steps"):
                        st.markdown("#### " + t("Các bước thực hiện", "Cooking instructions"))
                        for n, step in enumerate(dish["cooking_steps"], 1):
                            st.markdown(f"**{n}.** {escape(step)}")
                    else:
                        st.write(dish.get("how_to_cook") or t("Chưa có công thức.", "Recipe not available."))
                    if dish.get("cooking_tips"):
                        st.markdown("#### " + t("Mẹo chế biến", "Cooking tips"))
                        for tip in dish["cooking_tips"]:
                            st.markdown("- " + escape(tip))
                with tab3:
                    st.markdown("#### " + t("Cách thưởng thức", "How to enjoy"))
                    st.write(dish.get("how_to_eat") or t("Chưa có thông tin.", "Not available."))
                    if dish.get("serving_tips"):
                        st.markdown("#### " + t("Gợi ý dùng món", "Serving suggestions"))
                        for tip in dish["serving_tips"]:
                            st.markdown("- " + escape(tip))
                    if dish.get("pairings"):
                        st.markdown("#### " + t("Món ăn kèm", "Recommended accompaniments"))
                        for pairing in dish["pairings"]:
                            st.markdown("- " + escape(pairing))
                    if dish.get("dietary_notes"):
                        st.info(t("Lưu ý thành phần (cần xác nhận)", "Ingredient notes (verify before eating)") + ": " + dish["dietary_notes"])
                st.caption(t("Nội dung chỉ mang tính tham khảo. Công thức, nguyên liệu và dị ứng cần tự xác minh.", "Content is for reference only. Verify recipes, ingredients, and allergies independently."))
                if len(foods) > 1:
                    with st.expander(t("Tất cả món đã phát hiện", "All detected dishes")):
                        for i, item in enumerate(foods):
                            st.markdown(f'<span class="vn-dot" style="background:{COLORS[i % len(COLORS)]}"></span> **{i+1:02d}. {escape(item["food_name"])}** · {item["confidence"]:.0f}/100', unsafe_allow_html=True)

with st.expander("🧰 " + t("Công cụ và bảo trì", "Tools and maintenance"), expanded=False):
    clear_col, info_col = st.columns([1, 3])
    with clear_col:
        if st.button(t("🗑️ Xóa cache", "🗑️ Clear cache"), use_container_width=True):
            clear_cache()
            st.session_state.pop("last_analysis", None)
            st.session_state.pop("last_analysis_key", None)
            st.success(t("Đã xóa cache. Chọn nhận diện để tải kết quả mới.", "Cache cleared. Analyze again for fresh results."))
    with info_col:
        st.caption(t("API key chỉ được đọc trên máy chủ từ secrets.toml. Không đưa khóa lên GitHub.", "API key stays server-side in secrets.toml. Never commit it to GitHub."))

st.markdown('<div class="vn-footer">VNFood · Vietnamese Cuisine Recognition · Powered by dohungclgt</div>', unsafe_allow_html=True)

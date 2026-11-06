import io
import logging

import streamlit as st
from PIL import Image, ImageOps, UnidentifiedImageError

from core.gemini_handler import MODEL_NAME, analyze_food, normalize_result
from core.image_tools import draw_bounding_box
from core.utils import clear_cache, get_cache_key, load_cache, save_cache

logging.basicConfig(level=logging.INFO)

st.set_page_config(page_title="🍜 Vietnamese Food Classifier", layout="wide")
st.markdown("""
<style>
.title {text-align:center;font-size:36px;font-weight:700;color:#b33c00;margin-bottom:10px}
.subtitle {text-align:center;color:#666;font-size:15px;margin-bottom:30px}
.stButton>button {border-radius:10px;font-weight:600}
</style>
""", unsafe_allow_html=True)
st.markdown('<div class="title">🍜 Vietnamese Food Classifier</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">AI-powered Vietnamese cuisine recognition and description</div>', unsafe_allow_html=True)

st.sidebar.header("⚙️ Settings / Cài đặt")
language = st.sidebar.radio("🌐 Language / Ngôn ngữ", ["English", "Tiếng Việt"])
region = st.sidebar.selectbox("📍 Region / Vùng miền", [
    "Northern Vietnam (Miền Bắc)",
    "Central Vietnam (Miền Trung)",
    "Southern Vietnam (Miền Nam)",
])
with st.sidebar:
    col_a, col_b = st.columns(2)
    with col_a:
        clear_clicked = st.button("🧹 Clear Cache / Xóa Cache", use_container_width=True)
    with col_b:
        reload_clicked = st.button("🔄 Reload Analysis / Phân tích lại", use_container_width=True)

if clear_clicked:
    clear_cache()
    st.sidebar.success("✅ Cache cleared / Đã xóa cache!")

uploaded = st.file_uploader(
    "📸 Upload a Vietnamese food image / Tải lên ảnh món ăn Việt Nam",
    type=["jpg", "jpeg", "png"],
)
analyze_clicked = st.button("🔍 Analyze / Phân tích", use_container_width=True)

if uploaded is not None:
    try:
        with Image.open(uploaded) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
        buf = io.BytesIO()
        image.save(buf, format="JPEG", quality=92)
        image_bytes = buf.getvalue()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        st.error(f"Không thể đọc ảnh: {exc}")
        st.stop()

    cache_key = get_cache_key(image_bytes, region, language, MODEL_NAME)
    result = None
    if analyze_clicked or reload_clicked:
        with st.spinner("🧠 Analyzing your food..." if language == "English" else "🧠 Đang phân tích món ăn..."):
            result = normalize_result(analyze_food(image_bytes, region, language))
            save_cache(cache_key, result)
    elif not clear_clicked:
        cached = load_cache(cache_key)
        if cached is not None:
            result = normalize_result(cached)
            if "error" not in result:
                st.toast("✅ Loaded from cache" if language == "English" else "✅ Đã tải từ bộ nhớ cache")

    if result is None:
        st.info("👆 Please click **Analyze / Phân tích** to start recognition." if language == "English"
                else "👆 Hãy bấm **Phân tích** để bắt đầu nhận diện món ăn.")
    else:
        if not isinstance(result, dict):
            result = {"error": "Invalid result format"}
        if "error" in result:
            st.error("❌ " + str(result["error"]))
            st.image(image, caption="📷 Original image / Ảnh gốc", use_container_width=True)
        else:
            processed = draw_bounding_box(image_bytes, result.get("bounding_box"))
            left, right = st.columns([1, 1.2])
            with left:
                st.image(processed, caption="📷 Detected Food" if language == "English" else "📷 Ảnh món ăn", use_container_width=True)
            with right:
                en = language == "English"
                st.markdown(f"### 🍽️ {'Dish' if en else 'Phát hiện món ăn'}: {result['food_name']}")
                st.markdown(f"**🎯 {'Confidence (AI estimate)' if en else 'Độ tin cậy (AI ước lượng)'}:** {result['confidence']:.1f}%")
                st.markdown(f"**🗺️ {'Region' if en else 'Vùng miền'}:** {result.get('region') or region}")
                sections = (
                    ("description", "📖 Description", "📖 Mô tả món ăn"),
                    ("how_to_cook", "🍳 How to Cook", "🍳 Cách chế biến"),
                    ("how_to_eat", "🥢 How to Eat", "🥢 Cách ăn"),
                )
                for key, label_en, label_vi in sections:
                    st.markdown(f"### {label_en if en else label_vi}")
                    st.write(result.get(key) or ("No information available." if en else "Không có dữ liệu."))

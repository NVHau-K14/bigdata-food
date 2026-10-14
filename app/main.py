"""
Ứng dụng Streamlit: Hệ Thống Phân Tích Hành Vi Ăn Uống & Gợi Ý Món Ăn (Big Data 2026)
Entrypoint chính điều hướng Multipage App sử dụng st.navigation và st.Page.
Đọc dữ liệu hoàn toàn bằng Pandas & PyArrow, độc lập với cụm Spark khi chạy demo.
"""

import sys
from pathlib import Path

# Đảm bảo đường dẫn gốc của project luôn nằm trong sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
from app.utils.styles import apply_custom_css

# Thiết lập cấu hình trang toàn cục
st.set_page_config(
    page_title="Hệ Thống Phân Tích Hành Vi & Gợi Ý Món Ăn",
    page_icon="🍲",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Áp dụng giao diện CSS đồng nhất
apply_custom_css()

# Khởi tạo trạng thái phiên làm việc (Session State)
if "dataset" not in st.session_state:
    st.session_state["dataset"] = "vifoodrec"

# ==========================================================
# THANH BÊN (SIDEBAR) - BỘ CHỌN DỮ LIỆU & THÔNG TIN HỆ THỐNG
# ==========================================================
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 0.5rem 0 1rem 0;">
        <span style="font-size: 2.2rem;">🍽️</span>
        <h2 style="margin: 0; color: #10b981; font-weight: 800; font-size: 1.35rem;">BIG DATA FOOD AI</h2>
        <p style="margin: 0; color: #94a3b8; font-size: 0.8rem;">Đồ án Nhập môn Big Data</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🗂️ Bộ Dữ Liệu Mục Tiêu")
    
    # Lựa chọn bộ dữ liệu (mặc định ViFoodRec theo yêu cầu)
    dataset_option = st.selectbox(
        "Chọn bộ dữ liệu phân tích & gợi ý:",
        options=["ViFoodRec (Món Việt Nam - Mặc định)", "Food.com (Quy mô lớn Kaggle)"],
        index=0 if st.session_state["dataset"] == "vifoodrec" else 1,
        help="Pipeline Spark xử lý độc lập hai bộ dữ liệu không gộp vì không có người dùng chung.",
    )
    
    selected_key = "vifoodrec" if "ViFoodRec" in dataset_option else "food_com"
    st.session_state["dataset"] = selected_key

    # Hiển thị badge trạng thái bộ dữ liệu đang chọn
    if selected_key == "vifoodrec":
        st.info("🇻🇳 **ViFoodRec**: 4,000 món Việt Nam, 101 users khảo sát, 149K đánh giá sạch (K-core=3).")
    else:
        st.success("🌐 **Food.com**: 78,171 công thức, 30,836 users, 706K đánh giá sạch (K-core=3).")

    st.markdown("---")
    st.markdown("### ⚙️ Kiến Trúc Hệ Thống Thật")
    st.markdown("""
    <div style="background: rgba(15, 23, 42, 0.6); padding: 0.75rem; border-radius: 8px; border: 1px solid rgba(255,255,255,0.06); font-size: 0.78rem; line-height: 1.5; color: #cbd5e1;">
        <div><b>HDFS 3.3.6:</b> NameNode + 2 DataNodes</div>
        <div><b>Spark 4.2.0:</b> 1 Master + 2 Workers (4 Cores, 7GB RAM)</div>
        <div><b>ML Pipeline:</b> ALS & K-Means MLlib</div>
        <div><b>Serving Layer:</b> Pandas & PyArrow (18.2 MB)</div>
        <div><b>Spark Overhead:</b> 0% (Độc lập cụm)</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.caption("Khóa 2026 • Đồ án Big Data • Chạy chế độ Độc lập Cụm")

# ==========================================================
# ĐỊNH NGHĨA CÁC TRANG MULTIPAGE BẰNG ST.NAVIGATION
# ==========================================================
pages = [
    st.Page("pages/1_Tong_quan.py", title="1. Tổng quan & Kiến trúc", icon="📊", default=True),
    st.Page("pages/2_Hanh_vi_nguoi_dung.py", title="2. Hành vi người dùng", icon="👥"),
    st.Page("pages/3_Goi_y_mon.py", title="3. Gợi ý món ăn", icon="🍲"),
    st.Page("pages/4_Danh_gia_mo_hinh.py", title="4. Đánh giá mô hình", icon="📈"),
]

pg = st.navigation(pages)
pg.run()

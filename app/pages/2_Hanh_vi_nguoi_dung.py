"""
Trang 2: Phân tích hành vi người dùng và phân cụm món ăn (K-means MLlib).
"""

import sys
from pathlib import Path

# Đảm bảo đường dẫn gốc của project luôn nằm trong sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
import altair as alt
from app.utils.styles import apply_custom_css
from app.utils.data_loader import (
    load_cluster_profiles,
    load_food_cluster_profiles,
    load_eda_table,
    load_kmeans_tuning,
)

apply_custom_css()

# Thư mục chứa hình ảnh báo cáo
REPORTS_FIG_DIR = Path(__file__).resolve().parent.parent.parent / "reports" / "figures"

st.markdown('<div class="hero-title">👥 Phân Tích Hành Vi Người Dùng & Phân Cụm Món Ăn</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Mô hình phân cụm K-means (Spark MLlib) kết hợp giảm chiều không gian PCA 2D và phân tích chuỗi thời gian hành vi ẩm thực.</div>',
    unsafe_allow_html=True,
)

# Lấy bộ dữ liệu đang chọn từ session state hoặc cho phép chọn trực tiếp trên trang
current_dataset = st.session_state.get("dataset", "vifoodrec")

tab_user_clusters, tab_temporal, tab_food_clusters = st.tabs([
    "👤 Phân Cụm Người Dùng (K-Means)",
    "📅 Xu Hướng Theo Thời Gian (Food.com)",
    "🍲 Phân Cụm Món Ăn (ViFoodRec)",
])

# ==========================================================
# TAB 1: PHÂN CỤM NGƯỜI DÙNG
# ==========================================================
with tab_user_clusters:
    sub_col1, sub_col2 = st.columns([1, 3])
    with sub_col1:
        chosen_ds = st.selectbox(
            "Chọn bộ dữ liệu phân cụm:",
            options=["ViFoodRec (101 Users)", "Food.com (30,772 Users)"],
            index=0 if current_dataset == "vifoodrec" else 1,
            key="tab1_ds_select",
        )
    
    ds_key = "vifoodrec" if "ViFoodRec" in chosen_ds else "food_com"
    profiles_df = load_cluster_profiles(ds_key)

    if not profiles_df.empty:
        # Lọc bỏ dòng 'Toàn bộ hệ thống' khi vẽ biểu đồ
        clusters_only = profiles_df[profiles_df["cluster"] >= 0].copy()

        st.markdown(f"#### Hồ Sơ Định Lượng Các Cụm Người Dùng ({'ViFoodRec: k=3' if ds_key == 'vifoodrec' else 'Food.com: k=4'})")
        
        # Bảng hồ sơ chi tiết
        st.dataframe(profiles_df, use_container_width=True)

        col_left, col_right = st.columns(2)

        with col_left:
            # Biểu đồ quy mô cụm
            chart_pie = alt.Chart(clusters_only).mark_arc(innerRadius=45).encode(
                theta=alt.Theta("user_pct:Q", title="Tỷ Lệ (%)"),
                color=alt.Color("cluster_name:N", scale=alt.Scale(range=["#10b981", "#3b82f6", "#f59e0b", "#ec4899"]), title="Cụm Người Dùng"),
                tooltip=["cluster", "cluster_name", "user_count", "user_pct"]
            ).properties(
                height=300,
                title="Tỷ Trọng Số Lượng Người Dùng Trong Từng Cụm (%)"
            )
            st.altair_chart(chart_pie, use_container_width=True)

        with col_right:
            if ds_key == "food_com":
                chart_bar = alt.Chart(clusters_only).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                    x=alt.X("cluster_name:N", title="Cụm Người Dùng", axis=alt.Axis(labelAngle=-15)),
                    y=alt.Y("avg_minutes:Q", title="Thời Gian Nấu Trung Bình (Phút)"),
                    color=alt.Color("cluster_name:N", legend=None),
                    tooltip=["cluster_name", "avg_minutes", "avg_calories", "avg_rating"]
                ).properties(
                    height=300,
                    title="Thời Gian Nấu Món Trung Bình Giữa Các Cụm (Phút)"
                )
                st.altair_chart(chart_bar, use_container_width=True)
            else:
                chart_bar = alt.Chart(clusters_only).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                    x=alt.X("cluster_name:N", title="Cụm Người Dùng", axis=alt.Axis(labelAngle=-15)),
                    y=alt.Y("avg_rating:Q", title="Điểm Đánh Giá TB (Sao)", scale=alt.Scale(domain=[2.8, 3.2])),
                    color=alt.Color("cluster_name:N", legend=None),
                    tooltip=["cluster_name", "avg_rating", "user_count", "pct_man_high"]
                ).properties(
                    height=300,
                    title="Điểm Đánh Giá Trung Bình Giữa Các Cụm (Sao)"
                )
                st.altair_chart(chart_bar, use_container_width=True)

        # Món tiêu biểu từng cụm
        if ds_key == "food_com":
            st.markdown("#### 🌟 Món Ăn Tiêu Biểu Cho Từng Cụm Người Dùng Food.com")
            m1, m2, m3, m4 = st.columns(4)
            with m1:
                st.info("**Cụm 0: Đánh Giá Khắt Khe (13.0%)**\n\n• `creamy cajun chicken pasta`\n• `crock pot chicken with black beans`\n• `to die for crock pot roast`")
            with m2:
                st.success("**Cụm 1: Phổ Thông Dễ Tính (34.7%)**\n\n• `crock pot chicken with cream cheese`\n• `to die for crock pot roast`\n• `creamy cajun chicken pasta`")
            with m3:
                st.warning("**Cụm 2: Chuộng Món Nhanh (25.7%)**\n\n• `fudge crinkles 4 ingredient cookie`\n• `whatever floats your boat brownies`\n• `quick easy skillet meals`")
            with m4:
                st.info("**Cụm 3: Thâm Niên Tích Cực (26.6%)**\n\n• `to die for crock pot roast`\n• `crock pot chicken cream cheese`\n• `whatever floats your boat brownies`")

            st.markdown("""
            <div class="conclusion-box">
                <strong>💡 Kết luận phân cụm Food.com (k=4):</strong> Thuật toán tách biệt thành công <b>Cụm 0 (12.98%)</b> với điểm đánh giá thấp bất thường (3.83 sao so với TB 4.68 sao); <b>Cụm 2 (25.69%)</b> ưu tiên các món chế biến thần tốc (45.53 phút so với 105.88 phút ở Cụm 1); và <b>Cụm 3 (26.63%)</b> gồm những thành viên kỳ cựu với thâm niên trung bình tới 5.3 năm (1,948 ngày).
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="conclusion-box">
                <strong>💡 Kết luận phân cụm ViFoodRec (k=3):</strong> Mặc dù dữ liệu có mật độ dày và điểm đánh giá xấp xỉ 3.0 sao, mô hình vẫn nhận diện được <b>Cụm 0 (43.56%)</b> chuộng bữa ăn nhanh và món mặn nhất (32.19% chấm cao món mặn); <b>Cụm 1 (27.72%)</b> khắt khe nhất (rating 2.96 sao); và <b>Cụm 2 (28.71%)</b> năng động nhất với 1,234 lượt đánh giá/người.
            </div>
            """, unsafe_allow_html=True)

        # Hiển thị ảnh phân tán PCA 2D từ Spark MLlib nếu có
        pca_fig = REPORTS_FIG_DIR / ("kmeans_user_clusters_vifood_pca.png" if ds_key == "vifoodrec" else "kmeans_user_clusters_foodcom_pca.png")
        if pca_fig.exists():
            with st.expander("🖼️ Xem Biểu Đồ Phân Tán Giảm Chiều PCA 2D (Spark MLlib Xuất Thực Tế)", expanded=False):
                st.image(str(pca_fig), caption="Biểu đồ phân tán PCA 2D phản ánh sự tách cụm của vector người dùng", use_column_width=True)

    else:
        st.warning("Không tìm thấy dữ liệu cluster_profiles tương ứng.")

# ==========================================================
# TAB 2: XU HƯỚNG THEO THỜI GIAN (FOOD.COM)
# ==========================================================
with tab_temporal:
    st.markdown("#### 📈 Phân Tích Chuỗi Thời Gian Hoạt Động Ẩm Thực (Food.com 2000 - 2018)")

    trend_df = load_eda_table("eda_05_food_com_yearly_trend.csv")
    month_df = load_eda_table("eda_06_food_com_monthly.csv")

    if not trend_df.empty:
        col_t1, col_t2 = st.columns([3, 2])

        with col_t1:
            chart_year = alt.Chart(trend_df).mark_line(point=True, color="#10b981").encode(
                x=alt.X("year:O", title="Năm Hoạt Động"),
                y=alt.Y("num_ratings:Q", title="Số Lượng Đánh Giá (Lượt)"),
                tooltip=["year", "num_ratings", "avg_rating"]
            ).properties(
                height=320,
                title="Số Lượng Lượt Đánh Giá Theo Từng Năm (2000 - 2018) (Đơn vị: Lượt)"
            )
            st.altair_chart(chart_year, use_container_width=True)

        with col_t2:
            if not month_df.empty:
                chart_m = alt.Chart(month_df).mark_bar(color="#3b82f6", cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                    x=alt.X("m:O", title="Tháng Trong Năm (1 - 12)"),
                    y=alt.Y("count:Q", title="Tổng Lượt Tương Tác"),
                    tooltip=["m", "count"]
                ).properties(
                    height=320,
                    title="Phân Bố Hoạt Động Theo Tháng (Đơn vị: Lượt)"
                )
                st.altair_chart(chart_m, use_container_width=True)

        # Tìm năm đỉnh điểm
        max_row = trend_df.loc[trend_df["num_ratings"].idxmax()]
        peak_year = int(max_row["year"])
        peak_count = int(max_row["num_ratings"])

        st.markdown(f"""
        <div class="conclusion-box">
            <strong>💡 Kết luận xu hướng thời gian:</strong> Cộng đồng Food.com hoạt động sôi nổi nhất trong giai đoạn 2006–2009, đạt đỉnh tuyệt đối vào <b>năm {peak_year} với {peak_count:,} lượt đánh giá</b>. Về mùa vụ, <b>tháng 1</b> (đầu năm mới) có lượng tương tác cao nhất (gần 70,000 lượt) khi người dùng tích cực tìm kiếm công thức dinh dưỡng cho kế hoạch năm mới.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Chưa tìm thấy tệp eda_05_food_com_yearly_trend.csv trong app/data/eda/.")

# ==========================================================
# TAB 3: PHÂN CỤM MÓN ĂN VIFOODREC
# ==========================================================
with tab_food_clusters:
    st.markdown("#### 🍲 Phân Cụm Dinh Dưỡng & Ẩm Thực 4,000 Món Ăn ViFoodRec (k=4)")

    food_prof_df = load_food_cluster_profiles()

    if not food_prof_df.empty:
        st.dataframe(food_prof_df, use_container_width=True)

        food_clusters_only = food_prof_df[food_prof_df["cluster"] >= 0].copy()

        # Biểu đồ dinh dưỡng so sánh
        c_left, c_right = st.columns(2)
        with c_left:
            chart_nutri = alt.Chart(food_clusters_only).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                x=alt.X("cluster_name:N", title="Cụm Món Ăn", axis=alt.Axis(labelAngle=-15)),
                y=alt.Y("calories:Q", title="Năng Lượng Trung Bình (kcal)"),
                color=alt.Color("cluster_name:N", legend=None),
                tooltip=["cluster_name", "calories", "sugar", "protein", "fat"]
            ).properties(
                height=300,
                title="Lượng Calo Trung Bình Của 4 Cụm Món Ăn (kcal)"
            )
            st.altair_chart(chart_nutri, use_container_width=True)

        with c_right:
            chart_time = alt.Chart(food_clusters_only).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                x=alt.X("cluster_name:N", title="Cụm Món Ăn", axis=alt.Axis(labelAngle=-15)),
                y=alt.Y("sugar:Q", title="Lượng Đường Trung Bình (g)"),
                color=alt.Color("cluster_name:N", legend=None),
                tooltip=["cluster_name", "sugar", "cooking_time_min", "n_ingredients"]
            ).properties(
                height=300,
                title="Lượng Đường Trung Bình Nêm Nếm Giữa Các Cụm (g)"
            )
            st.altair_chart(chart_time, use_container_width=True)

        st.markdown("#### 🥗 Đặc Trưng Ẩm Thực & Món Ăn Tiêu Biểu Trong Thực Tế")
        f1, f2, f3, f4 = st.columns(4)
        with f1:
            st.info("**Cụm 0: Chiên Xào Đậm Vị (37.2%)**\n\n• Calo: 465 kcal (Cao nhất)\n• Đường: 24.3g (Đậm đà)\n• *Món ví dụ:* `Bánh Canh Chả Cá Nha Trang`, `Bánh Khoai Sọ Chiên Giòn`")
        with f2:
            st.success("**Cụm 1: Canh Hầm Ít Đường (30.3%)**\n\n• Đạm: 23.1g (Giàu protein)\n• Đường: 13.3g (Ít đường)\n• *Món ví dụ:* `Canh Chua Tôm Bông So Đũa`, `Bánh giò trứng cút`")
        with f3:
            st.warning("**Cụm 2: Món Chay Thanh Tịnh (4.9%)**\n\n• **100% Thuần Chay**\n• Nguyên liệu: 12.2 (Phức tạp nhất)\n• *Món ví dụ:* `Bánh khọt chay`, `Canh Rau Mồng Tơi Chay`, `Miến Xào Chay`")
        with f4:
            st.info("**Cụm 3: Bánh & Ăn Vặt (27.7%)**\n\n• Calo: 249.7 kcal (Thấp nhất)\n• Nấu nhanh, ăn nhẹ\n• *Món ví dụ:* `Bánh Crepe Trà Sữa`, `Bánh Tráng Trộn`, `Bánh Quy Earl Grey`")

        st.markdown("""
        <div class="conclusion-box">
            <strong>💡 Kết luận phân cụm món ăn ViFoodRec:</strong> K-means phân tách hoàn hảo nhóm <b>Món Chay (Cụm 2, 195 món thuần chay)</b> với số nguyên liệu trung bình cao nhất (12.21 nguyên liệu) để tạo hương vị chay trọn vẹn, đồng thời tách biệt rõ ràng giữa nhóm <b>Canh hầm thanh đạm ít đường (Cụm 1: 13.34g đường)</b> và nhóm <b>Món mặn chiên xào đậm ngọt (Cụm 0: 24.25g đường)</b>.
        </div>
        """, unsafe_allow_html=True)

        pca_food_fig = REPORTS_FIG_DIR / "kmeans_food_clusters_vifood_pca.png"
        if pca_food_fig.exists():
            with st.expander("🖼️ Xem Biểu Đồ Phân Tán PCA 2D 4 Cụm Món Ăn ViFoodRec", expanded=False):
                st.image(str(pca_food_fig), caption="Phân tán PCA 2D món ăn ViFoodRec chứng minh sự tách biệt rõ ràng giữa món Chay và món Mặn", use_column_width=True)
    else:
        st.warning("Không tìm thấy dữ liệu food_cluster_profiles_vietnam.csv.")

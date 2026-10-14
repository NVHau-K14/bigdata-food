"""
Trang 3: Hệ thống gợi ý món ăn (Recommendation Engine) với 2 chế độ:
1. Gợi ý cá nhân hóa cho người dùng có sẵn (ALS Matrix Factorization).
2. Gợi ý cho người dùng mới (Cold-Start Recommender) dựa trên Cosine Item Neighbors.
"""

import sys
from pathlib import Path

# Đảm bảo đường dẫn gốc của project luôn nằm trong sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import streamlit as st
import pandas as pd
from app.utils.styles import apply_custom_css
from app.utils.data_loader import (
    load_foods_catalog,
    load_recommendations,
    load_user_clusters,
)
from app.utils.recommender import (
    get_personalized_recommendations,
    get_cold_start_recommendations,
)

apply_custom_css()

st.markdown('<div class="hero-title">🍲 Hệ Thống Gợi Ý Món Ăn Thông Minh</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">Mô hình phân rã ma trận ALS (Spark MLlib) kết hợp thuật toán Cold-Start từ ma trận Item Latent Factors.</div>',
    unsafe_allow_html=True,
)

# Lấy bộ dữ liệu đang chọn
current_dataset = st.session_state.get("dataset", "vifoodrec")

# Hiển thị thanh thông báo bộ dữ liệu hiện hành
col_info, col_switch = st.columns([3, 1])
with col_info:
    if current_dataset == "vifoodrec":
        st.info("🇻🇳 Đang áp dụng cho bộ dữ liệu **ViFoodRec** (4,000 món ăn Việt Nam, 101 users khảo sát).")
    else:
        st.success("🌐 Đang áp dụng cho bộ dữ liệu **Food.com** (Mẫu 5,000 users, 78,171 công thức nấu ăn).")
with col_switch:
    new_choice = st.selectbox(
        "Đổi bộ dữ liệu:",
        options=["ViFoodRec (Món Việt)", "Food.com (Quốc tế)"],
        index=0 if current_dataset == "vifoodrec" else 1,
        key="recommender_page_ds_switch",
    )
    selected_ds = "vifoodrec" if "ViFoodRec" in new_choice else "food_com"
    if selected_ds != current_dataset:
        st.session_state["dataset"] = selected_ds
        st.rerun()

tab_personal, tab_cold_start = st.tabs([
    "👤 1. Người Dùng Có Sẵn (Personalized ALS)",
    "❄️ 2. Người Dùng Mới (Cold-Start Recommender)",
])

# ==========================================================
# CHẾ ĐỘ 1: NGƯỜI DÙNG CÓ SẴN (PERSONALIZED ALS)
# ==========================================================
with tab_personal:
    st.markdown("### Gợi Ý Cá Nhân Hóa Dựa Trên Lịch Sử Đánh Giá (ALS Model)")
    
    recs_df = load_recommendations(current_dataset)
    clusters_df = load_user_clusters(current_dataset)

    if not recs_df.empty:
        available_users = sorted(recs_df["user_id"].unique().tolist())

        # Hàng điều khiển chọn người dùng và tham số
        ctrl_c1, ctrl_c2, ctrl_c3 = st.columns([1.5, 1, 1.5])
        with ctrl_c1:
            selected_user = st.selectbox(
                "Chọn ID Người Dùng:",
                options=available_users,
                index=0,
                help=f"Có {len(available_users):,} người dùng sẵn có trong tập gợi ý.",
            )
        with ctrl_c2:
            top_n = st.slider("Số lượng gợi ý (Top-N):", min_value=3, max_value=10, value=10, step=1)
        with ctrl_c3:
            dish_type_filter = "Tất cả"
            if current_dataset == "vifoodrec":
                dish_type_filter = st.selectbox("Lọc thể loại món:", options=["Tất cả", "Món mặn", "Món chay"])

        # Bộ lọc thời gian nấu và calo
        f_col1, f_col2 = st.columns(2)
        with f_col1:
            max_cook_time = st.slider("Thời gian nấu tối đa (phút):", min_value=10, max_value=180, value=180, step=5)
        with f_col2:
            max_calories = st.slider("Lượng calo tối đa (kcal):", min_value=100, max_value=1200, value=1200, step=50)

        # Hiển thị thẻ hồ sơ cụm của người dùng
        user_cluster_info = None
        if not clusters_df.empty:
            uc_row = clusters_df[clusters_df["user_id"] == selected_user]
            if not uc_row.empty:
                user_cluster_info = uc_row.iloc[0]["cluster_name"]

        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 8px; padding: 0.75rem 1rem; margin-bottom: 1.25rem;">
            👤 <b>Hồ sơ Người dùng #{selected_user}:</b> Phân khúc hành vi: <span class="food-badge badge-cluster">{user_cluster_info or 'Chưa phân cụm'}</span>
        </div>
        """, unsafe_allow_html=True)

        # Lấy gợi ý
        p_recs = get_personalized_recommendations(
            user_id=selected_user,
            dataset=current_dataset,
            top_n=top_n,
            dish_type=dish_type_filter if dish_type_filter != "Tất cả" else None,
            max_time=max_cook_time if max_cook_time < 180 else None,
            max_calories=float(max_calories) if max_calories < 1200 else None,
        )

        if not p_recs.empty:
            st.markdown(f"#### 🏆 Top-{len(p_recs)} Món Ăn Được ALS Khuyến Nghị Cho Người Dùng #{selected_user}:")

            # Hiển thị dạng danh sách thẻ đẹp mắt
            for _, r in p_recs.iterrows():
                rank_num = int(r["rank"])
                dish_name = r.get("dish_name", r.get("name", "Món ăn"))
                dish_type = r.get("dish_type", "Chung")
                calo = r.get("calories", None)
                cook_time = r.get("cooking_time", r.get("cooking_time_min", r.get("minutes_clean", None)))
                ingredients = r.get("ingredients", "Đang cập nhật...")

                badge_class = "badge-chay" if dish_type == "Món chay" else "badge-savory"

                calo_str = f"{calo:.1f} kcal" if pd.notna(calo) else "N/A"
                time_str = f"{cook_time} phút" if pd.notna(cook_time) else "N/A"

                st.markdown(f"""
                <div class="food-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <div>
                            <span class="food-badge badge-rank"># {rank_num}</span>
                            <span style="font-size: 1.15rem; font-weight: 700; color: #f8fafc; margin-left: 0.5rem;">{dish_name}</span>
                        </div>
                        <span class="food-badge {badge_class}">{dish_type}</span>
                    </div>
                    <div style="display: flex; gap: 1.5rem; font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.5rem;">
                        <span>🔥 Năng lượng: <b style="color: #fbbf24;">{calo_str}</b></span>
                        <span>⏱️ Thời gian nấu: <b style="color: #38bdf8;">{time_str}</b></span>
                    </div>
                    <div style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.4;">
                        <b>Thành phần nguyên liệu:</b> {ingredients}
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with st.expander("📋 Xem Bảng Dữ Liệu Chi Tiết / Tải Về CSV", expanded=False):
                st.dataframe(p_recs, use_container_width=True)
                csv_bytes = p_recs.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Tải Danh Sách Gợi Ý (.csv)", data=csv_bytes, file_name=f"als_recs_user_{selected_user}.csv", mime="text/csv")
        else:
            st.warning("Không tìm thấy món ăn nào thỏa mãn đồng thời các bộ lọc. Vui lòng mở rộng dải thời gian nấu hoặc mức calo.")

    else:
        st.warning("Không tìm thấy bảng gợi ý recommendations trong app/data/.")

# ==========================================================
# CHẾ ĐỘ 2: NGƯỜI DÙNG MỚI (COLD-START RECOMMENDER)
# ==========================================================
with tab_cold_start:
    st.markdown("### Gợi Ý Cho Khách Ghé Thăm Chưa Có Lịch Sử (Cold-Start)")
    st.markdown("""
    Chọn **từ 3 đến 5 món ăn bạn yêu thích**. Hệ thống sẽ sử dụng ma trận **Cosine Item Neighbors** 
    trích xuất từ vector tiềm ẩn (Latent Factors) của mô hình Spark MLlib ALS để tìm các món đồng điệu nhất với gu ẩm thực của bạn!
    """)

    catalog_df = load_foods_catalog(current_dataset)

    if not catalog_df.empty:
        id_col = "food_id" if current_dataset == "vifoodrec" else "recipe_id"
        name_col = "dish_name" if current_dataset == "vifoodrec" else "name"

        # 3 Nút Preset chọn nhanh phục vụ kiểm thử và demo
        st.markdown("##### ⚡ Bộ Món Chọn Thử Nhanh (Preset Testing):")
        p_col1, p_col2, p_col3 = st.columns(3)

        preset_selection = []
        if current_dataset == "vifoodrec":
            with p_col1:
                if st.button("🌱 Preset 1: Gu Thuần Chay (3 món)", use_container_width=True):
                    # 321: Bánh khọt chay, 2774: Canh Rau Mồng Tơi Chay, 1964: Món Miến Xào Rau Củ Chay
                    st.session_state["cold_start_items"] = [321, 2774, 1964]
            with p_col2:
                if st.button("⚡ Preset 2: Bữa Nhanh & Đậm Vị (3 món)", use_container_width=True):
                    # 3390: Bánh Bò Bông, 2841: Bánh Khoai Sọ Chiên Giòn, 3548: Bánh Tằm Bì
                    st.session_state["cold_start_items"] = [3390, 2841, 3548]
            with p_col3:
                if st.button("🍲 Preset 3: Canh Hầm & Ăn Vặt (3 món)", use_container_width=True):
                    # 1736: Bánh Canh Chả Cá Nha Trang, 1557: Bánh Tráng Trộn, 3121: Bánh Crepe Trà Sữa Thái
                    st.session_state["cold_start_items"] = [1736, 1557, 3121]
        else:
            sample_ids = catalog_df[id_col].head(9).tolist()
            with p_col1:
                if st.button("🍕 Preset 1: Food.com 3 Món Mẫu", use_container_width=True):
                    st.session_state["cold_start_items"] = sample_ids[0:3]
            with p_col2:
                if st.button("🍰 Preset 2: Food.com 3 Món Mẫu", use_container_width=True):
                    st.session_state["cold_start_items"] = sample_ids[3:6]
            with p_col3:
                if st.button("🥗 Preset 3: Food.com 3 Món Mẫu", use_container_width=True):
                    st.session_state["cold_start_items"] = sample_ids[6:9]

        # Khởi tạo lựa chọn mặc định
        if "cold_start_items" not in st.session_state:
            if current_dataset == "vifoodrec":
                st.session_state["cold_start_items"] = [321, 2774, 1964]  # Mặc định bộ món chay để kiểm chứng tiêu chí đạt
            else:
                st.session_state["cold_start_items"] = catalog_df[id_col].head(3).tolist()

        # Tạo map định danh để hiển thị tên món trong Multiselect
        dish_display_map = {
            row[id_col]: f"{row[name_col]} (ID: {row[id_col]})"
            for _, row in catalog_df.iterrows()
        }

        # Multiselect cho phép người dùng tự tìm kiếm và chọn bất kỳ món nào
        selected_dish_ids = st.multiselect(
            "Tìm kiếm và chọn các món ăn bạn ưa thích (Khuyên dùng 3 đến 5 món):",
            options=catalog_df[id_col].tolist(),
            format_func=lambda x: dish_display_map.get(x, f"Món #{x}"),
            default=[x for x in st.session_state["cold_start_items"] if x in dish_display_map],
        )

        # Bộ lọc bổ sung cho Cold-Start
        cs_c1, cs_c2, cs_c3 = st.columns([1, 1, 1])
        with cs_c1:
            cs_top_n = st.slider("Số lượng gợi ý:", min_value=3, max_value=10, value=5, key="cs_top_n_slider")
        with cs_c2:
            cs_dish_type = "Tất cả"
            if current_dataset == "vifoodrec":
                cs_dish_type = st.selectbox("Lọc thể loại món:", options=["Tất cả", "Món mặn", "Món chay"], key="cs_dish_type_select")
        with cs_c3:
            cs_max_time = st.slider("Thời gian nấu tối đa:", min_value=10, max_value=180, value=180, key="cs_time_slider")

        # Kiểm tra điều kiện tối thiểu 3 món
        if len(selected_dish_ids) < 3:
            st.warning(f"⚠️ Bạn mới chọn **{len(selected_dish_ids)}** món. Vui lòng chọn tối thiểu **3 món** để thuật toán phân tích chính xác vector sở thích của bạn.")
        else:
            st.success(f"✅ Đã chọn **{len(selected_dish_ids)} món**. Đang kích hoạt thuật toán truy vấn ma trận tương đồng Item Latent Factors...")

            cold_recs = get_cold_start_recommendations(
                selected_ids=selected_dish_ids,
                dataset=current_dataset,
                top_n=cs_top_n,
                dish_type=cs_dish_type if cs_dish_type != "Tất cả" else None,
                max_time=cs_max_time if cs_max_time < 180 else None,
            )

            if not cold_recs.empty:
                st.markdown(f"#### 🎯 Top-{len(cold_recs)} Món Tương Đồng Nhất Với Gu Ẩm Thực Của Bạn:")

                for _, r in cold_recs.iterrows():
                    rank_num = int(r["rank"])
                    dish_name = r.get("dish_name", r.get("name", "Món ăn"))
                    dish_type = r.get("dish_type", "Chung")
                    calo = r.get("calories", None)
                    cook_time = r.get("cooking_time", r.get("cooking_time_min", r.get("minutes_clean", None)))
                    reason = r.get("recommendation_reason", "")
                    sim_score = r.get("similarity_score", 0.0)
                    ingredients = r.get("ingredients", "Đang cập nhật...")

                    badge_class = "badge-chay" if dish_type == "Món chay" else "badge-savory"
                    calo_str = f"{calo:.1f} kcal" if pd.notna(calo) else "N/A"
                    time_str = f"{cook_time} phút" if pd.notna(cook_time) else "N/A"

                    st.markdown(f"""
                    <div class="food-card" style="border-left: 4px solid #10b981;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                            <div>
                                <span class="food-badge badge-rank"># {rank_num}</span>
                                <span style="font-size: 1.15rem; font-weight: 700; color: #f8fafc; margin-left: 0.5rem;">{dish_name}</span>
                            </div>
                            <div>
                                <span class="food-badge badge-rank">Độ tương đồng: {sim_score*100:.1f}%</span>
                                <span class="food-badge {badge_class}" style="margin-left: 0.35rem;">{dish_type}</span>
                            </div>
                        </div>
                        <div style="background: rgba(16, 185, 129, 0.1); border-radius: 6px; padding: 0.4rem 0.75rem; font-size: 0.85rem; color: #34d399; margin-bottom: 0.6rem;">
                            💡 <b>Lý do gợi ý:</b> {reason}
                        </div>
                        <div style="display: flex; gap: 1.5rem; font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.5rem;">
                            <span>🔥 Năng lượng: <b style="color: #fbbf24;">{calo_str}</b></span>
                            <span>⏱️ Thời gian nấu: <b style="color: #38bdf8;">{time_str}</b></span>
                        </div>
                        <div style="font-size: 0.85rem; color: #cbd5e1; line-height: 1.4;">
                            <b>Thành phần nguyên liệu:</b> {ingredients}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

                with st.expander("📋 Xem Bảng Dữ Liệu Kết Quả Cold-Start", expanded=False):
                    st.dataframe(cold_recs, use_container_width=True)
            else:
                st.warning("Không tìm thấy món lân cận nào phù hợp với bộ lọc hiện tại. Vui lòng thử nới lỏng điều kiện lọc.")

    else:
        st.warning("Không tìm thấy danh mục món ăn trong app/data/.")

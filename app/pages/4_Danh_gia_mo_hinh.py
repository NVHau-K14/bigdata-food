"""
Trang 4: Đánh giá mô hình (Baseline vs ALS), phân rã RMSE, kết quả tuning và thực nghiệm mở rộng quy mô (Scalability).
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
    load_model_comparison,
    load_rmse_breakdown,
    load_als_tuning,
    load_scalability,
)

apply_custom_css()

# Thư mục hình ảnh báo cáo
REPORTS_FIG_DIR = Path(__file__).resolve().parent.parent.parent / "reports" / "figures"

st.markdown('<div class="hero-title">📈 Đánh Giá Mô Hình & Mở Rộng Quy Mô (Scalability)</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-subtitle">So sánh trực diện Baseline vs ALS Matrix Factorization trên tập Test, phân rã sai số theo thang điểm, nhật ký Grid Search và đo lường mở rộng phân tán.</div>',
    unsafe_allow_html=True,
)

tab_comp, tab_breakdown, tab_tuning, tab_scale = st.tabs([
    "🏆 1. So Sánh Baseline vs ALS",
    "🎯 2. Phân Rã RMSE Theo Thang Điểm",
    "⚙️ 3. Nhật Ký Tinh Chỉnh Siêu Tham Số (Tuning)",
    "⚡ 4. Thực Nghiệm Mở Rộng Quy Mô (Scalability)",
])

# ==========================================================
# TAB 1: SO SÁNH BASELINE VS ALS MATRIX FACTORIZATION
# ==========================================================
with tab_comp:
    st.markdown("### 1. Bảng So Sánh Tổng Hợp Mô Hình Trên Tập Kiểm Thử (Test Set)")

    comp_df = load_model_comparison()

    if not comp_df.empty:
        # Bộ chọn tập dữ liệu
        col_sel, col_empty = st.columns([2, 2])
        with col_sel:
            ds_choice = st.selectbox(
                "Chọn bộ dữ liệu kiểm thử:",
                options=["ViFoodRec (food_vietnam)", "Food.com (food_com)"],
                index=0,
                key="model_comp_ds_select",
            )
        ds_filter = "food_vietnam" if "ViFoodRec" in ds_choice else "food_com"
        sub_comp = comp_df[comp_df["dataset"] == ds_filter].copy()

        # Hiển thị bảng số liệu chuẩn
        st.dataframe(sub_comp, use_container_width=True)

        # Biểu đồ cột kép so sánh RMSE và MAE
        col_c1, col_c2 = st.columns(2)

        with col_c1:
            chart_error = alt.Chart(sub_comp).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                x=alt.X("model:N", title="Mô Hình Thử Nghiệm", axis=alt.Axis(labelAngle=-15)),
                y=alt.Y("RMSE:Q", title="Root Mean Squared Error (RMSE)"),
                color=alt.Color("model:N", scale=alt.Scale(range=["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6"]), legend=None),
                tooltip=["dataset", "model", "RMSE", "MAE", "Precision@10"]
            ).properties(
                height=320,
                title=f"So Sánh Sai Số RMSE ({ds_choice}) (Đơn vị: Điểm sao - Càng thấp càng tốt)"
            )
            st.altair_chart(chart_error, use_container_width=True)

        with col_c2:
            chart_prec = alt.Chart(sub_comp).mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6).encode(
                x=alt.X("model:N", title="Mô Hình Thử Nghiệm", axis=alt.Axis(labelAngle=-15)),
                y=alt.Y("Precision@10:Q", title="Độ Chính Xác Top-10 (Precision@10)"),
                color=alt.Color("model:N", scale=alt.Scale(range=["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6"]), legend=None),
                tooltip=["dataset", "model", "Precision@10", "Recall@10"]
            ).properties(
                height=320,
                title=f"Độ Chính Xác Xếp Hạng Precision@10 ({ds_choice})"
            )
            st.altair_chart(chart_prec, use_container_width=True)

        # Phân tích nguyên nhân khoa học trung thực
        if ds_filter == "food_vietnam":
            als_row = sub_comp[sub_comp["model"].str.contains("ALS")].iloc[0]
            gm_row = sub_comp[sub_comp["model"].str.contains("Global Mean")].iloc[0]
            st.markdown(f"""
            <div class="conclusion-box">
                <strong>💡 Phân tích trung thực trên ViFoodRec:</strong> Trên tập Test ViFoodRec, mô hình ALS đạt <b>RMSE = {als_row['RMSE']:.4f}</b> (cao hơn nhẹ so với Global Mean {gm_row['RMSE']:.4f}).<br>
                <b>Nguyên nhân cốt lõi:</b> Dữ liệu ViFoodRec có phân phối điểm rất phẳng quanh giá trị 3.0 sao (do tác giả điền khuyết bằng trung vị), khiến một dự đoán hằng số $y=3.0$ tự nhiên đạt RMSE thấp. Tuy nhiên, Global Mean hoàn toàn bất lực trong việc xếp hạng cá nhân hóa (Precision@10 = 0.0), trong khi ALS mang lại khả năng phân loại sở thích cá nhân độc đáo và sinh ra ma trận Item Latent Factors để phục vụ Cold-Start.
            </div>
            """, unsafe_allow_html=True)
        else:
            als_row = sub_comp[sub_comp["model"].str.contains("ALS")].iloc[0]
            st.markdown(f"""
            <div class="conclusion-box">
                <strong>💡 Phân tích trung thực trên Food.com:</strong> Trên tập dữ liệu cực thưa (99.97%), ALS Matrix Factorization đạt <b>RMSE = {als_row['RMSE']:.4f}</b> trên tập Test. Mô hình Top-N Popular đạt Precision@10 cao nhất do thói quen tập trung vào các công thức nấu ăn thịnh hành của cộng đồng Food.com.
            </div>
            """, unsafe_allow_html=True)

    else:
        st.warning("Chưa tìm thấy tệp model_comparison.csv trong app/data/.")

# ==========================================================
# TAB 2: PHÂN RÃ RMSE THEO TỪNG THANG ĐIỂM
# ==========================================================
with tab_breakdown:
    st.markdown("### 2. Phân Rã Sai Số RMSE Theo Từng Mức Điểm Đánh Giá Thật (1.0 đến 5.0 Sao)")
    st.markdown("Giúp trả lời câu hỏi phản biện: *'Mô hình dự đoán tốt ở dải điểm nào, và có bị ảnh hưởng bởi hiện tượng lệch chuẩn rating không?'*")

    col_b_sel, _ = st.columns([2, 2])
    with col_b_sel:
        ds_b_choice = st.selectbox(
            "Chọn bộ dữ liệu phân rã:",
            options=["ViFoodRec (Món Việt)", "Food.com (Kaggle)"],
            index=0,
            key="rmse_breakdown_ds_select",
        )
    ds_b_key = "food_vietnam" if "ViFoodRec" in ds_b_choice else "food_com"
    breakdown_df = load_rmse_breakdown(ds_b_key)

    if not breakdown_df.empty:
        chart_line_rmse = alt.Chart(breakdown_df).mark_line(point=True).encode(
            x=alt.X("rating_level:O", title="Mức Điểm Đánh Giá Thật (Sao)"),
            y=alt.Y("rmse:Q", title="Sai Số RMSE Tại Mức Điểm"),
            color=alt.Color("model:N", scale=alt.Scale(range=["#10b981", "#3b82f6", "#f59e0b", "#ec4899"]), title="Mô Hình"),
            tooltip=["dataset", "model", "rating_level", "rmse"]
        ).properties(
            height=340,
            title=f"Đường Biểu Diễn Sai Số RMSE Theo Từng Bậc Điểm ({ds_b_choice}) (Đơn vị: Điểm sao)"
        )
        st.altair_chart(chart_line_rmse, use_container_width=True)

        if ds_b_key == "food_com":
            st.markdown("""
            <div class="conclusion-box">
                <strong>💡 Phát hiện khoa học quan trọng (Food.com):</strong> Dữ liệu Food.com có gần 80% đánh giá là 5 sao. Các mô hình Baseline chỉ dự đoán điểm cao nên sai số tại mức 1 sao lên tới >3.5 điểm. Ngược lại, <b>ALS Matrix Factorization giảm sai số rõ rệt ở dải 1.0 đến 4.0 sao</b>, chứng minh khả năng học được đặc trưng của nhóm khách hàng khó tính (Critical Reviewers).
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="conclusion-box">
                <strong>💡 Phát hiện khoa học (ViFoodRec):</strong> Sai số RMSE của ALS đạt cực tiểu tại mức điểm 3.0 sao (RMSE chỉ 0.4927), và tăng dần về hai phía cực biên (1.0 sao: 1.9511; 5.0 sao: 2.1751) do hiệu ứng quy chuẩn hóa regularization kéo các dự đoán thưa về giá trị trung vị 3.0.
            </div>
            """, unsafe_allow_html=True)

        with st.expander("📋 Xem Bảng Dữ Liệu Phân Rã Chi Tiết", expanded=False):
            st.dataframe(breakdown_df, use_container_width=True)
    else:
        st.warning("Không tìm thấy dữ liệu rmse_breakdown tương ứng.")

# ==========================================================
# TAB 3: NHẬT KÝ TINH CHỈNH SIÊU THAM SỐ (TUNING)
# ==========================================================
with tab_tuning:
    st.markdown("### 3. Nhật Ký Dò Tìm Siêu Tham Số Tối Ưu (Grid Search trên Tập Validation)")
    st.markdown("Nguyên tắc khoa học: **Lựa chọn tham số hoàn toàn diễn ra trên tập Validation, tuyệt đối không dùng tập Test**.")

    col_t_sel, _ = st.columns([2, 2])
    with col_t_sel:
        ds_t_choice = st.selectbox(
            "Chọn tập dữ liệu Tuning:",
            options=["ViFoodRec (24 Cấu hình)", "Food.com (8 Cấu hình)"],
            index=0,
            key="tuning_ds_select",
        )
    ds_t_key = "vifoodrec" if "ViFoodRec" in ds_t_choice else "food_com"
    tuning_df = load_als_tuning(ds_t_key)

    if not tuning_df.empty:
        st.dataframe(tuning_df, use_container_width=True)

        # Biểu đồ đường thể hiện ảnh hưởng của Regularization (regParam) và Rank
        if "regParam" in tuning_df.columns and "val_rmse" in tuning_df.columns:
            tooltip_cols = [c for c in ["rank", "regParam", "maxIter", "val_rmse", "train_time_sec"] if c in tuning_df.columns]
            chart_tune = alt.Chart(tuning_df).mark_line(point=True).encode(
                x=alt.X("regParam:O", title="Hệ Số Điều Chuẩn (regParam - Lambda)"),
                y=alt.Y("val_rmse:Q", title="Validation RMSE (Càng thấp càng tốt)", scale=alt.Scale(zero=False)),
                color=alt.Color("rank:N", title="Số Chiều Tiềm Ẩn (Rank k)"),
                tooltip=tooltip_cols
            ).properties(
                height=320,
                title=f"Xu Hướng Validation RMSE Theo Siêu Tham Số ({ds_t_choice})"
            )
            st.altair_chart(chart_tune, use_container_width=True)

        # Tìm cấu hình tốt nhất
        best_cfg = tuning_df.loc[tuning_df["val_rmse"].idxmin()]
        time_val = best_cfg.get("train_time_sec", best_cfg.get("total_time_sec", 0.0))
        st.markdown(f"""
        <div class="conclusion-box">
            <strong>🎯 Cấu hình tối ưu được chọn (Best Model):</strong><br>
            • <b>Rank (k):</b> {int(best_cfg['rank'])} &nbsp;|&nbsp; 
            • <b>regParam (λ):</b> {best_cfg['regParam']} &nbsp;|&nbsp; 
            • <b>maxIter:</b> {int(best_cfg['maxIter'])} &nbsp;|&nbsp; 
            • <b>Validation RMSE:</b> <span style="color: #34d399; font-weight: 700;">{best_cfg['val_rmse']:.4f}</span> &nbsp;|&nbsp; 
            • <b>Thời gian huấn luyện:</b> {float(time_val):.1f} giây.
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Chưa tìm thấy tệp nhật ký tinh chỉnh siêu tham số.")

# ==========================================================
# TAB 4: THỰC NGHIỆM MỞ RỘNG QUY MÔ (SCALABILITY)
# ==========================================================
with tab_scale:
    st.markdown("### 4. Thực Nghiệm Mở Rộng Quy Mô Dữ Liệu & Tài Nguyên Phân Tán")
    st.markdown("Thực nghiệm trên **Food.com** với 4 mức quy mô người dùng (10%, 25%, 50%, 100%) và 2 cấu hình cụm Spark (1 Worker vs 2 Workers).")

    scale_df = load_scalability()

    if not scale_df.empty:
        # Lọc các bước chính
        step_pipeline = scale_df[scale_df["step"] == "Tổng cộng Pipeline"].copy()

        c_sc1, c_sc2 = st.columns(2)

        with c_sc1:
            chart_scale_time = alt.Chart(step_pipeline).mark_line(point=True).encode(
                x=alt.X("sample_ratio:O", title="Tỷ Lệ Mẫu Dữ Liệu (%)", sort=["10%", "25%", "50%", "100%"]),
                y=alt.Y("avg_time:Q", title="Thời Gian Thực Thi Trung Bình (Giây)"),
                color=alt.Color("resource:N", scale=alt.Scale(range=["#3b82f6", "#10b981"]), title="Cấu Hình Cụm"),
                tooltip=["sample_ratio", "num_rows", "resource", "avg_time", "time_run_1", "time_run_2"]
            ).properties(
                height=320,
                title="Thời Gian Thực Thi Pipeline Theo Quy Mô Dữ Liệu (Đơn vị: Giây)"
            )
            st.altair_chart(chart_scale_time, use_container_width=True)

        with c_sc2:
            # Biểu đồ ổn định RMSE của ALS theo kích thước mẫu
            als_steps = scale_df[(scale_df["step"] == "Step 2: Huấn luyện ALS") & (scale_df["rmse"].notna())].copy()
            chart_scale_rmse = alt.Chart(als_steps).mark_line(point=True, color="#f59e0b").encode(
                x=alt.X("sample_ratio:O", title="Tỷ Lệ Mẫu Dữ Liệu (%)", sort=["10%", "25%", "50%", "100%"]),
                y=alt.Y("rmse:Q", title="ALS Test RMSE", scale=alt.Scale(domain=[0.6, 1.25])),
                tooltip=["sample_ratio", "num_rows", "resource", "rmse"]
            ).properties(
                height=320,
                title="Độ Ổn Định & Hội Tụ RMSE Của ALS Khi Tăng Kích Thước Dữ Liệu"
            )
            st.altair_chart(chart_scale_rmse, use_container_width=True)

        # Trích xuất số liệu thật để đưa vào kết luận
        rmse_10 = als_steps[als_steps["sample_ratio"] == "10%"]["rmse"].iloc[0]
        rmse_100 = als_steps[als_steps["sample_ratio"] == "100%"]["rmse"].iloc[0]
        st.markdown(f"""
        <div class="conclusion-box">
            <strong>💡 Kết luận khoa học từ số liệu thực nghiệm:</strong><br>
            1. <b>Chất lượng mô hình ALS tăng vọt khi mở rộng dữ liệu:</b> RMSE giảm mạnh từ <b>{rmse_10:.4f}</b> (ở 10% dữ liệu) xuống <b>{rmse_100:.4f}</b> (ở 100% dữ liệu), chứng minh tính hiệu quả của Big Data trong việc giải quyết bài toán ma trận cực thưa.<br>
            2. <b>Phân tích tính mở rộng tài nguyên (1 Worker vs 2 Workers):</b> Trên môi trường Docker ảo hóa cùng chia sẻ CPU/RAM vật lý của máy chủ Windows, cấu hình 2 Workers tăng tốc xử lý cho các tác vụ tính toán nặng (ALS Matrix Factorization), nhưng có độ trễ điều phối mạng (Shuffle Overhead) đối với các tác vụ quét dữ liệu nhẹ.
        </div>
        """, unsafe_allow_html=True)

        with st.expander("📋 Xem Chi Tiết Bảng Đo Lường Mở Rộng 32 Bản Ghi", expanded=False):
            st.dataframe(scale_df, use_container_width=True)

        # Hiển thị biểu đồ hình ảnh từ P9 nếu có
        fig_scale = REPORTS_FIG_DIR / "scalability_data_size.png"
        if fig_scale.exists():
            with st.expander("🖼️ Xem Biểu Đồ 4 Khung Mở Rộng Quy Mô (Spark MLlib Xuất Báo Cáo)", expanded=False):
                st.image(str(fig_scale), caption="Biểu đồ mở rộng quy mô chi tiết từng bước: Đọc & Thống kê, ALS, K-means và Tổng thể", use_column_width=True)
    else:
        st.warning("Chưa tìm thấy tệp scalability.csv trong app/data/.")

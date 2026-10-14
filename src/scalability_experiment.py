"""
src/scalability_experiment.py
-----------------------------
Đo lường và đánh giá khả năng mở rộng quy mô (Scalability Experiment) của pipeline
phân tích dữ liệu lớn trên bộ dữ liệu Food.com (P9).

Nguyên tắc thực nghiệm:
1. Mẫu dữ liệu: Lấy mẫu THEO NGƯỜI DÙNG (User-based sampling) bằng hàm băm xác định
   với seed=42 để bảo toàn toàn bộ lịch sử tương tác của từng cá nhân.
   Các tỷ lệ: 10%, 25%, 50%, 100%. Ghi nhận số dòng, số user, số món thực tế.
2. Với mỗi tỷ lệ mẫu, thực hiện 3 bước nghiệp vụ:
   - Bước 1 (Ingestion & Aggregation): Đọc dữ liệu sạch và tính thống kê tổng hợp.
   - Bước 2 (ALS Training): Huấn luyện ALS với tham số tối ưu ở P7 (rank=10, reg=0.20, maxIter=10),
     đánh giá RMSE trên tập Test.
   - Bước 3 (K-means Clustering): Huấn luyện K-means với k=4 tối ưu ở P8 trên đặc trưng người dùng.
3. Biến số tài nguyên phân tán:
   - 1 Worker (2 Cores, 3.5 GB RAM)
   - 2 Workers (4 Cores, 7.0 GB RAM)
4. Đo lặp lại 2 lần cho mỗi cấu hình bằng time.perf_counter quanh các action thực thi thực tế.
5. Xuất kết quả ra results/scalability.csv và vẽ biểu đồ trực quan trong reports/figures/.
"""

import os
import sys
import time
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from pyspark.sql import functions as F, Window
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.clustering import KMeans
from pyspark.ml.feature import VectorAssembler, StandardScaler

# Đảm bảo nạp đúng cấu hình dự án
sys.path.append(str(Path(__file__).resolve().parent))
from config import get_spark_session, get_path, get_storage_mode, PROJECT_ROOT
from user_features import extract_food_com_user_features


def parse_args():
    parser = argparse.ArgumentParser(description="Chạy thực nghiệm mở rộng quy mô (P9)")
    parser.add_argument(
        "--resource",
        type=str,
        default="auto",
        help="Cấu hình tài nguyên đo lường (ví dụ: '1 Worker (2 Cores)' hoặc '2 Workers (4 Cores)')"
    )
    parser.add_argument(
        "--reps",
        type=int,
        default=2,
        help="Số lần chạy lặp lại cho mỗi cấu hình (mặc định 2)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(PROJECT_ROOT / "results" / "scalability.csv"),
        help="Đường dẫn file CSV kết quả"
    )
    parser.add_argument(
        "--plot-only",
        action="store_true",
        help="Chỉ vẽ biểu đồ từ file CSV kết quả đã có"
    )
    return parser.parse_args()


def detect_cluster_resource(spark):
    """
    Xác định cấu hình tài nguyên thực tế từ SparkContext.

    PySpark 4.x không còn trả id và số nhân của executor trong getExecutorInfos(), nên đếm executor bằng host
    khác host của driver và lấy số nhân từ spark.executor.cores. Chạy một job nhỏ rồi đợi số executor ổn định
    (executor đăng ký bất đồng bộ, đếm sớm có thể thiếu).
    """
    sc = spark.sparkContext
    sc.parallelize(range(64), 8).count()
    driver_host = sc.getConf().get("spark.driver.host", "")
    cores_per_executor = int(sc.getConf().get("spark.executor.cores", "2"))

    def count_executors():
        return len([e for e in sc.statusTracker().getExecutorInfos() if e.host != driver_host])

    n_executors, stable = count_executors(), 0
    for _ in range(30):
        time.sleep(1)
        current = count_executors()
        stable = stable + 1 if current == n_executors else 0
        n_executors = current
        if stable >= 3 and n_executors >= 1:
            break

    if n_executors <= 1:
        return "1 Worker (2 Cores)"
    else:
        return f"{n_executors} Workers ({n_executors * cores_per_executor} Cores)"


def run_experiment_for_ratio(spark, ratio_pct, recipes_df, train_base_df, test_base_df, clean_interactions_df, all_users_df):
    """
    Thực hiện 1 lượt đo lường cho một tỷ lệ mẫu xác định.
    Trả về: metrics_dict chứa thời gian các bước và thông tin mẫu.
    """
    print(f"\n---> [Mẫu {ratio_pct}%] Chuẩn bị tập dữ liệu lấy mẫu theo người dùng...")
    
    # 1. Lọc người dùng xác định (Deterministic user sampling bằng hash)
    if ratio_pct >= 100:
        sampled_users = all_users_df
    else:
        sampled_users = all_users_df.filter(
            F.abs(F.hash(F.col("user_id"), F.lit(42))) % 100 < ratio_pct
        )

    # Đếm số lượng thực tế
    actual_users = sampled_users.count()

    # Dữ liệu tương tác sạch cho Bước 1
    clean_sample = clean_interactions_df.join(sampled_users, on="user_id", how="inner").cache()
    actual_rows = clean_sample.count()
    actual_recipes = clean_sample.select("recipe_id").distinct().count()

    print(f"     + Số User thực tế: {actual_users:,}")
    print(f"     + Số Tương tác sạch: {actual_rows:,}")
    print(f"     + Số Món thực tế: {actual_recipes:,}")

    # =========================================================================
    # BƯỚC 1: Đọc dữ liệu sạch và tính thống kê tổng hợp (Ingestion & Aggregation)
    # =========================================================================
    print(f"     [Bước 1] Đo thời gian tính toán thống kê tổng hợp...")
    t0 = time.perf_counter()
    # Action thực tế: Nhóm theo rating và tính count, avg rating
    agg_res = clean_sample.groupBy("rating").agg(
        F.count("*").alias("cnt"),
        F.avg("rating").alias("mean_r")
    ).collect()
    step1_time = time.perf_counter() - t0
    print(f"     -> Bước 1 hoàn thành trong {step1_time:.3f} giây (kết quả {len(agg_res)} nhóm rating).")
    clean_sample.unpersist()

    # =========================================================================
    # BƯỚC 2: Huấn luyện ALS với tham số cố định tối ưu ở P7
    # =========================================================================
    print(f"     [Bước 2] Đo thời gian huấn luyện ALS (rank=10, regParam=0.20, maxIter=10)...")
    train_sample = train_base_df.join(sampled_users, on="user_id", how="inner").cache()
    test_sample = test_base_df.join(sampled_users, on="user_id", how="inner").cache()
    
    n_train = train_sample.count()
    n_test = test_sample.count()

    als = ALS(
        rank=10,
        regParam=0.20,
        maxIter=10,
        seed=42,
        userCol="user_id",
        itemCol="recipe_id",
        ratingCol="rating",
        coldStartStrategy="drop"
    )

    t0 = time.perf_counter()
    als_model = als.fit(train_sample)
    step2_time = time.perf_counter() - t0
    print(f"     -> Bước 2 huấn luyện ALS hoàn thành trong {step2_time:.3f} giây.")

    # Đánh giá RMSE trên test
    evaluator = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")
    preds = als_model.transform(test_sample)
    als_rmse = evaluator.evaluate(preds)
    print(f"     -> ALS Test RMSE đạt: {als_rmse:.4f} (trên {n_test:,} bản ghi test).")

    # =========================================================================
    # BƯỚC 3: Huấn luyện K-means với k=4 tối ưu ở P8 trên đặc trưng người dùng
    # =========================================================================
    print(f"     [Bước 3] Đo thời gian huấn luyện K-means người dùng (k=4)...")
    user_feats = extract_food_com_user_features(spark, train_sample, recipes_df)
    feature_cols = [
        "log_n_ratings", "avg_rating", "std_rating", "pct_high_rating",
        "log_avg_minutes", "log_avg_calories", "avg_n_ingredients", "log_activity_span"
    ]
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="raw_vec")
    assembled = assembler.transform(user_feats)
    scaler = StandardScaler(inputCol="raw_vec", outputCol="features", withMean=True, withStd=True)
    scaled = scaler.fit(assembled).transform(assembled).cache()
    # Materialize features trước khi đo vòng lặp K-means
    scaled.count()

    kmeans = KMeans(featuresCol="features", k=4, seed=42, maxIter=25)
    t0 = time.perf_counter()
    km_model = kmeans.fit(scaled)
    step3_time = time.perf_counter() - t0
    training_cost = km_model.summary.trainingCost
    print(f"     -> Bước 3 huấn luyện K-means hoàn thành trong {step3_time:.3f} giây (Cost: {training_cost:,.1f}).")

    # Giải phóng cache
    scaled.unpersist()
    train_sample.unpersist()
    test_sample.unpersist()

    total_pipeline_time = step1_time + step2_time + step3_time

    return {
        "actual_users": actual_users,
        "actual_recipes": actual_recipes,
        "actual_rows": actual_rows,
        "step1_time": step1_time,
        "step2_time": step2_time,
        "step3_time": step3_time,
        "total_time": total_pipeline_time,
        "als_rmse": als_rmse
    }


def plot_scalability_results(csv_path: str, figures_dir: str):
    """
    Vẽ 3 biểu đồ trực quan hóa khoa học chất lượng cao:
    1. scalability_data_size.png: Thời gian thực thi theo kích thước dữ liệu và tài nguyên.
    2. scalability_speedup_efficiency.png: Hệ số tăng tốc (Speedup) và Hiệu suất mở rộng (Efficiency).
    3. scalability_als_rmse.png: Độ ổn định sai số RMSE của ALS qua các tỷ lệ lấy mẫu.
    """
    df = pd.read_csv(csv_path)
    Path(figures_dir).mkdir(parents=True, exist_ok=True)
    
    # Thiết lập phong cách trực quan hóa hiện đại
    sns.set_theme(style="whitegrid")
    plt.rcParams["font.sans-serif"] = "DejaVu Sans"
    plt.rcParams["axes.unicode_minus"] = False

    # -------------------------------------------------------------------------
    # BIỂU ĐỒ 1: Thời gian thực thi theo kích thước dữ liệu và tài nguyên
    # -------------------------------------------------------------------------
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    
    steps = [
        ("Step 1: Đọc & Thống kê", axes[0, 0], "Thời gian Bước 1: Đọc & Thống kê", "Thời gian (giây)"),
        ("Step 2: Huấn luyện ALS", axes[0, 1], "Thời gian Bước 2: Huấn luyện ALS (rank=10, reg=0.20)", "Thời gian (giây)"),
        ("Step 3: Phân cụm K-means", axes[1, 0], "Thời gian Bước 3: Phân cụm K-means (k=4)", "Thời gian (giây)"),
        ("Tổng cộng Pipeline", axes[1, 1], "Tổng thời gian toàn bộ Pipeline", "Thời gian (giây)")
    ]

    palette = {"1 Worker (2 Cores)": "#d95f02", "2 Workers (4 Cores)": "#1b9e77"}

    for step_name, ax, title, ylabel in steps:
        sub_df = df[df["step"] == step_name].copy()
        if sub_df.empty:
            continue
        
        # Sắp xếp theo tỷ lệ mẫu
        sub_df["ratio_num"] = sub_df["sample_ratio"].str.rstrip("%").astype(int)
        sub_df = sub_df.sort_values("ratio_num")

        for res, res_df in sub_df.groupby("resource"):
            color = palette.get(res, "#7570b3")
            ax.plot(
                res_df["sample_ratio"],
                res_df["avg_time"],
                marker="o",
                linewidth=2.5,
                markersize=8,
                label=res,
                color=color
            )
            # Thêm nhãn giá trị tại các điểm
            for _, row in res_df.iterrows():
                ax.annotate(
                    f"{row['avg_time']:.2f}s",
                    (row["sample_ratio"], row["avg_time"]),
                    textcoords="offset points",
                    xytext=(0, 8),
                    ha="center",
                    fontsize=9,
                    fontweight="bold",
                    color=color
                )

        ax.set_title(title, fontsize=13, fontweight="bold", pad=10)
        ax.set_xlabel("Tỷ lệ mẫu người dùng Food.com", fontsize=11, labelpad=8)
        ax.set_ylabel(ylabel, fontsize=11, labelpad=8)
        ax.legend(title="Tài nguyên", frameon=True, fontsize=10)
        ax.grid(True, linestyle="--", alpha=0.6)

    plt.suptitle("THỰC NGHIỆM MỞ RỘNG QUY MÔ (SCALABILITY): THỜI GIAN THEO KÍCH THƯỚC DỮ LIỆU VÀ TÀI NGUYÊN",
                 fontsize=15, fontweight="bold", y=0.99)
    plt.tight_layout()
    fig1_path = os.path.join(figures_dir, "scalability_data_size.png")
    plt.savefig(fig1_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"-> Đã lưu biểu đồ 1 tại: {fig1_path}")

    # -------------------------------------------------------------------------
    # BIỂU ĐỒ 2: Hệ số tăng tốc (Speedup) và Hiệu suất mở rộng (Efficiency)
    # -------------------------------------------------------------------------
    total_df = df[df["step"] == "Tổng cộng Pipeline"].copy()
    if len(total_df["resource"].unique()) >= 2:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        total_df["ratio_num"] = total_df["sample_ratio"].str.rstrip("%").astype(int)
        pivot = total_df.pivot(index=["ratio_num", "sample_ratio"], columns="resource", values="avg_time").reset_index()
        pivot = pivot.sort_values("ratio_num")

        # Giả định res1 là 1 Worker, res2 là 2 Workers
        res1_col = [c for c in pivot.columns if "1 Worker" in c][0]
        res2_col = [c for c in pivot.columns if "2 Workers" in c][0]

        pivot["speedup"] = pivot[res1_col] / pivot[res2_col]
        pivot["efficiency"] = (pivot["speedup"] / 2.0) * 100.0  # 2 workers = 2x lý tưởng

        # Biểu đồ Speedup
        bars1 = ax1.bar(
            pivot["sample_ratio"],
            pivot["speedup"],
            color="#2b83ba",
            width=0.45,
            edgecolor="black",
            linewidth=1.2
        )
        ax1.axhline(2.0, color="#d7191c", linestyle="--", linewidth=2, label="Tăng tốc lý tưởng (Linear 2.0x)")
        ax1.axhline(1.0, color="#636363", linestyle=":", linewidth=1.5, label="Không tăng tốc (1.0x)")

        for bar in bars1:
            h = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width() / 2., h + 0.03, f"{h:.2f}x", ha="center", va="bottom",
                     fontweight="bold", fontsize=10)

        ax1.set_title("Hệ số Tăng tốc Thực tế (Speedup Factor: $S = T_1 / T_2$)", fontsize=12, fontweight="bold")
        ax1.set_xlabel("Tỷ lệ mẫu người dùng", fontsize=11)
        ax1.set_ylabel("Hệ số tăng tốc (Speedup)", fontsize=11)
        ax1.set_ylim(0, 2.3)
        ax1.legend(loc="upper left", frameon=True)
        ax1.grid(True, linestyle="--", alpha=0.5)

        # Biểu đồ Efficiency
        bars2 = ax2.bar(
            pivot["sample_ratio"],
            pivot["efficiency"],
            color="#abdda4",
            width=0.45,
            edgecolor="black",
            linewidth=1.2
        )
        ax2.axhline(100.0, color="#d7191c", linestyle="--", linewidth=2, label="Hiệu suất lý tưởng (100%)")

        for bar in bars2:
            h = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width() / 2., h + 1.5, f"{h:.1f}%", ha="center", va="bottom",
                     fontweight="bold", fontsize=10)

        ax2.set_title("Hiệu suất Mở rộng Phân tán (Scaling Efficiency: $E = S / P$)", fontsize=12, fontweight="bold")
        ax2.set_xlabel("Tỷ lệ mẫu người dùng", fontsize=11)
        ax2.set_ylabel("Hiệu suất (%)", fontsize=11)
        ax2.set_ylim(0, 115)
        ax2.legend(loc="upper left", frameon=True)
        ax2.grid(True, linestyle="--", alpha=0.5)

        plt.suptitle("ĐÁNH GIÁ KHẢ NĂNG MỞ RỘNG TÀI NGUYÊN (1 WORKER VS 2 WORKERS)", fontsize=14, fontweight="bold")
        plt.tight_layout()
        fig2_path = os.path.join(figures_dir, "scalability_speedup_efficiency.png")
        plt.savefig(fig2_path, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"-> Đã lưu biểu đồ 2 tại: {fig2_path}")

    # -------------------------------------------------------------------------
    # BIỂU ĐỒ 3: Độ ổn định của RMSE mô hình ALS qua các tỷ lệ mẫu
    # -------------------------------------------------------------------------
    als_df = df[df["step"] == "Step 2: Huấn luyện ALS"].copy()
    if not als_df.empty:
        fig, ax = plt.subplots(figsize=(9, 5))
        als_df["ratio_num"] = als_df["sample_ratio"].str.rstrip("%").astype(int)
        # Nhóm lấy rmse trung bình theo tỷ lệ mẫu
        rmse_summary = als_df.groupby(["ratio_num", "sample_ratio"])["rmse"].mean().reset_index()
        rmse_summary = rmse_summary.sort_values("ratio_num")

        ax.plot(
            rmse_summary["sample_ratio"],
            rmse_summary["rmse"],
            marker="s",
            color="#7570b3",
            linewidth=2.5,
            markersize=9,
            label="ALS Test RMSE"
        )
        for _, r in rmse_summary.iterrows():
            ax.annotate(
                f"RMSE = {r['rmse']:.4f}",
                (r["sample_ratio"], r["rmse"]),
                textcoords="offset points",
                xytext=(0, 10),
                ha="center",
                fontsize=10,
                fontweight="bold",
                color="#7570b3"
            )

        ax.set_title("ĐỘ ỔN ĐỊNH CHẤT LƯỢNG MÔ HÌNH ALS THEO QUY MÔ DỮ LIỆU", fontsize=13, fontweight="bold", pad=12)
        ax.set_xlabel("Tỷ lệ mẫu người dùng Food.com", fontsize=11, labelpad=8)
        ax.set_ylabel("Test RMSE (sao)", fontsize=11, labelpad=8)
        ax.set_ylim(0.5, 1.35)
        ax.grid(True, linestyle="--", alpha=0.6)
        ax.legend(frameon=True, fontsize=10)

        plt.tight_layout()
        fig3_path = os.path.join(figures_dir, "scalability_als_rmse.png")
        plt.savefig(fig3_path, dpi=300, bbox_inches="tight")
        plt.close()
        print(f"-> Đã lưu biểu đồ 3 tại: {fig3_path}")


def main():
    args = parse_args()
    figures_dir = str(PROJECT_ROOT / "reports" / "figures")

    if args.plot_only:
        print(f"=== CHỈ VẼ BIỂU ĐỒ TỪ: {args.output} ===")
        plot_scalability_results(args.output, figures_dir)
        return

    print("=" * 75)
    print("THỰC NGHIỆM MỞ RỘNG QUY MÔ DỮ LIỆU VÀ TÀI NGUYÊN (GIAI ĐOẠN P9)")
    print(f"Chế độ lưu trữ (STORAGE_MODE): {get_storage_mode()}")
    print("=" * 75)

    spark = get_spark_session(app_name="ScalabilityExperiment_P9")
    
    resource_name = args.resource
    if resource_name == "auto":
        resource_name = detect_cluster_resource(spark)
    print(f"-> Cấu hình tài nguyên ghi nhận: {resource_name}")

    # Đọc dữ liệu cơ sở từ HDFS/local
    clean_interactions_path = get_path("clean", "food_com", "interactions_clean.parquet")
    recipes_clean_path = get_path("clean", "food_com", "recipes_clean.parquet")
    train_path = get_path("splits", "food_com", "train.parquet")
    test_path = get_path("splits", "food_com", "test.parquet")

    print(f"-> Đọc interactions sạch từ: {clean_interactions_path}")
    clean_interactions_df = spark.read.parquet(clean_interactions_path).cache()
    recipes_df = spark.read.parquet(recipes_clean_path).cache()
    train_base_df = spark.read.parquet(train_path).cache()
    test_base_df = spark.read.parquet(test_path).cache()

    # Danh sách người dùng duy nhất
    all_users_df = clean_interactions_df.select("user_id").distinct().cache()
    total_users_count = all_users_df.count()
    print(f"-> Tổng số người dùng Food.com duy nhất: {total_users_count:,} users.")

    ratios = [10, 25, 50, 100]
    records = []

    for ratio in ratios:
        ratio_label = f"{ratio}%"
        print("\n" + "#" * 60)
        print(f"TIẾN HÀNH ĐO LƯỜNG TỶ LỆ MẪU: {ratio_label} ({args.reps} LẦN CHẠY LẶP)")
        print("#" * 60)

        # Chạy 2 lần lặp (hoặc số lần quy định)
        rep_results = []
        for rep in range(1, args.reps + 1):
            print(f"\n--- [LẦN CHẠY {rep}/{args.reps}] ---")
            res = run_experiment_for_ratio(
                spark=spark,
                ratio_pct=ratio,
                recipes_df=recipes_df,
                train_base_df=train_base_df,
                test_base_df=test_base_df,
                clean_interactions_df=clean_interactions_df,
                all_users_df=all_users_df
            )
            rep_results.append(res)

        # Tổng hợp thời gian lần 1, lần 2, trung bình cho từng bước
        actual_rows = rep_results[0]["actual_rows"]
        als_rmse = round(rep_results[0]["als_rmse"], 4)

        step_defs = [
            ("Step 1: Đọc & Thống kê", "step1_time", None),
            ("Step 2: Huấn luyện ALS", "step2_time", als_rmse),
            ("Step 3: Phân cụm K-means", "step3_time", None),
            ("Tổng cộng Pipeline", "total_time", als_rmse)
        ]

        for step_name, key, step_rmse in step_defs:
            t1 = rep_results[0][key]
            t2 = rep_results[1][key] if len(rep_results) > 1 else t1
            avg_t = (t1 + t2) / 2.0

            records.append({
                "sample_ratio": ratio_label,
                "num_rows": actual_rows,
                "resource": resource_name,
                "step": step_name,
                "time_run_1": round(t1, 3),
                "time_run_2": round(t2, 3),
                "avg_time": round(avg_t, 3),
                "rmse": step_rmse if step_rmse is not None else ""
            })

    spark.stop()

    # Xuất kết quả ra DataFrame
    new_df = pd.DataFrame(records)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Nếu file đã tồn tại (ví dụ đã chạy 1 Worker trước đó), gộp lại
    if out_path.exists():
        try:
            existing_df = pd.read_csv(out_path)
            # Loại bỏ các hàng cùng resource nếu có để tránh trùng
            filtered_existing = existing_df[existing_df["resource"] != resource_name]
            combined_df = pd.concat([filtered_existing, new_df], ignore_index=True)
            combined_df.to_csv(out_path, index=False)
            print(f"\n-> Đã cập nhật và gộp kết quả vào: {out_path}")
        except Exception as e:
            new_df.to_csv(out_path, index=False)
            print(f"\n-> Đã ghi mới kết quả vào: {out_path} ({e})")
    else:
        new_df.to_csv(out_path, index=False)
        print(f"\n-> Đã lưu kết quả đo lường tại: {out_path}")

    # Đồng bộ sang data/results/
    data_results_path = PROJECT_ROOT / "data" / "results" / "scalability.csv"
    data_results_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        final_df = pd.read_csv(out_path)
        final_df.to_csv(data_results_path, index=False)
        print(f"-> Đã đồng bộ sang: {data_results_path}")

    # Vẽ biểu đồ
    try:
        plot_scalability_results(str(out_path), figures_dir)
    except Exception as e:
        print(f"Lỗi khi vẽ biểu đồ tự động: {e}")

    print("\n" + "=" * 75)
    print("HOÀN TẤT THỰC NGHIỆM MỞ RỘNG QUY MÔ CHO CẤU HÌNH HIỆN TẠI!")
    print("=" * 75)


if __name__ == "__main__":
    main()

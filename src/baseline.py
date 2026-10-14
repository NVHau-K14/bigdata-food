"""
src/baseline.py
---------------
Xây dựng và đánh giá 3 mô hình Baseline trên tập kiểm thử cho cả Food.com và ViFoodRec:
1. Baseline 1: Global Mean (Trung bình toàn cục)
2. Baseline 2: Smoothed Item Mean (Trung bình theo món có làm trơn với m=5)
3. Baseline 3: Top-N Popular (Top món phổ biến nhất có lọc điểm chất lượng)

Đo lường các chỉ số:
- RMSE, MAE, Coverage
- Precision@10, Recall@10
- RMSE theo từng mức điểm đánh giá thật
Kết quả lưu ra data/results/baseline_metrics.csv và reports/evidence/baseline_metrics.csv
"""

import sys
import time
from pathlib import Path
import pandas as pd
from pyspark.sql import functions as F, Window

# Import config và evaluation
sys.path.append(str(Path(__file__).resolve().parent))
from config import get_spark_session, get_path, get_storage_mode, PROJECT_ROOT, SMOOTHING_M
from evaluation import evaluate_rating_predictions, evaluate_ranking_top_k


def run_baselines_for_dataset(spark, dataset_name: str, item_col: str, quality_threshold: float = 4.0):
    """
    Thực thi 3 mô hình Baseline cho một bộ dữ liệu cụ thể.
    """
    print(f"\n=======================================================")
    print(f"CHẠY BASELINES CHO: {dataset_name.upper()}")
    print(f"Cột item: {item_col}, Hệ số m: {SMOOTHING_M}")
    print(f"=======================================================")

    start_total = time.time()

    # 1. Tải dữ liệu Train và Test
    train_path = get_path("splits", dataset_name, "train.parquet")
    test_path = get_path("splits", dataset_name, "test.parquet")

    train_df = spark.read.parquet(train_path).cache()
    test_df = spark.read.parquet(test_path).cache()

    n_train = train_df.count()
    n_test = test_df.count()
    print(f"-> Train: {n_train:,} dòng | Test: {n_test:,} dòng")

    # 2. Tính toán thống kê toàn cục
    global_stats = train_df.select(
        F.avg("rating").alias("global_mean"),
        F.count("*").alias("total_ratings")
    ).collect()[0]

    mu = float(global_stats["global_mean"])
    print(f"-> Điểm trung bình toàn cục (Global Mean mu): {mu:.4f}")

    # 3. Tính toán thống kê theo từng món (Item Stats)
    # n_i, sum_r, raw_mean, smoothed_mean = (sum_r + m * mu) / (n_i + m)
    item_stats = train_df.groupBy(item_col).agg(
        F.count("rating").alias("n_ratings"),
        F.sum("rating").alias("sum_ratings"),
        F.avg("rating").alias("raw_mean")
    ).withColumn(
        "smoothed_mean",
        (F.col("sum_ratings") + F.lit(SMOOTHING_M * mu)) / (F.col("n_ratings") + F.lit(SMOOTHING_M))
    ).cache()

    metrics_list = []
    breakdown_list = []

    # =========================================================================
    # BASELINE 1: GLOBAL MEAN (Trung bình toàn cục)
    # =========================================================================
    print("\n--- [1] Đang đánh giá Baseline 1: Global Mean ---")
    t0 = time.time()
    b1_preds = test_df.withColumn("prediction", F.lit(mu))
    b1_res = evaluate_rating_predictions(b1_preds, label_col="rating", pred_col="prediction", total_test_count=n_test)

    # Vì dự đoán bằng nhau, không thể xếp hạng cá nhân hóa -> Top-10 ranking gán 0
    b1_p10 = 0.0
    b1_r10 = 0.0
    elapsed_b1 = time.time() - t0
    print(f"-> B1: RMSE={b1_res['rmse']:.4f}, MAE={b1_res['mae']:.4f}, Coverage={b1_res['coverage']:.1f}% ({elapsed_b1:.2f}s)")

    metrics_list.append({
        "dataset": dataset_name,
        "model": "Global Mean",
        "RMSE": round(b1_res["rmse"], 4),
        "MAE": round(b1_res["mae"], 4),
        "Precision@10": round(b1_p10, 5),
        "Recall@10": round(b1_r10, 5),
        "coverage": round(b1_res["coverage"], 2)
    })
    for r_val, r_rmse in b1_res["rmse_per_rating"].items():
        breakdown_list.append({
            "dataset": dataset_name,
            "model": "Global Mean",
            "rating_level": r_val,
            "rmse": round(r_rmse, 4)
        })

    # =========================================================================
    # BASELINE 2: SMOOTHED ITEM MEAN (Trung bình món có làm trơn)
    # =========================================================================
    print("\n--- [2] Đang đánh giá Baseline 2: Smoothed Item Mean ---")
    t0 = time.time()
    b2_preds = test_df.join(item_stats.select(item_col, "smoothed_mean"), on=item_col, how="left") \
                      .withColumn("prediction", F.coalesce(F.col("smoothed_mean"), F.lit(mu)))
    b2_res = evaluate_rating_predictions(b2_preds, label_col="rating", pred_col="prediction", total_test_count=n_test)

    # Xếp hạng Top-10 theo smoothed_mean giảm dần
    # Lấy top 100 món điểm smoothed cao nhất toàn cục
    top_smoothed_items = [
        row[item_col] for row in item_stats.orderBy(F.col("smoothed_mean").desc(), F.col("n_ratings").desc()).limit(150).collect()
    ]
    
    # Tạo top_k_recs_df cho user
    test_users = test_df.select("user_id").distinct()
    b2_recs_df = test_users.withColumn("top_items", F.array([F.lit(x) for x in top_smoothed_items]))

    # Đánh giá ranking
    b2_rank_res = evaluate_ranking_top_k(
        test_df=test_df,
        top_k_recs_df=b2_recs_df,
        train_df=train_df,
        k=10,
        relevant_threshold=quality_threshold,
        user_col="user_id",
        item_col=item_col
    )
    b2_p10 = b2_rank_res["precision@10"]
    b2_r10 = b2_rank_res["recall@10"]
    elapsed_b2 = time.time() - t0
    print(f"-> B2: RMSE={b2_res['rmse']:.4f}, MAE={b2_res['mae']:.4f}, P@10={b2_p10:.5f}, R@10={b2_r10:.5f} ({elapsed_b2:.2f}s)")

    metrics_list.append({
        "dataset": dataset_name,
        "model": "Smoothed Item Mean",
        "RMSE": round(b2_res["rmse"], 4),
        "MAE": round(b2_res["mae"], 4),
        "Precision@10": round(b2_p10, 5),
        "Recall@10": round(b2_r10, 5),
        "coverage": round(b2_res["coverage"], 2)
    })
    for r_val, r_rmse in b2_res["rmse_per_rating"].items():
        breakdown_list.append({
            "dataset": dataset_name,
            "model": "Smoothed Item Mean",
            "rating_level": r_val,
            "rmse": round(r_rmse, 4)
        })

    # =========================================================================
    # BASELINE 3: TOP-N POPULAR (Món phổ biến nhất)
    # =========================================================================
    print("\n--- [3] Đang đánh giá Baseline 3: Top-N Popular ---")
    t0 = time.time()
    # Với dự đoán rating, gán bằng điểm trung bình thực tế raw_mean của món (hoặc smoothed_mean)
    b3_preds = test_df.join(item_stats.select(item_col, "raw_mean"), on=item_col, how="left") \
                      .withColumn("prediction", F.coalesce(F.col("raw_mean"), F.lit(mu)))
    b3_res = evaluate_rating_predictions(b3_preds, label_col="rating", pred_col="prediction", total_test_count=n_test)

    # Với xếp hạng Top-N, chọn các món có n_ratings lớn nhất kèm điều kiện điểm >= quality_threshold
    # (Nếu không đủ, lấy món có n_ratings lớn nhất)
    pop_candidates = item_stats.filter(F.col("raw_mean") >= quality_threshold) \
                               .orderBy(F.col("n_ratings").desc()).limit(150).collect()
    if len(pop_candidates) < 20:
        pop_candidates = item_stats.orderBy(F.col("n_ratings").desc()).limit(150).collect()

    top_popular_items = [row[item_col] for row in pop_candidates]
    b3_recs_df = test_users.withColumn("top_items", F.array([F.lit(x) for x in top_popular_items]))

    b3_rank_res = evaluate_ranking_top_k(
        test_df=test_df,
        top_k_recs_df=b3_recs_df,
        train_df=train_df,
        k=10,
        relevant_threshold=quality_threshold,
        user_col="user_id",
        item_col=item_col
    )
    b3_p10 = b3_rank_res["precision@10"]
    b3_r10 = b3_rank_res["recall@10"]
    elapsed_b3 = time.time() - t0
    print(f"-> B3: RMSE={b3_res['rmse']:.4f}, MAE={b3_res['mae']:.4f}, P@10={b3_p10:.5f}, R@10={b3_r10:.5f} ({elapsed_b3:.2f}s)")

    metrics_list.append({
        "dataset": dataset_name,
        "model": "Top-N Popular",
        "RMSE": round(b3_res["rmse"], 4),
        "MAE": round(b3_res["mae"], 4),
        "Precision@10": round(b3_p10, 5),
        "Recall@10": round(b3_r10, 5),
        "coverage": round(b3_res["coverage"], 2)
    })
    for r_val, r_rmse in b3_res["rmse_per_rating"].items():
        breakdown_list.append({
            "dataset": dataset_name,
            "model": "Top-N Popular",
            "rating_level": r_val,
            "rmse": round(r_rmse, 4)
        })

    elapsed_all = time.time() - start_total
    print(f"-> Hoàn tất baselines cho {dataset_name} trong {elapsed_all:.2f}s!")

    return metrics_list, breakdown_list


def main():
    print("=" * 70)
    print("CHƯƠNG TRÌNH HUẤN LUYỆN VÀ ĐÁNH GIÁ 3 MÔ HÌNH BASELINE (P6)")
    print(f"Chế độ lưu trữ: {get_storage_mode()}")
    print("=" * 70)

    spark = get_spark_session(app_name="BaselineEvaluationPipeline", shuffle_partitions=8)

    all_metrics = []
    all_breakdowns = []

    # 1. Đánh giá Food.com
    # Với Food.com: điểm >= 4.0 là món phù hợp
    fc_metrics, fc_breakdowns = run_baselines_for_dataset(
        spark=spark,
        dataset_name="food_com",
        item_col="recipe_id",
        quality_threshold=4.0
    )
    all_metrics.extend(fc_metrics)
    all_breakdowns.extend(fc_breakdowns)

    # 2. Đánh giá ViFoodRec
    # Với ViFoodRec: do phân phối đều quanh 3.0, điểm >= 4.0 là món phù hợp
    vf_metrics, vf_breakdowns = run_baselines_for_dataset(
        spark=spark,
        dataset_name="food_vietnam",
        item_col="food_id",
        quality_threshold=4.0
    )
    all_metrics.extend(vf_metrics)
    all_breakdowns.extend(vf_breakdowns)

    # 3. Xuất file kết quả
    metrics_df = pd.DataFrame(all_metrics)
    breakdown_df = pd.DataFrame(all_breakdowns)

    # Đảm bảo các thư mục đích tồn tại
    data_results_dir = PROJECT_ROOT / "data" / "results"
    results_dir = PROJECT_ROOT / "results"
    evidence_dir = PROJECT_ROOT / "reports" / "evidence"

    data_results_dir.mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)

    metrics_df.to_csv(data_results_dir / "baseline_metrics.csv", index=False)
    metrics_df.to_csv(results_dir / "baseline_metrics.csv", index=False)
    metrics_df.to_csv(evidence_dir / "baseline_metrics.csv", index=False)

    breakdown_df.to_csv(data_results_dir / "baseline_rmse_breakdown.csv", index=False)
    breakdown_df.to_csv(results_dir / "baseline_rmse_breakdown.csv", index=False)
    breakdown_df.to_csv(evidence_dir / "baseline_rmse_breakdown.csv", index=False)

    print("\n" + "=" * 70)
    print("BẢNG KẾT QUẢ ĐÁNH GIÁ CÁC MÔ HÌNH BASELINE TRÊN TẬP TEST")
    print("=" * 70)
    print(metrics_df.to_string(index=False))

    print("\n" + "=" * 70)
    print("BẢNG PHÂN RÃ RMSE THEO TỪNG MỨC ĐIỂM THẬT (BREAKDOWN)")
    print("=" * 70)
    print(breakdown_df.to_string(index=False))

    spark.stop()
    print("\n[THÀNH CÔNG] Hoàn tất toàn bộ kịch bản đánh giá Baseline!")


if __name__ == "__main__":
    main()

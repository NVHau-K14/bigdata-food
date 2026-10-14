"""
src/evaluation.py
-----------------
Khung đánh giá thống nhất (Unified Evaluation Framework) cho hệ thống gợi ý.
Dùng chung cho các mô hình Baseline (P6) và ALS Matrix Factorization (P7).

Các chỉ số đánh giá:
1. Dự đoán điểm (Rating Prediction):
   - RMSE (Root Mean Squared Error)
   - MAE (Mean Absolute Error)
   - Coverage (% bản ghi kiểm thử có dự đoán hợp lệ)
   - RMSE theo từng mức điểm thật (Rating breakdown: 1.0, 2.0, 3.0, 4.0, 5.0)
2. Xếp hạng Top-K (Ranking Metrics):
   - Precision@K và Recall@K trên tập người dùng có ít nhất 1 món phù hợp (rating >= 4.0)
   - Loại trừ các món người dùng đã tương tác trong tập Train
"""

import math
from typing import Dict, Any, List, Optional
from pyspark.sql import DataFrame, functions as F
from pyspark.ml.evaluation import RegressionEvaluator


def evaluate_rating_predictions(
    predictions_df: DataFrame,
    label_col: str = "rating",
    pred_col: str = "prediction",
    total_test_count: Optional[int] = None
) -> Dict[str, Any]:
    """
    Tính toán các chỉ số dự đoán điểm số (RMSE, MAE, Coverage, RMSE theo từng mức điểm).

    Args:
        predictions_df: Spark DataFrame chứa cột điểm thật và cột dự đoán.
        label_col: Tên cột điểm đánh giá thực tế.
        pred_col: Tên cột điểm dự đoán.
        total_test_count: Tổng số dòng của tập test ban đầu (để tính coverage chính xác).

    Returns:
        Dict chứa rmse, mae, coverage, và dict breakdown rmse theo từng mức điểm.
    """
    # Lọc bỏ các bản ghi không có dự đoán (NaN hoặc Null do Cold-Start drop)
    valid_preds = predictions_df.filter(
        F.col(pred_col).isNotNull() & ~F.isnan(F.col(pred_col))
    ).cache()

    valid_count = valid_preds.count()
    if total_test_count is None or total_test_count <= 0:
        total_test_count = valid_count

    coverage = (valid_count / total_test_count) * 100.0 if total_test_count > 0 else 0.0

    if valid_count == 0:
        return {
            "rmse": None,
            "mae": None,
            "coverage": 0.0,
            "valid_count": 0,
            "total_count": total_test_count,
            "rmse_per_rating": {}
        }

    # Tính RMSE và MAE tổng thể bằng PySpark Evaluator
    evaluator_rmse = RegressionEvaluator(metricName="rmse", labelCol=label_col, predictionCol=pred_col)
    evaluator_mae = RegressionEvaluator(metricName="mae", labelCol=label_col, predictionCol=pred_col)

    rmse = evaluator_rmse.evaluate(valid_preds)
    mae = evaluator_mae.evaluate(valid_preds)

    # Tính RMSE theo từng mức điểm thật (1.0 đến 5.0)
    # Gom nhóm theo label_col, tính sqrt(avg((label - pred)^2))
    breakdown_df = valid_preds.groupBy(label_col).agg(
        F.count("*").alias("count"),
        F.sqrt(F.avg(F.pow(F.col(label_col) - F.col(pred_col), 2))).alias("group_rmse")
    ).orderBy(label_col)

    breakdown_rows = breakdown_df.collect()
    rmse_per_rating = {
        float(row[label_col]): float(row["group_rmse"]) if row["group_rmse"] is not None else 0.0
        for row in breakdown_rows
    }

    return {
        "rmse": float(rmse),
        "mae": float(mae),
        "coverage": float(coverage),
        "valid_count": int(valid_count),
        "total_count": int(total_test_count),
        "rmse_per_rating": rmse_per_rating
    }


def evaluate_ranking_top_k(
    test_df: DataFrame,
    top_k_recs_df: DataFrame,
    train_df: DataFrame,
    k: int = 10,
    relevant_threshold: float = 4.0,
    user_col: str = "user_id",
    item_col: str = "recipe_id"
) -> Dict[str, Any]:
    """
    Tính Precision@K và Recall@K trên tập người dùng có ít nhất 1 món phù hợp trong Test.
    
    Quy tắc:
    - Món phù hợp (Relevant items) của user = các món trong test có rating >= relevant_threshold.
    - Top-K gợi ý = K món có điểm xếp hạng cao nhất của user SAU KHI loại các món trong Train.
    - Precision@K = |TopK ∩ Relevant| / K.
    - Recall@K = |TopK ∩ Relevant| / |Relevant|.
    - Chỉ tính trung bình trên các user có |Relevant| > 0.

    Args:
        test_df: DataFrame tập test (user_col, item_col, rating).
        top_k_recs_df: DataFrame chứa (user_col, top_items: Array[item_id]).
        train_df: DataFrame tập train (để loại bỏ món đã tương tác).
        k: Số lượng món gợi ý Top-K (mặc định 10).
        relevant_threshold: Ngưỡng điểm để coi là món phù hợp (mặc định 4.0).
        user_col: Tên cột user.
        item_col: Tên cột item.

    Returns:
        Dict chứa precision@k, recall@k, số user được đánh giá, và tỷ lệ user có relevant items.
    """
    # 1. Xác định tập relevant items trong test cho mỗi user
    relevant_df = test_df.filter(F.col("rating") >= relevant_threshold) \
                         .groupBy(user_col) \
                         .agg(F.collect_set(item_col).alias("relevant_items")) \
                         .filter(F.size(F.col("relevant_items")) > 0) \
                         .cache()

    total_relevant_users = relevant_df.count()
    if total_relevant_users == 0:
        return {
            f"precision@{k}": 0.0,
            f"recall@{k}": 0.0,
            "evaluated_users": 0,
            "relevant_users": 0
        }

    # 2. Tập các món đã tương tác trong Train của mỗi user
    train_interacted_df = train_df.groupBy(user_col) \
                                  .agg(F.collect_set(item_col).alias("train_items"))

    # 3. Kết hợp với top_k_recs_df
    # top_k_recs_df có: user_col, raw_recommendations (Array)
    # Loại bỏ các món đã có trong Train, sau đó lấy đúng K phần tử đầu tiên
    joined_df = relevant_df.join(top_k_recs_df, on=user_col, how="inner") \
                           .join(train_interacted_df, on=user_col, how="left")

    # UDF hoặc native Spark SQL array functions
    # Sử dụng array_except để lọc bỏ train items, sau đó slice lấy k phần tử
    clean_recs_expr = F.when(
        F.col("train_items").isNotNull(),
        F.slice(F.array_except(F.col("top_items"), F.col("train_items")), 1, k)
    ).otherwise(
        F.slice(F.col("top_items"), 1, k)
    )

    eval_df = joined_df.withColumn("final_top_k", clean_recs_expr) \
                       .withColumn("hits", F.size(F.array_intersect(F.col("final_top_k"), F.col("relevant_items")))) \
                       .withColumn("n_rel", F.size(F.col("relevant_items"))) \
                       .withColumn("user_precision", F.col("hits") / F.lit(float(k))) \
                       .withColumn("user_recall", F.col("hits") / F.col("n_rel").cast("double"))

    summary = eval_df.select(
        F.avg("user_precision").alias("avg_precision"),
        F.avg("user_recall").alias("avg_recall"),
        F.count("*").alias("evaluated_users")
    ).collect()[0]

    avg_prec = float(summary["avg_precision"]) if summary["avg_precision"] is not None else 0.0
    avg_rec = float(summary["avg_recall"]) if summary["avg_recall"] is not None else 0.0
    evaluated_users = int(summary["evaluated_users"])

    return {
        f"precision@{k}": avg_prec,
        f"recall@{k}": avg_rec,
        "evaluated_users": evaluated_users,
        "relevant_users": total_relevant_users
    }

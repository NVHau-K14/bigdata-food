"""
src/train_als.py
----------------
Huấn luyện, tinh chỉnh siêu tham số và đánh giá mô hình ALS Matrix Factorization
trên cụm Apache Spark cho cả hai bộ dữ liệu Food.com và ViFoodRec.

Quy trình thực hiện (P7):
1. Grid Search chọn siêu tham số tối ưu (rank, regParam, maxIter) trên tập VALIDATION.
2. Lưu nhật ký tinh chỉnh vào results/als_tuning_<bộ>.csv.
3. Đánh giá mô hình tốt nhất trên tập TEST (RMSE, MAE, coverage, P@10, R@10, breakdown).
4. So sánh với 3 baseline P6 và xuất results/model_comparison.csv.
5. Lưu mô hình tốt nhất vào /models/als_<bộ>.
6. Xuất Top-10 gợi ý món ăn kèm metadata:
   - ViFoodRec: toàn bộ 101 user -> results/recommendations_food_vietnam.parquet
   - Food.com: mẫu 5.000 user -> results/recommendations_food_com.parquet
7. Tính độ tương đồng Cosine giữa các món từ Item Latent Factors (Top-10 neighbors):
   - ViFoodRec: toàn bộ 4.000 món -> results/item_neighbors_food_vietnam.parquet
   - Food.com: Top 20.000 món phổ biến nhất -> results/item_neighbors_food_com.parquet
"""

import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
from pyspark.sql import functions as F, Window
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator

# Đảm bảo import được config và evaluation từ src
sys.path.append(str(Path(__file__).resolve().parent))
from config import get_spark_session, get_path, get_storage_mode, PROJECT_ROOT
from evaluation import evaluate_rating_predictions, evaluate_ranking_top_k


def tune_als_model(spark, train_df, val_df, item_col, param_grid, dataset_name):
    """
    Thực hiện Grid Search tìm siêu tham số tốt nhất dựa trên RMSE trên tập Validation.
    """
    print(f"\n---> Bắt đầu Grid Search Tuning cho {dataset_name.upper()}...")
    tuning_records = []
    best_rmse = float("inf")
    best_params = None
    best_model = None

    evaluator = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")

    total_configs = len(param_grid)
    for idx, params in enumerate(param_grid):
        r = params["rank"]
        reg = params["regParam"]
        mi = params["maxIter"]

        t_start = time.perf_counter()
        als = ALS(
            rank=r,
            regParam=reg,
            maxIter=mi,
            userCol="user_id",
            itemCol=item_col,
            ratingCol="rating",
            coldStartStrategy="drop",
            nonnegative=True,
            seed=42
        )

        model = als.fit(train_df)
        fit_time = time.perf_counter() - t_start

        # Đánh giá trên tập Validation
        preds_val = model.transform(val_df)
        val_rmse = evaluator.evaluate(preds_val)

        eval_time = time.perf_counter() - t_start

        tuning_records.append({
            "dataset": dataset_name,
            "rank": r,
            "regParam": reg,
            "maxIter": mi,
            "val_rmse": round(val_rmse, 4),
            "train_time_sec": round(fit_time, 2),
            "total_time_sec": round(eval_time, 2)
        })

        print(f"[{idx+1}/{total_configs}] rank={r:2d}, reg={reg:.2f}, maxIter={mi:2d} | Val RMSE: {val_rmse:.4f} (Fit: {fit_time:.1f}s)")

        if val_rmse < best_rmse:
            best_rmse = val_rmse
            best_params = params
            best_model = model

    print(f"---> Tham số tốt nhất cho {dataset_name}: {best_params} với Validation RMSE = {best_rmse:.4f}")
    return best_model, best_params, tuning_records


def generate_als_recommendations(model, user_df, train_df, item_col, k=10, fetch_k=50):
    """
    Sinh Top-K món gợi ý cho danh sách user, tự động loại bỏ các món đã có trong Train.
    """
    # 1. Sinh danh sách ứng viên Top fetch_k từ ALS
    raw_recs = model.recommendForUserSubset(user_df.select("user_id").distinct(), fetch_k)

    # 2. Trích xuất mảng các item_id từ struct recommendations
    # recommendations là mảng struct (item_col, rating)
    raw_recs = raw_recs.withColumn(
        "top_items",
        F.expr(f"transform(recommendations, x -> x.{item_col})")
    )

    # 3. Lấy các món user đã ăn trong train
    train_interacted = train_df.groupBy("user_id").agg(F.collect_set(item_col).alias("train_items"))

    # 4. Trừ tập hợp các món đã ăn và lấy K phần tử đầu
    joined = raw_recs.join(train_interacted, on="user_id", how="left")
    clean_recs = joined.withColumn(
        "clean_top_k",
        F.when(
            F.col("train_items").isNotNull(),
            F.slice(F.array_except(F.col("top_items"), F.col("train_items")), 1, k)
        ).otherwise(
            F.slice(F.col("top_items"), 1, k)
        )
    )

    return clean_recs.select("user_id", F.col("clean_top_k").alias("top_items"))


def compute_item_cosine_neighbors(spark, model, item_col, limit_items=None, top_k=10):
    """
    Tính toán độ tương đồng Cosine giữa các món ăn từ Item Latent Factors và lấy Top-K lân cận.
    """
    print(f"\n---> Đang tính toán Cosine Similarity cho Item Latent Factors...")
    # itemFactors có schema: id (int), features (array<float>)
    item_factors_df = model.itemFactors

    if limit_items is not None:
        item_factors_df = item_factors_df.join(limit_items, item_factors_df.id == limit_items[item_col], "inner") \
                                         .select("id", "features")

    # Thu thập về mảng numpy để tính toán cosine vector hóa nhanh chóng
    rows = item_factors_df.collect()
    n_items = len(rows)
    print(f"-> Thu thập {n_items:,} vector món ăn để tính toán tương đồng.")

    item_ids = [r["id"] for r in rows]
    vectors = np.array([r["features"] for r in rows], dtype=np.float32)

    # Chuẩn hóa L2 vector
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    norms[norms == 0] = 1e-9
    normalized_vecs = vectors / norms

    # Tính cosine similarity theo từng batch để tiết kiệm RAM
    batch_size = 2000
    neighbor_records = []

    for i in range(0, n_items, batch_size):
        end_i = min(i + batch_size, n_items)
        batch = normalized_vecs[i:end_i]
        sim_matrix = np.dot(batch, normalized_vecs.T)

        for b_idx in range(len(batch)):
            curr_item_idx = i + b_idx
            curr_sims = sim_matrix[b_idx]
            # Đặt chính nó = -1 để không tự gợi ý chính mình
            curr_sims[curr_item_idx] = -1.0

            # Lấy top K chỉ số có tương đồng lớn nhất
            top_indices = np.argpartition(curr_sims, -top_k)[-top_k:]
            top_indices = top_indices[np.argsort(-curr_sims[top_indices])]

            neighbor_ids = [int(item_ids[idx]) for idx in top_indices]
            neighbor_scores = [float(curr_sims[idx]) for idx in top_indices]

            neighbor_records.append({
                item_col: int(item_ids[curr_item_idx]),
                "neighbor_ids": neighbor_ids,
                "similarity_scores": neighbor_scores
            })

    # Chuyển thành Spark DataFrame
    pdf = pd.DataFrame(neighbor_records)
    neighbors_df = spark.createDataFrame(pdf)
    return neighbors_df


def run_als_pipeline_for_dataset(spark, dataset_name: str, item_col: str, param_grid: list, is_food_com: bool = False):
    """
    Thực thi toàn bộ pipeline ALS cho một tập dữ liệu.
    """
    print(f"\n==================================================================")
    print(f"KHỞI CHẠY PIPELINE HUẤN LUYỆN ALS: {dataset_name.upper()}")
    print(f"==================================================================")

    # 1. Đọc dữ liệu Train, Validation, Test
    train_path = get_path("splits", dataset_name, "train.parquet")
    val_path = get_path("splits", dataset_name, "validation.parquet")
    test_path = get_path("splits", dataset_name, "test.parquet")

    train_df = spark.read.parquet(train_path).cache()
    val_df = spark.read.parquet(val_path).cache()
    test_df = spark.read.parquet(test_path).cache()

    n_train = train_df.count()
    n_val = val_df.count()
    n_test = test_df.count()
    print(f"-> Quy mô tập dữ liệu: Train={n_train:,} | Val={n_val:,} | Test={n_test:,}")

    # 2. Grid Search chọn siêu tham số tối ưu
    best_model, best_params, tuning_records = tune_als_model(
        spark=spark,
        train_df=train_df,
        val_df=val_df,
        item_col=item_col,
        param_grid=param_grid,
        dataset_name=dataset_name
    )

    # Lưu bảng tuning CSV
    tune_df = pd.DataFrame(tuning_records)
    tune_out_data = PROJECT_ROOT / "data" / "results" / f"als_tuning_{dataset_name}.csv"
    tune_out_res = PROJECT_ROOT / "results" / f"als_tuning_{dataset_name}.csv"
    tune_out_data.parent.mkdir(parents=True, exist_ok=True)
    tune_out_res.parent.mkdir(parents=True, exist_ok=True)
    tune_df.to_csv(tune_out_data, index=False)
    tune_df.to_csv(tune_out_res, index=False)
    print(f"-> Đã lưu kết quả tuning vào {tune_out_res}")

    # 3. Đánh giá mô hình tốt nhất trên tập Test
    print(f"\n---> Đang đánh giá mô hình ALS tốt nhất trên tập TEST...")
    t_inf_start = time.perf_counter()
    preds_test = best_model.transform(test_df).cache()
    preds_test.count() # Force action để đo thời gian suy luận
    inf_time = time.perf_counter() - t_inf_start

    # Đánh giá rating prediction (RMSE, MAE, coverage, breakdown)
    rating_metrics = evaluate_rating_predictions(
        predictions_df=preds_test,
        label_col="rating",
        pred_col="prediction",
        total_test_count=n_test
    )

    # Đánh giá ranking top-10
    print(f"-> Đang tính toán Precision@10 và Recall@10 trên tập Test...")
    test_users = test_df.select("user_id").distinct()
    top_k_recs = generate_als_recommendations(
        model=best_model,
        user_df=test_users,
        train_df=train_df,
        item_col=item_col,
        k=10,
        fetch_k=50
    )

    rank_metrics = evaluate_ranking_top_k(
        test_df=test_df,
        top_k_recs_df=top_k_recs,
        train_df=train_df,
        k=10,
        relevant_threshold=4.0,
        user_col="user_id",
        item_col=item_col
    )

    als_result = {
        "dataset": dataset_name,
        "model": "ALS Matrix Factorization",
        "RMSE": round(rating_metrics["rmse"], 4),
        "MAE": round(rating_metrics["mae"], 4),
        "Precision@10": round(rank_metrics["precision@10"], 5),
        "Recall@10": round(rank_metrics["recall@10"], 5),
        "coverage": round(rating_metrics["coverage"], 2),
        "inference_time_sec": round(inf_time, 2),
        "best_rank": best_params["rank"],
        "best_regParam": best_params["regParam"],
        "best_maxIter": best_params["maxIter"]
    }

    print("\n" + "=" * 60)
    print(f"KẾT QUẢ TEST SET - ALS ({dataset_name}):")
    print(f"RMSE: {als_result['RMSE']} | MAE: {als_result['MAE']} | Coverage: {als_result['coverage']}%")
    print(f"Precision@10: {als_result['Precision@10']} | Recall@10: {als_result['Recall@10']}")
    print(f"Thời gian suy luận: {als_result['inference_time_sec']}s")
    print("=" * 60)

    # 4. Lưu mô hình tốt nhất
    model_save_path = get_path("models", dataset_name, "als_best_model")
    print(f"\n-> Đang lưu mô hình tốt nhất vào: {model_save_path}")
    best_model.write().overwrite().save(model_save_path)

    # 5. Xuất Top-10 Gợi ý món ăn kèm Metadata
    print(f"\n---> Xuất Top-10 gợi ý món ăn kèm metadata...")
    if is_food_com:
        # Lấy mẫu ngẫu nhiên 5.000 user cố định với seed=42
        eval_sample_users = test_users.sample(withReplacement=False, fraction=1.0, seed=42).limit(5000)
        user_recs = generate_als_recommendations(best_model, eval_sample_users, train_df, item_col, k=10)
        
        # Đọc metadata recipes
        meta_recipes = spark.read.parquet(get_path("clean", "food_com", "recipes_clean.parquet")) \
                            .select("recipe_id", "name", "calories", "minutes_clean")
        
        # Explode mảng gợi ý để join metadata
        exploded = user_recs.withColumn(item_col, F.explode("top_items")) \
                            .join(meta_recipes, on=item_col, how="left")
        
        recs_out_path = get_path("results", "", "recommendations_food_com.parquet")
        recs_local_path = PROJECT_ROOT / "data" / "results" / "recommendations_food_com.parquet"
        exploded.write.mode("overwrite").parquet(recs_out_path)
        exploded.write.mode("overwrite").parquet(str(recs_local_path))
    else:
        # ViFoodRec: lấy cho toàn bộ 101 user
        user_recs = generate_als_recommendations(best_model, test_users, train_df, item_col, k=10)
        meta_foods = spark.read.parquet(get_path("clean", "food_vietnam", "foods_clean.parquet")) \
                          .select("food_id", "dish_name", "dish_type", "calories", "cooking_time")
        
        exploded = user_recs.withColumn(item_col, F.explode("top_items")) \
                            .join(meta_foods, on=item_col, how="left")
        
        recs_out_path = get_path("results", "", "recommendations_food_vietnam.parquet")
        recs_local_path = PROJECT_ROOT / "data" / "results" / "recommendations_food_vietnam.parquet"
        exploded.coalesce(1).write.mode("overwrite").parquet(recs_out_path)
        exploded.coalesce(1).write.mode("overwrite").parquet(str(recs_local_path))

    print(f"-> Đã xuất tệp recommendations thành công!")

    # 6. Tính toán Item Neighbors Cosine Similarity
    if is_food_com:
        # Giới hạn Top 20.000 món phổ biến nhất
        top_items_limit = train_df.groupBy(item_col).count().orderBy(F.col("count").desc()).limit(20000).select(item_col)
        neighbors_df = compute_item_cosine_neighbors(spark, best_model, item_col, limit_items=top_items_limit, top_k=10)
        item_nb_path = get_path("results", "", "item_neighbors_food_com.parquet")
        item_nb_local = PROJECT_ROOT / "data" / "results" / "item_neighbors_food_com.parquet"
        neighbors_df.write.mode("overwrite").parquet(item_nb_path)
        neighbors_df.write.mode("overwrite").parquet(str(item_nb_local))
    else:
        # Toàn bộ 4.000 món của ViFoodRec
        neighbors_df = compute_item_cosine_neighbors(spark, best_model, item_col, limit_items=None, top_k=10)
        item_nb_path = get_path("results", "", "item_neighbors_food_vietnam.parquet")
        item_nb_local = PROJECT_ROOT / "data" / "results" / "item_neighbors_food_vietnam.parquet"
        neighbors_df.coalesce(1).write.mode("overwrite").parquet(item_nb_path)
        neighbors_df.coalesce(1).write.mode("overwrite").parquet(str(item_nb_local))

    print(f"-> Đã xuất tệp item_neighbors thành công!")

    return als_result, rating_metrics["rmse_per_rating"]


def main():
    print("=" * 70)
    print("CHƯƠNG TRÌNH HUẤN LUYỆN, TINH CHỈNH VÀ ĐÁNH GIÁ MÔ HÌNH ALS (P7)")
    print(f"Chế độ lưu trữ: {get_storage_mode()}")
    print("=" * 70)

    spark = get_spark_session(app_name="ALSTrainingPipeline", shuffle_partitions=8)

    als_results = []
    rmse_breakdowns = []

    # =========================================================================
    # 1. HUẤN LUYỆN VÀ TINH CHỈNH VIFOODREC
    # =========================================================================
    # Lưới tham số cho ViFoodRec (101 user, 4000 món, 119k train)
    vf_param_grid = [
        {"rank": r, "regParam": reg, "maxIter": mi}
        for r in [10, 20, 50]
        for reg in [0.01, 0.05, 0.1, 0.5]
        for mi in [10, 15]
    ]

    vf_als_res, vf_breakdown = run_als_pipeline_for_dataset(
        spark=spark,
        dataset_name="food_vietnam",
        item_col="food_id",
        param_grid=vf_param_grid,
        is_food_com=False
    )
    als_results.append(vf_als_res)
    for r_val, r_rmse in vf_breakdown.items():
        rmse_breakdowns.append({
            "dataset": "food_vietnam",
            "model": "ALS Matrix Factorization",
            "rating_level": r_val,
            "rmse": round(r_rmse, 4)
        })

    # =========================================================================
    # 2. HUẤN LUYỆN VÀ TINH CHỈNH FOOD.COM
    # =========================================================================
    # Lưới tham số đại diện cho Food.com (565k train, 30k users, 78k món)
    # Rút gọn hợp lý để đảm bảo hoàn thành nhanh chóng trên cụm 4 cores
    fc_param_grid = [
        {"rank": 10, "regParam": 0.01, "maxIter": 10},
        {"rank": 10, "regParam": 0.05, "maxIter": 10},
        {"rank": 10, "regParam": 0.1,  "maxIter": 10},
        {"rank": 10, "regParam": 0.2,  "maxIter": 10},
        {"rank": 20, "regParam": 0.05, "maxIter": 10},
        {"rank": 20, "regParam": 0.1,  "maxIter": 10},
        {"rank": 20, "regParam": 0.05, "maxIter": 15},
        {"rank": 50, "regParam": 0.1,  "maxIter": 10}
    ]

    fc_als_res, fc_breakdown = run_als_pipeline_for_dataset(
        spark=spark,
        dataset_name="food_com",
        item_col="recipe_id",
        param_grid=fc_param_grid,
        is_food_com=True
    )
    als_results.append(fc_als_res)
    for r_val, r_rmse in fc_breakdown.items():
        rmse_breakdowns.append({
            "dataset": "food_com",
            "model": "ALS Matrix Factorization",
            "rating_level": r_val,
            "rmse": round(r_rmse, 4)
        })

    # =========================================================================
    # 3. TẠO BẢNG SO SÁNH TỔNG HỢP MODEL_COMPARISON.CSV
    # =========================================================================
    # Đọc kết quả baseline từ P6
    baseline_csv_path = PROJECT_ROOT / "data" / "results" / "baseline_metrics.csv"
    if baseline_csv_path.exists():
        base_df = pd.read_csv(baseline_csv_path)
    else:
        base_df = pd.DataFrame()

    als_df = pd.DataFrame(als_results)
    # Lấy các cột chung
    common_cols = ["dataset", "model", "RMSE", "MAE", "Precision@10", "Recall@10", "coverage"]
    als_common = als_df[common_cols]
    
    comparison_df = pd.concat([base_df, als_common], ignore_index=True)

    out_comp_data = PROJECT_ROOT / "data" / "results" / "model_comparison.csv"
    out_comp_res = PROJECT_ROOT / "results" / "model_comparison.csv"
    out_comp_evid = PROJECT_ROOT / "reports" / "evidence" / "model_comparison.csv"

    comparison_df.to_csv(out_comp_data, index=False)
    comparison_df.to_csv(out_comp_res, index=False)
    comparison_df.to_csv(out_comp_evid, index=False)

    # Lưu phân rã breakdown bổ sung
    breakdown_df = pd.DataFrame(rmse_breakdowns)
    out_bk_data = PROJECT_ROOT / "data" / "results" / "als_rmse_breakdown.csv"
    out_bk_res = PROJECT_ROOT / "results" / "als_rmse_breakdown.csv"
    breakdown_df.to_csv(out_bk_data, index=False)
    breakdown_df.to_csv(out_bk_res, index=False)

    print("\n" + "=" * 70)
    print("BẢNG SO SÁNH TỔNG HỢP BASELINE VÀ ALS (MODEL COMPARISON)")
    print("=" * 70)
    print(comparison_df.to_string(index=False))

    spark.stop()
    print("\n[THÀNH CÔNG] Hoàn tất toàn bộ kịch bản Giai đoạn P7!")


if __name__ == "__main__":
    main()

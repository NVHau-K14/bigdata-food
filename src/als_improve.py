"""
src/als_improve.py
------------------
Stage S3b (tùy chọn): thử cải thiện mô hình gợi ý. Không xóa hay ghi đè kết quả cũ, chỉ thêm dòng mới
vào model_comparison.csv.

1. Food.com, ALS dự đoán điểm với lưới regParam mở rộng: giá trị tốt nhất cũ là 0,2 nằm ở biên lưới.
   Thêm regParam 0,3 và 0,5 cho mọi cặp (rank, maxIter) của lưới cũ; chọn bằng Validation RMSE
   trên toàn bộ lưới cũ và mới (dòng cũ lấy từ results/als_tuning_food_com.csv).
2. ALS ngầm định (implicitPrefs=True) cho cả Food.com và ViFoodRec: chỉ dùng các dòng train có
   rating >= 4,0 làm phản hồi tích cực (giá trị 1,0), tham số chọn bằng Precision@10 trên VALIDATION
   (món phù hợp trong validation là rating >= 4,0, loại các món đã có trong train), đo test một lần.
   Mô hình ngầm định không dự đoán điểm nên RMSE, MAE để trống.

Đánh giá xếp hạng dùng đúng src/evaluation.py (Precision@10 và Recall@10, loại món đã có trong train).
Kết quả: results/als_improve_s3b.csv (nhật ký tinh chỉnh), results/als_improve_s3b_best.json (tham số tốt nhất),
và các dòng mới trong results/model_comparison.csv (cùng bản sao ở data/results/ và reports/evidence/).
"""

import json
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
from pyspark.sql import functions as F
from pyspark.ml.recommendation import ALS
from pyspark.ml.evaluation import RegressionEvaluator

from src.config import get_spark_session, get_path
from src.evaluation import evaluate_rating_predictions, evaluate_ranking_top_k
from src.train_als import generate_als_recommendations

MODEL_EXPLICIT = "ALS Matrix Factorization (lưới mở rộng)"
MODEL_IMPLICIT = "ALS ngầm định (điểm >= 4)"
RELEVANT_THRESHOLD = 4.0

# Lưới cũ của Food.com (src/train_als.py) để biết các cặp (rank, maxIter) cần thêm regParam mới
OLD_FC_PAIRS = [(10, 10), (20, 10), (20, 15), (50, 10)]
NEW_REGS = [0.3, 0.5]

# Lưới ALS ngầm định (dùng chung cho hai bộ)
IMPLICIT_GRID = [
    {"rank": r, "regParam": reg, "alpha": a, "maxIter": 10}
    for r in [10, 20, 50]
    for reg in [0.01, 0.1]
    for a in [1.0, 10.0, 40.0]
]
# Số món ứng viên lấy từ mô hình trước khi loại món đã có trong train. ALS ngầm định hay gợi ý lại món đã xem,
# nên cần lấy nhiều hơn mức 50 của ALS dự đoán điểm. ViFoodRec: mỗi người đã xem hơn 1.400 trong 4.000 món
# nên lấy toàn bộ 4.000 món.
FETCH_K = {"food_com": 300, "food_vietnam": 4000}
ITEM_COL = {"food_com": "recipe_id", "food_vietnam": "food_id"}


def load_splits(spark, dataset):
    train = spark.read.parquet(get_path("splits", dataset, "train.parquet")).cache()
    val = spark.read.parquet(get_path("splits", dataset, "validation.parquet")).cache()
    test = spark.read.parquet(get_path("splits", dataset, "test.parquet")).cache()
    return train, val, test


def ranking_metrics(model, eval_df, train_df, item_col, fetch_k):
    """Precision@10 và Recall@10 của model trên eval_df (validation hoặc test)."""
    users = eval_df.filter(F.col("rating") >= RELEVANT_THRESHOLD).select("user_id").distinct()
    recs = generate_als_recommendations(model, users, train_df, item_col, k=10, fetch_k=fetch_k)
    return evaluate_ranking_top_k(eval_df, recs, train_df, k=10, relevant_threshold=RELEVANT_THRESHOLD,
                                  user_col="user_id", item_col=item_col)


def short_list_fraction(model, eval_df, train_df, item_col, fetch_k):
    """Tỷ lệ người dùng có ít hơn 10 món gợi ý sau khi loại món đã có trong train (kiểm tra fetch_k đủ lớn)."""
    users = eval_df.filter(F.col("rating") >= RELEVANT_THRESHOLD).select("user_id").distinct()
    recs = generate_als_recommendations(model, users, train_df, item_col, k=10, fetch_k=fetch_k)
    n = recs.count()
    short = recs.filter(F.size("top_items") < 10).count()
    return short / n if n else 0.0, n


def explicit_extended_grid_food_com(spark, rows, comparison_rows):
    print("\n" + "=" * 70)
    print("1. FOOD.COM: ALS DỰ ĐOÁN ĐIỂM, LƯỚI regParam MỞ RỘNG")
    print("=" * 70)
    ds, item_col = "food_com", ITEM_COL["food_com"]
    train, val, test = load_splits(spark, ds)
    evaluator = RegressionEvaluator(metricName="rmse", labelCol="rating", predictionCol="prediction")

    old = pd.read_csv(ROOT_DIR / "results" / "als_tuning_food_com.csv")
    candidates = [{"rank": int(r.rank), "regParam": float(r.regParam), "maxIter": int(r.maxIter),
                   "val_rmse": float(r.val_rmse), "source": "cu"} for r in old.itertuples()]

    best = min(candidates, key=lambda c: c["val_rmse"])
    print(f"-> Tốt nhất ở lưới cũ: {best}")
    new_best_model = None
    for rank, mi in OLD_FC_PAIRS:
        for reg in NEW_REGS:
            t0 = time.perf_counter()
            model = ALS(rank=rank, regParam=reg, maxIter=mi, userCol="user_id", itemCol=item_col,
                        ratingCol="rating", coldStartStrategy="drop", nonnegative=True, seed=42).fit(train)
            v = evaluator.evaluate(model.transform(val))
            cand = {"rank": rank, "regParam": reg, "maxIter": mi, "val_rmse": round(v, 4), "source": "moi"}
            candidates.append(cand)
            print(f"   rank={rank:2d} reg={reg:.2f} maxIter={mi:2d} | Val RMSE: {v:.4f} ({time.perf_counter() - t0:.1f}s)")
            rows.append({"dataset": ds, "variant": "explicit_luoi_mo_rong", "rank": rank, "regParam": reg,
                         "alpha": None, "maxIter": mi, "val_rmse": round(v, 4), "val_p10": None, "val_r10": None})
            if v < best["val_rmse"]:
                best, new_best_model = cand, model

    print(f"-> Tốt nhất sau mở rộng lưới (theo Validation RMSE): {best}")
    improved = best["source"] == "moi"
    if not improved:
        print("-> Giá trị tốt nhất vẫn là của lưới cũ; huấn luyện lại cùng tham số để đo test với cùng quy trình.")
        new_best_model = ALS(rank=best["rank"], regParam=best["regParam"], maxIter=best["maxIter"], userCol="user_id",
                             itemCol=item_col, ratingCol="rating", coldStartStrategy="drop", nonnegative=True,
                             seed=42).fit(train)

    n_test = test.count()
    rating = evaluate_rating_predictions(new_best_model.transform(test), total_test_count=n_test)
    rank_res = ranking_metrics(new_best_model, test, train, item_col, fetch_k=50)  # fetch_k = 50 như ALS cũ
    print(f"-> TEST: RMSE={rating['rmse']:.4f} MAE={rating['mae']:.4f} "
          f"P@10={rank_res['precision@10']:.5f} R@10={rank_res['recall@10']:.5f}")
    comparison_rows.append({
        "dataset": ds, "model": MODEL_EXPLICIT, "RMSE": round(rating["rmse"], 4), "MAE": round(rating["mae"], 4),
        "Precision@10": round(rank_res["precision@10"], 5), "Recall@10": round(rank_res["recall@10"], 5),
        "coverage": round(rating["coverage"], 2)})
    return {"dataset": ds, "variant": "explicit_luoi_mo_rong", "best": best, "improved_over_old_grid": improved}


def implicit_als(spark, dataset, rows, comparison_rows):
    print("\n" + "=" * 70)
    print(f"2. {dataset.upper()}: ALS NGẦM ĐỊNH (điểm >= {RELEVANT_THRESHOLD} là phản hồi tích cực)")
    print("=" * 70)
    item_col, fetch_k = ITEM_COL[dataset], FETCH_K[dataset]
    train, val, test = load_splits(spark, dataset)

    pos_train = train.filter(F.col("rating") >= RELEVANT_THRESHOLD).withColumn("rating", F.lit(1.0)).cache()
    print(f"-> Train {train.count():,} dòng, trong đó phản hồi tích cực {pos_train.count():,} dòng; fetch_k = {fetch_k}")

    best, best_model = None, None
    for i, p in enumerate(IMPLICIT_GRID, 1):
        t0 = time.perf_counter()
        model = ALS(rank=p["rank"], regParam=p["regParam"], alpha=p["alpha"], maxIter=p["maxIter"], implicitPrefs=True,
                    userCol="user_id", itemCol=item_col, ratingCol="rating", coldStartStrategy="drop",
                    seed=42).fit(pos_train)
        m = ranking_metrics(model, val, train, item_col, fetch_k)
        print(f"[{i:2d}/{len(IMPLICIT_GRID)}] rank={p['rank']:2d} reg={p['regParam']:.2f} alpha={p['alpha']:5.1f} | "
              f"Val P@10={m['precision@10']:.5f} R@10={m['recall@10']:.5f} ({time.perf_counter() - t0:.1f}s)")
        rows.append({"dataset": dataset, "variant": "implicit", "rank": p["rank"], "regParam": p["regParam"],
                     "alpha": p["alpha"], "maxIter": p["maxIter"], "val_rmse": None,
                     "val_p10": round(m["precision@10"], 5), "val_r10": round(m["recall@10"], 5)})
        if best is None or m["precision@10"] > best["val_p10"]:
            best = dict(p, val_p10=m["precision@10"], val_r10=m["recall@10"])
            best_model = model

    print(f"-> Tốt nhất theo Validation Precision@10: {best}")
    test_m = ranking_metrics(best_model, test, train, item_col, fetch_k)
    short_frac, n_users = short_list_fraction(best_model, test, train, item_col, fetch_k)
    print(f"-> TEST: P@10={test_m['precision@10']:.5f} R@10={test_m['recall@10']:.5f} "
          f"(người dùng đánh giá: {test_m['evaluated_users']:,})")
    print(f"-> Kiểm tra fetch_k: {short_frac * 100:.2f}% trong {n_users:,} người dùng có dưới 10 món sau khi loại món đã xem")
    comparison_rows.append({
        "dataset": dataset, "model": MODEL_IMPLICIT, "RMSE": None, "MAE": None,
        "Precision@10": round(test_m["precision@10"], 5), "Recall@10": round(test_m["recall@10"], 5), "coverage": None})
    return {"dataset": dataset, "variant": "implicit", "best": best, "test_p10": test_m["precision@10"],
            "test_r10": test_m["recall@10"], "short_list_fraction": short_frac}


def main():
    spark = get_spark_session("ALSImproveS3b", shuffle_partitions=8)
    rows, comparison_rows, best_info = [], [], []

    best_info.append(explicit_extended_grid_food_com(spark, rows, comparison_rows))
    for ds in ["food_vietnam", "food_com"]:
        best_info.append(implicit_als(spark, ds, rows, comparison_rows))

    # Nhật ký tinh chỉnh và tham số tốt nhất
    res_dir = ROOT_DIR / "results"
    pd.DataFrame(rows).to_csv(res_dir / "als_improve_s3b.csv", index=False)
    (res_dir / "als_improve_s3b_best.json").write_text(json.dumps(best_info, ensure_ascii=False, indent=2), encoding="utf-8")

    # Thêm dòng mới vào model_comparison.csv, không xóa dòng cũ (chỉ thay dòng cùng tên mô hình nếu chạy lại)
    new_rows = pd.DataFrame(comparison_rows)
    comp = pd.read_csv(res_dir / "model_comparison.csv")
    comp = comp[~comp["model"].isin([MODEL_EXPLICIT, MODEL_IMPLICIT])]
    comp = pd.concat([comp, new_rows], ignore_index=True)
    for d in (res_dir, ROOT_DIR / "data" / "results", ROOT_DIR / "reports" / "evidence"):
        comp.to_csv(d / "model_comparison.csv", index=False)
        pd.DataFrame(rows).to_csv(d / "als_improve_s3b.csv", index=False)

    print("\n" + "=" * 70)
    print("BẢNG SO SÁNH MÔ HÌNH SAU S3b")
    print("=" * 70)
    print(comp.to_string(index=False))
    spark.stop()


if __name__ == "__main__":
    main()

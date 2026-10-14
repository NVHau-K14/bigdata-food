"""
src/vifoodrec_sensitivity.py
----------------------------
Đối chiếu độ nhạy của kết quả ViFoodRec với quy tắc lọc thang điểm (S3, bước 5).
KHÔNG dùng làm kết quả chính; chỉ để biết quyết định giữ 0,0 và 0,5 ảnh hưởng thế nào.

Ba biến thể, đều dựa trên ratings_clean.parquet của S2 (đã khử trùng cặp và kiểm tra khóa ngoại):
- chinh: giữ cả 11 mức 0,0 đến 5,0 (kết quả chính).
- A_bo_0_0: bỏ riêng điểm 0,0.
- B_giu_1_den_5: quy tắc cũ chỉ giữ điểm từ 1,0 đến 5,0 (bỏ 0,0 và 0,5).
Mỗi biến thể: K-core lặp K=3, chia 80/10/10 seed 42 và lọc cold-start bằng đúng hàm của split_data.py,
rồi đánh giá Global Mean, Smoothed Item Mean (m = SMOOTHING_M) và ALS với tham số đã chọn ở biến thể chính
(results/als_best_params_food_vietnam.json), không tinh chỉnh lại.

Kết quả: results/vifoodrec_sensitivity.csv (và bản sao ở data/results/, reports/evidence/).
Dòng "chinh" được đối chiếu với results/model_comparison.csv để chắc cùng một cách chia và huấn luyện.
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

from src.config import get_spark_session, get_path, K_CORE_DEFAULT, SMOOTHING_M
from src.evaluation import evaluate_rating_predictions
from src.split_data import split_with_cold_start_filter

VARIANTS = [
    ("chinh", "Giữ cả 11 mức 0,0 đến 5,0 (kết quả chính)", None),
    ("A_bo_0_0", "Bỏ riêng điểm 0,0", "rating > 0.0"),
    ("B_giu_1_den_5", "Quy tắc cũ: chỉ giữ điểm 1,0 đến 5,0", "rating >= 1.0"),
]


def k_core(df, k):
    """K-core lặp trên user_id và food_id đến khi hội tụ (cùng quy tắc làm sạch ở S2)."""
    rounds = 0
    while True:
        rounds += 1
        before = df.count()
        good_users = df.groupBy("user_id").count().filter(F.col("count") >= k).select("user_id")
        df = df.join(good_users, on="user_id", how="inner")
        good_items = df.groupBy("food_id").count().filter(F.col("count") >= k).select("food_id")
        df = df.join(good_items, on="food_id", how="inner").cache()
        after = df.count()
        if after == before:
            return df, rounds


def evaluate_models(train_df, test_df, params):
    """Trả về danh sách dict RMSE, MAE, coverage của 3 mô hình trên test."""
    n_test = test_df.count()
    mu = float(train_df.select(F.avg("rating")).collect()[0][0])

    item_stats = train_df.groupBy("food_id").agg(
        F.count("rating").alias("n"), F.sum("rating").alias("s")
    ).withColumn("smoothed", (F.col("s") + F.lit(SMOOTHING_M * mu)) / (F.col("n") + F.lit(SMOOTHING_M)))

    out = []
    r = evaluate_rating_predictions(test_df.withColumn("prediction", F.lit(mu)), total_test_count=n_test)
    out.append(("Global Mean", r))

    b2 = test_df.join(item_stats.select("food_id", "smoothed"), on="food_id", how="left") \
                .withColumn("prediction", F.coalesce(F.col("smoothed"), F.lit(mu)))
    out.append(("Smoothed Item Mean", evaluate_rating_predictions(b2, total_test_count=n_test)))

    als = ALS(rank=params["rank"], regParam=params["regParam"], maxIter=params["maxIter"],
              userCol="user_id", itemCol="food_id", ratingCol="rating",
              coldStartStrategy="drop", nonnegative=True, seed=params["seed"])
    model = als.fit(train_df)
    out.append(("ALS Matrix Factorization", evaluate_rating_predictions(model.transform(test_df), total_test_count=n_test)))
    return out


def main():
    spark = get_spark_session("ViFoodRecSensitivity", shuffle_partitions=8)
    params = json.loads((ROOT_DIR / "results" / "als_best_params_food_vietnam.json").read_text(encoding="utf-8"))
    print(f"Tham số ALS dùng cho cả 3 biến thể (chọn ở biến thể chính): {params}")

    base = spark.read.parquet(get_path("clean", "food_vietnam", "ratings_clean.parquet"))
    rows = []
    for name, desc, cond in VARIANTS:
        t0 = time.time()
        print("\n" + "=" * 70)
        print(f"BIẾN THỂ {name}: {desc}")
        df = base if cond is None else base.filter(cond)
        df = df.cache()
        n_before = df.count()
        df, rounds = k_core(df, K_CORE_DEFAULT)
        n_rows = df.count()
        levels = sorted(r[0] for r in df.select("rating").distinct().collect())
        print(f"-> Sau lọc: {n_before:,} dòng; sau K-core (K={K_CORE_DEFAULT}, {rounds} vòng): {n_rows:,} dòng; "
              f"{len(levels)} mức điểm: {levels}")

        train_df, val_df, test_df, st = split_with_cold_start_filter(df, "food_id", seed=42)
        print(f"-> Train={st['train_count']:,} | Val(sau lọc)={st['val_clean_count']:,} | Test(sau lọc)={st['test_clean_count']:,}")

        for model_name, res in evaluate_models(train_df, test_df, params):
            print(f"   {model_name:26s} RMSE={res['rmse']:.4f}  MAE={res['mae']:.4f}  coverage={res['coverage']:.2f}%")
            rows.append({
                "variant": name, "description": desc, "n_rows_clean": n_rows, "n_levels": len(levels),
                "n_train": st["train_count"], "n_test": st["test_clean_count"],
                "model": model_name, "RMSE": round(res["rmse"], 4), "MAE": round(res["mae"], 4),
                "coverage": round(res["coverage"], 2),
            })
        print(f"-> Xong biến thể {name} trong {time.time() - t0:.1f}s")
        df.unpersist()

    out = pd.DataFrame(rows)
    for d in (ROOT_DIR / "results", ROOT_DIR / "data" / "results", ROOT_DIR / "reports" / "evidence"):
        d.mkdir(parents=True, exist_ok=True)
        out.to_csv(d / "vifoodrec_sensitivity.csv", index=False)

    print("\n" + "=" * 70)
    print("BẢNG NHẠY CẢM")
    print(out.drop(columns=["description"]).to_string(index=False))

    # Đối chiếu biến thể chính với kết quả chính trong model_comparison.csv
    comp = pd.read_csv(ROOT_DIR / "results" / "model_comparison.csv")
    comp = comp[comp["dataset"] == "food_vietnam"].set_index("model")
    print("\nĐối chiếu biến thể chính với model_comparison.csv (chênh lệch phải bằng 0):")
    for _, r in out[out["variant"] == "chinh"].iterrows():
        d_rmse = round(r["RMSE"] - comp.loc[r["model"], "RMSE"], 4)
        d_mae = round(r["MAE"] - comp.loc[r["model"], "MAE"], 4)
        print(f"   {r['model']:26s} chênh RMSE = {d_rmse}, chênh MAE = {d_mae}")

    spark.stop()


if __name__ == "__main__":
    main()

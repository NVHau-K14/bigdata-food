"""
src/export_cluster_top_items.py
-------------------------------
Xuất "món được chấm cao nhiều nhất trong từng cụm người dùng" cho dashboard web (S4, lỗi A1).
Dữ liệu này trước đây chỉ được in ra màn hình ở kmeans_behavior.py, không được lưu, nên web phải
lấy tạm danh sách của cụm MÓN ViFoodRec theo id cụm và hiển thị sai món cho người dùng Food.com.

Cách tính (cùng định nghĩa với kmeans_behavior.py): chỉ dùng tập TRAIN, chỉ lấy các dòng có điểm
>= 4,0, ghép với nhãn cụm người dùng, đếm số lượt theo (cụm, món), giữ 10 món nhiều lượt nhất.
Chỉ ĐỌC dữ liệu; không đổi pipeline hay kết quả đã có.

Kết quả: app/data/cluster_top_items.csv (cột dataset, cluster, rank, item_id, name, count, calories,
time, dish_type) và bản sao results/cluster_top_items.csv.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
from pyspark.sql import functions as F, Window

from src.config import get_spark_session, get_path

TOP_N = 10
RELEVANT_THRESHOLD = 4.0


def top_items(train, clusters, catalog, item_col, dataset):
    """Top TOP_N món có điểm >= ngưỡng theo từng cụm; catalog đã đổi tên cột thành name, calories, time, dish_type."""
    pos = train.filter(F.col("rating") >= RELEVANT_THRESHOLD) \
               .join(clusters.select("user_id", "cluster"), on="user_id", how="inner") \
               .groupBy("cluster", item_col).count()
    win = Window.partitionBy("cluster").orderBy(F.col("count").desc(), F.col(item_col).asc())
    ranked = pos.withColumn("rank", F.row_number().over(win)).filter(F.col("rank") <= TOP_N)
    out = ranked.join(catalog, on=item_col, how="left") \
                .withColumnRenamed(item_col, "item_id") \
                .withColumn("dataset", F.lit(dataset)) \
                .select("dataset", "cluster", "rank", "item_id", "name", "count", "calories", "time", "dish_type") \
                .orderBy("cluster", "rank")
    return out.toPandas()


def main():
    spark = get_spark_session("ExportClusterTopItems", shuffle_partitions=8)

    # Food.com
    fc_train = spark.read.parquet(get_path("splits", "food_com", "train.parquet"))
    fc_clusters = spark.read.parquet(get_path("results", "", "user_clusters_food_com.parquet"))
    fc_recipes = spark.read.parquet(get_path("clean", "food_com", "recipes_clean.parquet")).select(
        "recipe_id", F.col("name"), F.col("calories"), F.col("minutes_clean").alias("time"),
        F.lit(None).cast("string").alias("dish_type"))
    fc = top_items(fc_train, fc_clusters, fc_recipes, "recipe_id", "food_com")

    # ViFoodRec (người dùng)
    vn_train = spark.read.parquet(get_path("splits", "food_vietnam", "train.parquet"))
    vn_clusters = spark.read.parquet(get_path("results", "", "user_clusters_food_vietnam.parquet"))
    vn_foods = spark.read.parquet(get_path("clean", "food_vietnam", "foods_clean.parquet")).select(
        "food_id", F.col("dish_name").alias("name"), F.col("calories"),
        F.col("cooking_time_min").alias("time"), F.col("dish_type"))
    vn = top_items(vn_train, vn_clusters, vn_foods, "food_id", "vifoodrec_users")

    out = pd.concat([fc, vn], ignore_index=True)
    for d in (ROOT_DIR / "app" / "data", ROOT_DIR / "results"):
        d.mkdir(parents=True, exist_ok=True)
        out.to_csv(d / "cluster_top_items.csv", index=False, encoding="utf-8-sig")

    print(out.to_string(index=False))
    print(f"\nTổng số dòng: {len(out)}; số cụm Food.com: {fc['cluster'].nunique()}, ViFoodRec: {vn['cluster'].nunique()}")
    print("Dòng thiếu tên món (kỳ vọng 0):", int(out["name"].isna().sum()))
    spark.stop()


if __name__ == "__main__":
    main()

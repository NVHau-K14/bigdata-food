"""
src/eda_analysis.py
-------------------
Phân tích khám phá dữ liệu (EDA) toàn diện bằng Apache Spark trên dữ liệu sạch:
- Thực hiện toàn bộ tính toán tổng hợp (Aggregation) phân tán trên cụm Spark.
- Lưu các bảng tổng hợp vào data/results/eda/ (dạng CSV) phục vụ Dashboard và kiểm chứng.
- Vẽ 13 biểu đồ trực quan hóa chuyên nghiệp bằng matplotlib lưu vào reports/figures/.
- Xuất số liệu thống kê chuẩn xác làm bằng chứng cho reports/evidence/eda_insights.md.
"""

import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from pyspark.sql.functions import (
    col, count as spark_count, avg, min as spark_min, max as spark_max,
    year, month, date_format, when, explode, split, trim, lower, lit, round as spark_round
)
from src.config import get_spark_session, get_path


def run_eda():
    start_time = time.time()
    spark = get_spark_session("EDA_Analysis_P5")
    
    print("=" * 80)
    print("   BẮT ĐẦU PHÂN TÍCH KHÁM PHÁ DỮ LIỆU (EDA) TRÊN CỤM SPARK (P5)")
    print("=" * 80)
    
    # Tạo các thư mục lưu trữ kết quả
    eda_results_dir = ROOT_DIR / "data" / "results" / "eda"
    eda_results_dir.mkdir(parents=True, exist_ok=True)
    
    figures_dir = ROOT_DIR / "reports" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    # ---------------------------------------------------------
    # 1. NẠP DỮ LIỆU SẠCH TỪ HDFS
    # ---------------------------------------------------------
    print("\n[1/13] Nạp dữ liệu Parquet sạch từ HDFS...")
    df_fc_inter = spark.read.parquet(get_path("clean", "food_com", "interactions_clean.parquet"))
    df_fc_rec = spark.read.parquet(get_path("clean", "food_com", "recipes_clean.parquet"))
    df_vn_rat = spark.read.parquet(get_path("clean", "food_vietnam", "ratings_clean.parquet"))
    df_vn_food = spark.read.parquet(get_path("clean", "food_vietnam", "foods_clean.parquet"))
    
    # Thiết lập style đồ họa
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["axes.edgecolor"] = "#cccccc"
    plt.rcParams["axes.linewidth"] = 0.8
    
    # ---------------------------------------------------------
    # EDA 1: PHÂN PHỐI ĐIỂM ĐÁNH GIÁ (RATING DISTRIBUTION)
    # ---------------------------------------------------------
    print("\n[2/13] EDA 1: Phân phối điểm đánh giá (Food.com vs ViFoodRec)...")
    fc_dist_df = df_fc_inter.groupBy("rating").agg(spark_count("user_id").alias("count")) \
                            .orderBy("rating").toPandas()
    fc_total = fc_dist_df["count"].sum()
    fc_dist_df["pct"] = (fc_dist_df["count"] / fc_total) * 100
    fc_dist_df.to_csv(eda_results_dir / "eda_01_food_com_rating_dist.csv", index=False)
    
    vn_dist_df = df_vn_rat.groupBy("rating").agg(spark_count("user_id").alias("count")) \
                          .orderBy("rating").toPandas()
    vn_total = vn_dist_df["count"].sum()
    vn_dist_df["pct"] = (vn_dist_df["count"] / vn_total) * 100
    vn_dist_df.to_csv(eda_results_dir / "eda_01_vifoodrec_rating_dist.csv", index=False)
    
    # Vẽ Biểu đồ 1
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    bars1 = ax1.bar(fc_dist_df["rating"].astype(str), fc_dist_df["count"], color="#e67e22", alpha=0.85)
    ax1.set_title(f"Phân phối điểm đánh giá: Food.com\n({fc_total:,} tương tác, điểm 1 đến 5)", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Mức điểm đánh giá (sao)", fontsize=10)
    ax1.set_ylabel("Số lượng đánh giá", fontsize=10)
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{int(y):,}"))
    for b, pct in zip(bars1, fc_dist_df["pct"]):
        h = b.get_height()
        ax1.annotate(f"{h:,}\n({pct:.1f}%)", xy=(b.get_x() + b.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
                     
    bars2 = ax2.bar(vn_dist_df["rating"].astype(str), vn_dist_df["count"], color="#27ae60", alpha=0.85)
    ax2.set_title(f"Phân phối điểm đánh giá: ViFoodRec\n({vn_total:,} tương tác, 11 mức điểm 0,0 đến 5,0)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Mức điểm đánh giá (sao)", fontsize=10)
    ax2.set_ylabel("Số lượng đánh giá", fontsize=10)
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{int(y):,}"))
    for b, pct in zip(bars2, vn_dist_df["pct"]):
        h = b.get_height()
        ax2.annotate(f"{h:,}\n({pct:.1f}%)", xy=(b.get_x() + b.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
                     
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_01_rating_distribution.png", dpi=300)
    plt.close()
    
    # ---------------------------------------------------------
    # EDA 2: PHÂN PHỐI SỐ LƯỢNG TƯƠNG TÁC (LONG TAIL / LOG SCALE)
    # ---------------------------------------------------------
    print("\n[3/13] EDA 2: Phân phối số tương tác theo User & Item (Hiện tượng đuôi dài)...")
    fc_user_activity = df_fc_inter.groupBy("user_id").agg(spark_count("recipe_id").alias("n_inter")) \
                                  .groupBy("n_inter").agg(spark_count("user_id").alias("user_count")) \
                                  .orderBy("n_inter").toPandas()
    fc_user_activity.to_csv(eda_results_dir / "eda_02_food_com_user_activity.csv", index=False)
    
    fc_item_activity = df_fc_inter.groupBy("recipe_id").agg(spark_count("user_id").alias("n_inter")) \
                                  .groupBy("n_inter").agg(spark_count("recipe_id").alias("item_count")) \
                                  .orderBy("n_inter").toPandas()
    fc_item_activity.to_csv(eda_results_dir / "eda_02_food_com_item_activity.csv", index=False)
    
    # Vẽ Biểu đồ 2
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    ax1.plot(fc_user_activity["n_inter"], fc_user_activity["user_count"], color="#8e44ad", lw=2, marker="o", markersize=3)
    ax1.set_xscale("log")
    ax1.set_yscale("log")
    ax1.set_title("Quy luật Đuôi dài (Power-Law): Tương tác theo User (Food.com)", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Số tương tác của mỗi User (Thang Log)", fontsize=10)
    ax1.set_ylabel("Số lượng User (Thang Log)", fontsize=10)
    ax1.annotate("Phần lớn user chỉ có 3 - 10 tương tác\n(Trung vị = 6)", xy=(6, 2500), xytext=(20, 3000),
                 arrowprops=dict(facecolor="#c0392b", shrink=0.05, width=1.5, headwidth=6), fontsize=9, fontweight="bold")
                 
    ax2.plot(fc_item_activity["n_inter"], fc_item_activity["item_count"], color="#2980b9", lw=2, marker="s", markersize=3)
    ax2.set_xscale("log")
    ax2.set_yscale("log")
    ax2.set_title("Quy luật Đuôi dài (Power-Law): Tương tác theo Recipe (Food.com)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Số tương tác của mỗi Recipe (Thang Log)", fontsize=10)
    ax2.set_ylabel("Số lượng Recipe (Thang Log)", fontsize=10)
    ax2.annotate("Đa số công thức chỉ có 3 - 5 đánh giá\n(Trung vị = 5)", xy=(5, 12000), xytext=(15, 15000),
                 arrowprops=dict(facecolor="#c0392b", shrink=0.05, width=1.5, headwidth=6), fontsize=9, fontweight="bold")
                 
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_02_interaction_distribution_log.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # EDA 3: FOOD.COM TOP 10 PHỔ BIẾN VS TOP 10 ĐIỂM CAO NHẤT (>=20 RATING)
    # ---------------------------------------------------------
    print("\n[4/13] EDA 3: Top món phổ biến vs Top món điểm cao Food.com...")
    recipe_stats = df_fc_inter.groupBy("recipe_id").agg(
        spark_count("user_id").alias("num_ratings"),
        avg("rating").alias("avg_rating")
    )
    recipe_meta = df_fc_rec.select("recipe_id", "name")
    recipe_joined = recipe_stats.join(recipe_meta, on="recipe_id", how="inner")
    
    top_popular_fc = recipe_joined.orderBy(col("num_ratings").desc()).limit(10).toPandas()
    top_popular_fc.to_csv(eda_results_dir / "eda_03_food_com_top_popular.csv", index=False)
    
    top_highest_fc = recipe_joined.filter(col("num_ratings") >= 20) \
                                  .orderBy(col("avg_rating").desc(), col("num_ratings").desc()) \
                                  .limit(10).toPandas()
    top_highest_fc.to_csv(eda_results_dir / "eda_03_food_com_top_highest.csv", index=False)
    
    # Vẽ Biểu đồ 3
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    ax1.barh(top_popular_fc["name"][::-1], top_popular_fc["num_ratings"][::-1], color="#3498db", alpha=0.85)
    ax1.set_title("Top 10 Món Ăn Phổ Biến Nhất (Food.com)\n(Xếp theo số lượt đánh giá)", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Số lượt đánh giá", fontsize=10)
    for idx, (val, avg_r) in enumerate(zip(top_popular_fc["num_ratings"][::-1], top_popular_fc["avg_rating"][::-1])):
        ax1.annotate(f"{val:,} lượt (TB: {avg_r:.2f} sao)", xy=(val, idx), xytext=(5, -2), textcoords="offset points", fontsize=8, fontweight="bold")
        
    ax2.barh(top_highest_fc["name"][::-1], top_highest_fc["avg_rating"][::-1], color="#f39c12", alpha=0.85)
    ax2.set_xlim(4.8, 5.05)
    ax2.set_title("Top 10 Món Ăn Điểm Cao Nhất (Food.com)\n(Chỉ xét món có ≥ 20 lượt đánh giá)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Điểm đánh giá trung bình (sao)", fontsize=10)
    for idx, (val, n_cnt) in enumerate(zip(top_highest_fc["avg_rating"][::-1], top_highest_fc["num_ratings"][::-1])):
        ax2.annotate(f"{val:.2f} sao ({n_cnt} lượt)", xy=(val, idx), xytext=(5, -2), textcoords="offset points", fontsize=8, fontweight="bold")
        
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_03_top_recipes_food_com.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # EDA 4: VIFOODREC TOP 10 PHỔ BIẾN VS TOP 10 ĐIỂM CAO NHẤT
    # ---------------------------------------------------------
    print("\n[5/13] EDA 4: Top món phổ biến vs Top món điểm cao ViFoodRec...")
    food_stats = df_vn_rat.groupBy("food_id").agg(
        spark_count("user_id").alias("num_ratings"),
        avg("rating").alias("avg_rating")
    )
    food_meta = df_vn_food.select("food_id", "dish_name")
    food_joined = food_stats.join(food_meta, on="food_id", how="inner")
    
    top_popular_vn = food_joined.orderBy(col("num_ratings").desc()).limit(10).toPandas()
    top_popular_vn.to_csv(eda_results_dir / "eda_04_vifoodrec_top_popular.csv", index=False)
    
    top_highest_vn = food_joined.orderBy(col("avg_rating").desc(), col("num_ratings").desc()).limit(10).toPandas()
    top_highest_vn.to_csv(eda_results_dir / "eda_04_vifoodrec_top_highest.csv", index=False)
    
    # Vẽ Biểu đồ 4
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    ax1.barh(top_popular_vn["dish_name"][::-1], top_popular_vn["num_ratings"][::-1], color="#16a085", alpha=0.85)
    ax1.set_title("Top 10 Món Ăn Được Đánh Giá Nhiều Nhất (ViFoodRec)", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Số lượt đánh giá", fontsize=10)
    for idx, (val, avg_r) in enumerate(zip(top_popular_vn["num_ratings"][::-1], top_popular_vn["avg_rating"][::-1])):
        ax1.annotate(f"{val} lượt (TB: {avg_r:.2f} sao)", xy=(val, idx), xytext=(5, -2), textcoords="offset points", fontsize=8, fontweight="bold")
        
    ax2.barh(top_highest_vn["dish_name"][::-1], top_highest_vn["avg_rating"][::-1], color="#d35400", alpha=0.85)
    ax2.set_xlim(0, 5.0)
    ax2.set_title("Top 10 Món Ăn Điểm Cao Nhất (ViFoodRec)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Điểm đánh giá trung bình (sao)", fontsize=10)
    for idx, (val, n_cnt) in enumerate(zip(top_highest_vn["avg_rating"][::-1], top_highest_vn["num_ratings"][::-1])):
        ax2.annotate(f"{val:.2f} sao ({n_cnt} lượt)", xy=(val, idx), xytext=(5, -2), textcoords="offset points", fontsize=8, fontweight="bold")
        
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_04_top_foods_vifoodrec.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # EDA 5: FOOD.COM XU HƯỚNG THEO THỜI GIAN (YEARLY TREND)
    # ---------------------------------------------------------
    print("\n[6/13] EDA 5: Xu hướng tương tác theo năm của Food.com...")
    df_fc_time = df_fc_inter.withColumn("year", year(col("date"))) \
                            .groupBy("year").agg(
                                spark_count("user_id").alias("num_ratings"),
                                avg("rating").alias("avg_rating")
                            ).filter((col("year") >= 2000) & (col("year") <= 2018)) \
                            .orderBy("year").toPandas()
    df_fc_time.to_csv(eda_results_dir / "eda_05_food_com_yearly_trend.csv", index=False)
    
    fig, ax1 = plt.subplots(figsize=(12, 5))
    color = "#2980b9"
    ax1.set_xlabel("Năm đánh giá", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Số lượng đánh giá hàng năm", color=color, fontsize=11, fontweight="bold")
    bars = ax1.bar(df_fc_time["year"], df_fc_time["num_ratings"], color=color, alpha=0.7, width=0.6, label="Số lượng tương tác")
    ax1.tick_params(axis="y", labelcolor=color)
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{int(y):,}"))
    
    ax2 = ax1.twinx()
    color = "#c0392b"
    ax2.set_ylabel("Điểm đánh giá trung bình (sao)", color=color, fontsize=11, fontweight="bold")
    line = ax2.plot(df_fc_time["year"], df_fc_time["avg_rating"], color=color, lw=2.5, marker="o", label="Điểm trung bình")
    ax2.tick_params(axis="y", labelcolor=color)
    ax2.set_ylim(4.4, 4.9)
    
    plt.title("Xu hướng Số lượng Đánh giá và Điểm Trung bình theo Năm (Food.com 2000 - 2018)", fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_05_food_com_yearly_trend.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # EDA 6: FOOD.COM THEO THỨ TRONG TUẦN & THÁNG (SEASONALITY)
    # ---------------------------------------------------------
    print("\n[7/13] EDA 6: Tính mùa vụ (Thứ trong tuần và Tháng trong năm)...")
    dow_df = df_fc_inter.withColumn("dow", date_format(col("date"), "EEEE")) \
                        .groupBy("dow").agg(spark_count("user_id").alias("count")) \
                        .toPandas()
    dow_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    dow_vn = ["Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ nhật"]
    dow_df["order"] = dow_df["dow"].apply(lambda x: dow_order.index(x) if x in dow_order else 99)
    dow_df = dow_df.sort_values("order").reset_index(drop=True)
    dow_df["dow_vn"] = dow_vn
    dow_df.to_csv(eda_results_dir / "eda_06_food_com_day_of_week.csv", index=False)
    
    month_df = df_fc_inter.withColumn("m", month(col("date"))) \
                          .groupBy("m").agg(spark_count("user_id").alias("count")) \
                          .orderBy("m").toPandas()
    month_df.to_csv(eda_results_dir / "eda_06_food_com_monthly.csv", index=False)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    ax1.bar(dow_df["dow_vn"], dow_df["count"], color="#1abc9c", alpha=0.85)
    ax1.set_title("Số lượng Đánh giá theo Thứ trong Tuần (Food.com)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Số lượng đánh giá", fontsize=10)
    ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{int(y):,}"))
    for b in ax1.patches:
        h = b.get_height()
        ax1.annotate(f"{h:,}", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
        
    ax2.plot(month_df["m"].astype(str), month_df["count"], color="#e74c3c", marker="o", lw=2)
    ax2.set_title("Phân phối Tương tác theo Tháng trong Năm (Food.com)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Tháng", fontsize=10)
    ax2.set_ylabel("Số lượng đánh giá", fontsize=10)
    ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{int(y):,}"))
    ax2.annotate("Đỉnh vào Tháng 1\n(Sau kỳ nghỉ Tết Dương lịch)", xy=(1, month_df["count"].iloc[0]), xytext=(2, 68000),
                 arrowprops=dict(facecolor="#34495e", shrink=0.05, width=1.5, headwidth=6), fontsize=9, fontweight="bold")
                 
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_06_food_com_day_of_week_and_time.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # EDA 7: FOOD.COM THỜI GIAN NẤU, CALO VÀ ĐIỂM ĐÁNH GIÁ
    # ---------------------------------------------------------
    print("\n[8/13] EDA 7: Quan hệ Thời gian nấu, Calo và Điểm trung bình...")
    joined_fc = df_fc_inter.join(df_fc_rec.select("recipe_id", "minutes_clean", "calories"), on="recipe_id", how="inner")
    
    # Chia nhóm thời gian nấu
    time_grouped = joined_fc.filter(col("minutes_clean").isNotNull()) \
        .withColumn("time_group", when(col("minutes_clean") <= 15, "1. Nhanh (<=15p)")
                                 .when(col("minutes_clean") <= 30, "2. Vừa (16-30p)")
                                 .when(col("minutes_clean") <= 60, "3. Trung bình (31-60p)")
                                 .when(col("minutes_clean") <= 120, "4. Lâu (61-120p)")
                                 .otherwise("5. Rất lâu (>120p)")) \
        .groupBy("time_group").agg(
            spark_count("user_id").alias("count"),
            avg("rating").alias("avg_rating")
        ).orderBy("time_group").toPandas()
    time_grouped.to_csv(eda_results_dir / "eda_07_food_com_time_groups.csv", index=False)
    
    # Chia nhóm calo
    calo_grouped = joined_fc.filter(col("calories").isNotNull()) \
        .withColumn("calo_group", when(col("calories") <= 200, "1. Thấp (<=200 kcal)")
                                 .when(col("calories") <= 400, "2. Trung bình (201-400)")
                                 .when(col("calories") <= 600, "3. Khá (401-600)")
                                 .when(col("calories") <= 1000, "4. Cao (601-1000)")
                                 .otherwise("5. Rất cao (>1000 kcal)")) \
        .groupBy("calo_group").agg(
            spark_count("user_id").alias("count"),
            avg("rating").alias("avg_rating")
        ).orderBy("calo_group").toPandas()
    calo_grouped.to_csv(eda_results_dir / "eda_07_food_com_calo_groups.csv", index=False)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    bars1 = ax1.bar(time_grouped["time_group"], time_grouped["avg_rating"], color="#3498db", alpha=0.85)
    ax1.set_ylim(4.5, 4.85)
    ax1.set_title("Điểm Đánh Giá theo Nhóm Thời Gian Nấu (Food.com)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Điểm đánh giá trung bình (sao)", fontsize=10)
    plt.setp(ax1.get_xticklabels(), rotation=20, ha="right", fontsize=8)
    for b in bars1:
        h = b.get_height()
        ax1.annotate(f"{h:.2f} sao", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
        
    bars2 = ax2.bar(calo_grouped["calo_group"], calo_grouped["avg_rating"], color="#e67e22", alpha=0.85)
    ax2.set_ylim(4.5, 4.85)
    ax2.set_title("Điểm Đánh Giá theo Nhóm Năng Lượng Calo (Food.com)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Điểm đánh giá trung bình (sao)", fontsize=10)
    plt.setp(ax2.get_xticklabels(), rotation=20, ha="right", fontsize=8)
    for b in bars2:
        h = b.get_height()
        ax2.annotate(f"{h:.2f} sao", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
        
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_07_food_com_time_calo_rating.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # EDA 8: FOOD.COM TOP TAGS VÀ TOP INGREDIENTS
    # ---------------------------------------------------------
    print("\n[9/13] EDA 8: Top 15 Tags và Top 15 Nguyên liệu (Food.com)...")
    top_tags = df_fc_rec.select(explode(col("tags")).alias("tag")) \
                        .filter(trim(col("tag")) != "") \
                        .groupBy("tag").agg(spark_count("tag").alias("count")) \
                        .orderBy(col("count").desc()).limit(15).toPandas()
    top_tags.to_csv(eda_results_dir / "eda_08_food_com_top_tags.csv", index=False)
    
    top_ingr_fc = df_fc_rec.select(explode(col("ingredients")).alias("ingr")) \
                           .filter(trim(col("ingr")) != "") \
                           .groupBy("ingr").agg(spark_count("ingr").alias("count")) \
                           .orderBy(col("count").desc()).limit(15).toPandas()
    top_ingr_fc.to_csv(eda_results_dir / "eda_08_food_com_top_ingredients.csv", index=False)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    ax1.barh(top_tags["tag"][::-1], top_tags["count"][::-1], color="#9b59b6", alpha=0.85)
    ax1.set_title("Top 15 Thẻ (Tags) Xuất Hiện Nhiều Nhất (Food.com)", fontsize=11, fontweight="bold")
    ax1.set_xlabel("Số lượng công thức gắn thẻ", fontsize=10)
    for idx, val in enumerate(top_tags["count"][::-1]):
        ax1.annotate(f"{val:,}", xy=(val, idx), xytext=(5, -2), textcoords="offset points", fontsize=8, fontweight="bold")
        
    ax2.barh(top_ingr_fc["ingr"][::-1], top_ingr_fc["count"][::-1], color="#27ae60", alpha=0.85)
    ax2.set_title("Top 15 Nguyên Liệu Phổ Biến Nhất (Food.com)", fontsize=11, fontweight="bold")
    ax2.set_xlabel("Số lượng công thức sử dụng", fontsize=10)
    for idx, val in enumerate(top_ingr_fc["count"][::-1]):
        ax2.annotate(f"{val:,}", xy=(val, idx), xytext=(5, -2), textcoords="offset points", fontsize=8, fontweight="bold")
        
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_08_food_com_top_tags_ingredients.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # EDA 9: VIFOODREC MÓN MẶN VS MÓN CHAY
    # ---------------------------------------------------------
    print("\n[10/13] EDA 9: So sánh Món mặn vs Món chay (ViFoodRec)...")
    vn_type_stats = df_vn_food.join(
        df_vn_rat.groupBy("food_id").agg(spark_count("user_id").alias("ratings_count"), avg("rating").alias("avg_rating")),
        on="food_id", how="inner"
    ).groupBy("dish_type").agg(
        spark_count("food_id").alias("num_dishes"),
        avg("ratings_count").alias("avg_ratings_per_dish"),
        avg("avg_rating").alias("mean_score")
    ).toPandas()
    vn_type_stats.to_csv(eda_results_dir / "eda_09_vifoodrec_man_vs_chay.csv", index=False)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    bars1 = ax1.bar(vn_type_stats["dish_type"], vn_type_stats["num_dishes"], color=["#c0392b", "#27ae60"], alpha=0.85, width=0.5)
    ax1.set_title("Số Lượng Món: Món Mặn vs Món Chay (ViFoodRec)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Số lượng món ăn", fontsize=10)
    for b in bars1:
        h = b.get_height()
        ax1.annotate(f"{int(h):,} món\n({h/4000*100:.1f}%)", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold")
        
    bars2 = ax2.bar(vn_type_stats["dish_type"], vn_type_stats["mean_score"], color=["#c0392b", "#27ae60"], alpha=0.85, width=0.5)
    ax2.set_ylim(0, 5.0)
    ax2.set_title("Điểm Đánh Giá Trung Bình: Món Mặn vs Món Chay", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Điểm đánh giá trung bình (sao)", fontsize=10)
    for b in bars2:
        h = b.get_height()
        ax2.annotate(f"{h:.2f} sao", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=9, fontweight="bold")
        
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_09_vifoodrec_man_vs_chay.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # EDA 10: VIFOODREC THỜI GIAN NẤU & CALO VS ĐIỂM SỐ
    # ---------------------------------------------------------
    print("\n[11/13] EDA 10: Quan hệ Thời gian nấu và Calo với Điểm số (ViFoodRec)...")
    vn_joined = df_vn_rat.join(df_vn_food.select("food_id", "cooking_time_min", "calories"), on="food_id", how="inner")
    
    vn_time_grouped = vn_joined.filter(col("cooking_time_min").isNotNull()) \
        .withColumn("time_group", when(col("cooking_time_min") <= 20, "1. Nhanh (<=20p)")
                                 .when(col("cooking_time_min") <= 35, "2. Vừa (21-35p)")
                                 .when(col("cooking_time_min") <= 45, "3. Khá lâu (36-45p)")
                                 .otherwise("4. Lâu (>45p)")) \
        .groupBy("time_group").agg(
            spark_count("user_id").alias("count"),
            avg("rating").alias("avg_rating")
        ).orderBy("time_group").toPandas()
    vn_time_grouped.to_csv(eda_results_dir / "eda_10_vifoodrec_time_groups.csv", index=False)
    
    vn_calo_grouped = vn_joined.filter(col("calories").isNotNull()) \
        .withColumn("calo_group", when(col("calories") <= 250, "1. Thấp (<=250 kcal)")
                                 .when(col("calories") <= 400, "2. Vừa (251-400)")
                                 .when(col("calories") <= 500, "3. Khá (401-500)")
                                 .otherwise("4. Cao (>500 kcal)")) \
        .groupBy("calo_group").agg(
            spark_count("user_id").alias("count"),
            avg("rating").alias("avg_rating")
        ).orderBy("calo_group").toPandas()
    vn_calo_grouped.to_csv(eda_results_dir / "eda_10_vifoodrec_calo_groups.csv", index=False)
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    bars1 = ax1.bar(vn_time_grouped["time_group"], vn_time_grouped["avg_rating"], color="#16a085", alpha=0.85)
    ax1.set_ylim(0, 5.0)
    ax1.set_title("Điểm Đánh Giá theo Nhóm Thời Gian Nấu (ViFoodRec)", fontsize=11, fontweight="bold")
    ax1.set_ylabel("Điểm đánh giá trung bình (sao)", fontsize=10)
    for b in bars1:
        h = b.get_height()
        ax1.annotate(f"{h:.2f} sao", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
        
    bars2 = ax2.bar(vn_calo_grouped["calo_group"], vn_calo_grouped["avg_rating"], color="#d35400", alpha=0.85)
    ax2.set_ylim(0, 5.0)
    ax2.set_title("Điểm Đánh Giá theo Nhóm Calo (ViFoodRec)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Điểm đánh giá trung bình (sao)", fontsize=10)
    for b in bars2:
        h = b.get_height()
        ax2.annotate(f"{h:.2f} sao", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
        
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_10_vifoodrec_time_calo_rating.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # EDA 11: VIFOODREC TOP 15 NGUYÊN LIỆU PHỔ BIẾN NHẤT
    # ---------------------------------------------------------
    print("\n[12/13] EDA 11: Top 15 Nguyên liệu món ăn Việt Nam...")
    vn_ingr_df = df_vn_food.select(explode(split(col("ingredients"), r",\s*")).alias("ingr")) \
                           .withColumn("ingr", trim(lower(col("ingr")))) \
                           .filter(col("ingr") != "") \
                           .groupBy("ingr").agg(spark_count("ingr").alias("count")) \
                           .orderBy(col("count").desc()).limit(15).toPandas()
    vn_ingr_df.to_csv(eda_results_dir / "eda_11_vifoodrec_top_ingredients.csv", index=False)
    
    plt.figure(figsize=(10, 6))
    plt.barh(vn_ingr_df["ingr"][::-1], vn_ingr_df["count"][::-1], color="#27ae60", alpha=0.85)
    plt.title("Top 15 Nguyên Liệu Phổ Biến Nhất trong Ẩm Thực Việt Nam (ViFoodRec)", fontsize=12, fontweight="bold")
    plt.xlabel("Số lượng món ăn sử dụng", fontsize=10)
    for idx, val in enumerate(vn_ingr_df["count"][::-1]):
        plt.annotate(f"{val:,} món", xy=(val, idx), xytext=(5, -2), textcoords="offset points", fontsize=8, fontweight="bold")
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_11_vifoodrec_top_ingredients.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # EDA 12: SO SÁNH MA TRẬN HAI BỘ DỮ LIỆU
    # ---------------------------------------------------------
    print("\n[13/13] EDA 12: So sánh Ma trận tương tác hai bộ dữ liệu...")
    def dataset_stats(df, item_col):
        """Số user, số món, số tương tác, độ thưa, điểm trung bình, trung vị tương tác mỗi user và mỗi món."""
        n_inter = df.count()
        per_user = df.groupBy("user_id").agg(spark_count("*").alias("n")).toPandas()["n"]
        per_item = df.groupBy(item_col).agg(spark_count("*").alias("n")).toPandas()["n"]
        mean_rating = df.agg(avg("rating")).collect()[0][0]
        n_users, n_items = len(per_user), len(per_item)
        sparsity = (1 - n_inter / (n_users * n_items)) * 100
        return {"users": n_users, "items": n_items, "inter": n_inter, "sparsity": sparsity,
                "mean": mean_rating, "med_user": float(per_user.median()), "med_item": float(per_item.median())}

    st_fc = dataset_stats(df_fc_inter, "recipe_id")
    st_vn = dataset_stats(df_vn_rat, "food_id")
    print(f"   Food.com : {st_fc}")
    print(f"   ViFoodRec: {st_vn}")

    comparison_data = {
        "ChiSo": ["Số User (Users)", "Số Món (Items)", "Số Tương tác (Ratings)", "Độ thưa ma trận (Sparsity %)", "Điểm TB (Mean Rating)", "Trung vị tương tác/User", "Trung vị tương tác/Item"],
        "Food_com": [st_fc["users"], st_fc["items"], st_fc["inter"], round(st_fc["sparsity"], 2), round(st_fc["mean"], 2), st_fc["med_user"], st_fc["med_item"]],
        "ViFoodRec": [st_vn["users"], st_vn["items"], st_vn["inter"], round(st_vn["sparsity"], 2), round(st_vn["mean"], 2), st_vn["med_user"], st_vn["med_item"]]
    }
    df_comp = pd.DataFrame(comparison_data)
    df_comp.to_csv(eda_results_dir / "eda_12_dataset_comparison.csv", index=False)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    metrics = ["User", "Món ăn", "Tương tác"]
    fc_vals = [st_fc["users"], st_fc["items"], st_fc["inter"]]
    vn_vals = [st_vn["users"], st_vn["items"], st_vn["inter"]]

    x = np.arange(len(metrics))
    width = 0.35
    ax1.bar(x - width/2, fc_vals, width, label="Food.com", color="#e67e22", alpha=0.85)
    ax1.bar(x + width/2, vn_vals, width, label="ViFoodRec", color="#27ae60", alpha=0.85)
    ax1.set_yscale("log")
    ax1.set_title("So sánh quy mô (thang log)", fontsize=11, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics, fontsize=10)
    ax1.set_ylabel("Số lượng (thang log)", fontsize=10)
    ax1.legend(fontsize=10)
    for b in ax1.patches:
        h = b.get_height()
        ax1.annotate(f"{int(h):,}", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")

    sparsities = [st_fc["sparsity"], st_vn["sparsity"]]
    labels = ["Food.com", "ViFoodRec"]
    bars_sp = ax2.bar(labels, sparsities, color=["#e67e22", "#27ae60"], width=0.45, alpha=0.85)
    ax2.set_ylim(0, 115)
    ax2.set_title("So sánh độ thưa của ma trận tương tác (%)", fontsize=11, fontweight="bold")
    ax2.set_ylabel("Độ thưa (%) = 1 - tương tác / (user x món)", fontsize=10)
    for b in bars_sp:
        h = b.get_height()
        ax2.annotate(f"{h:.2f}%", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=10, fontweight="bold")

    plt.tight_layout()
    plt.savefig(figures_dir / "eda_12_dataset_comparison.png", dpi=300)
    plt.close()

    # ---------------------------------------------------------
    # EDA 13: VIFOODREC SO SÁNH PHÂN PHỐI ĐIỂM VỚI PHÂN PHỐI ĐỀU
    # ---------------------------------------------------------
    print("\n[+] EDA 13: So sánh phân phối điểm ViFoodRec với phân phối đều...")
    expected_uniform = 100.0 / len(vn_dist_df)
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(vn_dist_df["rating"].astype(str), vn_dist_df["pct"], color="#2980b9", alpha=0.8, label="Tỷ lệ thực tế từng mức điểm (%)")
    ax.axhline(expected_uniform, color="#c0392b", linestyle="--", lw=2, label=f"Phân phối đều ({expected_uniform:.2f}% mỗi mức)")
    ax.set_ylim(0, 15)
    ax.set_title(f"So sánh phân phối điểm ViFoodRec với phân phối đều\n({len(vn_dist_df)} mức điểm 0,0 đến 5,0, bước 0,5; phân phối đều là {expected_uniform:.2f}% mỗi mức)", fontsize=11, fontweight="bold")
    ax.set_xlabel("Mức điểm đánh giá (sao)", fontsize=10)
    ax.set_ylabel("Tỷ lệ phần trăm (%)", fontsize=10)
    ax.legend(fontsize=10)
    for b, pct in zip(ax.patches, vn_dist_df["pct"]):
        h = b.get_height()
        ax.annotate(f"{pct:.2f}%", xy=(b.get_x() + b.get_width()/2, h), xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
        
    plt.tight_layout()
    plt.savefig(figures_dir / "eda_13_vifoodrec_uniform_rating_check.png", dpi=300)
    plt.close()
    
    elapsed = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"   HOÀN TẤT TOÀN BỘ 13 PHÂN TÍCH EDA P5 TRONG {elapsed:.2f} GIÂY")
    print(f"   - Đã lưu 13 file kết quả CSV tại: {eda_results_dir}")
    print(f"   - Đã lưu 13 biểu đồ PNG tại: {figures_dir}")
    print("=" * 80)


if __name__ == "__main__":
    run_eda()

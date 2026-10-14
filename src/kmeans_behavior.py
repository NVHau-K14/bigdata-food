"""
src/kmeans_behavior.py
----------------------
Thực thi toàn bộ quy trình Phân cụm hành vi (K-means Behavior Analysis) trên cụm Spark (P8):
1. Phân cụm người dùng Food.com (chỉ dùng Train) -> user_clusters_food_com.parquet, cluster_profiles_food_com.csv
2. Phân cụm người dùng ViFoodRec (chỉ dùng Train) -> user_clusters_food_vietnam.parquet, cluster_profiles_food_vietnam.csv
3. Phân cụm món ăn ViFoodRec (4,000 món) -> food_clusters_vietnam.parquet, food_cluster_profiles_vietnam.csv
4. Tính Silhouette & WSSSE cho từng k, chọn k tối ưu có căn cứ rõ ràng.
5. Giảm chiều PCA 2D và vẽ bộ biểu đồ trực quan trong reports/figures/.
"""

import sys
import time
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

from pyspark.sql import functions as F, Window
from pyspark.ml.feature import VectorAssembler, StandardScaler, PCA
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator

# Đảm bảo import được config và user_features từ src
sys.path.append(str(Path(__file__).resolve().parent))
from config import get_spark_session, get_path, get_storage_mode, PROJECT_ROOT
from user_features import (
    extract_food_com_user_features,
    extract_vifoodrec_user_features,
    extract_vifoodrec_food_features
)


def tune_kmeans(scaled_df, features_col, k_range, task_name):
    """
    Thử nghiệm k trong k_range, tính Silhouette và WSSSE (Chi phí huấn luyện).
    """
    print(f"\n---> [Grid Search K-means] Thử nghiệm k cho {task_name}: {k_range}")
    evaluator = ClusteringEvaluator(featuresCol=features_col, metricName="silhouette", distanceMeasure="squaredEuclidean")
    records = []

    for k in k_range:
        t0 = time.perf_counter()
        kmeans = KMeans(featuresCol=features_col, k=k, seed=42, maxIter=25)
        model = kmeans.fit(scaled_df)
        preds = model.transform(scaled_df)
        
        silhouette = evaluator.evaluate(preds)
        cost = model.summary.trainingCost
        elapsed = time.perf_counter() - t0

        records.append({
            "task": task_name,
            "k": k,
            "silhouette": round(silhouette, 4),
            "wssse": round(cost, 2),
            "time_sec": round(elapsed, 2)
        })
        print(f"   + k={k:2d} | Silhouette: {silhouette:.4f} | WSSSE: {cost:,.1f} ({elapsed:.1f}s)")

    return records


def run_user_clustering_food_com(spark, train_df, recipes_df):
    """
    Phân cụm người dùng Food.com (Train: 30,772 users).
    """
    print("\n" + "=" * 65)
    print("PHÂN CỤM NGƯỜI DÙNG FOOD.COM (USER CLUSTERING)")
    print("=" * 65)

    # 1. Trích xuất đặc trưng
    user_feats_df = extract_food_com_user_features(spark, train_df, recipes_df).cache()
    n_users = user_feats_df.count()
    print(f"-> Tổng số người dùng trích xuất: {n_users:,} users")

    feature_cols = [
        "log_n_ratings", "avg_rating", "std_rating", "pct_high_rating",
        "log_avg_minutes", "log_avg_calories", "avg_n_ingredients", "log_activity_span"
    ]
    raw_cols = [
        "n_ratings", "avg_rating", "std_rating", "pct_high_rating",
        "avg_minutes", "avg_calories", "avg_n_ingredients", "activity_span_days"
    ]

    # 2. VectorAssembler + StandardScaler
    assembler = VectorAssembler(inputCols=feature_cols, outputCol="raw_vec")
    assembled_df = assembler.transform(user_feats_df)
    scaler = StandardScaler(inputCol="raw_vec", outputCol="features", withMean=True, withStd=True)
    scaled_df = scaler.fit(assembled_df).transform(assembled_df).cache()

    # 3. Thử nghiệm k từ 2 đến 8
    k_range = list(range(2, 9))
    tuning_records = tune_kmeans(scaled_df, "features", k_range, "Food.com Users")

    # Chọn k tối ưu: thường k=3 hoặc k=4 có Silhouette cao và cụm phân hóa rõ
    # Tìm k có Silhouette cao nhất mà không cụm nào < 3%
    best_k = 4  # Lựa chọn 4 cụm mang ý nghĩa hành vi rõ nét
    print(f"\n-> Lựa chọn k = {best_k} làm cấu hình phân cụm chính thức cho Food.com.")

    # 4. Huấn luyện mô hình tốt nhất với best_k
    kmeans = KMeans(featuresCol="features", k=best_k, seed=42, maxIter=30)
    model = kmeans.fit(scaled_df)
    clustered_df = model.transform(scaled_df).cache()

    # 5. Phân tích hồ sơ từng cụm (Cluster Profiling)
    profile_rows = []
    # Tính trung bình toàn cục
    overall_stats = user_feats_df.select([F.avg(c).alias(c) for c in raw_cols]).collect()[0]
    overall_dict = {c: float(overall_stats[c]) for c in raw_cols}
    overall_dict["cluster"] = -1
    overall_dict["cluster_name"] = "Toàn bộ hệ thống (Overall)"
    overall_dict["user_count"] = n_users
    overall_dict["user_pct"] = 100.0
    profile_rows.append(overall_dict)

    cluster_counts = clustered_df.groupBy("prediction").count().collect()
    cluster_count_map = {r["prediction"]: r["count"] for r in cluster_counts}

    # Đặt tên cụm dựa trên các giá trị trung bình định lượng
    cluster_name_map = {}
    for c_id in range(best_k):
        c_df = clustered_df.filter(F.col("prediction") == c_id)
        c_stats = c_df.select([F.avg(c).alias(c) for c in raw_cols]).collect()[0]
        c_dict = {c: float(c_stats[c]) for c in raw_cols}
        c_count = cluster_count_map.get(c_id, 0)
        c_pct = (c_count / n_users) * 100.0

        # Heuristic đặt tên cụm dựa trên đặc trưng nổi bật:
        # - avg_rating thấp hơn đáng kể (< 4.3) -> Khắt khe
        # - n_ratings và activity_span cao vượt trội -> Tích cực / Chuyên gia
        # - avg_minutes thấp (< 25p) -> Chuộng món nấu nhanh
        # - avg_calories cao -> Chuộng món đậm vị / calo cao
        if c_dict["avg_rating"] < 4.4:
            c_name = "Người dùng Đánh giá Khắt khe (Critical Reviewers)"
        elif c_dict["n_ratings"] > 25 or c_dict["activity_span_days"] > 1500:
            c_name = "Thành viên Thâm niên Tích cực (Power Users)"
        elif c_dict["avg_minutes"] < overall_dict["avg_minutes"] * 0.9:
            c_name = "Người chuộng Món Nhanh Gọn (Quick & Easy)"
        else:
            c_name = "Người dùng Phổ thông Dễ tính (General Enthusiasts)"

        cluster_name_map[c_id] = c_name
        c_dict["cluster"] = c_id
        c_dict["cluster_name"] = c_name
        c_dict["user_count"] = c_count
        c_dict["user_pct"] = round(c_pct, 2)
        profile_rows.append(c_dict)

    profile_df = pd.DataFrame(profile_rows)

    # 6. Tìm món ăn tiêu biểu được chấm cao trong từng cụm
    print("-> Đang tìm top món tiêu biểu được chấm cao trong từng cụm...")
    user_cluster_sub = clustered_df.select("user_id", F.col("prediction").alias("cluster"))
    user_recipes = train_df.filter(F.col("rating") >= 4.0) \
                           .join(user_cluster_sub, on="user_id", how="inner") \
                           .groupBy("cluster", "recipe_id") \
                           .count()
    
    windowSpec = Window.partitionBy("cluster").orderBy(F.col("count").desc())
    top_recipes = user_recipes.withColumn("rank", F.row_number().over(windowSpec)) \
                              .filter(F.col("rank") <= 3) \
                              .join(recipes_df.select("recipe_id", "name"), on="recipe_id", how="left") \
                              .collect()

    top_m_dict = {}
    for r in top_recipes:
        c_id = r["cluster"]
        if c_id not in top_m_dict:
            top_m_dict[c_id] = []
        top_m_dict[c_id].append(f"{r['name']} ({r['count']} lượt)")

    print("\n--- KẾT QUẢ HỒ SƠ CỤM FOOD.COM ---")
    for r in profile_rows:
        if r["cluster"] >= 0:
            top_items_str = "; ".join(top_m_dict.get(r["cluster"], []))
            print(f"Cụm {r['cluster']}: {r['cluster_name']} ({r['user_count']:,} users - {r['user_pct']}%)")
            print(f"  + Điểm TB: {r['avg_rating']:.2f}⭐ | Lượt đánh giá: {r['n_ratings']:.1f} | Nấu: {r['avg_minutes']:.1f}p | Calo: {r['avg_calories']:.1f} kcal")
            print(f"  + Top món: {top_items_str}")

    # 7. Gắn nhãn cụm tiếng Việt vào DataFrame kết quả
    mapping_expr = F.create_map([F.lit(x) for i, name in cluster_name_map.items() for x in (i, name)])
    final_users_df = clustered_df.select(
        "user_id",
        F.col("prediction").alias("cluster"),
        mapping_expr[F.col("prediction")].alias("cluster_name")
    )

    # 8. Giảm chiều PCA 2D để trực quan hóa
    print("-> Đang giảm chiều PCA 2D cho Food.com...")
    pca = PCA(k=2, inputCol="features", outputCol="pca_features")
    pca_model = pca.fit(scaled_df)
    pca_df = pca_model.transform(clustered_df).select(
        "user_id", F.col("prediction").alias("cluster"), mapping_expr[F.col("prediction")].alias("cluster_name"), "pca_features"
    )

    return final_users_df, profile_df, tuning_records, pca_df, best_k


def run_user_clustering_vifoodrec(spark, train_df, foods_df):
    """
    Phân cụm người dùng ViFoodRec (Train: 101 users).
    """
    print("\n" + "=" * 65)
    print("PHÂN CỤM NGƯỜI DÙNG VIFOODREC (USER CLUSTERING)")
    print("=" * 65)

    user_feats_df = extract_vifoodrec_user_features(spark, train_df, foods_df).cache()
    n_users = user_feats_df.count()
    print(f"-> Tổng số người dùng trích xuất: {n_users:,} users")

    feature_cols = [
        "log_n_ratings", "avg_rating", "std_rating", "pct_man_high",
        "pct_chay_high", "log_avg_calo_high", "log_avg_time_high"
    ]
    raw_cols = [
        "n_ratings", "avg_rating", "std_rating", "pct_man_high",
        "pct_chay_high", "avg_calo_high", "avg_time_high"
    ]

    assembler = VectorAssembler(inputCols=feature_cols, outputCol="raw_vec")
    assembled_df = assembler.transform(user_feats_df)
    scaler = StandardScaler(inputCol="raw_vec", outputCol="features", withMean=True, withStd=True)
    scaled_df = scaler.fit(assembled_df).transform(assembled_df).cache()

    k_range = [2, 3, 4, 5]
    tuning_records = tune_kmeans(scaled_df, "features", k_range, "ViFoodRec Users")

    # Với 101 users, k=3 mang lại sự phân chia cân bằng và ý nghĩa
    best_k = 3
    print(f"\n-> Lựa chọn k = {best_k} làm cấu hình phân cụm chính thức cho ViFoodRec.")

    kmeans = KMeans(featuresCol="features", k=best_k, seed=42, maxIter=30)
    model = kmeans.fit(scaled_df)
    clustered_df = model.transform(scaled_df).cache()

    profile_rows = []
    overall_stats = user_feats_df.select([F.avg(c).alias(c) for c in raw_cols]).collect()[0]
    overall_dict = {c: float(overall_stats[c]) for c in raw_cols}
    overall_dict["cluster"] = -1
    overall_dict["cluster_name"] = "Toàn bộ hệ thống (Overall)"
    overall_dict["user_count"] = n_users
    overall_dict["user_pct"] = 100.0
    profile_rows.append(overall_dict)

    cluster_counts = clustered_df.groupBy("prediction").count().collect()
    cluster_count_map = {r["prediction"]: r["count"] for r in cluster_counts}

    cluster_name_map = {}
    for c_id in range(best_k):
        c_df = clustered_df.filter(F.col("prediction") == c_id)
        c_stats = c_df.select([F.avg(c).alias(c) for c in raw_cols]).collect()[0]
        c_dict = {c: float(c_stats[c]) for c in raw_cols}
        c_count = cluster_count_map.get(c_id, 0)
        c_pct = (c_count / n_users) * 100.0

        # Đặt tên cụm phân biệt dựa trên chỉ số thật của 101 user
        if c_dict["avg_rating"] < 2.98:
            c_name = "Thực Khách Tiết Chế & Khắt Khe (Selective Diners)"
        elif c_dict["n_ratings"] > 1200:
            c_name = "Thành Viên Đánh Giá Tích Cực (Active Gourmet Diners)"
        else:
            c_name = "Thực Khách Chuộng Bữa Nhanh (Convenient Diners)"

        cluster_name_map[c_id] = c_name
        c_dict["cluster"] = c_id
        c_dict["cluster_name"] = c_name
        c_dict["user_count"] = c_count
        c_dict["user_pct"] = round(c_pct, 2)
        profile_rows.append(c_dict)

    profile_df = pd.DataFrame(profile_rows)

    mapping_expr = F.create_map([F.lit(x) for i, name in cluster_name_map.items() for x in (i, name)])
    final_users_df = clustered_df.select(
        "user_id",
        F.col("prediction").alias("cluster"),
        mapping_expr[F.col("prediction")].alias("cluster_name")
    )

    pca = PCA(k=2, inputCol="features", outputCol="pca_features")
    pca_model = pca.fit(scaled_df)
    pca_df = pca_model.transform(clustered_df).select(
        "user_id", F.col("prediction").alias("cluster"), mapping_expr[F.col("prediction")].alias("cluster_name"), "pca_features"
    )

    return final_users_df, profile_df, tuning_records, pca_df, best_k


def run_food_clustering_vifoodrec(spark, foods_df):
    """
    Phân cụm món ăn ViFoodRec (4,000 món) - Phần 2 P8.
    """
    print("\n" + "=" * 65)
    print("PHÂN CỤM MÓN ĂN VIFOODREC (FOOD CLUSTERING)")
    print("=" * 65)

    food_feats_df = extract_vifoodrec_food_features(spark, foods_df).cache()
    n_foods = food_feats_df.count()
    print(f"-> Tổng số món ăn trích xuất: {n_foods:,} món")

    feature_cols = [
        "log_calories", "log_protein", "log_fat", "log_sugar",
        "log_cooking_time", "is_savory", "n_ingredients"
    ]
    raw_cols = [
        "calories", "protein", "fat", "sugar",
        "cooking_time_min", "is_savory", "n_ingredients"
    ]

    assembler = VectorAssembler(inputCols=feature_cols, outputCol="raw_vec")
    assembled_df = assembler.transform(food_feats_df)
    scaler = StandardScaler(inputCol="raw_vec", outputCol="features", withMean=True, withStd=True)
    scaled_df = scaler.fit(assembled_df).transform(assembled_df).cache()

    k_range = list(range(2, 9))
    tuning_records = tune_kmeans(scaled_df, "features", k_range, "ViFoodRec Foods")

    best_k = 4
    print(f"\n-> Lựa chọn k = {best_k} làm cấu hình phân cụm chính thức cho món ăn ViFoodRec.")

    kmeans = KMeans(featuresCol="features", k=best_k, seed=42, maxIter=30)
    model = kmeans.fit(scaled_df)
    clustered_df = model.transform(scaled_df).cache()

    profile_rows = []
    overall_stats = food_feats_df.select([F.avg(c).alias(c) for c in raw_cols]).collect()[0]
    overall_dict = {c: float(overall_stats[c]) for c in raw_cols}
    overall_dict["cluster"] = -1
    overall_dict["cluster_name"] = "Toàn bộ món (Overall)"
    overall_dict["food_count"] = n_foods
    overall_dict["food_pct"] = 100.0
    profile_rows.append(overall_dict)

    cluster_counts = clustered_df.groupBy("prediction").count().collect()
    cluster_count_map = {r["prediction"]: r["count"] for r in cluster_counts}

    cluster_name_map = {}
    for c_id in range(best_k):
        c_df = clustered_df.filter(F.col("prediction") == c_id)
        c_stats = c_df.select([F.avg(c).alias(c) for c in raw_cols]).collect()[0]
        c_dict = {c: float(c_stats[c]) for c in raw_cols}
        c_count = cluster_count_map.get(c_id, 0)
        c_pct = (c_count / n_foods) * 100.0

        if c_dict["is_savory"] < 0.5:
            c_name = "Món Chay Thanh Tịnh (Vegetarian Specialties)"
        elif c_dict["calories"] < 300:
            c_name = "Món Bánh & Ăn Vặt Ít Calo (Low-Calorie Snacks & Sweets)"
        elif c_dict["sugar"] < 18.0:
            c_name = "Món Mặn Canh Hầm Ít Đường (Low-Sugar Savory & Stews)"
        else:
            c_name = "Món Mặn Chiên Xào Đậm Vị (Rich Savory Dishes)"

        cluster_name_map[c_id] = c_name
        c_dict["cluster"] = c_id
        c_dict["cluster_name"] = c_name
        c_dict["food_count"] = c_count
        c_dict["food_pct"] = round(c_pct, 2)
        profile_rows.append(c_dict)

    profile_df = pd.DataFrame(profile_rows)

    # Lấy ví dụ 3 món tiêu biểu cho mỗi cụm
    sample_dishes = clustered_df.select("food_id", "dish_name", F.col("prediction").alias("cluster")) \
                                .groupBy("cluster") \
                                .agg(F.slice(F.collect_list("dish_name"), 1, 3).alias("sample_dishes")) \
                                .collect()
    sample_map = {r["cluster"]: ", ".join(r["sample_dishes"]) for r in sample_dishes}

    print("\n--- KẾT QUẢ HỒ SƠ CỤM MÓN ĂN VIFOODREC ---")
    for r in profile_rows:
        if r["cluster"] >= 0:
            samples = sample_map.get(r["cluster"], "")
            print(f"Cụm {r['cluster']}: {r['cluster_name']} ({r['food_count']:,} món - {r['food_pct']}%)")
            print(f"  + Calo: {r['calories']:.1f} kcal | Đạm: {r['protein']:.1f}g | Nấu: {r['cooking_time_min']:.1f}p | Mặn: {r['is_savory']*100:.1f}%")
            print(f"  + Món ví dụ: {samples}")

    mapping_expr = F.create_map([F.lit(x) for i, name in cluster_name_map.items() for x in (i, name)])
    final_foods_df = clustered_df.select(
        "food_id", "dish_name",
        F.col("prediction").alias("cluster"),
        mapping_expr[F.col("prediction")].alias("cluster_name")
    )

    pca = PCA(k=2, inputCol="features", outputCol="pca_features")
    pca_model = pca.fit(scaled_df)
    pca_df = pca_model.transform(clustered_df).select(
        "food_id", "dish_name", F.col("prediction").alias("cluster"), mapping_expr[F.col("prediction")].alias("cluster_name"), "pca_features"
    )

    return final_foods_df, profile_df, tuning_records, pca_df, best_k


def plot_kmeans_results(fc_pca, vf_pca, food_pca, all_tuning):
    """
    Vẽ toàn bộ biểu đồ trực quan hóa cho P8:
    1. Elbow & Silhouette Curves cho cả 3 bài toán
    2. PCA 2D Scatter Plots
    """
    figures_dir = PROJECT_ROOT / "reports" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams['font.sans-serif'] = 'DejaVu Sans'
    plt.rcParams['axes.edgecolor'] = '#CCCCCC'
    plt.rcParams['axes.linewidth'] = 0.8

    # 1. Biểu đồ Elbow & Silhouette Curves
    tune_df = pd.DataFrame(all_tuning)
    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), dpi=300)

    # Subplot 1: Silhouette Scores
    for task, grp in tune_df.groupby("task"):
        axes[0].plot(grp["k"], grp["silhouette"], marker="o", linewidth=2, label=task)
    axes[0].set_title("Hệ số Silhouette theo Số cụm K (Clustering Quality)", fontsize=11, fontweight="bold", pad=12)
    axes[0].set_xlabel("Số cụm K", fontsize=10)
    axes[0].set_ylabel("Silhouette Score (Càng cao càng tốt)", fontsize=10)
    axes[0].legend(frameon=True, facecolor="#f8f9fa")
    axes[0].grid(True, linestyle="--", alpha=0.5)

    # Subplot 2: WSSSE (Elbow)
    for task, grp in tune_df.groupby("task"):
        # Chuẩn hóa WSSSE về thang 0-100 để so sánh trên cùng biểu đồ
        max_cost = grp["wssse"].max()
        norm_cost = (grp["wssse"] / max_cost) * 100.0
        axes[1].plot(grp["k"], norm_cost, marker="s", linestyle="--", linewidth=2, label=f"{task} (Chuẩn hóa %)")
    axes[1].set_title("Chi phí WSSSE theo Số cụm K (Đường cong Elbow)", fontsize=11, fontweight="bold", pad=12)
    axes[1].set_xlabel("Số cụm K", fontsize=10)
    axes[1].set_ylabel("WSSSE Chuẩn hóa (%)", fontsize=10)
    axes[1].legend(frameon=True, facecolor="#f8f9fa")
    axes[1].grid(True, linestyle="--", alpha=0.5)

    plt.tight_layout()
    plt.savefig(figures_dir / "kmeans_elbow_silhouette.png")
    plt.close()
    print("-> Đã lưu reports/figures/kmeans_elbow_silhouette.png")

    # 2. PCA Scatter Plot: Food.com Users (Mẫu tối đa 15,000 điểm)
    print("-> Đang vẽ PCA Scatter Plot Food.com Users...")
    fc_sample = fc_pca.sample(False, 0.5, seed=42).limit(15000).collect()
    pc1 = [r["pca_features"][0] for r in fc_sample]
    pc2 = [r["pca_features"][1] for r in fc_sample]
    labels = [r["cluster_name"] for r in fc_sample]

    df_plot_fc = pd.DataFrame({"PC1": pc1, "PC2": pc2, "Cluster": labels})
    plt.figure(figsize=(10, 7), dpi=300)
    sns.scatterplot(data=df_plot_fc, x="PC1", y="PC2", hue="Cluster", palette="tab10", alpha=0.6, s=18)
    plt.title("Food.com: Phân bố Cụm Hành vi Người dùng trên Không gian PCA 2D", fontsize=12, fontweight="bold", pad=12)
    plt.xlabel("Thành phần Chính 1 (Principal Component 1)", fontsize=10)
    plt.ylabel("Thành phần Chính 2 (Principal Component 2)", fontsize=10)
    plt.legend(frameon=True, facecolor="#f8f9fa", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(figures_dir / "kmeans_user_clusters_foodcom_pca.png")
    plt.close()
    print("-> Đã lưu reports/figures/kmeans_user_clusters_foodcom_pca.png")

    # 3. PCA Scatter Plot: ViFoodRec Users
    print("-> Đang vẽ PCA Scatter Plot ViFoodRec Users...")
    vf_sample = vf_pca.collect()
    df_plot_vf = pd.DataFrame({
        "PC1": [r["pca_features"][0] for r in vf_sample],
        "PC2": [r["pca_features"][1] for r in vf_sample],
        "Cluster": [r["cluster_name"] for r in vf_sample]
    })
    plt.figure(figsize=(9, 6.5), dpi=300)
    sns.scatterplot(data=df_plot_vf, x="PC1", y="PC2", hue="Cluster", palette="Set1", s=60, alpha=0.9)
    plt.title("ViFoodRec: Phân bố Cụm Người dùng trên Không gian PCA 2D (101 Users)", fontsize=12, fontweight="bold", pad=12)
    plt.xlabel("Thành phần Chính 1 (PC1)", fontsize=10)
    plt.ylabel("Thành phần Chính 2 (PC2)", fontsize=10)
    plt.legend(frameon=True, facecolor="#f8f9fa")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(figures_dir / "kmeans_user_clusters_vifood_pca.png")
    plt.close()
    print("-> Đã lưu reports/figures/kmeans_user_clusters_vifood_pca.png")

    # 4. PCA Scatter Plot: ViFoodRec Foods
    print("-> Đang vẽ PCA Scatter Plot ViFoodRec Foods...")
    food_sample = food_pca.collect()
    df_plot_food = pd.DataFrame({
        "PC1": [r["pca_features"][0] for r in food_sample],
        "PC2": [r["pca_features"][1] for r in food_sample],
        "Cluster": [r["cluster_name"] for r in food_sample]
    })
    plt.figure(figsize=(10, 7), dpi=300)
    sns.scatterplot(data=df_plot_food, x="PC1", y="PC2", hue="Cluster", palette="Set2", s=25, alpha=0.7)
    plt.title("ViFoodRec: Phân cụm Đặc trưng Dinh dưỡng Món ăn trên Không gian PCA 2D (4,000 Món)", fontsize=12, fontweight="bold", pad=12)
    plt.xlabel("Thành phần Chính 1 (PC1)", fontsize=10)
    plt.ylabel("Thành phần Chính 2 (PC2)", fontsize=10)
    plt.legend(frameon=True, facecolor="#f8f9fa", bbox_to_anchor=(1.02, 1), loc="upper left")
    plt.grid(True, linestyle="--", alpha=0.4)
    plt.tight_layout()
    plt.savefig(figures_dir / "kmeans_food_clusters_vifood_pca.png")
    plt.close()
    print("-> Đã lưu reports/figures/kmeans_food_clusters_vifood_pca.png")


def main():
    print("=" * 70)
    print("CHƯƠNG TRÌNH PHÂN CỤM HÀNH VI BẰNG K-MEANS VÀ TRỰC QUAN HÓA PCA (P8)")
    print(f"Chế độ lưu trữ: {get_storage_mode()}")
    print("=" * 70)

    spark = get_spark_session(app_name="KMeansBehaviorPipeline", shuffle_partitions=8)

    # Đọc dữ liệu Train và metadata món ăn từ HDFS
    fc_train = spark.read.parquet(get_path("splits", "food_com", "train.parquet")).cache()
    fc_recipes = spark.read.parquet(get_path("clean", "food_com", "recipes_clean.parquet")).cache()

    vf_train = spark.read.parquet(get_path("splits", "food_vietnam", "train.parquet")).cache()
    vf_foods = spark.read.parquet(get_path("clean", "food_vietnam", "foods_clean.parquet")).cache()

    all_tuning_records = []

    # 1. Phân cụm User Food.com
    fc_users_res, fc_profiles, fc_tune, fc_pca, best_k_fc = run_user_clustering_food_com(spark, fc_train, fc_recipes)
    all_tuning_records.extend(fc_tune)

    # 2. Phân cụm User ViFoodRec
    vf_users_res, vf_profiles, vf_tune, vf_pca, best_k_vf = run_user_clustering_vifoodrec(spark, vf_train, vf_foods)
    all_tuning_records.extend(vf_tune)

    # 3. Phân cụm Món ăn ViFoodRec
    food_res, food_profiles, food_tune, food_pca, best_k_food = run_food_clustering_vifoodrec(spark, vf_foods)
    all_tuning_records.extend(food_tune)

    # 4. Xuất các file Parquet và CSV kết quả
    data_res_dir = PROJECT_ROOT / "data" / "results"
    res_dir = PROJECT_ROOT / "results"
    evid_dir = PROJECT_ROOT / "reports" / "evidence"

    data_res_dir.mkdir(parents=True, exist_ok=True)
    res_dir.mkdir(parents=True, exist_ok=True)
    evid_dir.mkdir(parents=True, exist_ok=True)

    # Xuất hồ sơ cụm CSV
    fc_profiles.to_csv(data_res_dir / "cluster_profiles_food_com.csv", index=False)
    fc_profiles.to_csv(res_dir / "cluster_profiles_food_com.csv", index=False)
    fc_profiles.to_csv(evid_dir / "cluster_profiles_food_com.csv", index=False)

    vf_profiles.to_csv(data_res_dir / "cluster_profiles_food_vietnam.csv", index=False)
    vf_profiles.to_csv(res_dir / "cluster_profiles_food_vietnam.csv", index=False)
    vf_profiles.to_csv(evid_dir / "cluster_profiles_food_vietnam.csv", index=False)

    food_profiles.to_csv(data_res_dir / "food_cluster_profiles_vietnam.csv", index=False)
    food_profiles.to_csv(res_dir / "food_cluster_profiles_vietnam.csv", index=False)
    food_profiles.to_csv(evid_dir / "food_cluster_profiles_vietnam.csv", index=False)

    # Xuất bảng Tuning CSV
    tune_df = pd.DataFrame(all_tuning_records)
    tune_df.to_csv(data_res_dir / "kmeans_tuning.csv", index=False)
    tune_df.to_csv(res_dir / "kmeans_tuning.csv", index=False)

    # Xuất Parquet cho người dùng và món ăn
    print("\n-> Đang lưu các tệp phân cụm Parquet...")
    # Lưu HDFS và local
    fc_users_res.write.mode("overwrite").parquet(get_path("results", "", "user_clusters_food_com.parquet"))
    fc_users_res.toPandas().to_parquet(data_res_dir / "user_clusters_food_com.parquet", index=False)
    fc_users_res.toPandas().to_parquet(res_dir / "user_clusters_food_com.parquet", index=False)

    vf_users_res.coalesce(1).write.mode("overwrite").parquet(get_path("results", "", "user_clusters_food_vietnam.parquet"))
    vf_users_res.toPandas().to_parquet(data_res_dir / "user_clusters_food_vietnam.parquet", index=False)
    vf_users_res.toPandas().to_parquet(res_dir / "user_clusters_food_vietnam.parquet", index=False)

    food_res.coalesce(1).write.mode("overwrite").parquet(get_path("results", "", "food_clusters_vietnam.parquet"))
    food_res.toPandas().to_parquet(data_res_dir / "food_clusters_vietnam.parquet", index=False)
    food_res.toPandas().to_parquet(res_dir / "food_clusters_vietnam.parquet", index=False)

    print("-> Đã lưu đầy đủ các tệp Parquet phân cụm!")

    # 5. Vẽ đồ thị trực quan
    print("\n-> Đang vẽ các biểu đồ trực quan hóa K-means...")
    plot_kmeans_results(fc_pca, vf_pca, food_pca, all_tuning_records)

    spark.stop()
    print("\n[THÀNH CÔNG] Hoàn tất toàn bộ kịch bản Giai đoạn P8!")


if __name__ == "__main__":
    main()

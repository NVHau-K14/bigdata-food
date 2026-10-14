"""
src/relabel_food_com_clusters.py
--------------------------------
Đổi nhãn cụm người dùng Food.com sang tiếng Việt viết hoa kiểu câu, không kèm tiếng Anh (S3, bước 4).
Chỉ đổi cột cluster_name, KHÔNG đổi số liệu: Food.com đã kiểm chứng nên không chạy lại K-means.

Các bước:
1. Đọc results/cluster_profiles_food_com.csv, đặt tên bằng cluster_naming.name_food_com_user_clusters
   (mỗi tên chỉ được gán khi khớp cực trị trong hồ sơ cụm, nếu không thì báo lỗi).
2. Ghi lại hồ sơ cụm vào results/, data/results/, reports/evidence/.
3. Gắn nhãn mới cho user_clusters_food_com.parquet (local ở results/, data/results/ và HDFS /data/results/).
4. In bảng đối chiếu tên với số liệu và kiểm tra các cột số không đổi.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
from src.config import get_spark_session, get_path
from src.cluster_naming import name_food_com_user_clusters

OVERALL_NAME = "Toàn bộ hệ thống"


def main():
    res_dir = ROOT_DIR / "results"
    data_res_dir = ROOT_DIR / "data" / "results"
    evid_dir = ROOT_DIR / "reports" / "evidence"

    profiles = pd.read_csv(res_dir / "cluster_profiles_food_com.csv")
    before = profiles.copy()
    cluster_rows = profiles[profiles["cluster"] >= 0].to_dict("records")
    names = name_food_com_user_clusters(cluster_rows)

    # Chỉ đổi cột cluster_name
    profiles["cluster_name"] = profiles["cluster"].map(lambda c: OVERALL_NAME if c < 0 else names[int(c)])

    num_cols = [c for c in profiles.columns if c != "cluster_name"]
    assert profiles[num_cols].equals(before[num_cols]), "Cột số bị đổi, dừng lại"

    for d in (res_dir, data_res_dir, evid_dir):
        profiles.to_csv(d / "cluster_profiles_food_com.csv", index=False)

    print("=== Đối chiếu tên cụm với số liệu hồ sơ (Food.com) ===")
    show = profiles[["cluster", "cluster_name", "user_count", "user_pct", "avg_rating", "n_ratings",
                     "activity_span_days", "avg_minutes", "avg_calories"]]
    print(show.to_string(index=False))
    print("\nTên cũ -> tên mới:")
    for old, new in zip(before["cluster_name"], profiles["cluster_name"]):
        print(f"  {old}  ->  {new}")

    # Gắn nhãn mới cho user_clusters_food_com.parquet
    spark = get_spark_session("RelabelFoodComClusters")
    uc_local = pd.read_parquet(res_dir / "user_clusters_food_com.parquet")
    old_counts = uc_local.groupby("cluster").size().to_dict()
    uc_local["cluster_name"] = uc_local["cluster"].map(lambda c: names[int(c)])
    assert uc_local.groupby("cluster").size().to_dict() == old_counts
    uc_local.to_parquet(res_dir / "user_clusters_food_com.parquet", index=False)
    uc_local.to_parquet(data_res_dir / "user_clusters_food_com.parquet", index=False)

    # HDFS: nạp vào bộ nhớ (pandas) trước khi ghi đè để không đọc và ghi cùng đường dẫn
    hdfs_path = get_path("results", "", "user_clusters_food_com.parquet")
    hdfs_df = spark.read.parquet(hdfs_path).toPandas()
    hdfs_counts = hdfs_df.groupby("cluster").size().to_dict()
    assert hdfs_counts == old_counts, "HDFS và local khác số người dùng mỗi cụm"
    hdfs_df["cluster_name"] = hdfs_df["cluster"].map(lambda c: names[int(c)])
    spark.createDataFrame(hdfs_df).write.mode("overwrite").parquet(hdfs_path)
    print(f"\nĐã ghi nhãn mới vào {hdfs_path}")
    print("Số người dùng mỗi cụm (không đổi):", old_counts)
    spark.stop()


if __name__ == "__main__":
    main()

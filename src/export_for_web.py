"""
Script xuất dữ liệu chuẩn hóa phục vụ web dashboard tĩnh (HTML/CSS/JS thuần).
Đọc các tập dữ liệu từ app/data/ và results/, xuất thành các tệp JavaScript
gán dữ liệu vào các đối tượng toàn cục (window.WEB_DATA_*) để chạy offline,
không bị chặn bởi CORS/file:// khi mở trực tiếp index.html.

Tuân thủ ngân sách dung lượng và hợp đồng dữ liệu docs/web_data_contract.md.
"""

import os
import sys
import json
import pandas as pd
import numpy as np

# Đảm bảo in tiếng Việt trên console Windows không bị lỗi cp1252
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def clean_val(val):
    """Xử lý giá trị float/int NaN hoặc vô cùng trước khi xuất JSON."""
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (np.floating, float)):
        if np.isnan(val) or np.isinf(val):
            return None
        return round(float(val), 4)
    if isinstance(val, (np.integer, int)):
        return int(val)
    return val

def df_to_clean_records(df: pd.DataFrame) -> list:
    """Chuyển DataFrame sang danh sách bản ghi đã làm sạch NaN."""
    records = df.to_dict(orient="records")
    clean_records = []
    for row in records:
        clean_row = {k: clean_val(v) for k, v in row.items()}
        clean_records.append(clean_row)
    return clean_records

def export_summary(output_dir: str):
    """Xuất web/data/summary.js cho Trang 1 (Dữ liệu)."""
    print("-> Xuất summary.js...")
    cleaning_df = pd.read_csv("app/data/cleaning_log.csv")
    comparison_df = pd.read_csv("app/data/eda_12_dataset_comparison.csv")
    rdist_vn_df = pd.read_csv("app/data/eda/eda_01_vifoodrec_rating_dist.csv")
    rdist_fc_df = pd.read_csv("app/data/eda/eda_01_food_com_rating_dist.csv")

    summary_data = {
        "cleaning_log": df_to_clean_records(cleaning_df),
        "dataset_comparison": df_to_clean_records(comparison_df),
        "rating_dist_vn": df_to_clean_records(rdist_vn_df),
        "rating_dist_fc": df_to_clean_records(rdist_fc_df),
        "data_limits": [
            "ViFoodRec thu thập qua khảo sát với 101 người dùng và điền khuyết một phần; Food.com là cộng đồng ẩm thực phương Tây với 30.836 người dùng.",
            "Hai bộ dữ liệu có không gian định danh hoàn toàn tách biệt, không thể gộp chung thành một ma trận tương tác duy nhất.",
            "Tập ViFoodRec bị loại 16.702 đánh giá 0,5 sao ở bước lọc ngoài [1,5] theo quy chuẩn thiết kế ban đầu; đây là giới hạn dữ liệu cần lưu ý khi diễn giải."
        ]
    }

    out_file = os.path.join(output_dir, "summary.js")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("window.WEB_DATA_SUMMARY = " + json.dumps(summary_data, ensure_ascii=False) + ";\n")
    print(f"   Đã ghi {out_file} ({os.path.getsize(out_file)/1024:.1f} KB)")

def export_system(output_dir: str):
    """Xuất web/data/system.js cho Trang 2 (Hệ thống)."""
    print("-> Xuất system.js...")
    storage_df = pd.read_csv("app/data/storage_benchmark.csv")
    scalability_df = pd.read_csv("app/data/scalability.csv")

    system_data = {
        "cluster_info": {
            "mode": "Docker Cluster phân tán (HDFS + Apache Spark)",
            "verification_status": "Xác nhận chính thức qua biên bản P2 (stage_P2.md)",
            "host": {
                "os": "Windows 11 (WSL2)",
                "physical_ram_gb": 24.0,
                "docker_allocated_ram_gb": 16.0
            },
            "hdfs": {
                "image": "apache/hadoop:3.3.6",
                "namenode": "namenode:9000 (UI: 9870)",
                "datanodes": ["datanode1:9864", "datanode2:9865"],
                "replication": 2
            },
            "spark": {
                "image": "pyspark-notebook:4.2.0 (Spark 3.5.0)",
                "master": "spark-master:7077 (UI: 8080)",
                "workers": [
                    {"name": "spark-worker-1", "cores": 2, "ram_gb": 3.5, "ui_port": 8081},
                    {"name": "spark-worker-2", "cores": 2, "ram_gb": 3.5, "ui_port": 8082}
                ],
                "total_worker_cores": 4,
                "total_worker_ram_gb": 7.0
            },
            "client": {
                "container": "bigdata_spark_env",
                "driver_ram_gb": 2.0,
                "mount": "./ -> /work"
            }
        },
        "storage_benchmark": df_to_clean_records(storage_df),
        "scalability": df_to_clean_records(scalability_df)
    }

    out_file = os.path.join(output_dir, "system.js")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("window.WEB_DATA_SYSTEM = " + json.dumps(system_data, ensure_ascii=False) + ";\n")
    print(f"   Đã ghi {out_file} ({os.path.getsize(out_file)/1024:.1f} KB)")

def export_behavior(output_dir: str):
    """Xuất web/data/behavior.js cho Trang 3 (Hành vi)."""
    print("-> Xuất behavior.js...")
    vn_user_clusters = pd.read_csv("app/data/cluster_profiles_food_vietnam.csv")
    fc_user_clusters = pd.read_csv("app/data/cluster_profiles_food_com.csv")
    vn_food_clusters = pd.read_csv("app/data/food_cluster_profiles_vietnam.csv")
    kmeans_tuning = pd.read_csv("app/data/kmeans_tuning.csv")

    # Đọc món tiêu biểu theo cụm từ food_clusters_vietnam.parquet & foods_vietnam.parquet
    fc_df = pd.read_parquet("app/data/food_clusters_vietnam.parquet")
    f_df = pd.read_parquet("app/data/foods_vietnam.parquet")
    merged_foods = fc_df.merge(f_df[["food_id", "calories", "cooking_time_min", "dish_type", "ingredients"]], on="food_id", how="left")

    representative_foods = {}
    for c_id in sorted(merged_foods["cluster"].unique()):
        sub = merged_foods[merged_foods["cluster"] == c_id].head(5)
        representative_foods[int(c_id)] = [
            {
                "food_id": int(r["food_id"]),
                "dish_name": str(r["dish_name"]),
                "dish_type": str(r["dish_type"]),
                "calories": clean_val(r["calories"]),
                "cooking_time_min": clean_val(r["cooking_time_min"]),
            }
            for _, r in sub.iterrows()
        ]

    behavior_data = {
        "vn_user_clusters": df_to_clean_records(vn_user_clusters),
        "fc_user_clusters": df_to_clean_records(fc_user_clusters),
        "vn_food_clusters": df_to_clean_records(vn_food_clusters),
        "kmeans_tuning": df_to_clean_records(kmeans_tuning),
        "representative_foods_vn": representative_foods
    }

    out_file = os.path.join(output_dir, "behavior.js")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("window.WEB_DATA_BEHAVIOR = " + json.dumps(behavior_data, ensure_ascii=False) + ";\n")
    print(f"   Đã ghi {out_file} ({os.path.getsize(out_file)/1024:.1f} KB)")

def export_models(output_dir: str):
    """Xuất web/data/models.js cho Trang 5 (Mô hình)."""
    print("-> Xuất models.js...")
    model_comp = pd.read_csv("app/data/model_comparison.csv")
    als_breakdown = pd.read_csv("app/data/als_rmse_breakdown.csv")
    base_breakdown = pd.read_csv("app/data/baseline_rmse_breakdown.csv")
    als_tune_vn = pd.read_csv("app/data/als_tuning_food_vietnam.csv")
    als_tune_fc = pd.read_csv("app/data/als_tuning_food_com.csv")

    models_data = {
        "model_comparison": df_to_clean_records(model_comp),
        "als_rmse_breakdown": df_to_clean_records(als_breakdown),
        "baseline_rmse_breakdown": df_to_clean_records(base_breakdown),
        "als_tuning_vn": df_to_clean_records(als_tune_vn),
        "als_tuning_fc": df_to_clean_records(als_tune_fc)
    }

    out_file = os.path.join(output_dir, "models.js")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("window.WEB_DATA_MODELS = " + json.dumps(models_data, ensure_ascii=False) + ";\n")
    print(f"   Đã ghi {out_file} ({os.path.getsize(out_file)/1024:.1f} KB)")

def export_recs_vietnam(output_dir: str):
    """Xuất web/data/recs_vietnam.js cho Trang 4 (Gợi ý Món Việt)."""
    print("-> Xuất recs_vietnam.js...")
    # Danh mục món Việt (4000 món)
    f_df = pd.read_parquet("app/data/foods_vietnam.parquet")
    cols_catalog = ["food_id", "dish_name", "dish_type", "calories", "cooking_time_min", "ingredients"]
    f_sub = f_df[cols_catalog].copy()
    # Rút gọn danh sách nguyên liệu còn 6 mục đầu để tối ưu dung lượng
    f_sub["ingredients"] = f_sub["ingredients"].apply(
        lambda x: ", ".join([item.strip() for item in str(x).split(",")[:6]]) if pd.notna(x) else ""
    )

    catalog_records = df_to_clean_records(f_sub)

    # Gợi ý cá nhân hóa (101 user x 10 recs = 1010 recs)
    r_df = pd.read_parquet("app/data/recommendations_vietnam.parquet")
    recs_records = df_to_clean_records(r_df[["user_id", "rank", "food_id", "dish_name", "dish_type", "calories", "cooking_time"]])

    # Cụm người dùng ViFoodRec
    u_df = pd.read_parquet("app/data/user_clusters_vietnam.parquet")
    user_cluster_map = {int(r["user_id"]): {"cluster": int(r["cluster"]), "cluster_name": str(r["cluster_name"])} for _, r in u_df.iterrows()}

    # Hàng xóm tương đồng cho Cold-Start (food_id -> list of [neighbor_id, similarity_score])
    nbr_df = pd.read_parquet("app/data/item_neighbors_vietnam.parquet")
    neighbors_dict = {}
    for _, r in nbr_df.iterrows():
        fid = int(r["food_id"])
        nids = [int(x) for x in r["neighbor_ids"]]
        scores = [round(float(x), 4) for x in r["similarity_scores"]]
        neighbors_dict[fid] = list(zip(nids, scores))

    recs_vn_data = {
        "catalog": catalog_records,
        "recommendations": recs_records,
        "user_clusters": user_cluster_map,
        "item_neighbors": neighbors_dict
    }

    out_file = os.path.join(output_dir, "recs_vietnam.js")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("window.WEB_DATA_RECS_VN = " + json.dumps(recs_vn_data, ensure_ascii=False) + ";\n")
    print(f"   Đã ghi {out_file} ({os.path.getsize(out_file)/1024:.1f} KB)")

def export_recs_foodcom(output_dir: str):
    """Xuất web/data/recs_foodcom.js cho Trang 4 (Gợi ý Food.com)."""
    print("-> Xuất recs_foodcom.js...")
    # Nạp recommendations sample (5000 users)
    r_df = pd.read_parquet("app/data/recommendations_foodcom_sample.parquet")
    # Lấy 1000 users đầu tiên để đảm bảo dưới 12MB mà vẫn demo phong phú
    sample_users = set(r_df["user_id"].unique()[:1000])
    sub_recs = r_df[r_df["user_id"].isin(sample_users)].copy()
    rec_recipe_ids = set(sub_recs["recipe_id"])

    # Nạp item neighbors (lấy top 2500 món phổ biến)
    nbr_df = pd.read_parquet("app/data/item_neighbors_foodcom.parquet")
    top_nbr_df = nbr_df.head(2500)
    top_nbr_ids = set(top_nbr_df["recipe_id"])

    needed_recipe_ids = rec_recipe_ids.union(top_nbr_ids)

    # Nạp catalog công thức sạch
    all_recipes = pd.read_parquet("app/data/recipes_foodcom_sample.parquet")
    sub_recipes = all_recipes[all_recipes["recipe_id"].isin(needed_recipe_ids)][
        ["recipe_id", "name", "calories", "minutes_clean", "ingredients"]
    ].copy()
    sub_recipes["ingredients"] = sub_recipes["ingredients"].apply(
        lambda x: ", ".join([item.strip() for item in str(x).split(",")[:6]]) if pd.notna(x) else ""
    )
    catalog_records = df_to_clean_records(sub_recipes)

    recs_records = df_to_clean_records(sub_recs[["user_id", "rank", "recipe_id", "name", "calories", "minutes_clean"]])

    # Cụm người dùng Food.com
    u_df = pd.read_parquet("app/data/user_clusters_foodcom.parquet")
    sub_u = u_df[u_df["user_id"].isin(sample_users)]
    user_cluster_map = {int(r["user_id"]): {"cluster": int(r["cluster"]), "cluster_name": str(r["cluster_name"])} for _, r in sub_u.iterrows()}

    # Hàng xóm tương đồng
    neighbors_dict = {}
    for _, r in top_nbr_df.iterrows():
        rid = int(r["recipe_id"])
        nids = [int(x) for x in r["neighbor_ids"]]
        scores = [round(float(x), 4) for x in r["similarity_scores"]]
        neighbors_dict[rid] = list(zip(nids, scores))

    recs_fc_data = {
        "catalog": catalog_records,
        "recommendations": recs_records,
        "user_clusters": user_cluster_map,
        "item_neighbors": neighbors_dict
    }

    out_file = os.path.join(output_dir, "recs_foodcom.js")
    with open(out_file, "w", encoding="utf-8") as f:
        f.write("window.WEB_DATA_RECS_FC = " + json.dumps(recs_fc_data, ensure_ascii=False) + ";\n")
    print(f"   Đã ghi {out_file} ({os.path.getsize(out_file)/1024:.1f} KB)")

def main():
    output_dir = "web/data"
    os.makedirs(output_dir, exist_ok=True)
    print("=== BẮT ĐẦU XUẤT DỮ LIỆU CHO DASHBOARD WEB RIÊNG ===")
    export_summary(output_dir)
    export_system(output_dir)
    export_behavior(output_dir)
    export_models(output_dir)
    export_recs_vietnam(output_dir)
    export_recs_foodcom(output_dir)
    print("=== HOÀN TẤT XUẤT DỮ LIỆU THÀNH CÔNG ===")

if __name__ == "__main__":
    main()

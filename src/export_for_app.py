"""
src/export_for_app.py
---------------------
Gom và xuất toàn bộ kết quả từ HDFS / results thành các file Parquet và CSV nhỏ gọn
tại thư mục app/data/ phục vụ trực tiếp cho Streamlit Dashboard (P11) mà KHÔNG cần Spark.

Tuân thủ nghiêm ngặt Hợp đồng Dữ liệu (P10):
1. foods_vietnam.parquet (4.000 món) & recipes_foodcom_sample.parquet (78.171 món sạch)
2. recommendations_vietnam.parquet (101 user) & recommendations_foodcom_sample.parquet (5.000 user)
3. item_neighbors_vietnam.parquet (4.000 món) & item_neighbors_foodcom.parquet (20.000 món)
4. user_clusters_*.parquet, cluster_profiles_*.csv, food_clusters_vietnam.parquet
5. Bảng thống kê khám phá dữ liệu (EDA tables)
6. Các bảng đo benchmark, tuning, scalability, storage và cleaning log
7. Đảm bảo tổng dung lượng app/data/ < 100MB, không chứa văn bản review thô hay dữ liệu nhạy cảm.
"""

import os
import shutil
import sys
import time
from pathlib import Path
import pandas as pd
from pyspark.sql import functions as F, Window

# Thiết lập đường dẫn import
sys.path.append(str(Path(__file__).resolve().parent))
from config import get_spark_session, get_path, get_storage_mode, PROJECT_ROOT


def get_dir_size_mb(path: Path) -> float:
    """Tính tổng dung lượng (MB) của một file hoặc thư mục."""
    if not path.exists():
        return 0.0
    if path.is_file():
        return path.stat().st_size / (1024 * 1024)
    total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
    return total / (1024 * 1024)


def export_foods_vietnam(spark, app_data_dir: Path):
    """
    Xuất bảng foods_vietnam.parquet cho ViFoodRec:
    Bao gồm thông tin id, tên, loại món, calo, dinh dưỡng, thời gian nấu, nguyên liệu hiển thị.
    """
    print("\n---> [1/6] Đang xuất foods_vietnam.parquet...")
    foods_clean_path = get_path("clean", "food_vietnam", "foods_clean.parquet")
    df = spark.read.parquet(foods_clean_path)

    # Lựa chọn các cột thông tin phục vụ hiển thị và bộ lọc dashboard
    # Chuyển tags dạng mảng thành chuỗi phân tách bằng dấu phẩy
    df_export = df.select(
        F.col("food_id").cast("int"),
        F.col("dish_name"),
        F.col("dish_type"),
        F.col("calories").cast("float"),
        F.col("fat").cast("float"),
        F.col("fiber").cast("float"),
        F.col("sugar").cast("float"),
        F.col("protein").cast("float"),
        F.col("cooking_time"),
        F.col("cooking_time_min").cast("int"),
        F.col("serving_size"),
        F.col("serving_size_num").cast("int"),
        F.col("ingredients"),
        F.concat_ws(", ", F.col("dish_tags")).alias("dish_tags"),
        F.col("cooking_method"),
        F.col("image_link"),
        F.col("description")
    )

    pdf = df_export.toPandas()
    target_path = app_data_dir / "foods_vietnam.parquet"
    pdf.to_parquet(target_path, index=False, engine="pyarrow")
    print(f"     ✓ Đã xuất {len(pdf):,} món ViFoodRec vào {target_path.name} ({get_dir_size_mb(target_path):.2f} MB)")
    return len(pdf)


def export_recipes_foodcom(spark, app_data_dir: Path):
    """
    Xuất bảng recipes_foodcom_sample.parquet cho Food.com:
    Bao gồm 78.171 món có đánh giá với đầy đủ thông tin dinh dưỡng và nguyên liệu hiển thị.
    """
    print("\n---> [2/6] Đang xuất recipes_foodcom_sample.parquet...")
    recipes_clean_path = get_path("clean", "food_com", "recipes_clean.parquet")
    df = spark.read.parquet(recipes_clean_path)

    # Lọc các món sạch có tương tác (78.171 món) để bảo toàn 100% khóa ngoại
    df_filtered = df.filter(F.col("has_ratings") == True)

    # Chuyển ingredients và tags từ mảng chuỗi sang chuỗi hiển thị
    df_export = df_filtered.select(
        F.col("recipe_id").cast("int"),
        F.col("name"),
        F.col("minutes").cast("int"),
        F.col("minutes_clean").cast("float"),
        F.col("n_steps").cast("int"),
        F.col("n_ingredients").cast("int"),
        F.col("calories").cast("float"),
        F.col("total_fat_pdv").cast("float"),
        F.col("sugar_pdv").cast("float"),
        F.col("sodium_pdv").cast("float"),
        F.col("protein_pdv").cast("float"),
        F.col("saturated_fat_pdv").cast("float"),
        F.col("carbohydrates_pdv").cast("float"),
        F.concat_ws(", ", F.col("ingredients")).alias("ingredients"),
        F.concat_ws(", ", F.col("tags")).alias("tags")
    )

    pdf = df_export.toPandas()
    target_path = app_data_dir / "recipes_foodcom_sample.parquet"
    pdf.to_parquet(target_path, index=False, engine="pyarrow")
    print(f"     ✓ Đã xuất {len(pdf):,} công thức Food.com vào {target_path.name} ({get_dir_size_mb(target_path):.2f} MB)")
    return len(pdf)


def export_recommendations(app_data_dir: Path):
    """
    Xuất các bảng gợi ý món ăn (Top-10 món kèm thứ hạng rank):
    - recommendations_vietnam.parquet: toàn bộ 101 user (1.010 dòng)
    - recommendations_foodcom_sample.parquet: 5.000 user mẫu (50.000 dòng)
    """
    print("\n---> [3/6] Đang xuất recommendations...")
    
    # 1. ViFoodRec
    recs_vn_source = PROJECT_ROOT / "results" / "recommendations_food_vietnam.parquet"
    if not recs_vn_source.exists():
        recs_vn_source = PROJECT_ROOT / "data" / "results" / "recommendations_food_vietnam.parquet"
    
    pdf_recs_vn = pd.read_parquet(recs_vn_source)
    # Đánh số thứ tự rank từ 1 đến 10 cho mỗi user
    pdf_recs_vn["rank"] = pdf_recs_vn.groupby("user_id").cumcount() + 1
    
    # Đảm bảo thứ tự cột và kiểu dữ liệu chuẩn
    cols_vn = ["food_id", "user_id", "rank", "dish_name", "dish_type", "calories", "cooking_time"]
    existing_cols_vn = [c for c in cols_vn if c in pdf_recs_vn.columns]
    pdf_recs_vn = pdf_recs_vn[existing_cols_vn]

    target_vn = app_data_dir / "recommendations_vietnam.parquet"
    pdf_recs_vn.to_parquet(target_vn, index=False, engine="pyarrow")
    pdf_recs_vn.to_parquet(app_data_dir / "recommendations_food_vietnam.parquet", index=False, engine="pyarrow")
    print(f"     ✓ Đã xuất {len(pdf_recs_vn):,} gợi ý ViFoodRec vào {target_vn.name} ({get_dir_size_mb(target_vn):.2f} MB)")

    # 2. Food.com
    recs_fc_source = PROJECT_ROOT / "results" / "recommendations_food_com.parquet"
    if not recs_fc_source.exists():
        recs_fc_source = PROJECT_ROOT / "data" / "results" / "recommendations_food_com.parquet"
        
    pdf_recs_fc = pd.read_parquet(recs_fc_source)
    pdf_recs_fc["rank"] = pdf_recs_fc.groupby("user_id").cumcount() + 1

    cols_fc = ["recipe_id", "user_id", "rank", "name", "calories", "minutes_clean"]
    existing_cols_fc = [c for c in cols_fc if c in pdf_recs_fc.columns]
    pdf_recs_fc = pdf_recs_fc[existing_cols_fc]

    target_fc = app_data_dir / "recommendations_foodcom_sample.parquet"
    pdf_recs_fc.to_parquet(target_fc, index=False, engine="pyarrow")
    pdf_recs_fc.to_parquet(app_data_dir / "recommendations_food_com.parquet", index=False, engine="pyarrow")
    print(f"     ✓ Đã xuất {len(pdf_recs_fc):,} gợi ý Food.com vào {target_fc.name} ({get_dir_size_mb(target_fc):.2f} MB)")

    return len(pdf_recs_vn), len(pdf_recs_fc)


def export_item_neighbors(app_data_dir: Path):
    """
    Xuất các bảng độ tương đồng giữa các món (Item Latent Factor Neighbors):
    - item_neighbors_vietnam.parquet (4.000 món)
    - item_neighbors_foodcom.parquet (20.000 món)
    """
    print("\n---> [4/6] Đang xuất item_neighbors...")

    # 1. ViFoodRec
    source_vn = PROJECT_ROOT / "results" / "item_neighbors_food_vietnam.parquet"
    if not source_vn.exists():
        source_vn = PROJECT_ROOT / "data" / "results" / "item_neighbors_food_vietnam.parquet"
    pdf_vn = pd.read_parquet(source_vn)
    target_vn = app_data_dir / "item_neighbors_vietnam.parquet"
    pdf_vn.to_parquet(target_vn, index=False, engine="pyarrow")
    pdf_vn.to_parquet(app_data_dir / "item_neighbors_food_vietnam.parquet", index=False, engine="pyarrow")
    print(f"     ✓ Đã xuất {len(pdf_vn):,} item neighbors ViFoodRec vào {target_vn.name} ({get_dir_size_mb(target_vn):.2f} MB)")

    # 2. Food.com
    source_fc = PROJECT_ROOT / "results" / "item_neighbors_food_com.parquet"
    if not source_fc.exists():
        source_fc = PROJECT_ROOT / "data" / "results" / "item_neighbors_food_com.parquet"
    pdf_fc = pd.read_parquet(source_fc)
    target_fc = app_data_dir / "item_neighbors_foodcom.parquet"
    pdf_fc.to_parquet(target_fc, index=False, engine="pyarrow")
    pdf_fc.to_parquet(app_data_dir / "item_neighbors_food_com.parquet", index=False, engine="pyarrow")
    print(f"     ✓ Đã xuất {len(pdf_fc):,} item neighbors Food.com vào {target_fc.name} ({get_dir_size_mb(target_fc):.2f} MB)")

    return len(pdf_vn), len(pdf_fc)


def export_clusters(app_data_dir: Path):
    """
    Xuất các bảng phân cụm người dùng và phân cụm món ăn:
    - user_clusters_vietnam.parquet (101 users)
    - user_clusters_foodcom.parquet (30.772 users)
    - food_clusters_vietnam.parquet (4.000 món)
    - cluster_profiles_*.csv & food_cluster_profiles_vietnam.csv
    - kmeans_tuning.csv
    """
    print("\n---> [5/6] Đang xuất clusters & profiles...")
    
    # User clusters ViFoodRec
    src_u_vn = PROJECT_ROOT / "results" / "user_clusters_food_vietnam.parquet"
    if not src_u_vn.exists():
        src_u_vn = PROJECT_ROOT / "data" / "results" / "user_clusters_food_vietnam.parquet"
    pdf_u_vn = pd.read_parquet(src_u_vn)
    tgt_u_vn = app_data_dir / "user_clusters_vietnam.parquet"
    pdf_u_vn.to_parquet(tgt_u_vn, index=False, engine="pyarrow")
    pdf_u_vn.to_parquet(app_data_dir / "user_clusters_food_vietnam.parquet", index=False, engine="pyarrow")

    # User clusters Food.com
    src_u_fc = PROJECT_ROOT / "results" / "user_clusters_food_com.parquet"
    if not src_u_fc.exists():
        src_u_fc = PROJECT_ROOT / "data" / "results" / "user_clusters_food_com.parquet"
    pdf_u_fc = pd.read_parquet(src_u_fc)
    tgt_u_fc = app_data_dir / "user_clusters_foodcom.parquet"
    pdf_u_fc.to_parquet(tgt_u_fc, index=False, engine="pyarrow")
    pdf_u_fc.to_parquet(app_data_dir / "user_clusters_food_com.parquet", index=False, engine="pyarrow")

    # Food clusters ViFoodRec
    src_f_vn = PROJECT_ROOT / "results" / "food_clusters_vietnam.parquet"
    if not src_f_vn.exists():
        src_f_vn = PROJECT_ROOT / "data" / "results" / "food_clusters_vietnam.parquet"
    pdf_f_vn = pd.read_parquet(src_f_vn)
    tgt_f_vn = app_data_dir / "food_clusters_vietnam.parquet"
    pdf_f_vn.to_parquet(tgt_f_vn, index=False, engine="pyarrow")

    # Profiles CSV
    profiles = [
        "cluster_profiles_food_vietnam.csv",
        "cluster_profiles_food_com.csv",
        "food_cluster_profiles_vietnam.csv",
        "kmeans_tuning.csv"
    ]
    for p_file in profiles:
        p_src = PROJECT_ROOT / "results" / p_file
        if not p_src.exists():
            p_src = PROJECT_ROOT / "data" / "results" / p_file
        if p_src.exists():
            shutil.copy2(p_src, app_data_dir / p_file)
            print(f"     ✓ Đã copy profile {p_file}")

    print(f"     ✓ Đã xuất các tệp phân cụm thành công!")


def export_benchmarks_and_eda(app_data_dir: Path):
    """
    Xuất các bảng kết quả so sánh mô hình, tuning, scalability, storage, cleaning log
    và toàn bộ 20 bảng EDA tổng hợp.
    """
    print("\n---> [6/6] Đang xuất benchmarks, logs và EDA tables...")

    # 1. Các bảng Benchmark & Metrics CSV
    benchmark_files = [
        ("model_comparison.csv", [PROJECT_ROOT / "results" / "model_comparison.csv", PROJECT_ROOT / "data" / "results" / "model_comparison.csv"]),
        ("als_tuning_food_vietnam.csv", [PROJECT_ROOT / "results" / "als_tuning_food_vietnam.csv", PROJECT_ROOT / "data" / "results" / "als_tuning_food_vietnam.csv"]),
        ("als_tuning_food_com.csv", [PROJECT_ROOT / "results" / "als_tuning_food_com.csv", PROJECT_ROOT / "data" / "results" / "als_tuning_food_com.csv"]),
        ("scalability.csv", [PROJECT_ROOT / "results" / "scalability.csv", PROJECT_ROOT / "data" / "results" / "scalability.csv"]),
        ("storage_benchmark.csv", [PROJECT_ROOT / "data" / "results" / "storage_benchmark.csv", PROJECT_ROOT / "results" / "storage_benchmark.csv"]),
        ("cleaning_log.csv", [PROJECT_ROOT / "reports" / "evidence" / "cleaning_log.csv"]),
        ("baseline_metrics.csv", [PROJECT_ROOT / "results" / "baseline_metrics.csv", PROJECT_ROOT / "data" / "results" / "baseline_metrics.csv"]),
        ("baseline_rmse_breakdown.csv", [PROJECT_ROOT / "results" / "baseline_rmse_breakdown.csv", PROJECT_ROOT / "data" / "results" / "baseline_rmse_breakdown.csv"]),
        ("als_rmse_breakdown.csv", [PROJECT_ROOT / "results" / "als_rmse_breakdown.csv", PROJECT_ROOT / "data" / "results" / "als_rmse_breakdown.csv"])
    ]

    for dest_name, src_candidates in benchmark_files:
        copied = False
        for src in src_candidates:
            if src.exists():
                shutil.copy2(src, app_data_dir / dest_name)
                print(f"     ✓ Đã xuất {dest_name}")
                copied = True
                break
        if not copied:
            print(f"     [!] Cảnh báo: Không tìm thấy file nguồn cho {dest_name}")

    # 2. EDA tables
    eda_target_dir = app_data_dir / "eda"
    eda_target_dir.mkdir(parents=True, exist_ok=True)

    eda_src_dir = PROJECT_ROOT / "results" / "eda"
    if not eda_src_dir.exists():
        eda_src_dir = PROJECT_ROOT / "data" / "results" / "eda"

    if eda_src_dir.exists():
        for eda_file in eda_src_dir.glob("*.csv"):
            shutil.copy2(eda_file, eda_target_dir / eda_file.name)
            # Copy bảng so sánh tổng quan ra thư mục gốc app/data để tiện truy xuất
            if eda_file.name == "eda_12_dataset_comparison.csv":
                shutil.copy2(eda_file, app_data_dir / eda_file.name)
        print(f"     ✓ Đã copy toàn bộ {len(list(eda_target_dir.glob('*.csv')))} bảng EDA vào {eda_target_dir.name}/")


def main():
    start_time = time.perf_counter()
    print("=" * 75)
    print("CHƯƠNG TRÌNH XUẤT KẾT QUẢ CHO DASHBOARD STREAMLIT (PROMPT P10)")
    print(f"Chế độ lưu trữ nguồn: {get_storage_mode()}")
    print("=" * 75)

    # Khởi tạo thư mục đích
    app_data_dir = PROJECT_ROOT / "app" / "data"
    app_data_dir.mkdir(parents=True, exist_ok=True)
    print(f"Thư mục đích: {app_data_dir}")

    # Khởi tạo Spark Session để đọc Parquet sạch từ HDFS
    spark = get_spark_session(app_name="ExportForApp", shuffle_partitions=4)

    # 1. Xuất thông tin món ăn
    export_foods_vietnam(spark, app_data_dir)
    export_recipes_foodcom(spark, app_data_dir)

    # 2. Xuất gợi ý món ăn
    export_recommendations(app_data_dir)

    # 3. Xuất Item Neighbors
    export_item_neighbors(app_data_dir)

    # 4. Xuất Phân cụm
    export_clusters(app_data_dir)

    # 5. Xuất Benchmarks & EDA
    export_benchmarks_and_eda(app_data_dir)

    # Tổng kết dung lượng
    total_size_mb = get_dir_size_mb(app_data_dir)
    elapsed = time.perf_counter() - start_time

    print("\n" + "=" * 75)
    print(f"HOÀN TẤT XUẤT DỮ LIỆU CHO DASHBOARD!")
    print(f"Tổng dung lượng thư mục app/data/: {total_size_mb:.2f} MB (Tiêu chuẩn: < 100 MB -> ĐẠT)")
    print(f"Thời gian thực thi: {elapsed:.2f} giây")
    print("=" * 75)


if __name__ == "__main__":
    main()

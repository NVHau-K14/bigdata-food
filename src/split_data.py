"""
src/split_data.py
-----------------
Thực hiện chia dữ liệu Train (80%), Validation (10%), Test (10%) với seed=42
cho cả hai bộ dữ liệu Food.com và ViFoodRec trên cụm Apache Spark HDFS.

Quy tắc thực hiện (P6):
1. Phân chia ngẫu nhiên có tính xác định (deterministic seed=42).
2. Lọc bỏ Cold-Start trên tập validation và test: loại bỏ các dòng có user_id
   hoặc recipe_id/food_id KHÔNG xuất hiện trong tập train.
3. Kiểm tra rò rỉ dữ liệu (Data Leakage Verification): kiểm tra giao cặp (user, item)
   giữa train/val/test phải bằng 0.
4. Ghi kết quả dạng Parquet vào /data/splits/<bộ>/ và xuất nhật ký split_log.csv.
"""

import os
import sys
import time
from pathlib import Path
import pandas as pd
from pyspark.sql import functions as F

# Đảm bảo import được config từ thư mục src
sys.path.append(str(Path(__file__).resolve().parent))
from config import get_spark_session, get_path, get_storage_mode, PROJECT_ROOT


def split_and_filter_dataset(spark, dataset_name, input_path, item_col, output_dir_stage):
    """
    Chia dữ liệu và lọc cold-start cho một bộ dữ liệu cụ thể.
    """
    print(f"\n=======================================================")
    print(f"BẮT ĐẦU CHIA DỮ LIỆU: {dataset_name.upper()}")
    print(f"Đường dẫn đầu vào: {input_path}")
    print(f"Cột item: {item_col}")
    print(f"=======================================================")

    start_time = time.time()
    
    # 1. Đọc dữ liệu sạch
    df = spark.read.parquet(input_path)
    total_raw_count = df.count()
    print(f"-> Tổng số tương tác đầu vào: {total_raw_count:,} dòng")

    # 2. Phân chia ngẫu nhiên xác định với rand(seed=42)
    # [0.0, 0.8) -> Train (80%), [0.8, 0.9) -> Val (10%), [0.9, 1.0] -> Test (10%)
    df_rand = df.withColumn("_split_rand", F.rand(seed=42))
    
    train_df = df_rand.filter(F.col("_split_rand") < 0.8).drop("_split_rand").cache()
    val_raw = df_rand.filter((F.col("_split_rand") >= 0.8) & (F.col("_split_rand") < 0.9)).drop("_split_rand").cache()
    test_raw = df_rand.filter(F.col("_split_rand") >= 0.9).drop("_split_rand").cache()

    train_count = train_df.count()
    val_raw_count = val_raw.count()
    test_raw_count = test_raw.count()

    print(f"-> Phân chia ban đầu: Train={train_count:,} ({train_count/total_raw_count:.2%}), "
          f"Val={val_raw_count:,} ({val_raw_count/total_raw_count:.2%}), "
          f"Test={test_raw_count:,} ({test_raw_count/total_raw_count:.2%})")

    # 3. Trích xuất danh sách user và item phân biệt có trong Train
    train_users = train_df.select("user_id").distinct()
    train_items = train_df.select(item_col).distinct()
    n_train_users = train_users.count()
    n_train_items = train_items.count()
    print(f"-> Tập Train có {n_train_users:,} users và {n_train_items:,} items")

    # 4. Lọc Cold-Start trên Validation và Test
    val_filtered = val_raw.join(train_users, on="user_id", how="inner") \
                          .join(train_items, on=item_col, how="inner").cache()
    test_filtered = test_raw.join(train_users, on="user_id", how="inner") \
                            .join(train_items, on=item_col, how="inner").cache()

    val_clean_count = val_filtered.count()
    test_clean_count = test_filtered.count()

    val_dropped = val_raw_count - val_clean_count
    val_drop_pct = (val_dropped / val_raw_count) * 100 if val_raw_count > 0 else 0.0

    test_dropped = test_raw_count - test_clean_count
    test_drop_pct = (test_dropped / test_raw_count) * 100 if test_raw_count > 0 else 0.0

    print(f"-> Lọc Cold-Start Validation: Giữ {val_clean_count:,} dòng (loại {val_dropped:,} dòng, {val_drop_pct:.2f}%)")
    print(f"-> Lọc Cold-Start Test:       Giữ {test_clean_count:,} dòng (loại {test_dropped:,} dòng, {test_drop_pct:.2f}%)")

    # 5. Kiểm tra rò rỉ dữ liệu (Data Leakage Verification)
    print("-> Đang kiểm tra rò rỉ dữ liệu giữa các tập...")
    leak_train_val = train_df.join(val_filtered, on=["user_id", item_col], how="inner").count()
    leak_train_test = train_df.join(test_filtered, on=["user_id", item_col], how="inner").count()
    leak_val_test = val_filtered.join(test_filtered, on=["user_id", item_col], how="inner").count()

    print(f"   + Cặp (user, item) trùng Train & Val:  {leak_train_val} (Kỳ vọng = 0)")
    print(f"   + Cặp (user, item) trùng Train & Test: {leak_train_test} (Kỳ vọng = 0)")
    print(f"   + Cặp (user, item) trùng Val & Test:   {leak_val_test} (Kỳ vọng = 0)")

    assert leak_train_val == 0, f"LỖI RÒ RỈ: Có {leak_train_val} cặp trùng giữa Train và Val!"
    assert leak_train_test == 0, f"LỖI RÒ RỈ: Có {leak_train_test} cặp trùng giữa Train và Test!"
    assert leak_val_test == 0, f"LỖI RÒ RỈ: Có {leak_val_test} cặp trùng giữa Val và Test!"
    print("   => XÁC NHẬN: Không có bất kỳ sự rò rỉ dữ liệu nào giữa các tập!")

    # 6. Ghi dữ liệu ra Parquet
    train_out_path = get_path("splits", dataset_name, "train.parquet")
    val_out_path = get_path("splits", dataset_name, "validation.parquet")
    test_out_path = get_path("splits", dataset_name, "test.parquet")

    print(f"-> Đang lưu dữ liệu ra Parquet...")
    print(f"   + Train: {train_out_path}")
    print(f"   + Val:   {val_out_path}")
    print(f"   + Test:  {test_out_path}")

    if dataset_name == "food_vietnam":
        train_df.coalesce(1).write.mode("overwrite").parquet(train_out_path)
        val_filtered.coalesce(1).write.mode("overwrite").parquet(val_out_path)
        test_filtered.coalesce(1).write.mode("overwrite").parquet(test_out_path)
    else:
        train_df.write.mode("overwrite").parquet(train_out_path)
        val_filtered.write.mode("overwrite").parquet(val_out_path)
        test_filtered.write.mode("overwrite").parquet(test_out_path)

    elapsed = time.time() - start_time
    print(f"-> Hoàn tất {dataset_name} trong {elapsed:.2f}s!")

    return {
        "dataset": dataset_name,
        "total_clean": total_raw_count,
        "train_rows": train_count,
        "train_pct": train_count / total_raw_count * 100,
        "val_raw_rows": val_raw_count,
        "val_clean_rows": val_clean_count,
        "val_dropped_rows": val_dropped,
        "val_drop_pct": val_drop_pct,
        "test_raw_rows": test_raw_count,
        "test_clean_rows": test_clean_count,
        "test_dropped_rows": test_dropped,
        "test_drop_pct": test_drop_pct,
        "leak_train_val": leak_train_val,
        "leak_train_test": leak_train_test,
        "leak_val_test": leak_val_test,
        "n_train_users": n_train_users,
        "n_train_items": n_train_items,
        "time_seconds": elapsed
    }


def main():
    print("=" * 70)
    print("CHƯƠNG TRÌNH PHÂN CHIA DỮ LIỆU TRAIN / VAL / TEST (P6)")
    print(f"Chế độ lưu trữ: {get_storage_mode()}")
    print("=" * 70)

    spark = get_spark_session(app_name="DataSplittingPipeline", shuffle_partitions=8)

    results = []

    # 1. Thực hiện cho Food.com
    food_com_input = get_path("clean", "food_com", "interactions_clean.parquet")
    res_food_com = split_and_filter_dataset(
        spark=spark,
        dataset_name="food_com",
        input_path=food_com_input,
        item_col="recipe_id",
        output_dir_stage="splits"
    )
    results.append(res_food_com)

    # 2. Thực hiện cho ViFoodRec
    vifood_input = get_path("clean", "food_vietnam", "ratings_clean.parquet")
    res_vifood = split_and_filter_dataset(
        spark=spark,
        dataset_name="food_vietnam",
        input_path=vifood_input,
        item_col="food_id",
        output_dir_stage="splits"
    )
    results.append(res_vifood)

    # 3. Xuất bảng tổng hợp split_log.csv
    log_df = pd.DataFrame(results)
    
    out_csv_results = PROJECT_ROOT / "data" / "results" / "split_log.csv"
    out_csv_reports = PROJECT_ROOT / "reports" / "evidence" / "split_log.csv"
    out_csv_results.parent.mkdir(parents=True, exist_ok=True)
    out_csv_reports.parent.mkdir(parents=True, exist_ok=True)

    log_df.to_csv(out_csv_results, index=False)
    log_df.to_csv(out_csv_reports, index=False)

    print("\n" + "=" * 70)
    print("BẢNG TỔNG HỢP NHẬT KÝ PHÂN CHIA DỮ LIỆU (SPLIT LOG)")
    print("=" * 70)
    print(log_df.to_string(index=False))
    print(f"\n-> Đã lưu bảng log tại:")
    print(f"   + {out_csv_results}")
    print(f"   + {out_csv_reports}")

    spark.stop()
    print("\n[THÀNH CÔNG] Hoàn tất toàn bộ quy trình phân chia dữ liệu!")


if __name__ == "__main__":
    main()

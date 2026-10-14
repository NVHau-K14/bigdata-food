"""
src/run_pipeline_p3.py
----------------------
Thực thi toàn bộ pipeline làm sạch P3 cho cả hai bộ dữ liệu (Food.com & ViFoodRec):
1. Khởi tạo SparkSession dùng chung.
2. Gọi clean_food_com() và clean_vietnam().
3. Tổng hợp danh sách nhật ký các bước thành DataFrame.
4. Ghi CSV tại reports/evidence/cleaning_log.csv.
5. Ghi Parquet tại data/results/cleaning_log.parquet (theo STORAGE_MODE).

Tham số --only vietnam: chỉ chạy lại ViFoodRec, giữ nguyên Parquet sạch của Food.com
(ghi lại sẽ đổi thứ tự dòng và làm đổi cách chia train/validation/test theo seed). Các dòng
Food.com trong nhật ký được lấy từ cleaning_log.csv hiện có.
"""

import argparse
import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
from pyspark.sql.types import (
    StructType, StructField, StringType, LongType
)
from src.config import get_spark_session, get_path
from src.clean_food_com import clean_food_com
from src.clean_vietnam import clean_vietnam


def run_full_cleaning_pipeline(only=None):
    start_time = time.time()
    spark = get_spark_session("RunPipelineP3")
    
    print("\n" + "=" * 80)
    print("   BẮT ĐẦU CHẠY PIPELINE LÀM SẠCH TOÀN DIỆN P3")
    print("=" * 80)
    
    evidence_dir = ROOT_DIR / "reports" / "evidence"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    csv_log_path = evidence_dir / "cleaning_log.csv"
    
    # 1. Chạy Food.com (hoặc lấy lại nhật ký đã có nếu chỉ chạy ViFoodRec)
    if only == "vietnam":
        old_log = pd.read_csv(csv_log_path)
        food_com_logs = old_log[old_log["dataset"].str.startswith("food_com")].to_dict("records")
        print(f"\n[Bỏ qua Food.com] Giữ {len(food_com_logs)} dòng nhật ký từ {csv_log_path}")
    else:
        food_com_logs = clean_food_com(spark)
    
    # 2. Chạy ViFoodRec
    vifood_logs = clean_vietnam(spark)
    
    all_logs = food_com_logs + vifood_logs
    
    # 3. Ghi cleaning_log.csv vào reports/evidence/
    
    df_pandas = pd.DataFrame(all_logs)
    df_pandas.to_csv(csv_log_path, index=False, encoding="utf-8-sig")
    print(f"\n[F] Đã ghi nhật ký làm sạch CSV: {csv_log_path}")
    print(df_pandas[["dataset", "step_name", "rows_before", "rows_after", "rows_dropped"]])
    
    # 4. Ghi Parquet vào results
    parquet_log_path = get_path("results", "", "cleaning_log.parquet")
    log_schema = StructType([
        StructField("dataset", StringType(), False),
        StructField("step_name", StringType(), False),
        StructField("rows_before", LongType(), False),
        StructField("rows_after", LongType(), False),
        StructField("rows_dropped", LongType(), False),
        StructField("notes", StringType(), True)
    ])
    
    df_spark_log = spark.createDataFrame(all_logs, schema=log_schema)
    df_spark_log.coalesce(1).write.mode("overwrite").parquet(parquet_log_path)
    print(f"[G] Đã ghi nhật ký làm sạch Parquet: {parquet_log_path}")
    
    total_time = time.time() - start_time
    print("\n" + "=" * 80)
    print(f"   HOÀN TẤT TOÀN BỘ PIPELINE P3 TRONG {total_time:.2f} GIÂY")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", choices=["vietnam"], default=None,
                        help="Chỉ chạy lại ViFoodRec, giữ nguyên Food.com")
    args = parser.parse_args()
    run_full_cleaning_pipeline(only=args.only)

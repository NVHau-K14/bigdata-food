"""
src/smoke_test_cluster.py
--------------------------
Kịch bản kiểm thử khói (Smoke Test) cho cụm HDFS + Spark Cluster:
1. Kết nối tới Spark Master (spark://spark-master:7077).
2. Kiểm tra thông tin cluster: số executor hoạt động, Master URL.
3. Đọc dữ liệu CSV từ HDFS: hdfs://namenode:9000/data/raw/food_com/RAW_interactions.csv.
4. Đếm số dòng và đối chiếu với con số chuẩn đã biết (1,132,367 dòng).
5. Lấy mẫu 1,000 dòng ghi ra HDFS Parquet: hdfs://namenode:9000/data/clean/smoke_test.parquet.
6. Đọc lại file Parquet từ HDFS và kiểm tra số dòng khớp 1,000.
7. Xóa file kiểm thử tạm (hoặc giữ lại để verify) và xuất kết luận SMOKE TEST PASSED.
"""

import sys
import time
from pathlib import Path

# Đảm bảo thư mục gốc dự án luôn nằm trong sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pyspark.sql.types import StructType, StructField, IntegerType, FloatType, StringType
from src.config import get_spark_session, get_path, get_storage_mode

EXPECTED_ROW_COUNT = 1132367
SAMPLE_SIZE = 1000

def run_smoke_test():
    print("=" * 70)
    print("   BẮT ĐẦU SMOKE TEST CỤM HDFS + SPARK (P2)")
    print("=" * 70)
    
    start_time = time.time()
    
    # 1. Khởi tạo Spark Session
    print(f"\n[1/5] Khởi tạo SparkSession (Chế độ lưu trữ: {get_storage_mode()})...")
    spark = get_spark_session(app_name="SmokeTestCluster_P2")
    sc = spark.sparkContext
    
    print(f"  - Spark Version : {spark.version}")
    print(f"  - Master URL    : {sc.master}")
    print(f"  - Application ID: {sc.applicationId}")
    print(f"  - Default Parallelism: {sc.defaultParallelism}")
    
    # Kiểm tra số executor
    # Chờ một chút để các executor đăng ký hoàn tất
    time.sleep(3)
    status_tracker = sc.statusTracker()
    executor_ids = status_tracker.getExecutorInfos()
    print(f"  - Số Executor (gồm driver): {len(executor_ids)}")
    for info in executor_ids:
        host = getattr(info, "host", "")
        port = getattr(info, "port", "")
        cores = getattr(info, "totalCores", "")
        print(f"    * Host: {host}, Port: {port}, Cores: {cores}")

    # 2. Đọc file CSV từ HDFS
    raw_path = get_path("raw", "food_com", "RAW_interactions.csv")
    print(f"\n[2/5] Đọc dữ liệu thô từ HDFS: {raw_path}")
    schema = StructType([
        StructField("user_id", IntegerType(), True),
        StructField("recipe_id", IntegerType(), True),
        StructField("date", StringType(), True),
        StructField("rating", FloatType(), True),
        StructField("review", StringType(), True)
    ])
    
    df_raw = spark.read.option("header", "true") \
                       .option("multiLine", "true") \
                       .option("escape", "\"") \
                       .schema(schema) \
                       .csv(raw_path)
                       
    # 3. Đếm số dòng
    print("\n[3/5] Thực thi Action đếm dòng trên toàn bộ cụm Spark Worker...")
    count_actual = df_raw.count()
    print(f"  - Số dòng đọc được thực tế: {count_actual:,}")
    print(f"  - Số dòng kỳ vọng (P1 audit): {EXPECTED_ROW_COUNT:,}")
    
    if count_actual != EXPECTED_ROW_COUNT:
        print(f"  [CẢNH BÁO / LỖI]: Số dòng không khớp kỳ vọng ({count_actual} != {EXPECTED_ROW_COUNT})!")
        sys.exit(1)
    else:
        print("  -> ĐỐI CHIẾU THÀNH CÔNG: Số dòng khớp chính xác 100%!")
        
    # 4. Ghi mẫu Parquet ra HDFS
    clean_sample_path = get_path("clean", "", "smoke_test.parquet")
    print(f"\n[4/5] Trích mẫu {SAMPLE_SIZE} dòng và ghi Parquet vào HDFS: {clean_sample_path}")
    df_sample = df_raw.limit(SAMPLE_SIZE)
    df_sample.write.mode("overwrite").parquet(clean_sample_path)
    print("  -> Ghi Parquet vào HDFS thành công!")
    
    # 5. Đọc lại từ Parquet và kiểm chứng
    print(f"\n[5/5] Đọc lại Parquet từ HDFS và kiểm tra số dòng...")
    df_verify = spark.read.parquet(clean_sample_path)
    verify_count = df_verify.count()
    print(f"  - Số dòng đọc lại từ Parquet: {verify_count}")
    
    if verify_count != SAMPLE_SIZE:
        print(f"  [LỖI]: Mẫu Parquet không khớp ({verify_count} != {SAMPLE_SIZE})!")
        sys.exit(1)
    else:
        print("  -> ĐỐI CHIẾU PARQUET THÀNH CÔNG: Số dòng đọc lại khớp 1,000 dòng!")
        
    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"   KẾT QUẢ: TOÀN BỘ SMOKE TEST P2 ĐẠT CHUẨN (Thời gian: {elapsed:.2f}s)")
    print("=" * 70)
    
    spark.stop()

if __name__ == "__main__":
    run_smoke_test()

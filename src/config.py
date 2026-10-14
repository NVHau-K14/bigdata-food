"""
src/config.py
-------------
Quản lý cấu hình tập trung cho toàn bộ pipeline Big Data.
Hỗ trợ đa chế độ lưu trữ: STORAGE_MODE = 'hdfs' | 'local'.
Cung cấp đường dẫn chuẩn hóa và hàm khởi tạo SparkSession đồng nhất.
"""

import os
from pathlib import Path
from pyspark.sql import SparkSession

# Chế độ lưu trữ mặc định: 'hdfs' hoặc 'local'
STORAGE_MODE = os.environ.get("STORAGE_MODE", "hdfs").lower()

# Địa chỉ cụm HDFS và Spark Master
HDFS_NAMENODE_URL = os.environ.get("HDFS_NAMENODE_URL", "hdfs://namenode:9000")
SPARK_MASTER_URL = os.environ.get("SPARK_MASTER_URL", "spark://spark-master:7077")

# Thư mục gốc trên HDFS, mặc định rỗng (đường dẫn dạng hdfs://namenode:9000/data/...). Đặt, ví dụ, HDFS_ROOT=/cleanrun
# để mọi đường dẫn nằm dưới /cleanrun/data/... khi chạy thử trên bản sao mà không đụng dữ liệu của bản chính.
HDFS_ROOT = os.environ.get("HDFS_ROOT", "").rstrip("/")

# Hệ số nhân bản HDFS, phải khớp dfs.replication trong docker-compose.yml
HDFS_REPLICATION = int(os.environ.get("HDFS_REPLICATION", 2))

# Thư mục gốc local khi chạy chế độ local
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOCAL_DATA_DIR = PROJECT_ROOT / "data"

# Tham số tiền xử lý mặc định
K_CORE_DEFAULT = int(os.environ.get("K_CORE_THRESHOLD", 3))

# Ngưỡng cắt ngoại lai minutes cho Food.com recipes: 1440 phút (24 giờ) là giá trị chọn tay, KHÔNG phải phân vị.
# Phân vị đo được (stage_P1_audit.md mục 2.2): 99% = 750 phút, 99.9% = 2.147.483.647 phút.
MAX_MINUTES_THRESHOLD = 1440

# Thang điểm ViFoodRec: 11 mức từ 0.0 đến 5.0, bước 0.5 (trùng thang trong bài báo gốc).
# Giữ cả 0.0 và 0.5 vì số dòng mỗi mức ngang nhau, không có bằng chứng 0.0 là "chưa chấm".
RATING_MIN_VN = 0.0
RATING_MAX_VN = 5.0
RATING_STEP_VN = 0.5

# Hệ số làm trơn m cho mô hình Baseline Smoothed Item Mean (P6)
SMOOTHING_M = int(os.environ.get("SMOOTHING_M", 5))


def get_storage_mode() -> str:
    """Trả về chế độ lưu trữ hiện tại ('hdfs' hoặc 'local')."""
    return STORAGE_MODE


def get_path(stage: str, dataset: str = "", filename: str = "") -> str:
    """
    Trả về đường dẫn chuẩn hóa cho file hoặc thư mục theo STORAGE_MODE.
    
    Args:
        stage: 'raw', 'clean', 'splits', 'results', hoặc 'models'
        dataset: 'food_com', 'food_vietnam', hoặc rỗng
        filename: tên file cụ thể (tùy chọn)
        
    Returns:
        Đường dẫn dạng hdfs://namenode:9000/... (nếu hdfs) hoặc path/to/file (nếu local)
    """
    stage = stage.strip("/").lower()
    dataset = dataset.strip("/")
    filename = filename.strip("/")
    
    # Xây dựng relative path
    sub_parts = []
    if stage in ["raw", "clean", "splits"]:
        sub_parts.append(f"data/{stage}")
        if dataset:
            sub_parts.append(dataset)
    elif stage == "results":
        sub_parts.append("data/results")
        if dataset:
            sub_parts.append(dataset)
    elif stage == "models":
        sub_parts.append("models")
        if dataset:
            sub_parts.append(dataset)
    else:
        sub_parts.append(stage)
        if dataset:
            sub_parts.append(dataset)
            
    if filename:
        sub_parts.append(filename)
        
    rel_path = "/".join(sub_parts)
    
    if STORAGE_MODE == "hdfs":
        return f"{HDFS_NAMENODE_URL}{HDFS_ROOT}/{rel_path}"
    else:
        return str(PROJECT_ROOT / rel_path)


def get_spark_session(
    app_name: str = "BigDataFoodPipeline",
    master: str = None,
    shuffle_partitions: int = 8,
    driver_memory: str = "2500m",
    executor_memory: str = "2g",
    executor_cores: int = 2
) -> SparkSession:
    """
    Khởi tạo hoặc lấy SparkSession cấu hình đồng nhất cho dự án.
    
    Args:
        app_name: Tên ứng dụng hiển thị trên Spark Web UI.
        master: URL master. Nếu None, tự động chọn theo STORAGE_MODE.
        shuffle_partitions: Số partition cho shuffle (mặc định 8, phù hợp cụm 4 cores).
        driver_memory: Bộ nhớ RAM cấp cho driver (tối đa 3GB theo quy định).
        executor_memory: Bộ nhớ RAM cấp cho mỗi executor.
        executor_cores: Số core cấp cho mỗi executor.
        
    Returns:
        SparkSession đã được cấu hình tối ưu.
    """
    if master is None:
        if STORAGE_MODE == "hdfs":
            master = SPARK_MASTER_URL
        else:
            master = "local[*]"
            
    builder = SparkSession.builder \
        .appName(app_name) \
        .master(master) \
        .config("spark.sql.ansi.enabled", "false") \
        .config("spark.sql.shuffle.partitions", str(shuffle_partitions)) \
        .config("spark.default.parallelism", str(shuffle_partitions)) \
        .config("spark.driver.memory", driver_memory) \
        .config("spark.executor.memory", executor_memory) \
        .config("spark.executor.cores", str(executor_cores)) \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .config("spark.sql.parquet.compression.codec", "snappy") \
        .config("spark.kryoserializer.buffer.max", "512m") \
        .config("spark.driver.maxResultSize", "1g")
        
    if STORAGE_MODE == "hdfs":
        # Client Spark không đọc hdfs-site.xml của cụm nên mặc định ghi với replication 3,
        # vượt số DataNode (2) và gây Under replicated blocks. Ép về 2 cho mọi file Spark ghi.
        builder = builder.config("spark.hadoop.fs.defaultFS", HDFS_NAMENODE_URL) \
            .config("spark.hadoop.dfs.replication", str(HDFS_REPLICATION))
        
    spark = builder.getOrCreate()
    
    # Đặt mức log giảm nhiễu
    spark.sparkContext.setLogLevel("WARN")
    
    return spark


if __name__ == "__main__":
    print(f"=== KIỂM TRA CẤU HÌNH CONFIG ===")
    print(f"STORAGE_MODE: {get_storage_mode()}")
    print(f"HDFS_NAMENODE_URL: {HDFS_NAMENODE_URL}")
    print(f"SPARK_MASTER_URL: {SPARK_MASTER_URL}")
    print(f"HDFS_ROOT: {HDFS_ROOT or '(rỗng)'}")
    print(f"Path raw food_com interactions: {get_path('raw', 'food_com', 'RAW_interactions.csv')}")
    print(f"Path clean food_com interactions: {get_path('clean', 'food_com', 'interactions_clean.parquet')}")
    print(f"Path models als_model: {get_path('models', 'food_com', 'als_best_model')}")

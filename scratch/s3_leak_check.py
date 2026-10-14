"""
scratch/s3_leak_check.py
Kiểm tra độc lập (truy vấn Spark SQL trên Parquet đã ghi ở HDFS) rằng không có rò rỉ giữa train, validation, test
của ViFoodRec, và số dòng khớp dữ liệu sạch. Không dùng lại mã trong split_data.py.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import get_spark_session, get_path

spark = get_spark_session("S3LeakCheck")
for name in ["train", "validation", "test"]:
    spark.read.parquet(get_path("splits", "food_vietnam", f"{name}.parquet")).createOrReplaceTempView(name)
spark.read.parquet(get_path("clean", "food_vietnam", "ratings_clean.parquet")).createOrReplaceTempView("clean")

q = lambda sql: spark.sql(sql).collect()[0][0]
print("Số dòng clean      :", q("SELECT COUNT(*) FROM clean"))
for name in ["train", "validation", "test"]:
    print(f"Số dòng {name:11s}:", q(f"SELECT COUNT(*) FROM {name}"),
          "| cặp phân biệt:", q(f"SELECT COUNT(*) FROM (SELECT DISTINCT user_id, food_id FROM {name})"))
print("Tổng train+validation+test:", q("SELECT (SELECT COUNT(*) FROM train)+(SELECT COUNT(*) FROM validation)+(SELECT COUNT(*) FROM test)"))
for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]:
    n = q(f"SELECT COUNT(*) FROM {a} x INNER JOIN {b} y ON x.user_id = y.user_id AND x.food_id = y.food_id")
    print(f"Giao cặp (user_id, food_id) {a} và {b}: {n}")
print("Số mức điểm phân biệt ở train:", q("SELECT COUNT(DISTINCT rating) FROM train"),
      "| ở validation:", q("SELECT COUNT(DISTINCT rating) FROM validation"), "| ở test:", q("SELECT COUNT(DISTINCT rating) FROM test"))
print("User và món ở test/validation không có trong train:",
      q("SELECT COUNT(*) FROM test WHERE user_id NOT IN (SELECT user_id FROM train) OR food_id NOT IN (SELECT food_id FROM train)"),
      q("SELECT COUNT(*) FROM validation WHERE user_id NOT IN (SELECT user_id FROM train) OR food_id NOT IN (SELECT food_id FROM train)"))
spark.stop()

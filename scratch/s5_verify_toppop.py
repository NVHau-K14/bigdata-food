"""
S5: kiểm chứng bằng truy vấn trên tập train ViFoodRec: có bao nhiêu món có điểm trung bình >= 4,0
(điều kiện của nhánh Top-N Popular trong baseline.py) và 14/1010 = P@10 của ALS.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import get_spark_session, get_path

spark = get_spark_session("S5VerifyTopPop")
df = spark.read.parquet(get_path("splits", "food_vietnam", "train.parquet"))
df.createOrReplaceTempView("train")
r = spark.sql("""SELECT COUNT(*) AS n_items, SUM(CASE WHEN m >= 4.0 THEN 1 ELSE 0 END) AS n_ge4, MAX(m) AS max_mean, MIN(m) AS min_mean
                 FROM (SELECT food_id, AVG(rating) AS m FROM train GROUP BY food_id)""").collect()[0]
print("Số món:", r["n_items"], "| món có điểm TB >= 4,0:", r["n_ge4"], "| điểm TB lớn nhất:", round(r["max_mean"], 4), "| nhỏ nhất:", round(r["min_mean"], 4))
spark.stop()

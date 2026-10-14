"""
scratch/s5_verify_mu.py
S5: kiểm chứng giá trị trung bình toàn cục (mu) của Global Mean bằng truy vấn trực tiếp trên tập train ở HDFS,
rồi đối chiếu với mu suy ra từ RMSE theo từng mức điểm trong baseline_rmse_breakdown.csv.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.config import get_spark_session, get_path

spark = get_spark_session("S5VerifyMu")
for ds, col in [("food_com", "rating"), ("food_vietnam", "rating")]:
    df = spark.read.parquet(get_path("splits", ds, "train.parquet"))
    r = df.selectExpr("COUNT(*) AS n", "AVG(rating) AS mu").collect()[0]
    print(f"{ds}: số dòng train = {r['n']}, mu (trung bình điểm tập train) = {r['mu']:.6f}")
spark.stop()

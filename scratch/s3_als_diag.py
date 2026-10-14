"""
scratch/s3_als_diag.py
Kiểm chứng nhanh vì sao 6 cấu hình ALS ViFoodRec có regParam = 0,5 cho cùng Validation RMSE 1,6576:
đo phân bố dự đoán của mô hình tốt nhất trên test và so với dự đoán hằng số.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from pyspark.sql import functions as F
from pyspark.ml.recommendation import ALSModel
from src.config import get_spark_session, get_path

spark = get_spark_session("S3AlsDiag")
model = ALSModel.load(get_path("models", "food_vietnam", "als_best_model"))
train = spark.read.parquet(get_path("splits", "food_vietnam", "train.parquet"))
test = spark.read.parquet(get_path("splits", "food_vietnam", "test.parquet"))
val = spark.read.parquet(get_path("splits", "food_vietnam", "validation.parquet"))
mu = train.agg(F.avg("rating")).collect()[0][0]
pred = model.transform(test)
s = pred.agg(F.avg("prediction"), F.stddev("prediction"), F.min("prediction"), F.max("prediction"),
             F.sqrt(F.avg(F.pow(F.col("rating") - F.col("prediction"), 2)))).collect()[0]
print(f"Global mean train           : {mu:.4f}")
print(f"Dự đoán ALS trên test       : mean={s[0]:.4f} std={s[1]:.4f} min={s[2]:.4f} max={s[3]:.4f}  RMSE={s[4]:.4f}")
for c in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5):
    r = test.agg(F.sqrt(F.avg(F.pow(F.col("rating") - F.lit(c), 2)))).collect()[0][0]
    print(f"RMSE nếu dự đoán hằng số {c:.1f}: {r:.4f}")
vr = val.agg(F.sqrt(F.avg(F.pow(F.col("rating") - F.lit(0.0), 2)))).collect()[0][0]
print(f"Validation RMSE nếu dự đoán hằng số 0.0: {vr:.4f}")
print("rank mô hình:", model.rank)
uf = model.userFactors.select(F.sqrt(F.expr("aggregate(features, 0D, (acc, x) -> acc + x*x)")).alias("n")).agg(F.avg("n"), F.max("n")).collect()[0]
itf = model.itemFactors.select(F.sqrt(F.expr("aggregate(features, 0D, (acc, x) -> acc + x*x)")).alias("n")).agg(F.avg("n"), F.max("n")).collect()[0]
print(f"Chuẩn vector user: TB={uf[0]:.4f} max={uf[1]:.4f} | item: TB={itf[0]:.4f} max={itf[1]:.4f}")
spark.stop()

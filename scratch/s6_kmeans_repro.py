"""
scratch/s6_kmeans_repro.py
--------------------------
Stage S6: kiểm chứng vì sao K-means Food.com của bản chạy sạch khác bản chính (silhouette, kích thước cụm).
Ba phép thử, chỉ ĐỌC dữ liệu, không ghi đè kết quả nào:
  A. Tập train Food.com của bản chính (/data) và bản sao (/cleanrun/data) có giống nhau theo tập hợp dòng không
     (exceptAll hai chiều, so cả user_id, recipe_id, rating, date).
  B. Bảng đặc trưng người dùng (extract_food_com_user_features) của hai bản có giống nhau không (nối theo user_id).
  C. Trên CÙNG một dữ liệu, chạy K-means k = 4, seed 42, maxIter 30 hai lần: kích thước cụm và chi phí có giống nhau không.
Chạy trong container client của bản sao: python scratch/s6_kmeans_repro.py
"""
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "src"))

from pyspark.sql import functions as F
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans

from config import get_spark_session
from user_features import extract_food_com_user_features

NN = "hdfs://namenode:9000"
MAIN = NN + "/data"
COPY = NN + "/cleanrun/data"

FEATURE_COLS = ["log_n_ratings", "avg_rating", "std_rating", "pct_high_rating",
                "log_avg_minutes", "log_avg_calories", "avg_n_ingredients", "log_activity_span"]


def features(spark, root):
    train = spark.read.parquet(f"{root}/splits/food_com/train.parquet")
    recipes = spark.read.parquet(f"{root}/clean/food_com/recipes_clean.parquet")
    return train, extract_food_com_user_features(spark, train, recipes)


def scaled(df):
    asm = VectorAssembler(inputCols=FEATURE_COLS, outputCol="raw_vec").transform(df)
    return StandardScaler(inputCol="raw_vec", outputCol="features", withMean=True, withStd=True).fit(asm).transform(asm)


def sizes(model, df):
    rows = model.transform(df).groupBy("prediction").count().orderBy("prediction").collect()
    return [r["count"] for r in rows]


def main():
    spark = get_spark_session(app_name="S6KMeansRepro")
    t_main, f_main = features(spark, MAIN)
    t_copy, f_copy = features(spark, COPY)

    print("=== A. Tập train Food.com: bản chính so với bản sao ===")
    print("số dòng bản chính:", t_main.count(), "| bản sao:", t_copy.count())
    print("dòng có ở bản chính mà không có ở bản sao:", t_main.exceptAll(t_copy).count())
    print("dòng có ở bản sao mà không có ở bản chính:", t_copy.exceptAll(t_main).count())

    print("\n=== B. Bảng đặc trưng người dùng: bản chính so với bản sao ===")
    j = f_main.alias("a").join(f_copy.alias("b"), "user_id", "full_outer")
    print("số người dùng bản chính:", f_main.count(), "| bản sao:", f_copy.count())
    print("người dùng chỉ có ở một bên:", j.filter(F.col("a.n_ratings").isNull() | F.col("b.n_ratings").isNull()).count())
    cols = [c for c in FEATURE_COLS + ["n_ratings", "activity_span_days"] if c in f_main.columns]
    both = f_main.alias("a").join(f_copy.alias("b"), "user_id", "inner")
    for c in cols:
        d = both.select(F.max(F.abs(F.col(f"a.{c}") - F.col(f"b.{c}"))).alias("d")).collect()[0]["d"]
        print(f"  lệch tối đa {c}: {d}")

    print("\n=== C. K-means k=4, seed 42, maxIter 30, chạy hai lần trên cùng dữ liệu ===")
    for label, f in [("bản chính", f_main), ("bản sao", f_copy)]:
        sc = scaled(f).cache()
        sc.count()
        for run in (1, 2):
            m = KMeans(featuresCol="features", k=4, seed=42, maxIter=30).fit(sc)
            print(f"  {label}, lần {run}: chi phí {m.summary.trainingCost:.4f}, kích thước cụm {sizes(m, sc)}")
        sc.unpersist()

    print("\n=== D. Sắp xếp theo user_id trước khi chạy (đối chứng thứ tự dòng) ===")
    for label, f in [("bản chính", f_main), ("bản sao", f_copy)]:
        sc = scaled(f.orderBy("user_id")).repartition(8).cache()
        sc.count()
        m = KMeans(featuresCol="features", k=4, seed=42, maxIter=30).fit(sc)
        print(f"  {label}: chi phí {m.summary.trainingCost:.4f}, kích thước cụm {sorted(sizes(m, sc))}")
        sc.unpersist()
    spark.stop()


if __name__ == "__main__":
    main()

import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.config import get_spark_session, get_path
from pyspark.sql.functions import col, expr

spark = get_spark_session("CheckRecipes")
raw_path = get_path("raw", "food_com", "RAW_recipes.csv")
print(f"Reading from: {raw_path}")
df = spark.read.option("header", "true") \
               .option("multiLine", "true") \
               .option("escape", "\"") \
               .csv(raw_path)

total = df.count()
print(f"Total RAW_recipes: {total}")

df = df.withColumn("minutes_int", col("minutes").cast("int")) \
       .withColumn("id_int", col("id").cast("int"))

null_min = df.filter(col("minutes_int").isNull()).count()
print(f"Null/Malformed minutes count: {null_min}")

if null_min > 0:
    print("Sample malformed rows:")
    df.filter(col("minutes_int").isNull()).select("name", "id", "minutes").show(5, truncate=False)

df_valid = df.filter(col("minutes_int").isNotNull())
print("Percentiles of minutes:")
df_valid.selectExpr("percentile_approx(minutes_int, array(0.01, 0.5, 0.9, 0.99, 0.999), 10000) as p").show(truncate=False)

print("Count minutes <= 0:", df_valid.filter(col("minutes_int") <= 0).count())
print("Count minutes > 1440 (24h):", df_valid.filter(col("minutes_int") > 1440).count())
print("Max minutes:", df_valid.agg({"minutes_int": "max"}).collect()[0][0])

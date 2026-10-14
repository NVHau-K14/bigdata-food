from pyspark.sql import SparkSession
from pyspark.sql.functions import col, expr
from pyspark.sql.types import StructType, StructField, IntegerType, FloatType, StringType

spark = SparkSession.builder \
    .appName("test_scan") \
    .config("spark.driver.memory", "4g") \
    .config("spark.sql.ansi.enabled", "false") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

print("--- Testing RAW_interactions.csv with multiLine=True ---")
df_inter = spark.read.csv(
    "data/raw/food_com/RAW_interactions.csv",
    header=True,
    multiLine=True,
    escape="\""
)
print("Total rows read with multiLine:", df_inter.count())
bad_inter = df_inter.filter(expr("try_cast(rating as double) is null and rating is not null"))
print("Bad rating count:", bad_inter.count())
if bad_inter.count() > 0:
    bad_inter.show(5, truncate=False)

print("\n--- Testing RAW_recipes.csv with multiLine=True ---")
df_rec = spark.read.csv(
    "data/raw/food_com/RAW_recipes.csv",
    header=True,
    multiLine=True,
    escape="\""
)
print("Total recipes read with multiLine:", df_rec.count())
bad_rec_id = df_rec.filter(expr("try_cast(id as integer) is null and id is not null"))
print("Bad recipe id count:", bad_rec_id.count())
if bad_rec_id.count() > 0:
    bad_rec_id.show(5, truncate=False)

spark.stop()

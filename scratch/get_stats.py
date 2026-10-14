import os
from pyspark.sql import SparkSession

spark = SparkSession.builder \
    .appName("stats") \
    .config("spark.driver.memory", "4g") \
    .config("spark.sql.ansi.enabled", "false") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

def stat(name, path, is_pq=False, multiline=True):
    if is_pq:
        df = spark.read.parquet(path)
    else:
        df = spark.read.csv(path, header=True, multiLine=multiline, escape="\"")
    cnt = df.count()
    cols = df.dtypes
    print(f"=== {name} ===")
    print(f"Path: {path}")
    print(f"Count: {cnt}")
    print("Columns & Types:")
    for c, t in cols:
        print(f"  - {c}: {t}")
    print()

stat("RAW Food.com Interactions", "data/raw/food_com/RAW_interactions.csv")
stat("RAW Food.com Recipes", "data/raw/food_com/RAW_recipes.csv")
stat("PROCESSED Food.com Interactions", "data/processed/food_com/interactions.parquet", is_pq=True)
stat("PROCESSED Food.com Recipes", "data/processed/food_com/recipes.parquet", is_pq=True)

stat("RAW Vietnam Ratings", "data/raw/food_vietnam/ratings.csv")
stat("RAW Vietnam Foods", "data/raw/food_vietnam/foods.csv")
stat("PROCESSED Vietnam Ratings", "data/processed/food_vietnam/ratings.parquet", is_pq=True)
stat("PROCESSED Vietnam Foods", "data/processed/food_vietnam/foods.parquet", is_pq=True)

spark.stop()

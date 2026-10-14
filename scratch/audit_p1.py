import sys
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, min as spark_min, max as spark_max

spark = SparkSession.builder \
    .appName("audit_p1") \
    .config("spark.driver.memory", "4g") \
    .config("spark.sql.ansi.enabled", "false") \
    .config("spark.sql.shuffle.partitions", "8") \
    .getOrCreate()
spark.sparkContext.setLogLevel("ERROR")

def p(text=""):
    print(text, flush=True)

p("==================================================")
p("BƯỚC 2: KIỂM TOÁN 4 BẢNG PARQUET HIỆN CÓ")
p("==================================================")

# 1. Food.com Interactions
df_fc_inter = spark.read.parquet("data/processed/food_com/interactions.parquet")
fc_inter_cnt = df_fc_inter.count()
fc_u_cnt = df_fc_inter.select("user_id").distinct().count()
fc_r_cnt = df_fc_inter.select("recipe_id").distinct().count()
fc_sparsity = 1.0 - (fc_inter_cnt / (fc_u_cnt * fc_r_cnt))

p(f"\n[1] Food.com Interactions:")
p(f"  - Rows: {fc_inter_cnt}, Cols: {len(df_fc_inter.columns)}")
p(f"  - Schema: {df_fc_inter.dtypes}")
p(f"  - Distinct user_id: {fc_u_cnt}, Distinct recipe_id: {fc_r_cnt}")
p(f"  - Sparsity: {fc_sparsity:.6f} ({fc_sparsity*100:.4f}%)")

null_counts_fc_inter = {c: df_fc_inter.filter(col(c).isNull()).count() for c in df_fc_inter.columns}
p(f"  - Null counts: {null_counts_fc_inter}")

rating_dist_fc = df_fc_inter.groupBy("rating").count().orderBy("rating").collect()
p("  - Rating distribution:")
for r in rating_dist_fc:
    p(f"      rating {r['rating']}: {r['count']}")

dup_fc_inter = fc_inter_cnt - df_fc_inter.dropDuplicates(["user_id", "recipe_id"]).count()
p(f"  - Duplicate (user_id, recipe_id): {dup_fc_inter}")

u_min_fc = df_fc_inter.groupBy("user_id").agg(count("recipe_id").alias("c")).agg(spark_min("c")).collect()[0][0]
r_min_fc = df_fc_inter.groupBy("recipe_id").agg(count("user_id").alias("c")).agg(spark_min("c")).collect()[0][0]
u_lt3_fc = df_fc_inter.groupBy("user_id").agg(count("recipe_id").alias("c")).filter("c < 3").count()
r_lt3_fc = df_fc_inter.groupBy("recipe_id").agg(count("user_id").alias("c")).filter("c < 3").count()
p(f"  - K-core check: Min user interactions: {u_min_fc}, Min recipe interactions: {r_min_fc}")
p(f"  - Users with < 3 interactions: {u_lt3_fc}, Recipes with < 3 interactions: {r_lt3_fc}")

# 2. Food.com Recipes
df_fc_rec = spark.read.parquet("data/processed/food_com/recipes.parquet")
fc_rec_cnt = df_fc_rec.count()
p(f"\n[2] Food.com Recipes:")
p(f"  - Rows: {fc_rec_cnt}, Cols: {len(df_fc_rec.columns)}")
p(f"  - Schema: {df_fc_rec.dtypes}")

null_counts_fc_rec = {c: df_fc_rec.filter(col(c).isNull()).count() for c in df_fc_rec.columns}
p(f"  - Null counts: {null_counts_fc_rec}")

missing_recipes_in_rec = df_fc_inter.join(df_fc_rec, on="recipe_id", how="left_anti").select("recipe_id").distinct().count()
recipes_without_inter = df_fc_rec.join(df_fc_inter, on="recipe_id", how="left_anti").select("recipe_id").distinct().count()
p(f"  - Recipes in interactions missing from recipes.parquet: {missing_recipes_in_rec}")
p(f"  - Recipes in recipes.parquet with 0 interactions: {recipes_without_inter}")

for num_col in ["minutes", "n_steps", "n_ingredients"]:
    quantiles = df_fc_rec.stat.approxQuantile(num_col, [0.0, 0.01, 0.50, 0.99, 0.999, 1.0], 0.001)
    p(f"  - Percentiles for {num_col} [min, 1%, 50%, 99%, 99.9%, max]: {quantiles}")
min_le0 = df_fc_rec.filter("minutes <= 0").count()
min_gt_10000 = df_fc_rec.filter("minutes > 10000").count()
min_max = df_fc_rec.agg(spark_max("minutes")).collect()[0][0]
p(f"  - Recipes with minutes <= 0: {min_le0}, minutes > 10000: {min_gt_10000}, max minutes: {min_max}")

# 3. Vietnam Ratings
df_vn_rat = spark.read.parquet("data/processed/food_vietnam/ratings.parquet")
vn_rat_cnt = df_vn_rat.count()
vn_u_cnt = df_vn_rat.select("user_id").distinct().count()
vn_f_cnt = df_vn_rat.select("food_id").distinct().count()
vn_sparsity = 1.0 - (vn_rat_cnt / (vn_u_cnt * vn_f_cnt))

p(f"\n[3] Vietnam Ratings:")
p(f"  - Rows: {vn_rat_cnt}, Cols: {len(df_vn_rat.columns)}")
p(f"  - Schema: {df_vn_rat.dtypes}")
p(f"  - Distinct user_id: {vn_u_cnt}, Distinct food_id: {vn_f_cnt}")
p(f"  - Sparsity: {vn_sparsity:.6f} ({vn_sparsity*100:.4f}%)")

null_counts_vn_rat = {c: df_vn_rat.filter(col(c).isNull()).count() for c in df_vn_rat.columns}
p(f"  - Null counts: {null_counts_vn_rat}")

rating_dist_vn = df_vn_rat.groupBy("rating").count().orderBy("rating").collect()
p("  - Rating distribution:")
for r in rating_dist_vn:
    p(f"      rating {r['rating']}: {r['count']}")

dup_vn_rat = vn_rat_cnt - df_vn_rat.dropDuplicates(["user_id", "food_id"]).count()
p(f"  - Duplicate (user_id, food_id): {dup_vn_rat}")

u_min_vn = df_vn_rat.groupBy("user_id").agg(count("food_id").alias("c")).agg(spark_min("c")).collect()[0][0]
f_min_vn = df_vn_rat.groupBy("food_id").agg(count("user_id").alias("c")).agg(spark_min("c")).collect()[0][0]
u_lt3_vn = df_vn_rat.groupBy("user_id").agg(count("food_id").alias("c")).filter("c < 3").count()
f_lt3_vn = df_vn_rat.groupBy("food_id").agg(count("user_id").alias("c")).filter("c < 3").count()
p(f"  - K-core check: Min user ratings: {u_min_vn}, Min food ratings: {f_min_vn}")
p(f"  - Users with < 3 ratings: {u_lt3_vn}, Foods with < 3 ratings: {f_lt3_vn}")

# 4. Vietnam Foods
df_vn_food = spark.read.parquet("data/processed/food_vietnam/foods.parquet")
vn_food_cnt = df_vn_food.count()
p(f"\n[4] Vietnam Foods:")
p(f"  - Rows: {vn_food_cnt}, Cols: {len(df_vn_food.columns)}")
p(f"  - Exact Column Names: {df_vn_food.columns}")
p(f"  - Schema: {df_vn_food.dtypes}")

null_counts_vn_food = {c: df_vn_food.filter(col(c).isNull()).count() for c in df_vn_food.columns}
p(f"  - Null counts: {null_counts_vn_food}")

distinct_counts_vn_food = {c: df_vn_food.select(c).distinct().count() for c in df_vn_food.columns}
p(f"  - Distinct value counts: {distinct_counts_vn_food}")

missing_foods_in_foods = df_vn_rat.join(df_vn_food, on="food_id", how="left_anti").select("food_id").distinct().count()
foods_without_ratings = df_vn_food.join(df_vn_rat, on="food_id", how="left_anti").select("food_id").distinct().count()
p(f"  - Foods in ratings missing from foods.parquet: {missing_foods_in_foods}")
p(f"  - Foods in foods.parquet with 0 ratings: {foods_without_ratings}")

p("  - 5 Sample Rows from foods.parquet:")
df_vn_food.select("food_id", "dish_name", "dish_type", "calories", "cooking_time").show(5, truncate=False)

p("\n==================================================")
p("BƯỚC 3: PHÂN TÍCH QUY TRÌNH LỌC TỪ DỮ LIỆU THÔ")
p("==================================================")

# A. Food.com RAW Interactions funnel
p("\n[Food.com Interactions Funnel]")
raw_fc = spark.read.csv("data/raw/food_com/RAW_interactions.csv", header=True, multiLine=True, escape="\"", inferSchema=False)
raw_fc_total = raw_fc.count()
p(f"  Step 0 - Raw MultiLine read: {raw_fc_total}")

s1_fc = raw_fc.select(
    col("user_id").cast("integer"),
    col("recipe_id").cast("integer"),
    col("rating").cast("float"),
    col("date").cast("string")
)
s1_fc_valid = s1_fc.dropna(subset=["user_id", "recipe_id", "rating"]).localCheckpoint()
s1_fc_null_dropped = raw_fc_total - s1_fc_valid.count()
p(f"  Step 1 - Dropped NULL in keys/rating: {s1_fc_null_dropped} rows")

s2_fc_r0 = s1_fc_valid.filter(col("rating") == 0).count()
p(f"  Step 2 - rating == 0: {s2_fc_r0} rows")

s2_fc_out = s1_fc_valid.filter((col("rating") < 1.0) | (col("rating") > 5.0)).count() - s2_fc_r0
p(f"  Step 2b - rating outside [1, 5] (not including 0): {s2_fc_out} rows")

s2_fc_clean_r = s1_fc_valid.filter((col("rating") >= 1.0) & (col("rating") <= 5.0)).localCheckpoint()
after_r_filter = s2_fc_clean_r.count()
p(f"  Step 2c - Total remaining after rating [1, 5]: {after_r_filter} rows")

s3_fc_dedup = s2_fc_clean_r.dropDuplicates(["user_id", "recipe_id"]).localCheckpoint()
after_dedup = s3_fc_dedup.count()
dup_dropped = after_r_filter - after_dedup
p(f"  Step 3 - Dropped duplicates (user, recipe): {dup_dropped} rows -> remaining: {after_dedup}")

# 1-pass K-core
u_cnts = s3_fc_dedup.groupBy("user_id").agg(count("recipe_id").alias("uc")).filter("uc >= 3").select("user_id")
r_cnts = s3_fc_dedup.groupBy("recipe_id").agg(count("user_id").alias("rc")).filter("rc >= 3").select("recipe_id")

k1_fc = s3_fc_dedup.join(u_cnts, "user_id").join(r_cnts, "recipe_id").localCheckpoint()
k1_fc_cnt = k1_fc.count()
k1_dropped = after_dedup - k1_fc_cnt
p(f"  Step 4 - 1-pass K-core >= 3: dropped {k1_dropped} rows -> remaining: {k1_fc_cnt}")

# Check minimum interactions in 1-pass K-core
min_u_k1 = k1_fc.groupBy("user_id").agg(count("recipe_id").alias("c")).agg(spark_min("c")).collect()[0][0]
min_r_k1 = k1_fc.groupBy("recipe_id").agg(count("user_id").alias("c")).agg(spark_min("c")).collect()[0][0]
p(f"    Notice in 1-pass: Min user interactions = {min_u_k1}, Min recipe interactions = {min_r_k1}")

# Iterative K-core until convergence
cur_df = s3_fc_dedup
iteration = 0
while True:
    iteration += 1
    u_c = cur_df.groupBy("user_id").agg(count("recipe_id").alias("uc")).filter("uc >= 3").select("user_id")
    r_c = cur_df.groupBy("recipe_id").agg(count("user_id").alias("rc")).filter("rc >= 3").select("recipe_id")
    next_df = cur_df.join(u_c, "user_id").join(r_c, "recipe_id").localCheckpoint()
    prev_cnt = cur_df.count()
    next_cnt = next_df.count()
    p(f"    Iterative K-core iter {iteration}: {prev_cnt} -> {next_cnt} (dropped {prev_cnt - next_cnt})")
    cur_df = next_df
    if prev_cnt == next_cnt or iteration >= 10:
        break
k_iter_cnt = cur_df.count()
p(f"  Step 5 - Iterative K-core final: {k_iter_cnt} rows (difference vs 1-pass: {k1_fc_cnt - k_iter_cnt})")


# B. ViFoodRec RAW Ratings Funnel
p("\n[ViFoodRec Ratings Funnel]")
raw_vn = spark.read.csv("data/raw/food_vietnam/ratings.csv", header=True, multiLine=True, escape="\"", inferSchema=False)
raw_vn_total = raw_vn.count()
p(f"  Step 0 - Raw Read: {raw_vn_total}")

for c in raw_vn.columns:
    norm = c.strip().lower()
    if norm == "userid": norm = "user_id"
    elif norm == "foodid": norm = "food_id"
    raw_vn = raw_vn.withColumnRenamed(c, norm)

s1_vn = raw_vn.select(
    col("user_id").cast("integer"),
    col("food_id").cast("integer"),
    col("rating").cast("float")
)
s1_vn_valid = s1_vn.dropna(subset=["user_id", "food_id", "rating"]).localCheckpoint()
vn_null_dropped = raw_vn_total - s1_vn_valid.count()
p(f"  Step 1 - Dropped NULL in keys/rating: {vn_null_dropped} rows")

vn_r0 = s1_vn_valid.filter(col("rating") == 0).count()
p(f"  Step 2 - rating == 0: {vn_r0} rows")

vn_out = s1_vn_valid.filter((col("rating") < 1.0) | (col("rating") > 5.0)).count() - vn_r0
p(f"  Step 2b - rating outside [1, 5] (excl 0): {vn_out} rows")

s2_vn_clean_r = s1_vn_valid.filter((col("rating") >= 1.0) & (col("rating") <= 5.0)).localCheckpoint()
vn_after_r = s2_vn_clean_r.count()
p(f"  Step 2c - Total remaining after rating [1, 5]: {vn_after_r} rows")

s3_vn_dedup = s2_vn_clean_r.dropDuplicates(["user_id", "food_id"]).localCheckpoint()
vn_after_dedup = s3_vn_dedup.count()
vn_dup_dropped = vn_after_r - vn_after_dedup
p(f"  Step 3 - Dropped duplicates (user, food): {vn_dup_dropped} rows -> remaining: {vn_after_dedup}")

u_cnts_vn = s3_vn_dedup.groupBy("user_id").agg(count("food_id").alias("uc")).filter("uc >= 3").select("user_id")
f_cnts_vn = s3_vn_dedup.groupBy("food_id").agg(count("user_id").alias("fc")).filter("fc >= 3").select("food_id")

k1_vn = s3_vn_dedup.join(u_cnts_vn, "user_id").join(f_cnts_vn, "food_id").localCheckpoint()
k1_vn_cnt = k1_vn.count()
k1_vn_dropped = vn_after_dedup - k1_vn_cnt
p(f"  Step 4 - 1-pass K-core >= 3: dropped {k1_vn_dropped} rows -> remaining: {k1_vn_cnt}")

min_u_k1_vn = k1_vn.groupBy("user_id").agg(count("food_id").alias("c")).agg(spark_min("c")).collect()[0][0]
min_f_k1_vn = k1_vn.groupBy("food_id").agg(count("user_id").alias("c")).agg(spark_min("c")).collect()[0][0]
p(f"    Notice in 1-pass VN: Min user ratings = {min_u_k1_vn}, Min food ratings = {min_f_k1_vn}")

p("\n>>> GIẢI THÍCH 33.211 DÒNG BỊ MẤT CỦA VIFOODREC (182.678 -> 149.467):")
p(f"    - Tổng dòng thô ban đầu: {raw_vn_total}")
p(f"    - Bị loại do NULL: {vn_null_dropped} ({vn_null_dropped/raw_vn_total*100:.2f}%)")
p(f"    - Bị loại do rating == 0: {vn_r0} ({vn_r0/raw_vn_total*100:.2f}%)")
p(f"    - Bị loại do rating ngoài [1, 5]: {vn_out} ({vn_out/raw_vn_total*100:.2f}%)")
p(f"    - Bị loại do trùng lặp (user_id, food_id): {vn_dup_dropped} ({vn_dup_dropped/raw_vn_total*100:.2f}%)")
p(f"    - Bị loại do K-core >= 3 (chủ yếu do món ăn có < 3 lượt chấm): {k1_vn_dropped} ({k1_vn_dropped/raw_vn_total*100:.2f}%)")
p(f"    => TỔNG CỘNG MẤT: {raw_vn_total - k1_vn_cnt} dòng ({(raw_vn_total - k1_vn_cnt)/raw_vn_total*100:.2f}%)")

# Iterative K-core for ViFoodRec
cur_vn = s3_vn_dedup
it_vn = 0
while True:
    it_vn += 1
    u_c = cur_vn.groupBy("user_id").agg(count("food_id").alias("uc")).filter("uc >= 3").select("user_id")
    f_c = cur_vn.groupBy("food_id").agg(count("user_id").alias("fc")).filter("fc >= 3").select("food_id")
    nxt = cur_vn.join(u_c, "user_id").join(f_c, "food_id").localCheckpoint()
    p_cnt = cur_vn.count()
    n_cnt = nxt.count()
    p(f"    Iterative K-core VN iter {it_vn}: {p_cnt} -> {n_cnt} (dropped {p_cnt - n_cnt})")
    cur_vn = nxt
    if p_cnt == n_cnt or it_vn >= 10:
        break
k_iter_vn_cnt = cur_vn.count()
p(f"  Step 5 - Iterative K-core VN final: {k_iter_vn_cnt} rows (difference vs 1-pass: {k1_vn_cnt - k_iter_vn_cnt})")

spark.stop()
p("\n=== HOÀN TẤT KIỂM TOÁN ===")

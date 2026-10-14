"""
src/clean_food_com.py
---------------------
Pipeline làm sạch chuẩn hóa cho bộ dữ liệu Food.com:
1. Đọc CSV tường minh với schema định nghĩa trước, multiLine=True, escape='"'.
2. Làm sạch bảng recipes:
   - Loại bỏ thiếu ID/name, khử trùng recipe_id.
   - Tách cột nutrition thành 7 cột số float chuẩn theo đặc tả Kaggle.
   - Chuyển tags và ingredients thành mảng chuỗi (array<string>).
   - Xử lý ngoại lai minutes: giữ cột gốc minutes, thêm cột minutes_clean (NULL nếu ngoại lai <= 0 hoặc > MAX_MINUTES_THRESHOLD).
   - Bỏ steps và description.
3. Làm sạch bảng interactions:
   - Ép kiểu user_id, recipe_id (int), rating (float), date (date).
   - Bỏ NULL, bỏ rating = 0, giữ rating trong [1, 5].
   - Khử trùng cặp (user_id, recipe_id) theo tiêu chí giữ bản ghi có date mới nhất.
   - Bỏ cột review.
   - Inner join đảm bảo toàn vẹn khóa ngoại với recipes sạch.
   - Áp dụng K-core LẶP đến khi hội tụ (K=3) và ghi nhận số vòng lặp.
4. Gắn cờ has_ratings cho bảng recipes sạch.
5. Ghi dữ liệu sạch ra HDFS dạng Parquet Snappy.
6. Trả về nhật ký cleaning_log cho từng bước xử lý.
"""

import sys
import time
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType, FloatType
)
from pyspark.sql.functions import (
    col, trim, when, split, regexp_replace, row_number, 
    to_date, count as spark_count, lit
)
from pyspark.sql.window import Window
from src.config import get_spark_session, get_path, K_CORE_DEFAULT, MAX_MINUTES_THRESHOLD


def clean_food_com(spark=None):
    if spark is None:
        spark = get_spark_session("CleanFoodCom")
        
    print("=" * 80)
    print("   BẮT ĐẦU PIPELINE LÀM SẠCH DỮ LIỆU FOOD.COM (P3)")
    print("=" * 80)
    
    logs = []
    
    # ---------------------------------------------------------
    # 1. ĐỊNH NGHĨA SCHEMA TƯỜNG MINH
    # ---------------------------------------------------------
    recipes_schema = StructType([
        StructField("name", StringType(), True),
        StructField("id", IntegerType(), True),
        StructField("minutes", IntegerType(), True),
        StructField("contributor_id", IntegerType(), True),
        StructField("submitted", StringType(), True),
        StructField("tags", StringType(), True),
        StructField("nutrition", StringType(), True),
        StructField("n_steps", IntegerType(), True),
        StructField("steps", StringType(), True),
        StructField("description", StringType(), True),
        StructField("ingredients", StringType(), True),
        StructField("n_ingredients", IntegerType(), True)
    ])
    
    interactions_schema = StructType([
        StructField("user_id", IntegerType(), True),
        StructField("recipe_id", IntegerType(), True),
        StructField("date", StringType(), True),
        StructField("rating", FloatType(), True),
        StructField("review", StringType(), True)
    ])
    
    raw_recipes_path = get_path("raw", "food_com", "RAW_recipes.csv")
    raw_inter_path = get_path("raw", "food_com", "RAW_interactions.csv")
    
    # ---------------------------------------------------------
    # 2. XỬ LÝ BẢNG RECIPES
    # ---------------------------------------------------------
    print(f"\n[A] Đọc dữ liệu thô recipes: {raw_recipes_path}")
    df_rec_raw = spark.read.option("header", "true") \
                           .option("multiLine", "true") \
                           .option("escape", "\"") \
                           .schema(recipes_schema) \
                           .csv(raw_recipes_path)
                           
    r0_count = df_rec_raw.count()
    print(f"  - Tổng số bản ghi ban đầu: {r0_count:,}")
    logs.append({
        "dataset": "food_com_recipes",
        "step_name": "raw_input",
        "rows_before": r0_count,
        "rows_after": r0_count,
        "rows_dropped": 0,
        "notes": "Đọc dữ liệu thô RAW_recipes.csv với schema tường minh"
    })
    
    # R1: Lọc bỏ thiếu ID hoặc name
    df_rec_valid = df_rec_raw.filter(
        col("id").isNotNull() & col("name").isNotNull() & (trim(col("name")) != "")
    )
    r1_count = df_rec_valid.count()
    r1_dropped = r0_count - r1_count
    print(f"  - Sau lọc thiếu ID/name: {r1_count:,} (Loại: {r1_dropped:,})")
    logs.append({
        "dataset": "food_com_recipes",
        "step_name": "filter_null_id_name",
        "rows_before": r0_count,
        "rows_after": r1_count,
        "rows_dropped": r1_dropped,
        "notes": "Loại bỏ bản ghi thiếu id hoặc name rỗng"
    })
    
    # R2: Khử trùng recipe_id
    df_rec_dedup = df_rec_valid.dropDuplicates(["id"])
    r2_count = df_rec_dedup.count()
    r2_dropped = r1_count - r2_count
    print(f"  - Sau khử trùng id: {r2_count:,} (Loại trùng: {r2_dropped:,})")
    logs.append({
        "dataset": "food_com_recipes",
        "step_name": "drop_duplicate_id",
        "rows_before": r1_count,
        "rows_after": r2_count,
        "rows_dropped": r2_dropped,
        "notes": "Khử trùng lặp khóa chính id (recipe_id)"
    })
    
    # R3: Tách cột nutrition và chuẩn hóa các cột
    print("  - Tách 7 chỉ số dinh dưỡng từ cột nutrition và chuẩn hóa tags/ingredients...")
    clean_nutr = regexp_replace(col("nutrition"), r"^\[|\]$", "")
    nutr_arr = split(clean_nutr, r",\s*")
    
    clean_tags_str = regexp_replace(regexp_replace(col("tags"), r"^\[|\]$", ""), r"'|\"", "")
    clean_ingr_str = regexp_replace(regexp_replace(col("ingredients"), r"^\[|\]$", ""), r"'|\"", "")
    
    df_rec_parsed = df_rec_dedup \
        .withColumnRenamed("id", "recipe_id") \
        .withColumn("submitted", to_date(col("submitted"), "yyyy-MM-dd")) \
        .withColumn("calories", nutr_arr[0].cast(FloatType())) \
        .withColumn("total_fat_pdv", nutr_arr[1].cast(FloatType())) \
        .withColumn("sugar_pdv", nutr_arr[2].cast(FloatType())) \
        .withColumn("sodium_pdv", nutr_arr[3].cast(FloatType())) \
        .withColumn("protein_pdv", nutr_arr[4].cast(FloatType())) \
        .withColumn("saturated_fat_pdv", nutr_arr[5].cast(FloatType())) \
        .withColumn("carbohydrates_pdv", nutr_arr[6].cast(FloatType())) \
        .withColumn("tags", split(trim(clean_tags_str), r",\s*")) \
        .withColumn("ingredients", split(trim(clean_ingr_str), r",\s*")) \
        .withColumn(
            "minutes_clean",
            when((col("minutes") > 0) & (col("minutes") <= MAX_MINUTES_THRESHOLD), col("minutes")).otherwise(None)
        ) \
        .select(
            "recipe_id", "name", "minutes", "minutes_clean", "contributor_id", "submitted",
            "n_steps", "n_ingredients", "calories", "total_fat_pdv", "sugar_pdv", "sodium_pdv",
            "protein_pdv", "saturated_fat_pdv", "carbohydrates_pdv", "tags", "ingredients"
        )
        
    df_rec_parsed.cache()
    
    # ---------------------------------------------------------
    # 3. XỬ LÝ BẢNG INTERACTIONS
    # ---------------------------------------------------------
    print(f"\n[B] Đọc dữ liệu thô interactions: {raw_inter_path}")
    df_int_raw = spark.read.option("header", "true") \
                           .option("multiLine", "true") \
                           .option("escape", "\"") \
                           .schema(interactions_schema) \
                           .csv(raw_inter_path)
                           
    i0_count = df_int_raw.count()
    print(f"  - Tổng số tương tác ban đầu: {i0_count:,}")
    logs.append({
        "dataset": "food_com_interactions",
        "step_name": "raw_input",
        "rows_before": i0_count,
        "rows_after": i0_count,
        "rows_dropped": 0,
        "notes": "Đọc dữ liệu thô RAW_interactions.csv"
    })
    
    # I1: Bỏ NULL ở các cột khóa chính & rating
    df_int_valid = df_int_raw.filter(
        col("user_id").isNotNull() & col("recipe_id").isNotNull() & col("rating").isNotNull()
    ).withColumn("date", to_date(col("date"), "yyyy-MM-dd")).drop("review")
    
    i1_count = df_int_valid.count()
    i1_dropped = i0_count - i1_count
    print(f"  - Sau bỏ NULL (và bỏ cột review): {i1_count:,} (Loại: {i1_dropped:,})")
    logs.append({
        "dataset": "food_com_interactions",
        "step_name": "filter_null_keys_drop_review",
        "rows_before": i0_count,
        "rows_after": i1_count,
        "rows_dropped": i1_dropped,
        "notes": "Bỏ NULL ở user_id, recipe_id, rating và lược bỏ cột text review"
    })
    
    # I2: Bỏ rating = 0 (tương tác chỉ xem/bình luận không chấm sao)
    df_int_nonzero = df_int_valid.filter(col("rating") != 0.0)
    i2_count = df_int_nonzero.count()
    i2_dropped = i1_count - i2_count
    print(f"  - Sau bỏ rating = 0: {i2_count:,} (Loại rating 0: {i2_dropped:,})")
    logs.append({
        "dataset": "food_com_interactions",
        "step_name": "filter_rating_zero",
        "rows_before": i1_count,
        "rows_after": i2_count,
        "rows_dropped": i2_dropped,
        "notes": "Loại bỏ các tương tác rating = 0 (không có đánh giá điểm)"
    })
    
    # I3: Giữ rating trong [1.0, 5.0]
    df_int_range = df_int_nonzero.filter((col("rating") >= 1.0) & (col("rating") <= 5.0))
    i3_count = df_int_range.count()
    i3_dropped = i2_count - i3_count
    print(f"  - Sau lọc rating [1, 5]: {i3_count:,} (Loại ngoài khoảng: {i3_dropped:,})")
    logs.append({
        "dataset": "food_com_interactions",
        "step_name": "filter_rating_range_1_to_5",
        "rows_before": i2_count,
        "rows_after": i3_count,
        "rows_dropped": i3_dropped,
        "notes": "Giữ rating trong khoảng hợp lệ [1.0, 5.0]"
    })
    
    # I4: Khử trùng cặp (user_id, recipe_id) giữ date mới nhất
    window_spec = Window.partitionBy("user_id", "recipe_id").orderBy(col("date").desc_nulls_last())
    df_int_dedup = df_int_range.withColumn("rn", row_number().over(window_spec)) \
                               .filter(col("rn") == 1) \
                               .drop("rn")
                               
    i4_count = df_int_dedup.count()
    i4_dropped = i3_count - i4_count
    print(f"  - Sau khử trùng cặp (user_id, recipe_id): {i4_count:,} (Loại trùng: {i4_dropped:,})")
    logs.append({
        "dataset": "food_com_interactions",
        "step_name": "deduplicate_user_recipe_pairs",
        "rows_before": i3_count,
        "rows_after": i4_count,
        "rows_dropped": i4_dropped,
        "notes": "Khử trùng lặp cặp (user, món), giữ bản ghi có date mới nhất"
    })
    
    # I5: Kiểm tra khóa ngoại với recipes sạch
    df_int_fk = df_int_dedup.join(
        df_rec_parsed.select("recipe_id"),
        on="recipe_id",
        how="inner"
    )
    i5_count = df_int_fk.count()
    i5_dropped = i4_count - i5_count
    print(f"  - Sau kiểm tra khóa ngoại với recipes: {i5_count:,} (Loại không khớp FK: {i5_dropped:,})")
    logs.append({
        "dataset": "food_com_interactions",
        "step_name": "foreign_key_join_recipes",
        "rows_before": i4_count,
        "rows_after": i5_count,
        "rows_dropped": i5_dropped,
        "notes": "Bảo đảm toàn vẹn khóa ngoại: mọi recipe_id phải tồn tại trong bảng recipes sạch"
    })
    
    # I6: VÒNG LẶP K-CORE ĐẾN KHI HỘI TỤ (K=3)
    print(f"\n[C] Thực thi vòng lặp K-core lặp đến khi hội tụ (Ngưỡng K={K_CORE_DEFAULT})...")
    curr_df = df_int_fk.localCheckpoint(eager=True)
    iteration = 0
    k = K_CORE_DEFAULT
    
    while True:
        iteration += 1
        # 1. Lọc user có >= k tương tác
        u_counts = curr_df.groupBy("user_id").agg(spark_count("recipe_id").alias("u_cnt")).filter(f"u_cnt >= {k}")
        df_user_filtered = curr_df.join(u_counts.select("user_id"), on="user_id", how="inner")
        
        # 2. Lọc recipe có >= k tương tác
        r_counts = df_user_filtered.groupBy("recipe_id").agg(spark_count("user_id").alias("r_cnt")).filter(f"r_cnt >= {k}")
        df_next = df_user_filtered.join(r_counts.select("recipe_id"), on="recipe_id", how="inner")
        
        # Cắt đứt lineage graph để giải phóng bộ nhớ và tránh lỗi deep lineage Serialization OOM
        df_next = df_next.localCheckpoint(eager=True)
        
        c_before = curr_df.count()
        c_after = df_next.count()
        print(f"    * Vòng lặp {iteration}: {c_before:,} -> {c_after:,} dòng (Giảm {c_before - c_after:,} dòng)")
        
        curr_df = df_next
        if c_before == c_after:
            print(f"  -> K-core đã HỘI TỤ sau {iteration} vòng lặp tại {c_after:,} dòng!")
            break
            
    df_inter_final = curr_df
    i6_count = c_after
    i6_dropped = i5_count - i6_count
    logs.append({
        "dataset": "food_com_interactions",
        "step_name": "iterative_k_core_convergence",
        "rows_before": i5_count,
        "rows_after": i6_count,
        "rows_dropped": i6_dropped,
        "notes": f"Lọc K-core lặp tới hội tụ (K={k}, hội tụ sau {iteration} vòng lặp)"
    })
    
    # ---------------------------------------------------------
    # 4. GẮN CỜ has_ratings CHO BẢNG RECIPES
    # ---------------------------------------------------------
    print("\n[D] Gắn cờ has_ratings cho bảng recipes...")
    rated_recipes = df_inter_final.select("recipe_id").distinct().withColumn("has_ratings", lit(True))
    df_recipes_final = df_rec_parsed.join(rated_recipes, on="recipe_id", how="left") \
                                    .withColumn("has_ratings", when(col("has_ratings").isNotNull(), lit(True)).otherwise(lit(False)))
                                    
    # ---------------------------------------------------------
    # 5. GHI DỮ LIỆU SẠCH RA HDFS PARQUET
    # ---------------------------------------------------------
    clean_inter_path = get_path("clean", "food_com", "interactions_clean.parquet")
    clean_rec_path = get_path("clean", "food_com", "recipes_clean.parquet")
    
    print(f"\n[E] Ghi Parquet sạch:")
    print(f"  - Interactions: {clean_inter_path}")
    df_inter_final.write.mode("overwrite").parquet(clean_inter_path)
    
    print(f"  - Recipes     : {clean_rec_path}")
    df_recipes_final.write.mode("overwrite").parquet(clean_rec_path)
    
    print("  -> Ghi Parquet Food.com hoàn tất thành công!")
    return logs


if __name__ == "__main__":
    t0 = time.time()
    clean_food_com()
    print(f"Tổng thời gian làm sạch Food.com: {time.time() - t0:.2f}s")
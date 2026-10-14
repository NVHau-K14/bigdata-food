"""
src/clean_vietnam.py
--------------------
Pipeline làm sạch chuẩn hóa cho bộ dữ liệu ViFoodRec (món ăn Việt Nam):
1. Đọc CSV tường minh với schema định nghĩa trước.
2. Làm sạch bảng foods:
   - Ép kiểu food_id (int).
   - Chuẩn hóa văn bản: trim, gộp khoảng trắng thừa, xóa thẻ HTML.
   - Trích xuất số cho serving_size (số người) và cooking_time (số phút).
   - Ép kiểu số cho 5 chỉ số dinh dưỡng (calories, fat, fiber, sugar, protein).
   - Tách dish_tags thành mảng chuỗi (array<string>).
   - Gắn cờ is_duplicate nếu trùng tên và nguyên liệu (không xóa để bảo toàn đánh giá).
3. Làm sạch bảng ratings:
   - Đổi tên userId -> user_id, foodId -> food_id.
   - Giữ nguyên thang điểm 11 mức (0.0 đến 5.0, bước 0.5); chỉ loại điểm nằm ngoài thang đó.
     Không loại 0.0 và 0.5 vì số dòng mỗi mức ngang nhau (quyết định ngày 14/10/2026).
   - Khử trùng cặp (user_id, food_id).
   - Kiểm tra khóa ngoại với foods (loại các dòng mang food_id không có trong foods).
   - Lọc K-core lặp đến khi hội tụ (K=3).
4. Gắn cờ has_ratings cho bảng foods.
5. Ghi Parquet sạch dạng coalesce(1) tránh phân mảnh file nhỏ.
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
    col, trim, when, split, regexp_replace, regexp_extract, row_number,
    count as spark_count, lit, round as spark_round
)
from pyspark.sql.window import Window
from src.config import (
    get_spark_session, get_path, K_CORE_DEFAULT,
    RATING_MIN_VN, RATING_MAX_VN, RATING_STEP_VN
)


def clean_vietnam(spark=None):
    if spark is None:
        spark = get_spark_session("CleanVietnam")
        
    print("=" * 80)
    print("   BẮT ĐẦU PIPELINE LÀM SẠCH DỮ LIỆU VIFOODREC (P3)")
    print("=" * 80)
    
    logs = []
    
    # ---------------------------------------------------------
    # 1. ĐỊNH NGHĨA SCHEMA TƯỜNG MINH
    # ---------------------------------------------------------
    ratings_schema = StructType([
        StructField("userId", IntegerType(), True),
        StructField("foodId", IntegerType(), True),
        StructField("rating", FloatType(), True)
    ])
    
    foods_schema = StructType([
        StructField("food_id", IntegerType(), True),
        StructField("dish_name", StringType(), True),
        StructField("description", StringType(), True),
        StructField("dish_type", StringType(), True),
        StructField("serving_size", StringType(), True),
        StructField("cooking_time", StringType(), True),
        StructField("ingredients", StringType(), True),
        StructField("cooking_method", StringType(), True),
        StructField("dish_tags", StringType(), True),
        StructField("calories", FloatType(), True),
        StructField("fat", FloatType(), True),
        StructField("fiber", FloatType(), True),
        StructField("sugar", FloatType(), True),
        StructField("protein", FloatType(), True),
        StructField("image_link", StringType(), True),
        StructField("nutrient_content", StringType(), True)
    ])
    
    raw_ratings_path = get_path("raw", "food_vietnam", "ratings.csv")
    raw_foods_path = get_path("raw", "food_vietnam", "foods.csv")
    
    # ---------------------------------------------------------
    # 2. XỬ LÝ BẢNG FOODS
    # ---------------------------------------------------------
    print(f"\n[A] Đọc dữ liệu thô foods: {raw_foods_path}")
    df_foods_raw = spark.read.option("header", "true") \
                             .option("multiLine", "true") \
                             .option("escape", "\"") \
                             .schema(foods_schema) \
                             .csv(raw_foods_path)
                             
    f0_count = df_foods_raw.count()
    print(f"  - Tổng số món ăn thô: {f0_count:,}")
    logs.append({
        "dataset": "vifoodrec_foods",
        "step_name": "raw_input",
        "rows_before": f0_count,
        "rows_after": f0_count,
        "rows_dropped": 0,
        "notes": "Đọc dữ liệu thô foods.csv với schema tường minh"
    })
    
    # F1: Lọc bỏ thiếu food_id hoặc dish_name
    df_foods_valid = df_foods_raw.filter(
        col("food_id").isNotNull() & col("dish_name").isNotNull() & (trim(col("dish_name")) != "")
    )
    f1_count = df_foods_valid.count()
    f1_dropped = f0_count - f1_count
    print(f"  - Sau lọc thiếu ID/name: {f1_count:,} (Loại: {f1_dropped:,})")
    logs.append({
        "dataset": "vifoodrec_foods",
        "step_name": "filter_null_id_name",
        "rows_before": f0_count,
        "rows_after": f1_count,
        "rows_dropped": f1_dropped,
        "notes": "Loại bỏ món thiếu food_id hoặc tên rỗng"
    })
    
    # F2: Chuẩn hóa văn bản, trích xuất số và gắn cờ trùng lặp
    print("  - Chuẩn hóa text, parse số khẩu phần/thời gian nấu, gắn cờ trùng lặp...")
    # Trích xuất số người từ serving_size (ví dụ: '4 người' -> 4)
    serving_num = regexp_extract(col("serving_size"), r"(\d+)", 1).cast(IntegerType())
    # Trích xuất số phút từ cooking_time (ví dụ: '50' -> 50)
    time_num = regexp_extract(col("cooking_time"), r"(\d+)", 1).cast(IntegerType())
    
    # Làm sạch tên món: gộp khoảng trắng thừa
    clean_name = regexp_replace(trim(col("dish_name")), r"\s+", " ")
    # Bỏ thẻ html trong mô tả
    clean_desc = regexp_replace(col("description"), r"<[^>]*>", "")
    
    # Gắn cờ món trùng: cùng tên và cùng nguyên liệu
    dup_window = Window.partitionBy(clean_name, col("ingredients")).orderBy(col("food_id"))
    df_foods_parsed = df_foods_valid \
        .withColumn("dish_name", clean_name) \
        .withColumn("description", clean_desc) \
        .withColumn("dish_type", trim(col("dish_type"))) \
        .withColumn("serving_size_num", serving_num) \
        .withColumn("cooking_time_min", time_num) \
        .withColumn("dish_tags", split(trim(col("dish_tags")), r",\s*")) \
        .withColumn("dup_rank", row_number().over(dup_window)) \
        .withColumn("is_duplicate", when(col("dup_rank") > 1, lit(True)).otherwise(lit(False))) \
        .drop("dup_rank")
        
    df_foods_parsed.cache()
    
    # ---------------------------------------------------------
    # 3. XỬ LÝ BẢNG RATINGS
    # ---------------------------------------------------------
    print(f"\n[B] Đọc dữ liệu thô ratings: {raw_ratings_path}")
    df_rat_raw = spark.read.option("header", "true") \
                           .schema(ratings_schema) \
                           .csv(raw_ratings_path) \
                           .withColumnRenamed("userId", "user_id") \
                           .withColumnRenamed("foodId", "food_id")
                           
    r0_count = df_rat_raw.count()
    print(f"  - Tổng số đánh giá thô: {r0_count:,}")
    logs.append({
        "dataset": "vifoodrec_ratings",
        "step_name": "raw_input",
        "rows_before": r0_count,
        "rows_after": r0_count,
        "rows_dropped": 0,
        "notes": "Đọc dữ liệu thô ratings.csv, đổi tên userId -> user_id, foodId -> food_id"
    })
    
    # R1: Bỏ NULL ở user_id, food_id, rating
    df_rat_valid = df_rat_raw.filter(
        col("user_id").isNotNull() & col("food_id").isNotNull() & col("rating").isNotNull()
    )
    r1_count = df_rat_valid.count()
    r1_dropped = r0_count - r1_count
    print(f"  - Sau bỏ NULL: {r1_count:,} (Loại: {r1_dropped:,})")
    logs.append({
        "dataset": "vifoodrec_ratings",
        "step_name": "filter_null_keys",
        "rows_before": r0_count,
        "rows_after": r1_count,
        "rows_dropped": r1_dropped,
        "notes": "Bỏ NULL ở user_id, food_id, rating"
    })
    
    # R2: Giữ rating thuộc thang 0.0, 0.5, ..., 5.0. Điểm đã nằm trong thang nên bước này
    # chỉ loại giá trị lệch bước 0.5 hoặc ngoài [0.0, 5.0] (nếu có). Bước 0.5 là lũy thừa của 2
    # nên phép chia và nhân với bước là chính xác trong số thực nhị phân.
    on_scale = (
        (col("rating") >= RATING_MIN_VN) & (col("rating") <= RATING_MAX_VN) &
        (spark_round(col("rating") / RATING_STEP_VN) * RATING_STEP_VN == col("rating"))
    )
    df_rat_range = df_rat_valid.filter(on_scale)
    r2_count = df_rat_range.count()
    r2_dropped = r1_count - r2_count
    n_levels = int(round((RATING_MAX_VN - RATING_MIN_VN) / RATING_STEP_VN)) + 1
    print(f"  - Sau lọc thang điểm {RATING_MIN_VN} đến {RATING_MAX_VN}, bước {RATING_STEP_VN} ({n_levels} mức): "
          f"{r2_count:,} (Loại ngoài thang: {r2_dropped:,})")
    logs.append({
        "dataset": "vifoodrec_ratings",
        "step_name": "filter_rating_scale_0_to_5_step_half",
        "rows_before": r1_count,
        "rows_after": r2_count,
        "rows_dropped": r2_dropped,
        "notes": f"Giữ rating thuộc thang {n_levels} mức từ {RATING_MIN_VN} đến {RATING_MAX_VN}, bước {RATING_STEP_VN}; "
                 f"loại điểm ngoài thang (không loại 0.0 và 0.5)"
    })
    
    # R3: Khử trùng cặp (user_id, food_id)
    df_rat_dedup = df_rat_range.dropDuplicates(["user_id", "food_id"])
    r3_count = df_rat_dedup.count()
    r3_dropped = r2_count - r3_count
    print(f"  - Sau khử trùng cặp (user_id, food_id): {r3_count:,} (Loại trùng: {r3_dropped:,})")
    logs.append({
        "dataset": "vifoodrec_ratings",
        "step_name": "deduplicate_user_food_pairs",
        "rows_before": r2_count,
        "rows_after": r3_count,
        "rows_dropped": r3_dropped,
        "notes": "Khử trùng lặp cặp (user_id, food_id)"
    })
    
    # R4: Kiểm tra toàn vẹn khóa ngoại với bảng foods
    # (Loại dòng có food_id không có trong foods; trong dữ liệu thô đó là food_id = 4000 vì foods chỉ có ID 0..3999)
    df_rat_fk = df_rat_dedup.join(
        df_foods_parsed.select("food_id"),
        on="food_id",
        how="inner"
    )
    r4_count = df_rat_fk.count()
    r4_dropped = r3_count - r4_count
    print(f"  - Sau kiểm tra khóa ngoại với foods: {r4_count:,} (Loại food_id không có trong foods: {r4_dropped:,})")
    logs.append({
        "dataset": "vifoodrec_ratings",
        "step_name": "foreign_key_join_foods",
        "rows_before": r3_count,
        "rows_after": r4_count,
        "rows_dropped": r4_dropped,
        "notes": f"Bảo đảm khóa ngoại: loại bỏ {r4_dropped:,} dòng có food_id không tồn tại trong danh mục foods"
    })
    
    # R5: VÒNG LẶP K-CORE LẶP ĐẾN HỘI TỤ (K=3)
    print(f"\n[C] Thực thi vòng lặp K-core lặp đến khi hội tụ (Ngưỡng K={K_CORE_DEFAULT})...")
    curr_df = df_rat_fk.localCheckpoint(eager=True)
    iteration = 0
    k = K_CORE_DEFAULT
    
    while True:
        iteration += 1
        # Đếm user
        u_cnt = curr_df.groupBy("user_id").agg(spark_count("food_id").alias("u_cnt")).filter(f"u_cnt >= {k}")
        df_u = curr_df.join(u_cnt.select("user_id"), on="user_id", how="inner")
        
        # Đếm food
        f_cnt = df_u.groupBy("food_id").agg(spark_count("user_id").alias("f_cnt")).filter(f"f_cnt >= {k}")
        df_next = df_u.join(f_cnt.select("food_id"), on="food_id", how="inner")
        
        df_next = df_next.localCheckpoint(eager=True)
        
        c_before = curr_df.count()
        c_after = df_next.count()
        print(f"    * Vòng lặp {iteration}: {c_before:,} -> {c_after:,} dòng (Giảm {c_before - c_after:,} dòng)")
        
        curr_df = df_next
        if c_before == c_after:
            print(f"  -> K-core ViFoodRec đã HỘI TỤ sau {iteration} vòng lặp tại {c_after:,} dòng!")
            break
            
    df_ratings_final = curr_df
    r5_count = c_after
    r5_dropped = r4_count - r5_count
    # Số user và món còn lại lấy từ dữ liệu, không viết cứng vào chuỗi nhật ký
    n_users_final = df_ratings_final.select("user_id").distinct().count()
    n_foods_final = df_ratings_final.select("food_id").distinct().count()
    logs.append({
        "dataset": "vifoodrec_ratings",
        "step_name": "iterative_k_core_convergence",
        "rows_before": r4_count,
        "rows_after": r5_count,
        "rows_dropped": r5_dropped,
        "notes": f"Lọc K-core lặp tới hội tụ (K={k}, hội tụ sau {iteration} vòng lặp, còn {n_users_final:,} user và {n_foods_final:,} món)"
    })
    
    # ---------------------------------------------------------
    # 4. GẮN CỜ has_ratings CHO BẢNG FOODS
    # ---------------------------------------------------------
    print("\n[D] Gắn cờ has_ratings cho bảng foods...")
    rated_foods = df_ratings_final.select("food_id").distinct().withColumn("has_ratings", lit(True))
    df_foods_final = df_foods_parsed.join(rated_foods, on="food_id", how="left") \
                                    .withColumn("has_ratings", when(col("has_ratings").isNotNull(), lit(True)).otherwise(lit(False)))
                                    
    # ---------------------------------------------------------
    # 5. GHI DỮ LIỆU SẠCH RA PARQUET COALESCE(1)
    # ---------------------------------------------------------
    clean_rat_path = get_path("clean", "food_vietnam", "ratings_clean.parquet")
    clean_food_path = get_path("clean", "food_vietnam", "foods_clean.parquet")
    
    print(f"\n[E] Ghi Parquet sạch (coalesce 1 partition):")
    print(f"  - Ratings: {clean_rat_path}")
    df_ratings_final.coalesce(1).write.mode("overwrite").parquet(clean_rat_path)
    
    print(f"  - Foods  : {clean_food_path}")
    df_foods_final.coalesce(1).write.mode("overwrite").parquet(clean_food_path)
    
    print("  -> Ghi Parquet ViFoodRec hoàn tất thành công!")
    return logs


if __name__ == "__main__":
    t0 = time.time()
    clean_vietnam()
    print(f"Tổng thời gian làm sạch ViFoodRec: {time.time() - t0:.2f}s")
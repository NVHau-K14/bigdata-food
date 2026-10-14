"""
src/user_features.py
--------------------
Trích xuất đặc trưng người dùng và món ăn từ tập Train phục vụ phân cụm hành vi K-means (P8).
Chỉ sử dụng dữ liệu TRAIN để tránh rò rỉ dữ liệu (No Data Leakage).

Bao gồm:
1. extract_food_com_user_features: 8 đặc trưng hành vi người dùng Food.com.
2. extract_vifoodrec_user_features: 7 đặc trưng hành vi người dùng ViFoodRec.
3. extract_vifoodrec_food_features: 7 đặc trưng dinh dưỡng món ăn ViFoodRec.
"""

from pyspark.sql import DataFrame, functions as F


def extract_food_com_user_features(spark, train_df: DataFrame, recipes_df: DataFrame) -> DataFrame:
    """
    Trích xuất đặc trưng người dùng Food.com từ tập Train và thông tin món ăn.
    
    Các đặc trưng:
    - n_ratings: số lượt đánh giá
    - avg_rating: điểm đánh giá trung bình
    - std_rating: độ lệch chuẩn điểm đánh giá
    - pct_high_rating: tỷ lệ điểm cao (>= 4.0)
    - avg_minutes: thời gian nấu trung bình của món đã đánh giá (minutes_clean)
    - avg_calories: lượng calo trung bình của món đã đánh giá
    - avg_n_ingredients: số lượng nguyên liệu trung bình của món đã đánh giá
    - activity_span_days: khoảng thời gian hoạt động (ngày) giữa lần đánh giá đầu và cuối
    """
    print("-> Đang trích xuất đặc trưng người dùng Food.com...")

    # Join train với bảng recipes_clean để lấy thuộc tính món
    recipes_sub = recipes_df.select(
        "recipe_id", "minutes_clean", "calories", "n_ingredients"
    )

    joined = train_df.join(recipes_sub, on="recipe_id", how="left")

    # Gom nhóm theo user_id để tính các chỉ số thống kê
    user_agg = joined.groupBy("user_id").agg(
        F.count("rating").alias("n_ratings"),
        F.avg("rating").alias("avg_rating"),
        F.stddev("rating").alias("std_rating"),
        F.avg(F.when(F.col("rating") >= 4.0, 1.0).otherwise(0.0)).alias("pct_high_rating"),
        F.avg("minutes_clean").alias("avg_minutes"),
        F.avg("calories").alias("avg_calories"),
        F.avg("n_ingredients").alias("avg_n_ingredients"),
        F.min("date").alias("first_date"),
        F.max("date").alias("last_date")
    ).withColumn(
        "activity_span_days",
        F.coalesce(F.datediff(F.col("last_date"), F.col("first_date")), F.lit(0))
    ).drop("first_date", "last_date")

    # Điền giá trị khuyết thiếu (nếu user chỉ đánh giá 1 món thì std_rating là null)
    # Lấy trung bình toàn cục cho các cột dinh dưỡng/thời gian nếu món đó bị null
    global_means = recipes_df.select(
        F.avg("minutes_clean").alias("m_min"),
        F.avg("calories").alias("m_cal"),
        F.avg("n_ingredients").alias("m_ing")
    ).collect()[0]

    user_features = user_agg.fillna({
        "std_rating": 0.0,
        "avg_minutes": float(global_means["m_min"] or 30.0),
        "avg_calories": float(global_means["m_cal"] or 350.0),
        "avg_n_ingredients": float(global_means["m_ing"] or 8.0),
        "activity_span_days": 0
    })

    # Xử lý độ lệch (Skewness) bằng hàm log1p cho các biến đếm và khoảng rộng
    features_clean = user_features.withColumn("log_n_ratings", F.log1p("n_ratings")) \
                                  .withColumn("log_activity_span", F.log1p(F.col("activity_span_days").cast("double"))) \
                                  .withColumn("log_avg_minutes", F.log1p("avg_minutes")) \
                                  .withColumn("log_avg_calories", F.log1p("avg_calories"))

    return features_clean


def extract_vifoodrec_user_features(spark, train_df: DataFrame, foods_df: DataFrame) -> DataFrame:
    """
    Trích xuất đặc trưng người dùng ViFoodRec từ tập Train và thông tin món ăn.
    
    Các đặc trưng:
    - n_ratings: số lượt đánh giá
    - avg_rating: điểm trung bình
    - std_rating: độ lệch chuẩn điểm
    - pct_man_high: tỷ lệ món mặn được chấm cao (rating >= 4.0)
    - pct_chay_high: tỷ lệ món chay được chấm cao (rating >= 4.0)
    - avg_calo_high: calo trung bình của món được chấm cao
    - avg_time_high: thời gian nấu trung bình của món được chấm cao
    """
    print("-> Đang trích xuất đặc trưng người dùng ViFoodRec...")

    foods_sub = foods_df.select(
        "food_id", "dish_type", "calories", "cooking_time_min"
    )

    joined = train_df.join(foods_sub, on="food_id", how="left")

    user_agg = joined.groupBy("user_id").agg(
        F.count("rating").alias("n_ratings"),
        F.avg("rating").alias("avg_rating"),
        F.stddev("rating").alias("std_rating"),
        F.sum(F.when((F.col("dish_type") == "Món mặn") & (F.col("rating") >= 4.0), 1).otherwise(0)).alias("count_man_high"),
        F.sum(F.when((F.col("dish_type") == "Món chay") & (F.col("rating") >= 4.0), 1).otherwise(0)).alias("count_chay_high"),
        F.avg(F.when(F.col("rating") >= 4.0, F.col("calories"))).alias("avg_calo_high"),
        F.avg(F.when(F.col("rating") >= 4.0, F.col("cooking_time_min"))).alias("avg_time_high"),
        F.avg("calories").alias("avg_calo_all"),
        F.avg("cooking_time_min").alias("avg_time_all")
    )

    # Tính tỷ lệ và coalesce nếu user chưa có món cao
    user_features = user_agg.withColumn(
        "pct_man_high", F.col("count_man_high") / F.col("n_ratings")
    ).withColumn(
        "pct_chay_high", F.col("count_chay_high") / F.col("n_ratings")
    ).withColumn(
        "avg_calo_high", F.coalesce(F.col("avg_calo_high"), F.col("avg_calo_all"), F.lit(350.0))
    ).withColumn(
        "avg_time_high", F.coalesce(F.col("avg_time_high"), F.col("avg_time_all"), F.lit(30.0))
    ).fillna({"std_rating": 0.0}).drop("count_man_high", "count_chay_high", "avg_calo_all", "avg_time_all")

    # Log transform cho các trường đếm/rộng
    features_clean = user_features.withColumn("log_n_ratings", F.log1p("n_ratings")) \
                                  .withColumn("log_avg_calo_high", F.log1p("avg_calo_high")) \
                                  .withColumn("log_avg_time_high", F.log1p("avg_time_high"))

    return features_clean


def extract_vifoodrec_food_features(spark, foods_df: DataFrame) -> DataFrame:
    """
    Trích xuất đặc trưng dinh dưỡng món ăn ViFoodRec để phân cụm món ăn (Phần 2 P8).
    
    Các đặc trưng:
    - calories (calo)
    - protein (chất đạm)
    - fat (chất béo)
    - sugar (đường)
    - cooking_time_min (thời gian nấu, phút)
    - is_savory (1: Món mặn, 0: Món chay)
    - n_ingredients (số lượng nguyên liệu)
    """
    print("-> Đang trích xuất đặc trưng món ăn ViFoodRec...")

    food_sub = foods_df.select(
        "food_id", "dish_name", "dish_type", "calories", "protein", "fat", "sugar",
        "cooking_time_min", "ingredients"
    ).withColumn(
        "is_savory", F.when(F.col("dish_type") == "Món mặn", 1.0).otherwise(0.0)
    ).withColumn(
        "n_ingredients", F.when(F.col("ingredients").isNotNull(), F.size(F.split(F.col("ingredients"), ","))).otherwise(F.lit(5))
    )

    # Điền giá trị thiếu
    means = food_sub.select(
        F.avg("calories").alias("m_cal"),
        F.avg("protein").alias("m_pro"),
        F.avg("fat").alias("m_fat"),
        F.avg("sugar").alias("m_sug"),
        F.avg("cooking_time_min").alias("m_time"),
        F.avg("n_ingredients").alias("m_ing")
    ).collect()[0]

    food_clean = food_sub.fillna({
        "calories": float(means["m_cal"] or 350.0),
        "protein": float(means["m_pro"] or 15.0),
        "fat": float(means["m_fat"] or 10.0),
        "sugar": float(means["m_sug"] or 5.0),
        "cooking_time_min": float(means["m_time"] or 30.0),
        "n_ingredients": int(means["m_ing"] or 6)
    })

    # Log transform cho biến lệch
    food_features = food_clean.withColumn("log_calories", F.log1p("calories")) \
                              .withColumn("log_protein", F.log1p("protein")) \
                              .withColumn("log_fat", F.log1p("fat")) \
                              .withColumn("log_sugar", F.log1p("sugar")) \
                              .withColumn("log_cooking_time", F.log1p("cooking_time_min"))

    return food_features

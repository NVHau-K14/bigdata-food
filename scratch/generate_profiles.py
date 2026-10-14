"""
scratch/generate_profiles.py
----------------------------
Tính toán toàn bộ số liệu thống kê mô tả (Data Profile) cho cả Food.com và ViFoodRec:
- Số dòng, số user, số món, độ thưa (sparsity = 1 - rows / (users * items))
- Phân phối điểm rating
- Trung bình, trung vị (median), phân vị số tương tác/user và tương tác/món
- Phân vị các cột số của bảng món (minutes_clean, n_steps, n_ingredients, calories, v.v.)
"""

import sys
import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pyspark.sql.functions import col, count as spark_count, avg, min as spark_min, max as spark_max, expr
from src.config import get_spark_session, get_path


def compute_profiles():
    spark = get_spark_session("ComputeProfiles")
    
    # ---------------------------------------------------------
    # A. FOOD.COM PROFILE
    # ---------------------------------------------------------
    print("=== COMPUTING FOOD.COM PROFILE ===")
    df_fc_inter = spark.read.parquet(get_path("clean", "food_com", "interactions_clean.parquet"))
    df_fc_rec = spark.read.parquet(get_path("clean", "food_com", "recipes_clean.parquet"))
    
    fc_rows = df_fc_inter.count()
    fc_users = df_fc_inter.select("user_id").distinct().count()
    fc_items = df_fc_inter.select("recipe_id").distinct().count()
    fc_rec_total = df_fc_rec.count()
    fc_rec_with_ratings = df_fc_rec.filter(col("has_ratings") == True).count()
    
    fc_sparsity = 1.0 - (fc_rows / (fc_users * fc_items))
    
    # Rating distribution
    fc_rat_dist = df_fc_inter.groupBy("rating").count().orderBy("rating").collect()
    fc_dist_dict = {row["rating"]: row["count"] for row in fc_rat_dist}
    
    # User interaction stats
    u_counts = df_fc_inter.groupBy("user_id").agg(spark_count("recipe_id").alias("cnt"))
    fc_u_stats = u_counts.selectExpr(
        "avg(cnt) as avg_cnt",
        "percentile_approx(cnt, array(0.25, 0.5, 0.75, 0.9, 0.99), 10000) as quantiles",
        "min(cnt) as min_cnt",
        "max(cnt) as max_cnt"
    ).collect()[0]
    
    # Item interaction stats
    r_counts = df_fc_inter.groupBy("recipe_id").agg(spark_count("user_id").alias("cnt"))
    fc_r_stats = r_counts.selectExpr(
        "avg(cnt) as avg_cnt",
        "percentile_approx(cnt, array(0.25, 0.5, 0.75, 0.9, 0.99), 10000) as quantiles",
        "min(cnt) as min_cnt",
        "max(cnt) as max_cnt"
    ).collect()[0]
    
    # Recipes numeric columns percentiles
    fc_rec_stats = df_fc_rec.selectExpr(
        "percentile_approx(minutes_clean, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_minutes",
        "percentile_approx(n_steps, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_steps",
        "percentile_approx(n_ingredients, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_ingr",
        "percentile_approx(calories, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_cal",
        "percentile_approx(total_fat_pdv, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_fat",
        "percentile_approx(sugar_pdv, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_sugar",
        "percentile_approx(protein_pdv, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_protein"
    ).collect()[0]
    
    fc_data = {
        "rows": fc_rows,
        "users": fc_users,
        "items": fc_items,
        "recipes_total": fc_rec_total,
        "recipes_with_ratings": fc_rec_with_ratings,
        "sparsity": fc_sparsity,
        "rating_dist": fc_dist_dict,
        "user_avg": fc_u_stats["avg_cnt"],
        "user_min": fc_u_stats["min_cnt"],
        "user_max": fc_u_stats["max_cnt"],
        "user_quantiles": fc_u_stats["quantiles"],
        "item_avg": fc_r_stats["avg_cnt"],
        "item_min": fc_r_stats["min_cnt"],
        "item_max": fc_r_stats["max_cnt"],
        "item_quantiles": fc_r_stats["quantiles"],
        "rec_quantiles": {
            "minutes_clean": fc_rec_stats["p_minutes"],
            "n_steps": fc_rec_stats["p_steps"],
            "n_ingredients": fc_rec_stats["p_ingr"],
            "calories": fc_rec_stats["p_cal"],
            "total_fat_pdv": fc_rec_stats["p_fat"],
            "sugar_pdv": fc_rec_stats["p_sugar"],
            "protein_pdv": fc_rec_stats["p_protein"]
        }
    }
    
    # ---------------------------------------------------------
    # B. VIFOODREC PROFILE
    # ---------------------------------------------------------
    print("=== COMPUTING VIFOODREC PROFILE ===")
    df_vn_rat = spark.read.parquet(get_path("clean", "food_vietnam", "ratings_clean.parquet"))
    df_vn_food = spark.read.parquet(get_path("clean", "food_vietnam", "foods_clean.parquet"))
    
    vn_rows = df_vn_rat.count()
    vn_users = df_vn_rat.select("user_id").distinct().count()
    vn_items = df_vn_rat.select("food_id").distinct().count()
    vn_foods_total = df_vn_food.count()
    vn_foods_with_ratings = df_vn_food.filter(col("has_ratings") == True).count()
    
    vn_sparsity = 1.0 - (vn_rows / (vn_users * vn_items))
    
    # Rating distribution
    vn_rat_dist = df_vn_rat.groupBy("rating").count().orderBy("rating").collect()
    vn_dist_dict = {row["rating"]: row["count"] for row in vn_rat_dist}
    
    # User interaction stats
    vu_counts = df_vn_rat.groupBy("user_id").agg(spark_count("food_id").alias("cnt"))
    vn_u_stats = vu_counts.selectExpr(
        "avg(cnt) as avg_cnt",
        "percentile_approx(cnt, array(0.25, 0.5, 0.75, 0.9, 0.99), 10000) as quantiles",
        "min(cnt) as min_cnt",
        "max(cnt) as max_cnt"
    ).collect()[0]
    
    # Food interaction stats
    vf_counts = df_vn_rat.groupBy("food_id").agg(spark_count("user_id").alias("cnt"))
    vn_f_stats = vf_counts.selectExpr(
        "avg(cnt) as avg_cnt",
        "percentile_approx(cnt, array(0.25, 0.5, 0.75, 0.9, 0.99), 10000) as quantiles",
        "min(cnt) as min_cnt",
        "max(cnt) as max_cnt"
    ).collect()[0]
    
    # Foods numeric stats
    vn_food_stats = df_vn_food.selectExpr(
        "percentile_approx(cooking_time_min, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_time",
        "percentile_approx(serving_size_num, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_serving",
        "percentile_approx(calories, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_cal",
        "percentile_approx(fat, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_fat",
        "percentile_approx(fiber, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_fiber",
        "percentile_approx(sugar, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_sugar",
        "percentile_approx(protein, array(0.01, 0.25, 0.5, 0.75, 0.99), 10000) as p_protein"
    ).collect()[0]
    
    # Dish type distribution
    dish_types = df_vn_food.groupBy("dish_type").count().orderBy("count", ascending=False).collect()
    dish_types_dict = {row["dish_type"]: row["count"] for row in dish_types}
    
    vn_data = {
        "rows": vn_rows,
        "users": vn_users,
        "items": vn_items,
        "foods_total": vn_foods_total,
        "foods_with_ratings": vn_foods_with_ratings,
        "sparsity": vn_sparsity,
        "rating_dist": vn_dist_dict,
        "dish_types": dish_types_dict,
        "user_avg": vn_u_stats["avg_cnt"],
        "user_min": vn_u_stats["min_cnt"],
        "user_max": vn_u_stats["max_cnt"],
        "user_quantiles": vn_u_stats["quantiles"],
        "item_avg": vn_f_stats["avg_cnt"],
        "item_min": vn_f_stats["min_cnt"],
        "item_max": vn_f_stats["max_cnt"],
        "item_quantiles": vn_f_stats["quantiles"],
        "food_quantiles": {
            "cooking_time_min": vn_food_stats["p_time"],
            "serving_size_num": vn_food_stats["p_serving"],
            "calories": vn_food_stats["p_cal"],
            "fat": vn_food_stats["p_fat"],
            "fiber": vn_food_stats["p_fiber"],
            "sugar": vn_food_stats["p_sugar"],
            "protein": vn_food_stats["p_protein"]
        }
    }
    
    with open(ROOT_DIR / "scratch" / "profiles_summary.json", "w", encoding="utf-8") as f:
        json.dump({"food_com": fc_data, "vifoodrec": vn_data}, f, ensure_ascii=False, indent=2)
        
    print("SAVED profiles_summary.json successfully!")

if __name__ == "__main__":
    compute_profiles()

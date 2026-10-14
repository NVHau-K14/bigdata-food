"""
src/verify_clean.py
-------------------
Kịch bản kiểm chứng tự động độc lập cho dữ liệu sạch sau P3:
1. Kiểm tra NULL ở tất cả các cột khóa và rating.
2. Kiểm tra thang điểm: Food.com trong [1.0, 5.0]; ViFoodRec chỉ thuộc đúng 11 mức 0.0, 0.5, ..., 5.0.
3. Kiểm tra tính duy nhất (không trùng lặp cặp user - món).
4. Kiểm tra tiêu chí K-core (mọi user và mọi món có ít nhất 3 tương tác).
5. Kiểm tra toàn vẹn khóa ngoại (100% món trong tương tác phải có trong danh mục món).
6. Kiểm tra đối chiếu số dòng thực tế với cleaning_log.csv.
7. Thoát mã lỗi 0 nếu mọi kiểm tra ĐẠT, thoát mã lỗi 1 nếu có lỗi.
"""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
from pyspark.sql.functions import col, count as spark_count, min as spark_min, max as spark_max
from src.config import (
    get_spark_session, get_path, K_CORE_DEFAULT,
    RATING_MIN_VN, RATING_MAX_VN, RATING_STEP_VN
)


def verify_all():
    spark = get_spark_session("VerifyCleanP3")
    print("=" * 80)
    print("   BẮT ĐẦU KIỂM CHỨNG TỰ ĐỘNG ĐỘC LẬP (VERIFY CLEAN - P3)")
    print("=" * 80)
    
    passed_all = True
    check_results = []
    
    # ---------------------------------------------------------
    # 0. NẠP DỮ LIỆU SẠCH TỪ PARQUET
    # ---------------------------------------------------------
    path_fc_inter = get_path("clean", "food_com", "interactions_clean.parquet")
    path_fc_rec = get_path("clean", "food_com", "recipes_clean.parquet")
    path_vn_rat = get_path("clean", "food_vietnam", "ratings_clean.parquet")
    path_vn_food = get_path("clean", "food_vietnam", "foods_clean.parquet")
    
    print(f"\n[0] Nạp dữ liệu Parquet sạch:")
    print(f"  - Food.com interactions: {path_fc_inter}")
    print(f"  - Food.com recipes     : {path_fc_rec}")
    print(f"  - ViFoodRec ratings    : {path_vn_rat}")
    print(f"  - ViFoodRec foods      : {path_vn_food}")
    
    df_fc_inter = spark.read.parquet(path_fc_inter)
    df_fc_rec = spark.read.parquet(path_fc_rec)
    df_vn_rat = spark.read.parquet(path_vn_rat)
    df_vn_food = spark.read.parquet(path_vn_food)
    
    fc_inter_cnt = df_fc_inter.count()
    fc_rec_cnt = df_fc_rec.count()
    vn_rat_cnt = df_vn_rat.count()
    vn_food_cnt = df_vn_food.count()
    
    print(f"\n  * Số dòng đo được: Food.com inter={fc_inter_cnt:,}, recipes={fc_rec_cnt:,}")
    print(f"  * Số dòng đo được: ViFoodRec rat={vn_rat_cnt:,}, foods={vn_food_cnt:,}")
    
    # ---------------------------------------------------------
    # 1. KIỂM TRA NULL Ở CỘT KHÓA & RATING
    # ---------------------------------------------------------
    print("\n[1] Kiểm tra giá trị NULL ở các cột khóa chính và rating...")
    fc_inter_null = df_fc_inter.filter(
        col("user_id").isNull() | col("recipe_id").isNull() | col("rating").isNull()
    ).count()
    fc_rec_null = df_fc_rec.filter(col("recipe_id").isNull() | col("name").isNull()).count()
    vn_rat_null = df_vn_rat.filter(
        col("user_id").isNull() | col("food_id").isNull() | col("rating").isNull()
    ).count()
    vn_food_null = df_vn_food.filter(col("food_id").isNull() | col("dish_name").isNull()).count()
    
    ok1 = (fc_inter_null == 0 and fc_rec_null == 0 and vn_rat_null == 0 and vn_food_null == 0)
    check_results.append({
        "check": "No NULL in primary keys & ratings",
        "detail": f"fc_inter={fc_inter_null}, fc_rec={fc_rec_null}, vn_rat={vn_rat_null}, vn_food={vn_food_null}",
        "passed": ok1
    })
    print(f"  -> Kết quả: {'ĐẠT' if ok1 else 'KHÔNG ĐẠT'} (Tất cả NULL = 0)")
    if not ok1: passed_all = False

    # ---------------------------------------------------------
    # 2. KIỂM TRA THANG ĐIỂM RATING
    # ---------------------------------------------------------
    n_levels = int(round((RATING_MAX_VN - RATING_MIN_VN) / RATING_STEP_VN)) + 1
    vn_levels = [RATING_MIN_VN + i * RATING_STEP_VN for i in range(n_levels)]
    print(f"\n[2] Kiểm tra thang điểm: Food.com trong [1.0, 5.0]; ViFoodRec thuộc đúng {n_levels} mức {vn_levels[0]} đến {vn_levels[-1]}...")
    fc_rat_out = df_fc_inter.filter((col("rating") < 1.0) | (col("rating") > 5.0)).count()
    # So khớp bằng danh sách mức tường minh, không dùng khoảng, để bắt cả giá trị lệch bước 0.5
    vn_rat_out = df_vn_rat.filter(~col("rating").isin(vn_levels)).count()
    vn_distinct = sorted(r[0] for r in df_vn_rat.select("rating").distinct().collect())
    print(f"  - ViFoodRec: các mức điểm có trong dữ liệu sạch ({len(vn_distinct)} mức): {vn_distinct}")
    
    ok2 = (fc_rat_out == 0 and vn_rat_out == 0)
    check_results.append({
        "check": f"Rating scale (Food.com 1-5, ViFoodRec {n_levels} levels)",
        "detail": f"fc_out={fc_rat_out}, vn_out={vn_rat_out}, vn_distinct_levels={len(vn_distinct)}",
        "passed": ok2
    })
    print(f"  -> Kết quả: {'ĐẠT' if ok2 else 'KHÔNG ĐẠT'} (Điểm ngoài thang: Food.com={fc_rat_out}, ViFoodRec={vn_rat_out})")
    if not ok2: passed_all = False

    # ---------------------------------------------------------
    # 3. KIỂM TRA TRÙNG CẶP (USER, MÓN)
    # ---------------------------------------------------------
    print("\n[3] Kiểm tra tính duy nhất cặp (user, món)...")
    fc_pairs_cnt = df_fc_inter.select("user_id", "recipe_id").distinct().count()
    vn_pairs_cnt = df_vn_rat.select("user_id", "food_id").distinct().count()
    
    ok3_fc = (fc_inter_cnt == fc_pairs_cnt)
    ok3_vn = (vn_rat_cnt == vn_pairs_cnt)
    ok3 = ok3_fc and ok3_vn
    check_results.append({
        "check": "No duplicate (user, item) pairs",
        "detail": f"fc_inter({fc_inter_cnt}=={fc_pairs_cnt}), vn_rat({vn_rat_cnt}=={vn_pairs_cnt})",
        "passed": ok3
    })
    print(f"  -> Kết quả: {'ĐẠT' if ok3 else 'KHÔNG ĐẠT'} (Food.com: {ok3_fc}, ViFoodRec: {ok3_vn})")
    if not ok3: passed_all = False

    # ---------------------------------------------------------
    # 4. KIỂM TRA TIÊU CHÍ K-CORE (K >= 3)
    # ---------------------------------------------------------
    print(f"\n[4] Kiểm tra tiêu chí K-core (Ngưỡng K >= {K_CORE_DEFAULT})...")
    # Food.com
    fc_min_u = df_fc_inter.groupBy("user_id").agg(spark_count("recipe_id").alias("c")).agg(spark_min("c")).collect()[0][0]
    fc_min_r = df_fc_inter.groupBy("recipe_id").agg(spark_count("user_id").alias("c")).agg(spark_min("c")).collect()[0][0]
    
    # ViFoodRec
    vn_min_u = df_vn_rat.groupBy("user_id").agg(spark_count("food_id").alias("c")).agg(spark_min("c")).collect()[0][0]
    vn_min_f = df_vn_rat.groupBy("food_id").agg(spark_count("user_id").alias("c")).agg(spark_min("c")).collect()[0][0]
    
    ok4_fc = (fc_min_u is not None and fc_min_u >= K_CORE_DEFAULT and fc_min_r is not None and fc_min_r >= K_CORE_DEFAULT)
    ok4_vn = (vn_min_u is not None and vn_min_u >= K_CORE_DEFAULT and vn_min_f is not None and vn_min_f >= K_CORE_DEFAULT)
    ok4 = ok4_fc and ok4_vn
    
    check_results.append({
        "check": "K-core convergence (min interactions >= 3)",
        "detail": f"Food.com: min_u={fc_min_u}, min_r={fc_min_r} | ViFoodRec: min_u={vn_min_u}, min_f={vn_min_f}",
        "passed": ok4
    })
    print(f"  - Food.com  : min(user)={fc_min_u}, min(recipe)={fc_min_r} -> {'ĐẠT' if ok4_fc else 'KHÔNG ĐẠT'}")
    print(f"  - ViFoodRec : min(user)={vn_min_u}, min(food)={vn_min_f} -> {'ĐẠT' if ok4_vn else 'KHÔNG ĐẠT'}")
    print(f"  -> Kết quả K-core chung: {'ĐẠT' if ok4 else 'KHÔNG ĐẠT'}")
    if not ok4: passed_all = False

    # ---------------------------------------------------------
    # 5. KIỂM TRA TOÀN VẸN KHÓA NGOẠI
    # ---------------------------------------------------------
    print("\n[5] Kiểm tra toàn vẹn khóa ngoại (Foreign Key Integrity)...")
    # recipe_id trong interactions phải có trong recipes
    fc_orphan = df_fc_inter.join(df_fc_rec.select("recipe_id"), on="recipe_id", how="left_anti").count()
    # food_id trong ratings phải có trong foods
    vn_orphan = df_vn_rat.join(df_vn_food.select("food_id"), on="food_id", how="left_anti").count()
    
    ok5 = (fc_orphan == 0 and vn_orphan == 0)
    check_results.append({
        "check": "Foreign Key Integrity (0 orphan records)",
        "detail": f"fc_orphan={fc_orphan}, vn_orphan={vn_orphan}",
        "passed": ok5
    })
    print(f"  -> Kết quả: {'ĐẠT' if ok5 else 'KHÔNG ĐẠT'} (Food.com orphan={fc_orphan}, ViFoodRec orphan={vn_orphan})")
    if not ok5: passed_all = False

    # ---------------------------------------------------------
    # 6. ĐỐI CHIẾU SỐ DÒNG VỚI CLEANING_LOG.CSV
    # ---------------------------------------------------------
    print("\n[6] Đối chiếu số dòng với nhật ký cleaning_log.csv...")
    csv_log_path = ROOT_DIR / "reports" / "evidence" / "cleaning_log.csv"
    if not csv_log_path.exists():
        print(f"  [LỖI]: Không tìm thấy file {csv_log_path}!")
        ok6 = False
    else:
        df_log = pd.read_csv(csv_log_path)
        # Kiểm tra bước đầu vào thô
        raw_fc = df_log[(df_log["dataset"] == "food_com_interactions") & (df_log["step_name"] == "raw_input")]["rows_before"].values[0]
        raw_vn = df_log[(df_log["dataset"] == "vifoodrec_ratings") & (df_log["step_name"] == "raw_input")]["rows_before"].values[0]
        
        # Kiểm tra bước đầu ra cuối
        final_fc_inter = df_log[(df_log["dataset"] == "food_com_interactions") & (df_log["step_name"] == "iterative_k_core_convergence")]["rows_after"].values[0]
        final_fc_rec = df_log[(df_log["dataset"] == "food_com_recipes") & (df_log["step_name"] == "drop_duplicate_id")]["rows_after"].values[0]
        final_vn_rat = df_log[(df_log["dataset"] == "vifoodrec_ratings") & (df_log["step_name"] == "iterative_k_core_convergence")]["rows_after"].values[0]
        final_vn_food = df_log[(df_log["dataset"] == "vifoodrec_foods") & (df_log["step_name"] == "filter_null_id_name")]["rows_after"].values[0]
        
        ok6_raw = (raw_fc == 1132367 and raw_vn == 182678)
        ok6_final = (
            fc_inter_cnt == final_fc_inter and 
            fc_rec_cnt == final_fc_rec and 
            vn_rat_cnt == final_vn_rat and 
            vn_food_cnt == final_vn_food
        )
        ok6 = ok6_raw and ok6_final
        print(f"  - Số dòng thô: Food.com={raw_fc:,} (chuẩn 1,132,367), ViFoodRec={raw_vn:,} (chuẩn 182,678)")
        print(f"  - Khớp log cuối: fc_inter={fc_inter_cnt:,}=={final_fc_inter:,}, vn_rat={vn_rat_cnt:,}=={final_vn_rat:,}")
        
    check_results.append({
        "check": "Row count consistency with cleaning_log.csv",
        "detail": f"Raw matched={ok6_raw}, Final matched={ok6_final}",
        "passed": ok6
    })
    print(f"  -> Kết quả: {'ĐẠT' if ok6 else 'KHÔNG ĐẠT'}")
    if not ok6: passed_all = False

    # ---------------------------------------------------------
    # TỔNG KẾT VÀ EXIT
    # ---------------------------------------------------------
    print("\n" + "=" * 80)
    print("   BẢNG TỔNG HỢP KẾT QUẢ KIỂM CHỨNG TỰ ĐỘNG (VERIFY SUMMARY)")
    print("=" * 80)
    for idx, r in enumerate(check_results, 1):
        status = "ĐẠT [PASS]" if r["passed"] else "KHÔNG ĐẠT [FAIL]"
        print(f"{idx}. {r['check']:<45} : {status}")
        print(f"   Chi tiết: {r['detail']}")
        
    print("=" * 80)
    if passed_all:
        print("ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!")
        print("=" * 80)
        sys.exit(0)
    else:
        print("VERIFICATION FAILED: SOME CHECKS DID NOT PASS!")
        print("=" * 80)
        sys.exit(1)


if __name__ == "__main__":
    verify_all()

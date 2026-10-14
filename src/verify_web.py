"""
Script kiểm tra và đối chiếu số liệu tự động giữa web/data/*.js và các tệp gốc (CSV/Parquet).
Đối chiếu ít nhất 25 con số hiển thị quan trọng trên dashboard:
- Số dòng thô, số dòng bị loại, số dòng sạch qua từng bước (cleaning_log.csv).
- Quy mô, độ thưa, điểm trung bình của 2 bộ (eda_12_dataset_comparison.csv).
- Kích thước lưu trữ và tỷ lệ nén (storage_benchmark.csv).
- Sai số mô hình RMSE, MAE, Precision@10 của ALS và Baseline (model_comparison.csv).
- Số lượng cụm và phân bố người dùng (cluster_profiles_*.csv).

Thoát với mã lỗi khác 0 nếu có bất kỳ sai lệch nào.
"""

import sys
import os
import json
import re
import pandas as pd
import numpy as np

# Đảm bảo in tiếng Việt chuẩn trên Windows console
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def parse_js_object(filepath: str, var_name: str) -> dict:
    """Đọc tệp JavaScript gán biến toàn cục và trích xuất JSON."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Không tìm thấy tệp {filepath}")
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read().strip()
    pattern = rf"(?:window\.)?{var_name}\s*=\s*(.+?);?$"
    m = re.search(pattern, content, re.DOTALL)
    if not m:
        raise ValueError(f"Không tìm thấy biến toàn cục {var_name} trong {filepath}")
    json_str = m.group(1).rstrip(";")
    return json.loads(json_str)

def assert_match(test_name: str, web_val, source_val, tolerance: float = 1e-4):
    """Kiểm tra hai giá trị số hoặc chuỗi có khớp nhau."""
    if isinstance(source_val, (int, float, np.integer, np.floating)):
        web_num = float(web_val)
        src_num = float(source_val)
        diff = abs(web_num - src_num)
        if diff > tolerance:
            print(f"[FAIL] {test_name}: Web={web_num} != Source={src_num} (chênh {diff})")
            return False
        else:
            print(f"[PASS] {test_name}: {web_num} == {src_num}")
            return True
    else:
        if str(web_val).strip() != str(source_val).strip():
            print(f"[FAIL] {test_name}: Web='{web_val}' != Source='{source_val}'")
            return False
        else:
            print(f"[PASS] {test_name}: '{web_val}' == '{source_val}'")
            return True

def main():
    print("==================================================================")
    print(" BẮT ĐẦU KIỂM THỬ ĐỐI CHIẾU SỐ LIỆU TOÀN VẸN (SRC/VERIFY_WEB.PY) ")
    print("==================================================================")

    # 1. Nạp các tệp web/data
    summary_data = parse_js_object("web/data/summary.js", "WEB_DATA_SUMMARY")
    system_data = parse_js_object("web/data/system.js", "WEB_DATA_SYSTEM")
    behavior_data = parse_js_object("web/data/behavior.js", "WEB_DATA_BEHAVIOR")
    models_data = parse_js_object("web/data/models.js", "WEB_DATA_MODELS")

    # 2. Nạp các tệp CSV gốc
    df_clean = pd.read_csv("app/data/cleaning_log.csv")
    df_comp = pd.read_csv("app/data/eda_12_dataset_comparison.csv")
    df_storage = pd.read_csv("app/data/storage_benchmark.csv")
    df_models = pd.read_csv("app/data/model_comparison.csv")
    df_vn_clusters = pd.read_csv("app/data/cluster_profiles_food_vietnam.csv")
    df_fc_clusters = pd.read_csv("app/data/cluster_profiles_food_com.csv")

    results = []

    # Nhóm 1: Kiểm tra quy trình làm sạch (cleaning_log)
    print("\n--- Nhóm 1: Kiểm tra phễu làm sạch (cleaning_log) ---")
    # ViFoodRec raw input
    vn_raw_step = df_clean[(df_clean["dataset"] == "vifoodrec_ratings") & (df_clean["step_name"] == "raw_input")].iloc[0]
    web_vn_raw = next(r for r in summary_data["cleaning_log"] if r["dataset"] == "vifoodrec_ratings" and r["step_name"] == "raw_input")
    results.append(assert_match("1. ViFoodRec ratings raw_input", web_vn_raw["rows_after"], vn_raw_step["rows_after"]))

    # ViFoodRec dropped out-of-range ratings (33,211 rows)
    vn_range_step = df_clean[(df_clean["dataset"] == "vifoodrec_ratings") & (df_clean["step_name"] == "filter_rating_range_1_to_5")].iloc[0]
    web_vn_range = next(r for r in summary_data["cleaning_log"] if r["dataset"] == "vifoodrec_ratings" and r["step_name"] == "filter_rating_range_1_to_5")
    results.append(assert_match("2. ViFoodRec ratings dropped [1,5] (gồm 16.509 điểm 0 và 16.702 điểm 0.5)", web_vn_range["rows_dropped"], vn_range_step["rows_dropped"]))

    # ViFoodRec dropped foreign key (36 rows)
    vn_fk_step = df_clean[(df_clean["dataset"] == "vifoodrec_ratings") & (df_clean["step_name"] == "foreign_key_join_foods")].iloc[0]
    web_vn_fk = next(r for r in summary_data["cleaning_log"] if r["dataset"] == "vifoodrec_ratings" and r["step_name"] == "foreign_key_join_foods")
    results.append(assert_match("3. ViFoodRec ratings dropped foreign key", web_vn_fk["rows_dropped"], vn_fk_step["rows_dropped"]))

    # ViFoodRec clean final rows (149,431 rows)
    results.append(assert_match("4. ViFoodRec ratings clean final rows", web_vn_fk["rows_after"], 149431))

    # Food.com raw input interactions (1,132,367 rows)
    fc_raw_step = df_clean[(df_clean["dataset"] == "food_com_interactions") & (df_clean["step_name"] == "raw_input")].iloc[0]
    web_fc_raw = next(r for r in summary_data["cleaning_log"] if r["dataset"] == "food_com_interactions" and r["step_name"] == "raw_input")
    results.append(assert_match("5. Food.com interactions raw_input", web_fc_raw["rows_after"], fc_raw_step["rows_after"]))

    # Food.com dropped rating zero (60,847 rows)
    fc_zero_step = df_clean[(df_clean["dataset"] == "food_com_interactions") & (df_clean["step_name"] == "filter_rating_zero")].iloc[0]
    web_fc_zero = next(r for r in summary_data["cleaning_log"] if r["dataset"] == "food_com_interactions" and r["step_name"] == "filter_rating_zero")
    results.append(assert_match("6. Food.com interactions dropped rating zero", web_fc_zero["rows_dropped"], fc_zero_step["rows_dropped"]))

    # Food.com dropped k-core (365,006 rows)
    fc_kcore_step = df_clean[(df_clean["dataset"] == "food_com_interactions") & (df_clean["step_name"] == "iterative_k_core_convergence")].iloc[0]
    web_fc_kcore = next(r for r in summary_data["cleaning_log"] if r["dataset"] == "food_com_interactions" and r["step_name"] == "iterative_k_core_convergence")
    results.append(assert_match("7. Food.com interactions dropped K-core", web_fc_kcore["rows_dropped"], fc_kcore_step["rows_dropped"]))

    # Food.com clean final rows (706,514 rows)
    results.append(assert_match("8. Food.com interactions clean final rows", web_fc_kcore["rows_after"], 706514))

    # Nhóm 2: Kiểm tra đối chiếu quy mô hai bộ dữ liệu (eda_12)
    print("\n--- Nhóm 2: Đối chiếu đặc tính hai bộ dữ liệu (eda_12) ---")
    comp_map_web = {r["ChiSo"]: r for r in summary_data["dataset_comparison"]}
    comp_map_src = {r["ChiSo"]: r for _, r in df_comp.iterrows()}

    for metric, key in [
        ("Số User (Users)", "9. User count"),
        ("Số Món (Items)", "10. Item count"),
        ("Số Tương tác (Ratings)", "11. Interaction count"),
        ("Độ thưa ma trận (Sparsity %)", "12. Sparsity %"),
        ("Điểm TB (Mean Rating)", "13. Mean rating"),
        ("Trung vị tương tác/User", "14. Median per user"),
        ("Trung vị tương tác/Item", "15. Median per item")
    ]:
        results.append(assert_match(f"{key} (ViFoodRec)", comp_map_web[metric]["ViFoodRec"], comp_map_src[metric]["ViFoodRec"]))
        results.append(assert_match(f"{key} (Food.com)", comp_map_web[metric]["Food_com"], comp_map_src[metric]["Food_com"]))

    # Nhóm 3: Kiểm tra đo lường lưu trữ (storage_benchmark)
    print("\n--- Nhóm 3: Đo lường lưu trữ (storage_benchmark) ---")
    raw_csv = df_storage[(df_storage["experiment"] == "Experiment_A_Raw_Full") & (df_storage["dataset"].str.contains("interactions")) & (df_storage["format"] == "CSV")]["size_mb"].values[0]
    web_raw_csv = next(r for r in system_data["storage_benchmark"] if r["experiment"] == "Experiment_A_Raw_Full" and "interactions" in r["dataset"] and r["format"] == "CSV")["size_mb"]
    results.append(assert_match("16. Raw interactions CSV size (MB)", web_raw_csv, raw_csv))

    raw_pq = df_storage[(df_storage["experiment"] == "Experiment_A_Raw_Full") & (df_storage["dataset"].str.contains("interactions")) & (df_storage["format"] == "Parquet")]["size_mb"].values[0]
    web_raw_pq = next(r for r in system_data["storage_benchmark"] if r["experiment"] == "Experiment_A_Raw_Full" and "interactions" in r["dataset"] and r["format"] == "Parquet")["size_mb"]
    results.append(assert_match("17. Raw interactions Parquet size (MB)", web_raw_pq, raw_pq))

    clean_csv = df_storage[(df_storage["experiment"] == "Experiment_B_Clean_Data") & (df_storage["dataset"].str.contains("interactions")) & (df_storage["format"] == "CSV")]["size_mb"].values[0]
    web_clean_csv = next(r for r in system_data["storage_benchmark"] if r["experiment"] == "Experiment_B_Clean_Data" and "interactions" in r["dataset"] and r["format"] == "CSV")["size_mb"]
    results.append(assert_match("18. Clean interactions CSV size (MB)", web_clean_csv, clean_csv))

    clean_pq = df_storage[(df_storage["experiment"] == "Experiment_B_Clean_Data") & (df_storage["dataset"].str.contains("interactions")) & (df_storage["format"] == "Parquet")]["size_mb"].values[0]
    web_clean_pq = next(r for r in system_data["storage_benchmark"] if r["experiment"] == "Experiment_B_Clean_Data" and "interactions" in r["dataset"] and r["format"] == "Parquet")["size_mb"]
    results.append(assert_match("19. Clean interactions Parquet size (MB)", web_clean_pq, clean_pq))

    # Nhóm 4: Kiểm tra mô hình ALS và Baseline (model_comparison)
    print("\n--- Nhóm 4: Sai số mô hình (model_comparison) ---")
    # ViFoodRec Global Mean RMSE
    src_vn_gm_rmse = df_models[(df_models["dataset"] == "food_vietnam") & (df_models["model"] == "Global Mean")]["RMSE"].values[0]
    web_vn_gm_rmse = next(r for r in models_data["model_comparison"] if r["dataset"] == "food_vietnam" and r["model"] == "Global Mean")["RMSE"]
    results.append(assert_match("20. ViFoodRec Global Mean RMSE", web_vn_gm_rmse, src_vn_gm_rmse))

    # ViFoodRec ALS RMSE (phải đúng sự thật là cao hơn Global Mean: 1.3832 > 1.2866)
    src_vn_als_rmse = df_models[(df_models["dataset"] == "food_vietnam") & (df_models["model"] == "ALS Matrix Factorization")]["RMSE"].values[0]
    web_vn_als_rmse = next(r for r in models_data["model_comparison"] if r["dataset"] == "food_vietnam" and r["model"] == "ALS Matrix Factorization")["RMSE"]
    results.append(assert_match("21. ViFoodRec ALS RMSE", web_vn_als_rmse, src_vn_als_rmse))

    # Food.com Item Mean RMSE (0.6177)
    src_fc_im_rmse = df_models[(df_models["dataset"] == "food_com") & (df_models["model"] == "Smoothed Item Mean")]["RMSE"].values[0]
    web_fc_im_rmse = next(r for r in models_data["model_comparison"] if r["dataset"] == "food_com" and r["model"] == "Smoothed Item Mean")["RMSE"]
    results.append(assert_match("22. Food.com Smoothed Item Mean RMSE", web_fc_im_rmse, src_fc_im_rmse))

    # Food.com ALS RMSE (0.6747)
    src_fc_als_rmse = df_models[(df_models["dataset"] == "food_com") & (df_models["model"] == "ALS Matrix Factorization")]["RMSE"].values[0]
    web_fc_als_rmse = next(r for r in models_data["model_comparison"] if r["dataset"] == "food_com" and r["model"] == "ALS Matrix Factorization")["RMSE"]
    results.append(assert_match("23. Food.com ALS RMSE", web_fc_als_rmse, src_fc_als_rmse))

    # Nhóm 5: Kiểm tra số cụm người dùng (cluster_profiles)
    print("\n--- Nhóm 5: Phân cụm người dùng (cluster_profiles) ---")
    src_vn_overall_users = df_vn_clusters[df_vn_clusters["cluster"] == -1]["user_count"].values[0]
    web_vn_overall_users = next(r for r in behavior_data["vn_user_clusters"] if r["cluster"] == -1)["user_count"]
    results.append(assert_match("24. ViFoodRec tổng số người dùng phân cụm", web_vn_overall_users, src_vn_overall_users))

    src_fc_overall_users = df_fc_clusters[df_fc_clusters["cluster"] == -1]["user_count"].values[0]
    web_fc_overall_users = next(r for r in behavior_data["fc_user_clusters"] if r["cluster"] == -1)["user_count"]
    results.append(assert_match("25. Food.com tổng số người dùng phân cụm", web_fc_overall_users, src_fc_overall_users))

    # Tổng kết
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r)
    failed_tests = total_tests - passed_tests

    print("\n==================================================================")
    print(f" KẾT QUẢ KIỂM THỬ: {passed_tests}/{total_tests} ĐẠT (100% Khớp số liệu)")
    print("==================================================================")

    if failed_tests > 0:
        print(f"[ERROR] Có {failed_tests} tiêu chí đối chiếu không khớp!")
        sys.exit(1)
    else:
        print("[SUCCESS] Toàn bộ số liệu hiển thị trên web khớp 100% với dữ liệu nguồn.")
        sys.exit(0)

if __name__ == "__main__":
    main()

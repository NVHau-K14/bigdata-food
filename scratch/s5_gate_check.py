"""
S5: cổng kiểm tra. Đối chiếu các số ở mục 6 của STATUS.md với file nguồn; chọn ngẫu nhiên 5 số để in riêng.
"""
import random
import pandas as pd

R = "results/"
mc = pd.read_csv(R + "model_comparison.csv")
cl = pd.read_csv("reports/evidence/cleaning_log.csv", encoding="utf-8-sig")
sp = pd.read_csv("reports/evidence/split_log.csv").set_index("dataset")
e12 = pd.read_csv(R + "eda/eda_12_dataset_comparison.csv").set_index("ChiSo")
kt = pd.read_csv(R + "kmeans_tuning.csv")
sb = pd.read_csv("data/results/storage_benchmark.csv", encoding="utf-8-sig")
sc = pd.read_csv(R + "scalability.csv")

def m(ds, model, col):
    return float(mc[(mc.dataset == ds) & (mc.model == model)][col].iloc[0])

def kt_sil(task, k):
    return float(kt[(kt.task == task) & (kt.k == k)].silhouette.iloc[0])

checks = [
    ("Food.com ALS RMSE", m("food_com", "ALS Matrix Factorization", "RMSE"), 0.6747),
    ("Food.com ALS ngầm định P@10", m("food_com", "ALS ngầm định (điểm >= 4)", "Precision@10"), 0.0057),
    ("ViFoodRec Global Mean RMSE", m("food_vietnam", "Global Mean", "RMSE"), 1.5706),
    ("ViFoodRec ALS MAE", m("food_vietnam", "ALS Matrix Factorization", "MAE"), 1.4185),
    ("ViFoodRec Top-N P@10", m("food_vietnam", "Top-N Popular", "Precision@10"), 0.02277),
    ("ViFoodRec ALS ngầm định R@10", m("food_vietnam", "ALS ngầm định (điểm >= 4)", "Recall@10"), 0.00428),
    ("Food.com số dòng thô", float(cl[(cl.dataset == "food_com_interactions") & (cl.step_name == "raw_input")].rows_after.iloc[0]), 1132367),
    ("Food.com số dòng sạch", float(cl[(cl.dataset == "food_com_interactions") & (cl.step_name == "iterative_k_core_convergence")].rows_after.iloc[0]), 706514),
    ("ViFoodRec số dòng sạch", float(cl[(cl.dataset == "vifoodrec_ratings") & (cl.step_name == "iterative_k_core_convergence")].rows_after.iloc[0]), 182631),
    ("ViFoodRec dòng loại khóa ngoại", float(cl[(cl.dataset == "vifoodrec_ratings") & (cl.step_name == "foreign_key_join_foods")].rows_dropped.iloc[0]), 47),
    ("Food.com dòng bị loại tổng", float(cl[(cl.dataset == "food_com_interactions")].rows_dropped.sum()), 425853),
    ("Food.com số người dùng", e12.loc["Số User (Users)", "Food_com"], 30836),
    ("ViFoodRec độ thưa", e12.loc["Độ thưa ma trận (Sparsity %)", "ViFoodRec"], 54.79),
    ("Food.com điểm TB", e12.loc["Điểm TB (Mean Rating)", "Food_com"], 4.71),
    ("Food.com train", float(sp.loc["food_com", "train_rows"]), 565420),
    ("ViFoodRec test", float(sp.loc["food_vietnam", "test_clean_rows"]), 18415),
    ("Food.com cold-start val", float(sp.loc["food_com", "val_dropped_rows"]), 422),
    ("Silhouette Food.com k=4", kt_sil("Food.com Users", 4), 0.2743),
    ("Silhouette ViFoodRec Users k=3", kt_sil("ViFoodRec Users", 3), 0.2219),
    ("Silhouette ViFoodRec Foods k=4", kt_sil("ViFoodRec Foods", 4), 0.2334),
    ("Storage nén interactions sạch", round(float(sb[(sb.dataset == "Food.com interactions_clean") & (sb.format == "CSV")].size_mb.iloc[0]) / float(sb[(sb.dataset == "Food.com interactions_clean") & (sb.format == "Parquet")].size_mb.iloc[0]), 2), 4.19),
    ("Mở rộng 2W 100%", float(sc[(sc.sample_ratio == "100%") & (sc.resource.str.startswith("2")) & (sc.step == "Tổng cộng Pipeline")].avg_time.iloc[0]), 7.933),
    ("Mở rộng 1W 10%", float(sc[(sc.sample_ratio == "10%") & (sc.resource.str.startswith("1")) & (sc.step == "Tổng cộng Pipeline")].avg_time.iloc[0]), 10.583),
]
bad = 0
for name, got, exp in checks:
    ok = abs(got - exp) < 1e-6 or (abs(exp) < 100 and abs(got - exp) < 0.5 * 10 ** -len(str(exp).split(".")[-1]) + 1e-12)
    bad += (not ok)
    print(("ĐẠT " if ok else "SAI  "), f"{name}: nguồn = {got} | STATUS = {exp}")
print("Tổng:", len(checks), "| sai:", bad)
random.seed(5)
print("5 số chọn ngẫu nhiên:", [c[0] for c in random.sample(checks, 5)])

"""
S5: kiểm chứng các số ở mục 4B của STATUS cũ bằng cách tính lại từ file kết quả (chỉ đọc).
"""
import pandas as pd

R = "results/"
# mu suy ra từ RMSE theo mức điểm của Global Mean: RMSE tại mức r = |r - mu| (một điểm dữ liệu cùng mức, dự đoán hằng số)
bd = pd.read_csv(R + "baseline_rmse_breakdown.csv")
for ds, level_hi, level_lo in [("food_com", 5.0, 1.0), ("food_vietnam", 5.0, 0.0)]:
    g = bd[(bd.dataset == ds) & (bd.model == "Global Mean")].set_index("rating_level")["rmse"]
    print(f"{ds}: mu suy từ mức {level_hi} = {level_hi - g[level_hi]:.4f}; từ mức {level_lo} = {level_lo + g[level_lo]:.4f}")

# B2: giảm RMSE của ALS ở mức 1,0 sao, Food.com
als = pd.read_csv(R + "als_rmse_breakdown.csv")
fc_als = als[als.dataset == "food_com"].set_index("rating_level")["rmse"]
for base in ["Global Mean", "Smoothed Item Mean", "Top-N Popular"]:
    b = bd[(bd.dataset == "food_com") & (bd.model == base)].set_index("rating_level")["rmse"]
    print(f"Food.com mức 1,0: ALS {fc_als[1.0]} so với {base} {b[1.0]} -> {100*(fc_als[1.0]-b[1.0])/b[1.0]:+.1f}%")
b = bd[(bd.dataset == "food_com") & (bd.model == "Smoothed Item Mean")].set_index("rating_level")["rmse"]
for lv in [1.0, 2.0, 3.0, 4.0, 5.0]:
    print(f"  mức {lv}: ALS so với Smoothed Item Mean {100*(fc_als[lv]-b[lv])/b[lv]:+.1f}%")

# B3: cụm Food.com nhỏ nhất
c = pd.read_csv(R + "cluster_profiles_food_com.csv")
c = c[c.cluster >= 0]
print("Food.com tỷ lệ người dùng mỗi cụm:", dict(zip(c.cluster, c.user_pct)), "| nhỏ nhất =", c.user_pct.min())
cv = pd.read_csv(R + "cluster_profiles_food_vietnam.csv")
print("ViFoodRec người dùng mỗi cụm:", dict(zip(cv.cluster, cv.user_pct)) if "user_pct" in cv else cv.columns.tolist())

# B4: kmeans_tuning có cột kích thước cụm không
kt = pd.read_csv(R + "kmeans_tuning.csv")
print("Cột của kmeans_tuning.csv:", list(kt.columns))

# B5/B6: scalability.csv có cột thứ tự chạy không
sc = pd.read_csv(R + "scalability.csv")
print("Cột của scalability.csv:", list(sc.columns))
tot = sc[sc.step == "Tổng cộng Pipeline"].pivot(index="sample_ratio", columns="resource", values=["time_run_1", "time_run_2", "avg_time"])
print(tot.to_string())

# B7: P@10 ngẫu nhiên: ước tính thô trong STATUS cũ (ViFoodRec) không còn áp dụng, không tính lại ở đây

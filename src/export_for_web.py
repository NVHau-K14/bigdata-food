"""
Script xuất dữ liệu chuẩn hóa phục vụ web dashboard tĩnh (HTML/CSS/JS thuần).
Đọc các tập dữ liệu từ app/data/ (và docker-compose.yml, log của S1 đến S3), xuất thành các tệp JavaScript
gán dữ liệu vào các đối tượng toàn cục (window.WEB_DATA_*) để chạy offline, không bị chặn bởi
CORS/file:// khi mở trực tiếp index.html.

S4: mọi số và chữ hiển thị trên web đến từ dữ liệu, không viết cứng trong JS. Các trường "facts" chỉ chứa SỐ
(định dạng kiểu Việt Nam làm ở web/js/format.js, một hàm duy nhất). Nhãn hiển thị lấy từ src/web_labels.py.

Tuân thủ ngân sách dung lượng và hợp đồng dữ liệu docs/web_data_contract.md.
"""

import os
import re
import sys
import json
import pandas as pd
import numpy as np

# Đảm bảo in tiếng Việt trên console Windows không bị lỗi cp1252
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import web_labels as WL  # noqa: E402

OUTPUT_DIR = "web/data"


def clean_val(val):
    """Xử lý giá trị float/int NaN hoặc vô cùng trước khi xuất JSON."""
    if val is None:
        return None
    if isinstance(val, (list, tuple, dict, np.ndarray)):
        return val
    if pd.isna(val):
        return None
    if isinstance(val, (np.floating, float)):
        if np.isnan(val) or np.isinf(val):
            return None
        return round(float(val), 6)
    if isinstance(val, (np.integer, int)):
        return int(val)
    return val


def df_to_clean_records(df: pd.DataFrame) -> list:
    """Chuyển DataFrame sang danh sách bản ghi đã làm sạch NaN."""
    return [{k: clean_val(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def write_js(var_name: str, payload: dict, filename: str):
    out_file = os.path.join(OUTPUT_DIR, filename)
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(f"window.{var_name} = " + json.dumps(payload, ensure_ascii=False) + ";\n")
    print(f"   Đã ghi {out_file} ({os.path.getsize(out_file) / 1024:.1f} KB)")


def read_csv(path):
    return pd.read_csv(path, encoding="utf-8-sig")


# =============================================================================
# labels.js
# =============================================================================
def export_labels():
    print("-> Xuất labels.js...")
    write_js("WEB_LABELS", {
        "dish_type": WL.DISH_TYPE_LABELS,
        "models": WL.MODEL_LABELS,
        "datasets": WL.DATASET_LABELS,
        "cluster_name_replacements": WL.CLUSTER_NAME_REPLACEMENTS,
    }, "labels.js")


# =============================================================================
# summary.js (Trang 1: Dữ liệu)
# =============================================================================
def export_summary():
    print("-> Xuất summary.js...")
    log = read_csv("app/data/cleaning_log.csv")
    comp = read_csv("app/data/eda_12_dataset_comparison.csv")
    rd_vn = read_csv("app/data/eda/eda_01_vifoodrec_rating_dist.csv")
    rd_fc = read_csv("app/data/eda/eda_01_food_com_rating_dist.csv")

    def step(dataset, name):
        return log[(log["dataset"] == dataset) & (log["step_name"] == name)].iloc[0]

    # Phễu ViFoodRec: các bước lấy từ cleaning_log.csv; chữ không chứa số, số được web điền từ trường dữ liệu
    vn_raw = step("vifoodrec_ratings", "raw_input")
    vn_scale = step("vifoodrec_ratings", "filter_rating_scale_0_to_5_step_half")
    vn_fk = step("vifoodrec_ratings", "foreign_key_join_foods")
    vn_kc = step("vifoodrec_ratings", "iterative_k_core_convergence")
    vn_rounds = int(re.search(r"sau (\d+) vòng", vn_kc["notes"]).group(1))
    fc_raw = step("food_com_interactions", "raw_input")
    fc_zero = step("food_com_interactions", "filter_rating_zero")
    fc_kc = step("food_com_interactions", "iterative_k_core_convergence")
    fc_rounds = int(re.search(r"sau (\d+) vòng", fc_kc["notes"]).group(1))

    funnel = {
        "vifoodrec": [
            {"key": "raw", "count": int(vn_raw["rows_after"]), "dropped": 0},
            {"key": "scale", "count": int(vn_scale["rows_after"]), "dropped": int(vn_scale["rows_dropped"]),
             "levels": int(len(rd_vn))},
            {"key": "fk", "count": int(vn_fk["rows_after"]), "dropped": int(vn_fk["rows_dropped"])},
            {"key": "kcore", "count": int(vn_kc["rows_after"]), "dropped": int(vn_kc["rows_dropped"]),
             "rounds": vn_rounds},
        ],
        "food_com": [
            {"key": "raw", "count": int(fc_raw["rows_after"]), "dropped": 0},
            {"key": "zero", "count": int(fc_zero["rows_after"]), "dropped": int(fc_zero["rows_dropped"])},
            {"key": "kcore", "count": int(fc_kc["rows_after"]), "dropped": int(fc_kc["rows_dropped"]),
             "rounds": fc_rounds},
        ],
    }

    comp_map = {r["ChiSo"]: r for _, r in comp.iterrows()}
    comparison = []
    for raw_label, label in WL.COMPARISON_LABELS.items():
        r = comp_map[raw_label]
        comparison.append({"key": raw_label, "label": label,
                           "vifoodrec": clean_val(r["ViFoodRec"]), "food_com": clean_val(r["Food_com"])})

    fc_5 = float(rd_fc[rd_fc["rating"] == 5.0]["pct"].iloc[0])
    facts = {
        "vn_users": int(comp_map["Số User (Users)"]["ViFoodRec"]),
        "vn_items": int(comp_map["Số Món (Items)"]["ViFoodRec"]),
        "vn_ratings": int(comp_map["Số Tương tác (Ratings)"]["ViFoodRec"]),
        "vn_sparsity": float(comp_map["Độ thưa ma trận (Sparsity %)"]["ViFoodRec"]),
        "fc_users": int(comp_map["Số User (Users)"]["Food_com"]),
        "fc_items": int(comp_map["Số Món (Items)"]["Food_com"]),
        "fc_ratings": int(comp_map["Số Tương tác (Ratings)"]["Food_com"]),
        "fc_sparsity": float(comp_map["Độ thưa ma trận (Sparsity %)"]["Food_com"]),
        "vn_levels": int(len(rd_vn)),
        "vn_min_pct": float(rd_vn["pct"].min()),
        "vn_max_pct": float(rd_vn["pct"].max()),
        "fc_pct5": fc_5,
        "vn_fk_dropped": int(vn_fk["rows_dropped"]),
    }

    write_js("WEB_DATA_SUMMARY", {
        "cleaning_log": df_to_clean_records(log),
        "funnel": funnel,
        "dataset_comparison": comparison,
        "rating_dist_vn": df_to_clean_records(rd_vn),
        "rating_dist_fc": df_to_clean_records(rd_fc),
        "facts": facts,
        "source": "cleaning_log.csv, eda_12_dataset_comparison.csv, eda_01_vifoodrec_rating_dist.csv, eda_01_food_com_rating_dist.csv",
    }, "summary.js")


# =============================================================================
# system.js (Trang 2: Hệ thống)
# =============================================================================
def parse_compose(path="docker-compose.yml"):
    """Đọc phiên bản và cấu hình cụm từ docker-compose.yml (không dùng PyYAML)."""
    text = open(path, encoding="utf-8").read()
    hadoop_tag = re.search(r"image:\s*apache/hadoop:([\d.]+)", text).group(1)
    spark_tag = re.search(r"image:\s*quay\.io/jupyter/pyspark-notebook:spark-([\d.]+)", text).group(1)
    replication = int(re.search(r'dfs\.replication:\s*"(\d+)"', text).group(1))
    names = re.findall(r"container_name:\s*(\S+)", text)
    workers = re.findall(r"-c\", \"(\d+)\", \"-m\", \"(\d+)M\"", text)
    return {
        "hadoop_version": hadoop_tag,
        "spark_image_version": spark_tag,
        "replication": replication,
        "n_namenodes": sum(1 for n in names if n.startswith("namenode")),
        "n_datanodes": sum(1 for n in names if n.startswith("datanode")),
        "n_masters": sum(1 for n in names if n.startswith("spark-master")),
        "n_workers": sum(1 for n in names if n.startswith("spark-worker")),
        "worker_cores": int(workers[0][0]) if workers else None,
        "worker_ram_mb": int(workers[0][1]) if workers else None,
    }


def parse_spark_runtime_version():
    """Phiên bản Spark thật chạy pipeline, trích từ log của một lần chạy (dòng 'Running Spark version')."""
    log_path = "reports/evidence/logs/S2_03_clean_vietnam.log"
    m = re.search(r"Running Spark version ([\d.]+)", open(log_path, encoding="utf-8", errors="replace").read())
    return m.group(1) if m else None


def parse_fsck(path="reports/evidence/logs/S3_14_fsck.log"):
    text = open(path, encoding="utf-8", errors="replace").read()
    out = []
    for block in re.split(r"== fsck ", text)[1:]:
        p = block.splitlines()[0].strip()
        status = re.search(r"Status:\s*(\w+)", block).group(1)
        under = int(re.search(r"Under-replicated blocks:\s*(\d+)", block).group(1))
        files = int(re.search(r"Total files:\s*(\d+)", block).group(1))
        out.append({"path": p, "status": status, "under_replicated": under, "files": files})
    return out


def export_system():
    print("-> Xuất system.js...")
    storage = read_csv("app/data/storage_benchmark.csv")
    scal = read_csv("app/data/scalability.csv")
    cfg = parse_compose()
    spark_runtime = parse_spark_runtime_version()
    fsck = parse_fsck()

    def size(exp, ds, fmt):
        return float(storage[(storage["experiment"] == exp) & (storage["dataset"] == ds) & (storage["format"] == fmt)]["size_mb"].iloc[0])

    storage_rows = []
    for exp, ds, label in [
        ("Experiment_A_Raw_Full", "Food.com RAW_interactions", "Đánh giá thô"),
        ("Experiment_A_Raw_Full", "Food.com RAW_recipes", "Công thức thô"),
        ("Experiment_B_Clean_Data", "Food.com interactions_clean", "Đánh giá sạch"),
        ("Experiment_B_Clean_Data", "Food.com recipes_clean", "Công thức sạch"),
    ]:
        c, p = size(exp, ds, "CSV"), size(exp, ds, "Parquet")
        storage_rows.append({"label": label, "dataset": ds, "csv_mb": c, "parquet_mb": p, "ratio": c / p})

    lat = storage[storage["experiment"] == "Experiment_C_Query_Latency"]
    latency_rows = []
    for ds, label in [("Food.com Q1_Row_Count", "Đếm dòng toàn bảng"),
                      ("Food.com Q2_Avg_Rating_By_Recipe", "Điểm trung bình theo món"),
                      ("Food.com Q3_Projection_Filter_3_Cols", "Chọn 3 cột và lọc điểm")]:
        c = lat[(lat["dataset"] == ds) & (lat["format"] == "CSV")].iloc[0]
        p = lat[(lat["dataset"] == ds) & (lat["format"] == "Parquet")].iloc[0]
        latency_rows.append({"label": label, "csv_avg": float(c["avg_time_sec"]), "csv_std": float(c["std_time_sec"]),
                             "parquet_avg": float(p["avg_time_sec"]), "parquet_std": float(p["std_time_sec"]),
                             "speedup": float(c["avg_time_sec"]) / float(p["avg_time_sec"])})

    total = scal[scal["step"] == "Tổng cộng Pipeline"]
    scal_points = []
    for _, r in total.iterrows():
        scal_points.append({"ratio": r["sample_ratio"], "rows": int(r["num_rows"]), "resource": r["resource"],
                            "avg_time": float(r["avg_time"])})

    write_js("WEB_DATA_SYSTEM", {
        "cluster_info": {
            "host": {"os": "Windows 11 (WSL2)", "ram_gb": 24, "docker_ram_gb": 16, "source": "stage_P2.md"},
            "hdfs": {"version": cfg["hadoop_version"], "namenodes": cfg["n_namenodes"], "datanodes": cfg["n_datanodes"],
                     "replication": cfg["replication"], "fsck": fsck},
            "spark": {"version": spark_runtime or cfg["spark_image_version"], "image_version": cfg["spark_image_version"], "masters": cfg["n_masters"],
                      "workers": cfg["n_workers"], "worker_cores": cfg["worker_cores"],
                      "worker_ram_mb": cfg["worker_ram_mb"],
                      "total_cores": cfg["n_workers"] * cfg["worker_cores"],
                      "total_ram_mb": cfg["n_workers"] * cfg["worker_ram_mb"]},
        },
        "storage_rows": storage_rows,
        "latency_rows": latency_rows,
        "scalability": scal_points,
        "source": "docker-compose.yml, S3_14_fsck.log, storage_benchmark.csv, scalability.csv",
    }, "system.js")


# =============================================================================
# behavior.js (Trang 3: Hành vi)
# =============================================================================
def profile_records(df):
    recs = df_to_clean_records(df)
    for r in recs:
        if r.get("cluster_name"):
            r["cluster_name"] = WL.display_cluster_name(r["cluster_name"])
    return recs


def export_behavior():
    print("-> Xuất behavior.js...")
    vn_users = read_csv("app/data/cluster_profiles_food_vietnam.csv")
    fc_users = read_csv("app/data/cluster_profiles_food_com.csv")
    vn_foods = read_csv("app/data/food_cluster_profiles_vietnam.csv")
    tuning = read_csv("app/data/kmeans_tuning.csv")
    top = read_csv("app/data/cluster_top_items.csv")

    top_items = {"food_com": {}, "vifoodrec_users": {}, "vifoodrec_foods": {}}
    for ds in ("food_com", "vifoodrec_users"):
        for c, g in top[top["dataset"] == ds].groupby("cluster"):
            g = g.sort_values("rank")
            top_items[ds][str(int(c))] = [
                {"id": int(r["item_id"]), "name": str(r["name"]), "count": int(r["count"]),
                 "calories": clean_val(r["calories"]), "time": clean_val(r["time"]),
                 "dish_type": clean_val(r["dish_type"])}
                for _, r in g.iterrows()]

    # Cụm món: 5 món đầu theo food_id tăng dần (ví dụ minh họa, không phải "tiêu biểu" theo thước đo nào)
    fcl = pd.read_parquet("app/data/food_clusters_vietnam.parquet")
    foods = pd.read_parquet("app/data/foods_vietnam.parquet")[["food_id", "calories", "cooking_time_min", "dish_type"]]
    m = fcl.merge(foods, on="food_id", how="left").sort_values(["cluster", "food_id"])
    for c, g in m.groupby("cluster"):
        top_items["vifoodrec_foods"][str(int(c))] = [
            {"id": int(r["food_id"]), "name": str(r["dish_name"]), "count": None,
             "calories": clean_val(r["calories"]), "time": clean_val(r["cooking_time_min"]),
             "dish_type": clean_val(r["dish_type"])}
            for _, r in g.head(10).iterrows()]

    def minmax(df, col):
        c = df[df["cluster"] >= 0][col]
        return float(c.min()), float(c.max())

    # Chênh lệch tương đối giữa các cụm người dùng ViFoodRec (cùng định nghĩa với src/cluster_naming.py)
    feats = ["n_ratings", "avg_rating", "std_rating", "pct_man_high", "pct_chay_high", "avg_calo_high", "avg_time_high"]
    overall = vn_users[vn_users["cluster"] < 0].iloc[0]
    rel = {f: float((vn_users[vn_users["cluster"] >= 0][f].max() - vn_users[vn_users["cluster"] >= 0][f].min()) / abs(overall[f]))
           for f in feats}

    def sil(task, k):
        return float(tuning[(tuning["task"] == task) & (tuning["k"] == k)]["silhouette"].iloc[0])

    facts = {
        "fc_avg_rating": minmax(fc_users, "avg_rating"),
        "fc_avg_minutes": minmax(fc_users, "avg_minutes"),
        "fc_k": int(len(fc_users) - 1),
        "fc_silhouette": sil("Food.com Users", int(len(fc_users) - 1)),
        "vn_avg_rating": minmax(vn_users, "avg_rating"),
        "vn_k": int(len(vn_users) - 1),
        "vn_silhouette": sil("ViFoodRec Users", int(len(vn_users) - 1)),
        "vn_rel_diff": rel,
        "vn_rel_diff_max": max(rel.values()),
        "vn_rel_diff_max_feature": max(rel, key=rel.get),
        "vn_food_k": int(len(vn_foods) - 1),
        "vn_food_silhouette": sil("ViFoodRec Foods", int(len(vn_foods) - 1)),
        "vn_food_calories": minmax(vn_foods, "calories"),
    }

    write_js("WEB_DATA_BEHAVIOR", {
        "vn_user_clusters": profile_records(vn_users),
        "fc_user_clusters": profile_records(fc_users),
        "vn_food_clusters": profile_records(vn_foods),
        "kmeans_tuning": df_to_clean_records(tuning),
        "top_items": top_items,
        "facts": facts,
        "source": "cluster_profiles_*.csv, food_cluster_profiles_vietnam.csv, kmeans_tuning.csv, cluster_top_items.csv",
    }, "behavior.js")


# =============================================================================
# models.js (Trang 5: Mô hình)
# =============================================================================
LOWER_BETTER = {"RMSE": True, "MAE": True, "Precision@10": False, "Recall@10": False}


def export_models():
    print("-> Xuất models.js...")
    comp = read_csv("app/data/model_comparison.csv")
    comp = comp[~comp["model"].isin(WL.HIDDEN_MODELS)].copy()
    als_bd = read_csv("app/data/als_rmse_breakdown.csv")
    base_bd = read_csv("app/data/baseline_rmse_breakdown.csv")
    tune_vn = read_csv("app/data/als_tuning_food_vietnam.csv")
    tune_fc = read_csv("app/data/als_tuning_food_com.csv")

    order = list(WL.MODEL_LABELS.keys())
    comp["_o"] = comp["model"].map({m: i for i, m in enumerate(order)})
    comp = comp.sort_values(["dataset", "_o"]).drop(columns="_o")
    rows = df_to_clean_records(comp)
    for r in rows:
        r["model_label"] = WL.display_model(r["model"])
        r["is_als"] = r["model"].startswith("ALS")

    # Mô hình đứng đầu từng độ đo (để sinh tiêu đề từ số liệu)
    facts = {}
    for ds in comp["dataset"].unique():
        sub = comp[comp["dataset"] == ds]
        best = {}
        for metric, lower in LOWER_BETTER.items():
            s = sub.dropna(subset=[metric])
            idx = s[metric].idxmin() if lower else s[metric].idxmax()
            best[metric] = {"model": sub.loc[idx, "model"], "label": WL.display_model(sub.loc[idx, "model"]),
                            "value": float(sub.loc[idx, metric])}
        facts[ds] = best

    write_js("WEB_DATA_MODELS", {
        "model_comparison": rows,
        "als_rmse_breakdown": df_to_clean_records(als_bd),
        "baseline_rmse_breakdown": df_to_clean_records(base_bd),
        "als_tuning_vn": df_to_clean_records(tune_vn),
        "als_tuning_fc": df_to_clean_records(tune_fc),
        "facts": facts,
        "source": "model_comparison.csv, als_tuning_*.csv, als_rmse_breakdown.csv, baseline_rmse_breakdown.csv",
    }, "models.js")


# =============================================================================
# recs_vietnam.js, recs_foodcom.js (Trang 4: Gợi ý)
# =============================================================================
def short_ingredients(x, n=6):
    return ", ".join([item.strip() for item in str(x).split(",")[:n]]) if pd.notna(x) else ""


def neighbor_stats(nbr_df, shown_ids=None):
    """Thống kê điểm cosine của danh sách láng giềng (để web cảnh báo khi các điểm gần như bằng nhau)."""
    df = nbr_df if shown_ids is None else nbr_df[nbr_df.iloc[:, 0].isin(shown_ids)]
    sims = np.concatenate([np.array(x, dtype=float) for x in df["similarity_scores"]])
    return {"min": round(float(sims.min()), 6), "median": round(float(np.median(sims)), 6),
            "share_ge_0_999": round(float((sims >= 0.999).mean()), 4), "n_scores": int(len(sims))}


def export_recs_vietnam():
    print("-> Xuất recs_vietnam.js...")
    f_df = pd.read_parquet("app/data/foods_vietnam.parquet")
    f_sub = f_df[["food_id", "dish_name", "dish_type", "calories", "cooking_time_min", "ingredients"]].copy()
    f_sub["ingredients"] = f_sub["ingredients"].apply(short_ingredients)

    r_df = pd.read_parquet("app/data/recommendations_vietnam.parquet")
    recs = df_to_clean_records(r_df[["user_id", "rank", "food_id", "dish_name", "dish_type", "calories", "cooking_time"]])

    u_df = pd.read_parquet("app/data/user_clusters_vietnam.parquet")
    user_cluster_map = {int(r["user_id"]): {"cluster": int(r["cluster"]), "cluster_name": str(r["cluster_name"])}
                        for _, r in u_df.iterrows()}

    nbr_df = pd.read_parquet("app/data/item_neighbors_vietnam.parquet")
    neighbors = {int(r["food_id"]): list(zip([int(x) for x in r["neighbor_ids"]],
                                             [round(float(x), 4) for x in r["similarity_scores"]]))
                 for _, r in nbr_df.iterrows()}

    write_js("WEB_DATA_RECS_VN", {
        "catalog": df_to_clean_records(f_sub),
        "recommendations": recs,
        "user_clusters": user_cluster_map,
        "item_neighbors": neighbors,
        "neighbor_stats": neighbor_stats(nbr_df),
    }, "recs_vietnam.js")


def export_recs_foodcom():
    print("-> Xuất recs_foodcom.js...")
    r_df = pd.read_parquet("app/data/recommendations_foodcom_sample.parquet")
    sample_users = set(r_df["user_id"].unique()[:1000])
    sub_recs = r_df[r_df["user_id"].isin(sample_users)].copy()
    rec_ids = set(sub_recs["recipe_id"])

    nbr_df = pd.read_parquet("app/data/item_neighbors_foodcom.parquet")
    top_nbr_df = nbr_df.head(2500)
    # Catalog phải chứa cả món gợi ý, món có danh sách láng giềng và mọi món xuất hiện trong danh sách láng giềng đó,
    # nếu không web hiện "Món <mã>" thay cho tên món (lỗi phát hiện ở S4).
    nbr_ids = {int(x) for ids in top_nbr_df["neighbor_ids"] for x in ids}
    needed = rec_ids.union(set(top_nbr_df["recipe_id"])).union(nbr_ids)

    all_recipes = pd.read_parquet("app/data/recipes_foodcom_sample.parquet")
    sub_recipes = all_recipes[all_recipes["recipe_id"].isin(needed)][
        ["recipe_id", "name", "calories", "minutes_clean", "ingredients"]].copy()
    sub_recipes["ingredients"] = sub_recipes["ingredients"].apply(short_ingredients)

    u_df = pd.read_parquet("app/data/user_clusters_foodcom.parquet")
    sub_u = u_df[u_df["user_id"].isin(sample_users)]
    user_cluster_map = {int(r["user_id"]): {"cluster": int(r["cluster"]), "cluster_name": str(r["cluster_name"])}
                        for _, r in sub_u.iterrows()}

    neighbors = {int(r["recipe_id"]): list(zip([int(x) for x in r["neighbor_ids"]],
                                               [round(float(x), 4) for x in r["similarity_scores"]]))
                 for _, r in top_nbr_df.iterrows()}

    write_js("WEB_DATA_RECS_FC", {
        "catalog": df_to_clean_records(sub_recipes),
        "recommendations": df_to_clean_records(sub_recs[["user_id", "rank", "recipe_id", "name", "calories", "minutes_clean"]]),
        "user_clusters": user_cluster_map,
        "item_neighbors": neighbors,
        "neighbor_stats": neighbor_stats(top_nbr_df),
    }, "recs_foodcom.js")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print("=== BẮT ĐẦU XUẤT DỮ LIỆU CHO DASHBOARD WEB ===")
    export_labels()
    export_summary()
    export_system()
    export_behavior()
    export_models()
    export_recs_vietnam()
    export_recs_foodcom()
    print("=== HOÀN TẤT XUẤT DỮ LIỆU THÀNH CÔNG ===")


if __name__ == "__main__":
    main()

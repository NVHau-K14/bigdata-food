"""
src/verify_web.py
-----------------
Kiểm tra tự động số liệu và nội dung hiển thị của dashboard web (S4, mục E1).

Hai lớp kiểm tra:
1. Dữ liệu web (web/data/*.js) so với tệp nguồn (app/data/*.csv, *.parquet) và với docker-compose.yml.
2. Văn bản THỰC SỰ hiển thị trên từng trang: bước này cần tệp reports/evidence/logs/S4_ui_texts.json do
   `node src/verify_web_ui.mjs` ghi ra (Chrome headless đọc innerText của trang). Mỗi số kỳ vọng được định dạng
   theo ĐÚNG số chữ số hiển thị rồi tìm trong văn bản của trang tương ứng; không dùng dung sai che lỗi làm tròn.

Kiểm tra riêng cho các lỗi đã sửa: A1 (món tiêu biểu đúng bộ dữ liệu), A3 (phiên bản và replication lấy từ dữ liệu,
không còn chuỗi "Spark 3."), A4 (đúng chữ số của P@10, R@10), C2 (một hàm định dạng, dấu phẩy thập phân).
Thoát mã khác 0 nếu có bất kỳ mục nào sai.
"""

import json
import os
import re
import sys

import numpy as np
import pandas as pd

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import web_labels as WL  # noqa: E402
import export_for_web as EW  # noqa: E402

TEXTS_PATH = "reports/evidence/logs/S4_ui_texts.json"
SIZE = "1920x1080"

results = []


def check(name, ok, detail=""):
    results.append(bool(ok))
    print(f"[{'DAT' if ok else 'KHONG DAT'}] {name}" + (f" : {detail}" if detail else ""))


def vn(val, decimals=None):
    """Định dạng giống hệt FormatUtils.fmt trong web/js/format.js."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "không áp dụng"
    num = float(val)
    if decimals is not None:
        s = f"{num:.{decimals}f}"
    elif num == int(num):
        s = str(int(num))
    else:
        s = f"{num:.4f}".rstrip("0").rstrip(".")
    ip, _, dp = s.partition(".")
    ip = re.sub(r"(?<=\d)(?=(\d{3})+(?!\d))", ".", ip)
    return ip + ("," + dp if dp else "")


def load_js(name, var):
    text = open(f"web/data/{name}", encoding="utf-8").read()
    m = re.search(rf"window\.{var}\s*=\s*(.+?);\s*$", text, re.DOTALL)
    return json.loads(m.group(1))


def page_text(texts, state):
    key = f"{SIZE} {state}"
    if key not in texts:
        raise KeyError(f"Thiếu văn bản của trạng thái {key} trong {TEXTS_PATH}")
    return texts[key]


def expect(texts, state, label, shown):
    """Kiểm tra chuỗi hiển thị `shown` có nằm trong văn bản của trang `state`."""
    check(f"{label}: {shown}", shown in page_text(texts, state), f"trang {state}")


def main():
    print("=" * 70)
    print(" KIỂM THỬ ĐỐI CHIẾU SỐ LIỆU VÀ NỘI DUNG DASHBOARD WEB (src/verify_web.py)")
    print("=" * 70)

    if not os.path.exists(TEXTS_PATH):
        print(f"[LỖI] Chưa có {TEXTS_PATH}. Chạy trước: node src/verify_web_ui.mjs")
        sys.exit(2)
    texts = json.load(open(TEXTS_PATH, encoding="utf-8"))

    summary = load_js("summary.js", "WEB_DATA_SUMMARY")
    system = load_js("system.js", "WEB_DATA_SYSTEM")
    behavior = load_js("behavior.js", "WEB_DATA_BEHAVIOR")
    models = load_js("models.js", "WEB_DATA_MODELS")
    labels = load_js("labels.js", "WEB_LABELS")
    recs_vn = load_js("recs_vietnam.js", "WEB_DATA_RECS_VN")
    recs_fc = load_js("recs_foodcom.js", "WEB_DATA_RECS_FC")

    # ------------------------------------------------------------------
    print("\n--- Nhóm 0: bảng nhãn dùng chung ---")
    check("labels.js khớp src/web_labels.py (loại món)", labels["dish_type"] == WL.DISH_TYPE_LABELS)
    check("labels.js khớp src/web_labels.py (tên mô hình)", labels["models"] == WL.MODEL_LABELS)

    # ------------------------------------------------------------------
    print("\n--- Nhóm 1: trang Dữ liệu (cleaning_log.csv, eda_12, eda_01) ---")
    log = pd.read_csv("app/data/cleaning_log.csv", encoding="utf-8-sig")

    def row(ds, step):
        return log[(log["dataset"] == ds) & (log["step_name"] == step)].iloc[0]

    vn_raw = row("vifoodrec_ratings", "raw_input")
    vn_fk = row("vifoodrec_ratings", "foreign_key_join_foods")
    vn_kc = row("vifoodrec_ratings", "iterative_k_core_convergence")
    fc_raw = row("food_com_interactions", "raw_input")
    fc_zero = row("food_com_interactions", "filter_rating_zero")
    fc_kc = row("food_com_interactions", "iterative_k_core_convergence")
    S = "du-lieu"
    expect(texts, S, "ViFoodRec dòng thô", vn("%d" % vn_raw["rows_after"]))
    expect(texts, S, "ViFoodRec loại khóa ngoại", f"Loại {vn('%d' % vn_fk['rows_dropped'])} dòng")
    expect(texts, S, "ViFoodRec dòng sạch", vn("%d" % vn_kc["rows_after"]))
    expect(texts, S, "ViFoodRec K-core hội tụ", f"Đã hội tụ sau {vn(1)} vòng")
    expect(texts, S, "Food.com dòng thô", vn("%d" % fc_raw["rows_after"]))
    expect(texts, S, "Food.com loại điểm 0", f"Loại {vn('%d' % fc_zero['rows_dropped'])} dòng")
    expect(texts, S, "Food.com loại K-core", f"Loại {vn('%d' % fc_kc['rows_dropped'])} dòng sau {vn(5)} vòng")
    # Không còn bước loại 0,0 và 0,5 ở ViFoodRec (A5)
    check("Phễu ViFoodRec không còn bước loại điểm 0,0 và 0,5 (A5)",
          int(row("vifoodrec_ratings", "filter_rating_scale_0_to_5_step_half")["rows_dropped"]) == 0
          and "33.211" not in page_text(texts, S) and "quy chuẩn thiết kế ban đầu" not in page_text(texts, S))

    comp = pd.read_csv("app/data/eda_12_dataset_comparison.csv", encoding="utf-8-sig").set_index("ChiSo")
    spec = {"Số User (Users)": 0, "Số Món (Items)": 0, "Số Tương tác (Ratings)": 0,
            "Độ thưa ma trận (Sparsity %)": 2, "Điểm TB (Mean Rating)": 2,
            "Trung vị tương tác/User": 0, "Trung vị tương tác/Item": 0}
    for key, dec in spec.items():
        for col, who in (("ViFoodRec", "ViFoodRec"), ("Food_com", "Food.com")):
            val = comp.loc[key, col]
            shown = vn(val, dec) + ("%" if "thưa" in key else "")
            expect(texts, S, f"{WL.COMPARISON_LABELS[key]} ({who})", shown)

    rd = pd.read_csv("app/data/eda/eda_01_vifoodrec_rating_dist.csv")
    expect(texts, S, "Phần trăm mức điểm nhỏ nhất ViFoodRec", vn(rd["pct"].min(), 2) + "%")
    expect(texts, S, "Phần trăm mức điểm lớn nhất ViFoodRec", vn(rd["pct"].max(), 2) + "%")
    check("Phân phối ViFoodRec có 11 mức điểm từ 0,0 đến 5,0 (A5)", len(rd) == 11 and rd["rating"].min() == 0 and rd["rating"].max() == 5)
    rf = pd.read_csv("app/data/eda/eda_01_food_com_rating_dist.csv")
    expect(texts, S, "Food.com 5 sao", vn(rf[rf["rating"] == 5.0]["pct"].iloc[0], 1) + "%")

    # ------------------------------------------------------------------
    print("\n--- Nhóm 2: trang Hệ thống (storage_benchmark.csv, scalability.csv, docker-compose.yml) ---")
    st = pd.read_csv("app/data/storage_benchmark.csv", encoding="utf-8-sig")
    S = "he-thong-luu-tru"
    for ds, label in [("Food.com RAW_interactions", "Đánh giá thô"), ("Food.com RAW_recipes", "Công thức thô"),
                      ("Food.com interactions_clean", "Đánh giá sạch"), ("Food.com recipes_clean", "Công thức sạch")]:
        sub = st[st["dataset"] == ds]
        c = float(sub[sub["format"] == "CSV"]["size_mb"].iloc[0])
        p = float(sub[sub["format"] == "Parquet"]["size_mb"].iloc[0])
        expect(texts, S, f"{label}: CSV", vn(c, 2) + " MB")
        expect(texts, S, f"{label}: Parquet", vn(p, 2) + " MB")
        expect(texts, S, f"{label}: tỷ lệ nén", vn(c / p, 2) + " lần")
    lat = st[st["experiment"] == "Experiment_C_Query_Latency"]
    for ds in ["Food.com Q1_Row_Count", "Food.com Q2_Avg_Rating_By_Recipe", "Food.com Q3_Projection_Filter_3_Cols"]:
        c = lat[(lat["dataset"] == ds) & (lat["format"] == "CSV")].iloc[0]
        p = lat[(lat["dataset"] == ds) & (lat["format"] == "Parquet")].iloc[0]
        expect(texts, S, f"{ds}: thời gian CSV", f"{vn(c['avg_time_sec'], 3)} s (độ lệch {vn(c['std_time_sec'], 3)})")
        expect(texts, S, f"{ds}: tăng tốc", vn(c["avg_time_sec"] / p["avg_time_sec"], 2) + " lần")

    compose = open("docker-compose.yml", encoding="utf-8").read()
    hadoop_v = re.search(r"apache/hadoop:([\d.]+)", compose).group(1)
    spark_v_img = re.search(r"pyspark-notebook:spark-([\d.]+)", compose).group(1)
    repl = re.search(r'dfs\.replication:\s*"(\d+)"', compose).group(1)
    sys_text = page_text(texts, S)
    expect(texts, S, "Phiên bản Hadoop (A3)", f"HDFS {hadoop_v}")
    expect(texts, S, "Phiên bản Spark (A3)", f"Spark {spark_v_img}")
    expect(texts, S, "Replication khớp docker-compose.yml (A3)", f"Replication {repl}")
    sc = pd.read_csv("app/data/scalability.csv")
    tot = sc[(sc["step"] == "Tổng cộng Pipeline") & (sc["resource"].str.startswith("2 Workers"))]
    first, last = tot.iloc[0], tot.iloc[-1]
    expect(texts, "he-thong-mo-rong", "Thời gian 10% dữ liệu, 2 Worker", vn(first["avg_time"], 1) + " s")
    expect(texts, "he-thong-mo-rong", "Thời gian 100% dữ liệu, 2 Worker", vn(last["avg_time"], 1) + " s")

    # A3: không còn chuỗi "Spark 3." ở bất kỳ tệp nào trong web/
    hits = []
    for root, _, files in os.walk("web"):
        for f in files:
            if f.endswith((".js", ".html", ".css", ".md")):
                t = open(os.path.join(root, f), encoding="utf-8", errors="replace").read()
                if re.search(r"Spark 3\.", t):
                    hits.append(os.path.join(root, f))
    check('Không còn chuỗi "Spark 3." trong web/ (A3)', not hits, ", ".join(hits))
    check('Không còn chuỗi "rep=2" hay "Replication = 2" viết cứng trong web/js và web/index.html (A3)',
          not any(re.search(r"Replication = 2|rep=2", open(f, encoding="utf-8").read()) for f in
                  ["web/index.html", "web/js/app.js", "web/js/charts.js"]))
    check("Spark trong dữ liệu web khớp phiên bản chạy thật", system["cluster_info"]["spark"]["version"] == spark_v_img,
          system["cluster_info"]["spark"]["version"])

    # ------------------------------------------------------------------
    print("\n--- Nhóm 3: trang Mô hình (model_comparison.csv) (A4) ---")
    comp_m = pd.read_csv("app/data/model_comparison.csv")
    comp_m = comp_m[~comp_m["model"].isin(WL.HIDDEN_MODELS)]
    digits = {"RMSE": 4, "MAE": 4, "Precision@10": 5, "Recall@10": 5}
    for ds, state in (("food_vietnam", "mo-hinh-vifoodrec"), ("food_com", "mo-hinh-food-com")):
        sub = comp_m[comp_m["dataset"] == ds]
        t = page_text(texts, state)
        for _, r in sub.iterrows():
            line = next((ln for ln in t.splitlines() if ln.startswith(WL.display_model(r["model"]) + "\t")), "")
            for metric, dec in digits.items():
                shown = vn(r[metric], dec) if not pd.isna(r[metric]) else "không áp dụng"
                check(f"{ds} {WL.display_model(r['model'])} {metric}: {shown}", f"\t{shown}" in line or line.endswith(shown),
                      f"dòng: {line[:90]}")
    check("P@10 của ALS dự đoán điểm ViFoodRec hiển thị 0,01386, không phải 0,01390 (A4)",
          "0,01386" in page_text(texts, "mo-hinh-vifoodrec") and "0,01390" not in page_text(texts, "mo-hinh-vifoodrec"))
    check("R@10 của ALS dự đoán điểm ViFoodRec hiển thị 0,00285, không phải 0,00310 (A4)",
          "0,00285" in page_text(texts, "mo-hinh-vifoodrec") and "0,00310" not in page_text(texts, "mo-hinh-vifoodrec"))
    tv = pd.read_csv("app/data/als_tuning_food_vietnam.csv")
    expect(texts, "mo-hinh-vifoodrec", "RMSE validation tốt nhất", vn(tv["val_rmse"].min(), 4))

    # ------------------------------------------------------------------
    print("\n--- Nhóm 4: trang Hành vi (cluster_profiles_*.csv) ---")
    fcp = pd.read_csv("app/data/cluster_profiles_food_com.csv")
    for _, r in fcp[fcp["cluster"] >= 0].iterrows():
        expect(texts, "hanh-vi-food-com", f"Food.com cụm {int(r['cluster'])} số người", vn(r["user_count"], 0) + " người")
    vnp = pd.read_csv("app/data/cluster_profiles_food_vietnam.csv")
    for _, r in vnp[vnp["cluster"] >= 0].iterrows():
        expect(texts, "hanh-vi-vifoodrec-nguoi-dung", f"ViFoodRec cụm {int(r['cluster']) + 1} số người", vn(r["user_count"], 0) + " người")
    fdp = pd.read_csv("app/data/food_cluster_profiles_vietnam.csv")
    for _, r in fdp[fdp["cluster"] >= 0].iterrows():
        expect(texts, "hanh-vi-vifoodrec-mon", f"Cụm món {int(r['cluster'])} số món", vn(r["food_count"], 0) + " món")
    tun = pd.read_csv("app/data/kmeans_tuning.csv")
    sil = float(tun[(tun["task"] == "Food.com Users") & (tun["k"] == 4)]["silhouette"].iloc[0])
    expect(texts, "hanh-vi-food-com", "Silhouette Food.com k = 4", vn(sil, 4))
    check('Tiêu đề trang Hành vi không còn khẳng định "rõ rệt" (A7)',
          "rõ rệt" not in page_text(texts, "hanh-vi-food-com"))
    check("Tên cụm ViFoodRec hiển thị là Cụm 1, 2, 3 (A2)",
          all(f"Cụm {i}" in page_text(texts, "hanh-vi-vifoodrec-nguoi-dung") for i in (1, 2, 3)))

    # ------------------------------------------------------------------
    print("\n--- Nhóm 5: A1 món tiêu biểu thuộc đúng danh mục của bộ dữ liệu ---")
    fc_ids = set(pd.read_parquet("app/data/recipes_foodcom_sample.parquet", columns=["recipe_id"])["recipe_id"].astype(int))
    vn_cat = pd.read_parquet("app/data/foods_vietnam.parquet", columns=["food_id", "dish_name"])
    vn_ids = set(vn_cat["food_id"].astype(int))
    vn_names = set(vn_cat["dish_name"])
    fc_items = [it for items in behavior["top_items"]["food_com"].values() for it in items]
    vu_items = [it for items in behavior["top_items"]["vifoodrec_users"].values() for it in items]
    vf_items = [it for items in behavior["top_items"]["vifoodrec_foods"].values() for it in items]
    check("Mọi món trong panel Food.com có id thuộc danh mục Food.com", all(it["id"] in fc_ids for it in fc_items), f"{len(fc_items)} món")
    fc_cat = pd.read_parquet("app/data/recipes_foodcom_sample.parquet", columns=["recipe_id", "name"]).set_index("recipe_id")["name"]
    check("Tên món Food.com khớp danh mục theo id", all(fc_cat.get(it["id"]) == it["name"] for it in fc_items))
    check("Không món Food.com nào trùng tên món ViFoodRec", not any(it["name"] in vn_names for it in fc_items))
    check("Mọi món trong panel người dùng ViFoodRec có id thuộc danh mục ViFoodRec", all(it["id"] in vn_ids for it in vu_items), f"{len(vu_items)} món")
    check("Mọi món trong panel cụm món ViFoodRec có id thuộc danh mục ViFoodRec", all(it["id"] in vn_ids for it in vf_items), f"{len(vf_items)} món")
    top_csv = pd.read_csv("app/data/cluster_top_items.csv", encoding="utf-8-sig")
    check("Món trong behavior.js khớp cluster_top_items.csv", len(fc_items) + len(vu_items) == len(top_csv), f"{len(top_csv)} dòng")
    check("Catalog gợi ý Food.com chứa mọi món có trong danh sách láng giềng (không còn 'Món <mã>')",
          {int(x) for v in recs_fc["item_neighbors"].values() for x, _ in v}.issubset({c["recipe_id"] for c in recs_fc["catalog"]}))
    check("Catalog gợi ý ViFoodRec chứa đủ 4.000 món", len(recs_vn["catalog"]) == 4000)

    # ------------------------------------------------------------------
    print("\n--- Nhóm 6: C2 định dạng số kiểu Việt Nam qua một hàm ---")
    dec_pat = re.compile(r"\d\.\d")
    bad = []
    for key, t in texts.items():
        cleaned = re.sub(r"\b\d+\.\d+\.\d+\b", "", t)
        cleaned = re.sub(r"\b\d{1,3}(?:\.\d{3})+\b", "", cleaned)
        if dec_pat.search(cleaned):
            bad.append(key)
    check("Không có mẫu chữ số-chấm-chữ số (số thập phân dấu chấm) trong văn bản hiển thị", not bad, ", ".join(bad[:4]))
    offenders = []
    for f in ["web/js/app.js", "web/js/charts.js"]:
        t = open(f, encoding="utf-8").read()
        if "toFixed(" in t or re.search(r'\.replace\("\.",\s*","\)', t):
            offenders.append(f)
    check("Chỉ web/js/format.js dùng toFixed hay thay dấu chấm bằng dấu phẩy (một hàm duy nhất)", not offenders, ", ".join(offenders))
    check("Tiêu đề mọi trang (dòng đầu của văn bản trang) không quá 90 ký tự",
          all(len(t.splitlines()[0]) <= 90 for k, t in texts.items() if not k.endswith(("glossary", "tuning-modal"))),
          "; ".join(f"{len(t.splitlines()[0])}" for k, t in texts.items() if k.startswith(SIZE) and not k.endswith(("glossary", "tuning-modal")))[:120])

    # ------------------------------------------------------------------
    total = len(results)
    passed = sum(results)
    print("\n" + "=" * 70)
    print(f" KẾT QUẢ: {passed}/{total} đạt")
    print("=" * 70)
    if passed != total:
        print(f"[LỖI] {total - passed} mục không khớp")
        sys.exit(1)
    print("[THÀNH CÔNG] Số liệu và nội dung hiển thị khớp nguồn.")
    sys.exit(0)


if __name__ == "__main__":
    main()

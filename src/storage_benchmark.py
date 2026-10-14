"""
src/storage_benchmark.py
------------------------
Thực nghiệm lưu trữ và đo lường hiệu năng so sánh công bằng giữa CSV và Parquet:
1. Thí nghiệm A: Chuyển NGUYÊN BẢN dữ liệu thô (RAW_interactions và RAW_recipes) sang Parquet Snappy,
   giữ nguyên 100% cột và dòng. Đo dung lượng CSV thô vs Parquet thô.
2. Thí nghiệm B: Ghi bảng sạch (interactions_clean và recipes_clean) dưới cả 2 định dạng (CSV và Parquet).
   Đo dung lượng và phân rã mức giảm dung lượng: do lọc dòng/cột vs do nén Parquet.
3. Thí nghiệm C: Đo thời gian thực thi 3 truy vấn trên bảng sạch (CSV vs Parquet):
   - Q1: Đếm dòng (Full Scan)
   - Q2: Trung bình rating theo món (Aggregation GroupBy)
   - Q3: Chiếu và lọc trên 3 cột user_id, recipe_id, rating (Column Pruning)
   Mỗi truy vấn chạy 4 lần (lần 1 làm nóng, lấy trung bình và độ lệch chuẩn của 3 lần sau).
4. Xuất kết quả CSV ra data/results/storage_benchmark.csv và vẽ biểu đồ ra reports/figures/storage_benchmark.png.
"""

import sys
import time
import math
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pyspark.sql.functions import col, avg, to_json
from src.config import get_spark_session, get_path


def get_hdfs_path_size_mb(spark, hdfs_uri):
    """Lấy dung lượng thực tế của file hoặc thư mục trên HDFS (tính bằng MB)."""
    sc = spark.sparkContext
    conf = sc._jsc.hadoopConfiguration()
    path = sc._jvm.org.apache.hadoop.fs.Path(hdfs_uri)
    fs = path.getFileSystem(conf)
    if fs.exists(path):
        size_bytes = fs.getContentSummary(path).getLength()
        return round(size_bytes / (1024 * 1024), 2)
    return 0.0


def run_benchmark():
    start_all = time.time()
    spark = get_spark_session("StorageBenchmarkP4")
    sc = spark.sparkContext
    
    print("=" * 80)
    print("   BẮT ĐẦU THỰC NGHIỆM LƯU TRỮ CSV VS PARQUET (P4)")
    print("=" * 80)
    
    results = []
    benchmark_hdfs_dir = "hdfs://namenode:9000/data/benchmark"
    
    # =========================================================================
    # THÍ NGHIỆM A: DỮ LIỆU THÔ ĐẦY ĐỦ (FULL RAW)
    # =========================================================================
    print("\n" + "-" * 70)
    print("[THÍ NGHIỆM A] So sánh trên DỮ LIỆU THÔ ĐẦY ĐỦ (Giữ nguyên 100% cột & dòng)")
    print("-" * 70)
    
    raw_inter_csv_path = get_path("raw", "food_com", "RAW_interactions.csv")
    raw_rec_csv_path = get_path("raw", "food_com", "RAW_recipes.csv")
    
    raw_inter_pq_path = f"{benchmark_hdfs_dir}/raw_interactions_full.parquet"
    raw_rec_pq_path = f"{benchmark_hdfs_dir}/raw_recipes_full.parquet"
    
    print("1. Đọc dữ liệu thô nguyên bản và chuyển sang Parquet (Snappy)...")
    # Đọc RAW_interactions
    df_raw_inter = spark.read.option("header", "true") \
                             .option("multiLine", "true") \
                             .option("escape", "\"") \
                             .csv(raw_inter_csv_path)
                             
    print(f"  - RAW_interactions count: {df_raw_inter.count():,}")
    df_raw_inter.write.mode("overwrite").parquet(raw_inter_pq_path)
    print(f"  -> Ghi xong: {raw_inter_pq_path}")
    
    # Đọc RAW_recipes
    df_raw_rec = spark.read.option("header", "true") \
                           .option("multiLine", "true") \
                           .option("escape", "\"") \
                           .csv(raw_rec_csv_path)
                           
    print(f"  - RAW_recipes count: {df_raw_rec.count():,}")
    df_raw_rec.write.mode("overwrite").parquet(raw_rec_pq_path)
    print(f"  -> Ghi xong: {raw_rec_pq_path}")
    
    # Đo dung lượng Thí nghiệm A
    size_raw_inter_csv = get_hdfs_path_size_mb(spark, raw_inter_csv_path)
    size_raw_inter_pq = get_hdfs_path_size_mb(spark, raw_inter_pq_path)
    size_raw_rec_csv = get_hdfs_path_size_mb(spark, raw_rec_csv_path)
    size_raw_rec_pq = get_hdfs_path_size_mb(spark, raw_rec_pq_path)
    
    ratio_raw_inter = round(size_raw_inter_csv / size_raw_inter_pq, 2)
    ratio_raw_rec = round(size_raw_rec_csv / size_raw_rec_pq, 2)
    
    print("\nKết quả Thí nghiệm A:")
    print(f"  * RAW_interactions : CSV = {size_raw_inter_csv} MB | Parquet = {size_raw_inter_pq} MB (Nén {ratio_raw_inter}x)")
    print(f"  * RAW_recipes      : CSV = {size_raw_rec_csv} MB | Parquet = {size_raw_rec_pq} MB (Nén {ratio_raw_rec}x)")
    
    results.append({
        "experiment": "Experiment_A_Raw_Full",
        "dataset": "Food.com RAW_interactions",
        "format": "CSV",
        "size_mb": size_raw_inter_csv,
        "avg_time_sec": None,
        "std_time_sec": None,
        "notes": "100% cột thô (gồm review), 1,132,367 dòng"
    })
    results.append({
        "experiment": "Experiment_A_Raw_Full",
        "dataset": "Food.com RAW_interactions",
        "format": "Parquet",
        "size_mb": size_raw_inter_pq,
        "avg_time_sec": None,
        "std_time_sec": None,
        "notes": f"Nén Parquet Snappy thuần túy: giảm {ratio_raw_inter}x so với CSV"
    })
    results.append({
        "experiment": "Experiment_A_Raw_Full",
        "dataset": "Food.com RAW_recipes",
        "format": "CSV",
        "size_mb": size_raw_rec_csv,
        "avg_time_sec": None,
        "std_time_sec": None,
        "notes": "100% cột thô (gồm steps, description), 231,637 dòng"
    })
    results.append({
        "experiment": "Experiment_A_Raw_Full",
        "dataset": "Food.com RAW_recipes",
        "format": "Parquet",
        "size_mb": size_raw_rec_pq,
        "avg_time_sec": None,
        "std_time_sec": None,
        "notes": f"Nén Parquet Snappy thuần túy: giảm {ratio_raw_rec}x so với CSV"
    })
    
    # =========================================================================
    # THÍ NGHIỆM B: DỮ LIỆU ĐÃ LÀM SẠCH (CLEAN DATA)
    # =========================================================================
    print("\n" + "-" * 70)
    print("[THÍ NGHIỆM B] So sánh trên DỮ LIỆU ĐÃ LÀM SẠCH (Cùng nội dung)")
    print("-" * 70)
    
    clean_inter_pq_path = get_path("clean", "food_com", "interactions_clean.parquet")
    clean_rec_pq_path = get_path("clean", "food_com", "recipes_clean.parquet")
    
    clean_inter_csv_path = f"{benchmark_hdfs_dir}/interactions_clean.csv"
    clean_rec_csv_path = f"{benchmark_hdfs_dir}/recipes_clean.csv"
    
    # Nạp dữ liệu sạch Parquet
    df_clean_inter = spark.read.parquet(clean_inter_pq_path)
    df_clean_rec = spark.read.parquet(clean_rec_pq_path)
    
    print(f"1. Ghi bảng sạch ra định dạng CSV để so sánh cùng nội dung...")
    # Ghi CSV interactions sạch
    df_clean_inter.write.mode("overwrite").option("header", "true").csv(clean_inter_csv_path)
    print(f"  -> Ghi xong: {clean_inter_csv_path}")
    
    # Với recipes_clean có cột array (tags, ingredients), chuyển sang chuỗi JSON hoặc nối chuỗi để ghi CSV
    df_clean_rec_csv = df_clean_rec \
        .withColumn("tags", to_json(col("tags"))) \
        .withColumn("ingredients", to_json(col("ingredients")))
    df_clean_rec_csv.write.mode("overwrite").option("header", "true").option("quoteAll", "true").csv(clean_rec_csv_path)
    print(f"  -> Ghi xong: {clean_rec_csv_path}")
    
    # Đo dung lượng Thí nghiệm B
    size_clean_inter_pq = get_hdfs_path_size_mb(spark, clean_inter_pq_path)
    size_clean_inter_csv = get_hdfs_path_size_mb(spark, clean_inter_csv_path)
    size_clean_rec_pq = get_hdfs_path_size_mb(spark, clean_rec_pq_path)
    size_clean_rec_csv = get_hdfs_path_size_mb(spark, clean_rec_csv_path)
    
    ratio_clean_inter = round(size_clean_inter_csv / size_clean_inter_pq, 2)
    ratio_clean_rec = round(size_clean_rec_csv / size_clean_rec_pq, 2)
    
    # Tổng hợp mức giảm tổng thể từ RAW CSV -> CLEAN Parquet
    total_reduction_inter = round(size_raw_inter_csv / size_clean_inter_pq, 2)
    
    print("\nKết quả Thí nghiệm B:")
    print(f"  * Clean Interactions: CSV = {size_clean_inter_csv} MB | Parquet = {size_clean_inter_pq} MB (Nén {ratio_clean_inter}x)")
    print(f"  * Clean Recipes     : CSV = {size_clean_rec_csv} MB | Parquet = {size_clean_rec_pq} MB (Nén {ratio_clean_rec}x)")
    print(f"  * Phân rã Interactions:")
    print(f"    - RAW CSV (333 MB) -> Clean CSV ({size_clean_inter_csv} MB) : Giảm {round((1 - size_clean_inter_csv/size_raw_inter_csv)*100, 1)}% do BỎ CỘT REVIEW VÀ BỎ DÒNG")
    print(f"    - Clean CSV ({size_clean_inter_csv} MB) -> Clean Parquet ({size_clean_inter_pq} MB) : Giảm {round((1 - size_clean_inter_pq/size_clean_inter_csv)*100, 1)}% do NÉN PARQUET SNAPPY")
    print(f"    - Tổng cộng RAW CSV -> Clean Parquet: Giảm {total_reduction_inter}x (không phải do Parquet nén 60x!)")
    
    results.append({
        "experiment": "Experiment_B_Clean_Data",
        "dataset": "Food.com interactions_clean",
        "format": "CSV",
        "size_mb": size_clean_inter_csv,
        "avg_time_sec": None,
        "std_time_sec": None,
        "notes": "706,514 dòng sạch, 4 cột"
    })
    results.append({
        "experiment": "Experiment_B_Clean_Data",
        "dataset": "Food.com interactions_clean",
        "format": "Parquet",
        "size_mb": size_clean_inter_pq,
        "avg_time_sec": None,
        "std_time_sec": None,
        "notes": f"Nén Parquet Snappy: giảm {ratio_clean_inter}x so với CSV sạch"
    })
    results.append({
        "experiment": "Experiment_B_Clean_Data",
        "dataset": "Food.com recipes_clean",
        "format": "CSV",
        "size_mb": size_clean_rec_csv,
        "avg_time_sec": None,
        "std_time_sec": None,
        "notes": "231,636 dòng sạch, 18 cột"
    })
    results.append({
        "experiment": "Experiment_B_Clean_Data",
        "dataset": "Food.com recipes_clean",
        "format": "Parquet",
        "size_mb": size_clean_rec_pq,
        "avg_time_sec": None,
        "std_time_sec": None,
        "notes": f"Nén Parquet Snappy: giảm {ratio_clean_rec}x so với CSV sạch"
    })
    
    # =========================================================================
    # THÍ NGHIỆM C: THỜI GIAN ĐỌC VÀ TRUY VẤN (QUERY BENCHMARK)
    # =========================================================================
    print("\n" + "-" * 70)
    print("[THÍ NGHIỆM C] Đo thời gian thực thi truy vấn (4 lần chạy, bỏ lần 1 làm nóng)")
    print("-" * 70)
    
    queries = [
        {
            "name": "Q1_Row_Count",
            "desc": "Đếm dòng toàn bảng (Full Scan)",
            "fn_csv": lambda: spark.read.option("header", "true").csv(clean_inter_csv_path).count(),
            "fn_pq": lambda: spark.read.parquet(clean_inter_pq_path).count()
        },
        {
            "name": "Q2_Avg_Rating_By_Recipe",
            "desc": "Tính trung bình rating theo món (Aggregation GroupBy)",
            "fn_csv": lambda: spark.read.option("header", "true").csv(clean_inter_csv_path) \
                                   .groupBy("recipe_id").agg(avg(col("rating").cast("float"))).count(),
            "fn_pq": lambda: spark.read.parquet(clean_inter_pq_path) \
                                  .groupBy("recipe_id").agg(avg("rating")).count()
        },
        {
            "name": "Q3_Projection_Filter_3_Cols",
            "desc": "Chỉ đọc 3 cột & lọc rating >= 4.0 (Column Pruning Pushdown)",
            "fn_csv": lambda: spark.read.option("header", "true").csv(clean_inter_csv_path) \
                                   .select("user_id", "recipe_id", "rating") \
                                   .filter(col("rating").cast("float") >= 4.0).count(),
            "fn_pq": lambda: spark.read.parquet(clean_inter_pq_path) \
                                  .select("user_id", "recipe_id", "rating") \
                                  .filter(col("rating") >= 4.0).count()
        }
    ]
    
    q_bench_records = []
    
    for q in queries:
        q_name = q["name"]
        q_desc = q["desc"]
        print(f"\n* Đang đo truy vấn: {q_name} ({q_desc})")
        
        # 1. Đo với CSV
        csv_times = []
        for r in range(4):
            t0 = time.perf_counter()
            cnt = q["fn_csv"]()
            elapsed = time.perf_counter() - t0
            if r == 0:
                print(f"    [CSV] Run 1 (Warmup): {elapsed:.4f}s (result={cnt:,})")
            else:
                csv_times.append(elapsed)
                print(f"    [CSV] Run {r+1}: {elapsed:.4f}s")
                
        csv_avg = float(np.mean(csv_times))
        csv_std = float(np.std(csv_times, ddof=1)) if len(csv_times) > 1 else 0.0
        
        # 2. Đo với Parquet
        pq_times = []
        for r in range(4):
            t0 = time.perf_counter()
            cnt = q["fn_pq"]()
            elapsed = time.perf_counter() - t0
            if r == 0:
                print(f"    [Parquet] Run 1 (Warmup): {elapsed:.4f}s (result={cnt:,})")
            else:
                pq_times.append(elapsed)
                print(f"    [Parquet] Run {r+1}: {elapsed:.4f}s")
                
        pq_avg = float(np.mean(pq_times))
        pq_std = float(np.std(pq_times, ddof=1)) if len(pq_times) > 1 else 0.0
        
        speedup = round(csv_avg / pq_avg, 2)
        print(f"  => {q_name}: CSV = {csv_avg:.3f}s ± {csv_std:.3f}s | Parquet = {pq_avg:.3f}s ± {pq_std:.3f}s -> Parquet nhanh gấp {speedup}x")
        
        results.append({
            "experiment": "Experiment_C_Query_Latency",
            "dataset": f"Food.com {q_name}",
            "format": "CSV",
            "size_mb": size_clean_inter_csv,
            "avg_time_sec": round(csv_avg, 3),
            "std_time_sec": round(csv_std, 3),
            "notes": f"Truy vấn: {q_desc}"
        })
        results.append({
            "experiment": "Experiment_C_Query_Latency",
            "dataset": f"Food.com {q_name}",
            "format": "Parquet",
            "size_mb": size_clean_inter_pq,
            "avg_time_sec": round(pq_avg, 3),
            "std_time_sec": round(pq_std, 3),
            "notes": f"Parquet nhanh gấp {speedup}x so với CSV"
        })
        
        q_bench_records.append({
            "query": q_name,
            "desc": q_desc,
            "csv_avg": csv_avg,
            "csv_std": csv_std,
            "pq_avg": pq_avg,
            "pq_std": pq_std,
            "speedup": speedup
        })
        
    # =========================================================================
    # LƯU KẾT QUẢ VÀ VẼ BIỂU ĐỒ
    # =========================================================================
    results_dir = ROOT_DIR / "data" / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    csv_out_path = results_dir / "storage_benchmark.csv"
    
    df_results = pd.DataFrame(results)
    df_results.to_csv(csv_out_path, index=False, encoding="utf-8-sig")
    print(f"\n[D] Đã lưu kết quả đo benchmark CSV: {csv_out_path}")
    
    figures_dir = ROOT_DIR / "reports" / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    fig_out_path = figures_dir / "storage_benchmark.png"
    
    print("\n[E] Đang tạo biểu đồ trực quan hóa: storage_benchmark.png...")
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
    
    # Subplot 1: So sánh dung lượng lưu trữ (MB)
    categories = [
        "RAW Interactions\n(1.13M dòng, full cột)",
        "RAW Recipes\n(231K dòng, full cột)",
        "Clean Interactions\n(706K dòng, 4 cột)",
        "Clean Recipes\n(231K dòng, 18 cột)"
    ]
    csv_sizes = [size_raw_inter_csv, size_raw_rec_csv, size_clean_inter_csv, size_clean_rec_csv]
    pq_sizes = [size_raw_inter_pq, size_raw_rec_pq, size_clean_inter_pq, size_clean_rec_pq]
    
    x = np.arange(len(categories))
    width = 0.35
    
    rects1 = ax1.bar(x - width/2, csv_sizes, width, label="Định dạng CSV", color="#e74c3c", alpha=0.85)
    rects2 = ax1.bar(x + width/2, pq_sizes, width, label="Định dạng Parquet (Snappy)", color="#2ecc71", alpha=0.85)
    
    ax1.set_ylabel("Dung lượng lưu trữ trên HDFS (MB)", fontsize=11, fontweight="bold")
    ax1.set_title("So sánh Dung lượng Lưu trữ: CSV vs Parquet\n(Đo lường công bằng trên cùng nội dung)", fontsize=12, fontweight="bold")
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories, fontsize=9)
    ax1.legend(fontsize=10)
    
    # Gắn nhãn giá trị
    for rect in rects1:
        h = rect.get_height()
        ax1.annotate(f"{h:.1f} MB", xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
    for rect in rects2:
        h = rect.get_height()
        ax1.annotate(f"{h:.1f} MB", xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
                     
    # Subplot 2: So sánh thời gian truy vấn (Latency)
    q_labels = ["Q1: Đếm dòng\n(Full Scan)", "Q2: GroupBy Rating\n(Aggregation)", "Q3: Chiếu 3 Cột\n(Projection Pushdown)"]
    c_times = [r["csv_avg"] for r in q_bench_records]
    c_stds = [r["csv_std"] for r in q_bench_records]
    p_times = [r["pq_avg"] for r in q_bench_records]
    p_stds = [r["pq_std"] for r in q_bench_records]
    
    xq = np.arange(len(q_labels))
    rects3 = ax2.bar(xq - width/2, c_times, width, yerr=c_stds, capsize=4, label="Định dạng CSV", color="#e74c3c", alpha=0.85)
    rects4 = ax2.bar(xq + width/2, p_times, width, yerr=p_stds, capsize=4, label="Định dạng Parquet", color="#3498db", alpha=0.85)
    
    ax2.set_ylabel("Thời gian thực thi trung bình (Giây)", fontsize=11, fontweight="bold")
    ax2.set_title("So sánh Thời gian Truy vấn (Query Latency)\n(Spark Standalone 4 Cores, trung bình 3 lần chạy)", fontsize=12, fontweight="bold")
    ax2.set_xticks(xq)
    ax2.set_xticklabels(q_labels, fontsize=9)
    ax2.legend(fontsize=10)
    
    for idx, (rect, sp) in enumerate(zip(rects4, [r["speedup"] for r in q_bench_records])):
        h = rect.get_height()
        ax2.annotate(f"{h:.2f}s\n(x{sp})", xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold", color="#2980b9")
    for rect in rects3:
        h = rect.get_height()
        ax2.annotate(f"{h:.2f}s", xy=(rect.get_x() + rect.get_width()/2, h),
                     xytext=(0, 3), textcoords="offset points", ha="center", va="bottom", fontsize=8, fontweight="bold")
                     
    plt.tight_layout()
    plt.savefig(fig_out_path, dpi=300)
    plt.close()
    print(f"  -> Đã lưu biểu đồ: {fig_out_path}")
    
    total_elapsed = time.time() - start_all
    print("\n" + "=" * 80)
    print(f"   HOÀN TẤT THỰC NGHIỆM LƯU TRỮ P4 TRONG {total_elapsed:.2f} GIÂY")
    print("=" * 80)
    

if __name__ == "__main__":
    run_benchmark()

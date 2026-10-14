# HỢP ĐỒNG DỮ LIỆU GIAO DIỆN WEB TĨNH (WEB DATA CONTRACT)

- **Phiên bản:** 1.0 (Triển khai Web Dashboard Tĩnh độc lập)
- **Thư mục đích:** `web/data/`
- **Công cụ sinh dữ liệu:** `src/export_for_web.py`
- **Cơ chế nạp:** Nạp qua thẻ `<script src="data/...js">`, gán dữ liệu vào đối tượng toàn cục `window.WEB_DATA_*` để hỗ trợ 100% chạy offline khi mở trực tiếp bằng giao thức `file://` (không bị CORS block) hoặc qua máy chủ cục bộ (`python -m http.server`).

---

## 1. Danh mục Tệp Dữ liệu và Ngân sách Dung lượng

| Tên tệp | Đối tượng toàn cục | Dung lượng thực tế | Ngân sách cho phép | Trang sử dụng | Cơ chế nạp |
|---|---|:---:|:---:|---|---|
| `summary.js` | `window.WEB_DATA_SUMMARY` | 5.7 KB | < 3 MB | Trang 1: Dữ liệu (`#/du-lieu`) | Nạp ngay ban đầu (Eager) |
| `system.js` | `window.WEB_DATA_SYSTEM` | 10.0 KB | < 3 MB | Trang 2: Hệ thống (`#/he-thong`) | Nạp ngay ban đầu (Eager) |
| `behavior.js` | `window.WEB_DATA_BEHAVIOR` | 8.5 KB | < 3 MB | Trang 3: Hành vi (`#/hanh-vi`) | Nạp ngay ban đầu (Eager) |
| `models.js` | `window.WEB_DATA_MODELS` | 10.8 KB | < 3 MB | Trang 5: Mô hình (`#/mo-hinh`) | Nạp ngay ban đầu (Eager) |
| `recs_vietnam.js` | `window.WEB_DATA_RECS_VN` | 1,916.4 KB (1.87 MB) | < 12 MB | Trang 4: Gợi ý (`#/goi-y`) | Nạp khi vào trang Gợi ý |
| `recs_foodcom.js` | `window.WEB_DATA_RECS_FC` | 2,410.1 KB (2.35 MB) | < 12 MB | Trang 4: Gợi ý (`#/goi-y`) | Nạp lười (Lazy) khi chọn Food.com |
| **Tổng cộng** | — | **4.36 MB** | **< 40 MB** | — | **ĐẠT 100% NGÂN SÁCH** |

---

## 2. Đặc tả Chi tiết Schema Từng Tệp

### 2.1. `summary.js` (`window.WEB_DATA_SUMMARY`)
- **Nguồn gốc:** `app/data/cleaning_log.csv`, `app/data/eda_12_dataset_comparison.csv`, `app/data/eda/eda_01_*_rating_dist.csv`.
- **Cấu trúc trường:**
  - `cleaning_log`: Mảng 18 bản ghi quy trình làm sạch dữ liệu:
    - `dataset`: Tên tập (`food_com_recipes`, `food_com_interactions`, `vifoodrec_foods`, `vifoodrec_ratings`).
    - `step_name`: Tên bước xử lý kỹ thuật.
    - `rows_before`, `rows_after`, `rows_dropped`: Số lượng bản ghi trước, sau và bị loại bỏ.
    - `notes`: Giải thích kỹ thuật nguyên nhân dòng bị loại.
  - `dataset_comparison`: Mảng 7 chỉ số so sánh Food.com và ViFoodRec (`ChiSo`, `Food_com`, `ViFoodRec`).
  - `rating_dist_vn`: Mảng 9 mức điểm của ViFoodRec (1.0 đến 5.0, bước 0.5) gồm `rating`, `count`, `pct`.
  - `rating_dist_fc`: Mảng 5 mức điểm của Food.com (1.0 đến 5.0) gồm `rating`, `count`, `pct`.
  - `data_limits`: Mảng 3 chuỗi giới hạn cốt lõi của dữ liệu.

### 2.2. `system.js` (`window.WEB_DATA_SYSTEM`)
- **Nguồn gốc:** `reports/evidence/stage_P2.md`, `app/data/storage_benchmark.csv`, `app/data/scalability.csv`.
- **Cấu trúc trường:**
  - `cluster_info`: Cấu hình cụm phân tán thật đo đạc từ môi trường Docker:
    - `mode`: Docker Cluster phân tán HDFS + Apache Spark.
    - `host`: Windows 11 WSL2, 24GB RAM vật lý, 16GB RAM Docker.
    - `hdfs`: 1 NameNode (IPC: 9000, UI: 9870), 2 DataNodes, replication 2.
    - `spark`: 1 Master (7077/8080), 2 Workers (mỗi worker 2 cores, 3.5GB RAM; tổng 4 cores, 7GB RAM).
    - `client`: `bigdata_spark_env` (2GB driver RAM).
  - `storage_benchmark`: 14 bản ghi đo lường dung lượng CSV vs Parquet và độ trễ truy vấn (Exp A, Exp B, Exp C).
  - `scalability`: 32 bản ghi đo thời gian chạy của 1 Worker vs 2 Workers trên các tỷ lệ dữ liệu 10%, 25%, 50%, 100%.

### 2.3. `behavior.js` (`window.WEB_DATA_BEHAVIOR`)
- **Nguồn gốc:** `app/data/cluster_profiles_*.csv`, `app/data/food_cluster_profiles_vietnam.csv`, `app/data/kmeans_tuning.csv`, `app/data/food_clusters_vietnam.parquet`.
- **Cấu trúc trường:**
  - `vn_user_clusters`: 4 hàng (3 cụm + overall) cho người dùng ViFoodRec.
  - `fc_user_clusters`: 5 hàng (4 cụm + overall) cho người dùng Food.com.
  - `vn_food_clusters`: 5 hàng (4 cụm món + overall) cho món ăn Việt Nam.
  - `kmeans_tuning`: 18 hàng dữ liệu dò tìm số cụm k (k, silhouette, wssse, time_sec).
  - `representative_foods_vn`: Từ điển {cluster_id: danh sách 5 món tiêu biểu}.

### 2.4. `models.js` (`window.WEB_DATA_MODELS`)
- **Nguồn gốc:** `app/data/model_comparison.csv`, `app/data/als_rmse_breakdown.csv`, `app/data/baseline_rmse_breakdown.csv`, `app/data/als_tuning_*.csv`.
- **Cấu trúc trường:**
  - `model_comparison`: 8 hàng đối đầu giữa 3 baselines và ALS trên 2 bộ dữ liệu (RMSE, MAE, Precision@10, Recall@10, coverage).
  - `als_rmse_breakdown`: Sai số RMSE của ALS phân rã theo điểm thật (1.0 - 5.0).
  - `baseline_rmse_breakdown`: Sai số RMSE của các baseline phân rã theo điểm thật.
  - `als_tuning_vn`: 24 cấu hình Grid Search ALS cho ViFoodRec.
  - `als_tuning_fc`: 8 cấu hình Grid Search ALS cho Food.com.

### 2.5. `recs_vietnam.js` (`window.WEB_DATA_RECS_VN`)
- **Nguồn gốc:** `app/data/foods_vietnam.parquet`, `app/data/recommendations_vietnam.parquet`, `app/data/user_clusters_vietnam.parquet`, `app/data/item_neighbors_vietnam.parquet`.
- **Cấu trúc trường:**
  - `catalog`: 4,000 món ăn Việt (`food_id`, `dish_name`, `dish_type`, `calories`, `cooking_time_min`, `ingredients`).
  - `recommendations`: 1,010 gợi ý ALS cho 101 người dùng (10 món/người).
  - `user_clusters`: Bản đồ 101 người dùng -> cụm hành vi.
  - `item_neighbors`: Bản đồ 4,000 món -> danh sách 10 món tương đồng gần nhất và điểm cosine.

### 2.6. `recs_foodcom.js` (`window.WEB_DATA_RECS_FC`)
- **Nguồn gốc:** `app/data/recipes_foodcom_sample.parquet`, `app/data/recommendations_foodcom_sample.parquet`, `app/data/user_clusters_foodcom.parquet`, `app/data/item_neighbors_foodcom.parquet`.
- **Cấu trúc trường:**
  - `catalog`: 3,055 công thức Food.com chọn lọc xuất hiện trong gợi ý và láng giềng hàng đầu (`recipe_id`, `name`, `calories`, `minutes_clean`, `ingredients`).
  - `recommendations`: 10,000 gợi ý ALS cho 1,000 người dùng mẫu.
  - `user_clusters`: Bản đồ 1,000 người dùng -> cụm hành vi.
  - `item_neighbors`: Bản đồ 2,500 món phổ biến -> danh sách 10 món tương đồng và điểm cosine.

---

## 3. Quy tắc Kiểm định Toàn vẹn
- Tất cả các trường số được làm sạch bằng `clean_val` đảm bảo không có `NaN`, `Infinity` gây lỗi `JSON.parse`.
- Giá trị chuỗi tiếng Việt chuẩn hóa UTF-8.
- Kịch bản xác thực `src/verify_web.py` sẽ đối chiếu trực tiếp các con số giữa `web/data/*.js` và các tệp nguồn gốc CSV/Parquet.

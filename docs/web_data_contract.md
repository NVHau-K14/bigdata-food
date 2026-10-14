# Hợp đồng dữ liệu giao diện web tĩnh

- **Phiên bản:** 2.0 (cập nhật ngày 14/10/2026 ở stage S4; thay phiên bản 1.0)
- **Thư mục đích:** `web/data/`
- **Công cụ sinh dữ liệu:** `src/export_for_web.py` (đọc `app/data/`, `docker-compose.yml`, log của S1 đến S3)
- **Cơ chế nạp:** thẻ `<script src="data/...js">`, gán vào đối tượng toàn cục `window.WEB_*`; chạy offline khi mở trực tiếp bằng `file://` hoặc qua máy chủ cục bộ.
- **Nguyên tắc:** mọi số và chữ hiển thị đến từ các tệp này, không viết cứng trong JS. Các trường `facts` chỉ chứa SỐ; định dạng kiểu Việt Nam (dấu phẩy thập phân, dấu chấm nghìn) làm ở `web/js/format.js`, một hàm `fmt()` duy nhất.

## 1. Danh mục tệp và dung lượng

| Tệp | Biến toàn cục | Dung lượng (14/10/2026) | Ngân sách | Trang dùng | Nạp |
|---|---|---:|---:|---|---|
| `labels.js` | `WEB_LABELS` | 0,5 KB | 3 MB | mọi trang | ngay |
| `summary.js` | `WEB_DATA_SUMMARY` | 6,4 KB | 3 MB | Dữ liệu | ngay |
| `system.js` | `WEB_DATA_SYSTEM` | 2,3 KB | 3 MB | Hệ thống | ngay |
| `behavior.js` | `WEB_DATA_BEHAVIOR` | 13,2 KB | 3 MB | Hành vi | ngay |
| `models.js` | `WEB_DATA_MODELS` | 13,4 KB | 3 MB | Mô hình | ngay |
| `recs_vietnam.js` | `WEB_DATA_RECS_VN` | 1.799 KB | 12 MB | Gợi ý | ngay |
| `recs_foodcom.js` | `WEB_DATA_RECS_FC` | 4.850 KB | 12 MB | Gợi ý | khi chọn Food.com |

Tổng khoảng 6,6 MB, trong ngân sách 40 MB.

## 2. Schema

### 2.1. `labels.js`
Bảng nhãn hiển thị duy nhất (nguồn `src/web_labels.py`, `verify_web.py` đối chiếu): `dish_type` ("Món mặn" thành "Không chay", "Món chay" thành "Chay"), `models` (tên mô hình tiếng Việt), `datasets`, `cluster_name_replacements`. Lý do: cột nguồn `dish_type` chỉ có hai giá trị, và chè, bánh cũng mang "Món mặn", nên "mặn" thực chất là "không gắn nhãn chay". Dữ liệu gốc không đổi.

### 2.2. `summary.js`
Nguồn: `cleaning_log.csv`, `eda_12_dataset_comparison.csv`, `eda/eda_01_*_rating_dist.csv`.
- `cleaning_log`: toàn bộ nhật ký làm sạch.
- `funnel`: `vifoodrec` (4 bước: raw, scale, fk, kcore) và `food_com` (3 bước: raw, zero, kcore); mỗi bước có `count`, `dropped` và số kèm theo (`levels`, `rounds`).
- `dataset_comparison`: 7 chỉ số, mỗi chỉ số có `key` (tên gốc trong CSV), `label` (tên hiển thị), `vifoodrec`, `food_com`.
- `rating_dist_vn`: 11 mức điểm 0,0 đến 5,0 (`rating`, `count`, `pct`); `rating_dist_fc`: 5 mức.
- `facts`: số dùng trong tiêu đề và ghi chú (số người dùng, món, đánh giá, độ thưa, phần trăm nhỏ nhất và lớn nhất, 5 sao của Food.com, số dòng loại ở khóa ngoại).
- `source`: tên các tệp nguồn.

### 2.3. `system.js`
Nguồn: `docker-compose.yml`, `reports/evidence/logs/S3_14_fsck.log`, log `S2_03` (dòng "Running Spark version"), `storage_benchmark.csv`, `scalability.csv`.
- `cluster_info.hdfs`: `version`, `namenodes`, `datanodes`, `replication`, `fsck` (từng đường dẫn: trạng thái, số khối thiếu bản sao, số tệp).
- `cluster_info.spark`: `version` (phiên bản chạy thật), `workers`, `worker_cores`, `worker_ram_mb`, tổng.
- `storage_rows` (4 dòng: CSV, Parquet, tỷ lệ nén), `latency_rows` (3 truy vấn: trung bình, độ lệch chuẩn, tỷ lệ tăng tốc), `scalability` (thời gian chạy cả pipeline theo tỷ lệ dữ liệu và số Worker).

### 2.4. `behavior.js`
Nguồn: `cluster_profiles_*.csv`, `food_cluster_profiles_vietnam.csv`, `kmeans_tuning.csv`, `cluster_top_items.csv`, `food_clusters_vietnam.parquet`, `foods_vietnam.parquet`.
- `fc_user_clusters`, `vn_user_clusters`, `vn_food_clusters`: hồ sơ cụm (cluster = -1 là dòng toàn hệ thống); tên cụm đã qua bảng thay thế "Món mặn" thành "Món không chay".
- `top_items`: khóa theo bộ dữ liệu (`food_com`, `vifoodrec_users`, `vifoodrec_foods`) rồi theo id cụm của chính bộ đó. `food_com` và `vifoodrec_users`: 5 món có điểm từ 4 trở lên nhiều lượt nhất trong tập train của cụm (`count`); `vifoodrec_foods`: 5 món có mã nhỏ nhất của cụm món (ví dụ minh họa, `count` là null). Đây là sửa lỗi A1: trước S4 web dùng nhầm danh sách cụm món ViFoodRec cho mọi bộ.
- `kmeans_tuning`, `facts` (khoảng điểm trung bình, thời gian nấu, hệ số Silhouette, chênh lệch tương đối giữa các cụm ViFoodRec).

### 2.5. `models.js`
Nguồn: `model_comparison.csv`, `als_rmse_breakdown.csv`, `baseline_rmse_breakdown.csv`, `als_tuning_*.csv`.
- `model_comparison`: các dòng của S3 và S3b (ALS ngầm định có RMSE, MAE là null); bỏ dòng "ALS Matrix Factorization (lưới mở rộng)" vì trùng hệt ALS cũ của Food.com. Mỗi dòng có `model_label` và `is_als`.
- `als_rmse_breakdown`, `baseline_rmse_breakdown`: RMSE theo điểm thật (ViFoodRec 11 mức, Food.com 5 mức).
- `als_tuning_vn` (24 cấu hình), `als_tuning_fc` (8 cấu hình dòng cũ).
- `facts`: mô hình đứng đầu từng độ đo theo bộ dữ liệu, dùng để sinh tiêu đề trang.

### 2.6. `recs_vietnam.js`, `recs_foodcom.js`
- `catalog`: ViFoodRec 4.000 món (`food_id`, `dish_name`, `dish_type`, `calories`, `cooking_time_min`, `ingredients`); Food.com gồm các công thức xuất hiện trong gợi ý, trong danh sách món có láng giềng và trong chính danh sách láng giềng (sửa lỗi: trước S4 thiếu các món láng giềng nên web hiện "Món <mã>").
- `recommendations`: ViFoodRec 1.010 dòng (101 người dùng x 10 món); Food.com 10.000 dòng (1.000 người dùng x 10 món).
- `user_clusters`: người dùng sang cụm; ViFoodRec là "Cụm 1, 2, 3".
- `item_neighbors`: món sang 10 món có độ tương đồng cosine cao nhất.
- `neighbor_stats`: nhỏ nhất, trung vị và tỷ lệ điểm tương đồng từ 0,999 trở lên. Ở ViFoodRec cả 40.000 điểm bằng 1,0 (nhỏ nhất 1,0), nên web cảnh báo rằng thứ tự gợi ý cho người dùng mới chưa phản ánh khác biệt giữa các món.

## 3. Kiểm định
- `src/verify_web.py`: đối chiếu `web/data/*.js` với tệp nguồn, và văn bản thực sự hiển thị (do `src/verify_web_ui.mjs` ghi) với số kỳ vọng định dạng theo đúng số chữ số hiển thị; kiểm tra A1, A3, A4, C2.
- `src/verify_web_ui.mjs`: Chrome headless, không cuộn trang ở 1920x1080 và 1366x768, quét văn bản hiển thị, luồng demo, ảnh chụp.
- `src/verify_web_style.py`: quét mã, tương phản, thang xám, diện tích màu cam, ảnh chia sẻ.

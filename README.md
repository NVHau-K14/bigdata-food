# Đồ án Big Data: phân tích hành vi ăn uống và gợi ý món ăn

Đồ án môn Nhập môn Big Data. Hai bộ dữ liệu ẩm thực được xử lý bằng cùng một pipeline Spark trên HDFS: làm sạch, mô hình cơ sở, ALS (gợi ý), K-means (hành vi), thực nghiệm mở rộng quy mô, rồi xuất kết quả cho dashboard web tĩnh.

Số liệu trong tệp này lấy từ các tệp kết quả ghi ở cột "Nguồn". Bảng số đầy đủ và các hạn chế nằm ở [reports/evidence/STATUS.md](reports/evidence/STATUS.md); câu hỏi phản biện ở [docs/Q_and_A.md](docs/Q_and_A.md).

---

## 1. Dữ liệu

Hai bộ không có người dùng chung nên không gộp; mỗi bộ chạy độc lập qua cùng một pipeline.

| Chỉ số | ViFoodRec (món Việt) | Food.com (món Âu Mỹ) | Nguồn |
|---|---:|---:|---|
| Số đánh giá thô | 182.678 | 1.132.367 | `reports/evidence/cleaning_log.csv` |
| Số đánh giá sau làm sạch | 182.631 | 706.514 | `reports/evidence/cleaning_log.csv` |
| Số người dùng sau làm sạch | 101 | 30.836 | `results/eda/eda_12_dataset_comparison.csv` |
| Số món có đánh giá | 4.000 | 78.171 | `results/eda/eda_12_dataset_comparison.csv` |
| Độ thưa của ma trận | 54,79% | 99,97% | `results/eda/eda_12_dataset_comparison.csv` |
| Điểm trung bình | 2,50 | 4,71 | `results/eda/eda_12_dataset_comparison.csv` |
| Thang điểm | 11 mức, 0,0 đến 5,0, bước 0,5 | 5 mức, 1 đến 5 (đã bỏ điểm 0) | `reports/evidence/cleaning_log.csv` |

- ViFoodRec: giữ cả điểm 0,0 và 0,5 vì số dòng mỗi mức ngang nhau (từ 8,99% đến 9,23%), không có bằng chứng 0,0 là "chưa chấm". Chỉ loại 47 dòng có `food_id` không có trong danh mục (`reports/evidence/stage_S2.md`).
- Food.com: phân phối lệch, 78,40% đánh giá là 5 sao (`results/eda/eda_01_food_com_rating_dist.csv`).
- Giấy phép dữ liệu ViFoodRec: **chưa xác nhận**. Người dùng cho biết đây là dự án công khai, miễn phí trên GitHub, nhưng bản sao kho dữ liệu trong máy (README và thư mục `Data`) không nêu giấy phép và không có tệp LICENSE. Khi trích dẫn, ghi nguồn bài báo PACLIC 2024 (xem mục 8).

---

## 2. Kiến trúc và yêu cầu máy

Cụm giả lập chạy bằng Docker Compose trên **một máy Windows**: các container dùng chung CPU và RAM của máy, mạng là cầu nối ảo của Docker, không có mạng thật giữa các máy. "Phân tán" ở đây nghĩa là phần mềm chạy theo kiến trúc phân tán (khối HDFS nhân bản, tác vụ Spark chia cho hai Worker), không phải nhiều máy vật lý.

```text
Máy Windows ─ Docker Compose ─┬─ namenode, datanode1, datanode2   HDFS 3.3.6, dfs.replication = 2
                              ├─ spark-master, spark-worker-1/2   Spark 4.2.0 Standalone, mỗi Worker 2 nhân, 3.500 MB
                              └─ bigdata_spark_env                container client (driver, Python 3.13.16), gắn thư mục dự án
Máy chủ (ngoài Docker): Python 3.11 và Node.js để xuất dữ liệu web và kiểm thử giao diện (Chrome hoặc Edge).
```

Yêu cầu máy (cấu hình đã chạy thật: 24 GB RAM, cấp cho Docker khoảng 16 GB):
- Windows 10 hoặc 11, PowerShell, Docker Desktop (Compose v2). Mức RAM tối thiểu chưa được thử; cấu hình Spark dùng hai Worker 3,5 GB và driver 2,5 GB.
- Ổ đĩa: dữ liệu thô 624 MB; `/data` trên HDFS khoảng 1,1 GB (2,2 GB sau nhân bản); thêm vài trăm MB cho kết quả.
- Python 3.11 và Node.js 24 trên máy chủ, Chrome hoặc Edge (chỉ cần cho bước kiểm thử giao diện web).
- Trạng thái cụm: `hdfs fsck` báo HEALTHY, Under-replicated blocks = 0, cả khi đọc ngày 14/10/2026 (`reports/evidence/logs/S5_03_infra_state.log`) lẫn sau lần chạy sạch ở S6 (`S6_30_hdfs_fsck.log`, `S6_31_hdfs_fsck_models.log`).

---

## 3. Kết quả chính (tập test)

Nguồn: `results/model_comparison.csv`. RMSE và MAE 4 chữ số thập phân, P@10 và R@10 5 chữ số.

| Bộ | Mô hình | RMSE | MAE | P@10 | R@10 |
|---|---|---:|---:|---:|---:|
| Food.com | Trung bình toàn cục | 0,6266 | 0,4468 | 0,00000 | 0,00000 |
| Food.com | Trung bình món làm trơn | 0,6177 | 0,4214 | 0,00048 | 0,00130 |
| Food.com | Top món phổ biến | 0,6568 | 0,4120 | 0,00534 | 0,02170 |
| Food.com | ALS dự đoán điểm | 0,6747 | 0,5094 | 0,00017 | 0,00096 |
| Food.com | ALS ngầm định | không áp dụng | không áp dụng | 0,00570 | 0,02118 |
| ViFoodRec | Trung bình toàn cục | 1,5706 | 1,3502 | 0,00000 | 0,00000 |
| ViFoodRec | Trung bình món làm trơn | 1,5873 | 1,3690 | 0,01584 | 0,00321 |
| ViFoodRec | Top món phổ biến | 1,5924 | 1,3723 | 0,02277 | 0,00461 |
| ViFoodRec | ALS dự đoán điểm | 1,6654 | 1,4185 | 0,01386 | 0,00285 |
| ViFoodRec | ALS ngầm định | không áp dụng | không áp dụng | 0,01980 | 0,00428 |

ALS dự đoán điểm không tốt hơn mô hình cơ sở ở độ đo nào, trên cả hai bộ. ALS ngầm định (xem [reports/evidence/stage_S3b.md](reports/evidence/stage_S3b.md)) trên Food.com có P@10 cao hơn Top món phổ biến một chút (0,00570 so với 0,00534) và R@10 thấp hơn một chút (0,02118 so với 0,02170); trên ViFoodRec vẫn thua. Rò rỉ giữa train, validation và test bằng 0 (`reports/evidence/split_log.csv`).

Bảng nhạy cảm cho 3 cách xử lý thang điểm ViFoodRec: `results/vifoodrec_sensitivity.csv`. Ở cả 3 biến thể thứ tự RMSE giữa các mô hình không đổi.

---

## 4. Dashboard web (`web/`)

Trang web tĩnh (HTML, CSS, JS thuần), mở được bằng cách nhấp đúp `web/index.html`, không cần mạng (phông chữ và dữ liệu lưu cục bộ). Năm trang: Dữ liệu, Hệ thống, Hành vi, Gợi ý, Mô hình. Mỗi trang vừa một màn hình ở 1920x1080 và 1366x768.

Kiểm thử (log trong `reports/evidence/logs/`): `verify_web.py` 122 mục (`S4_07`), `verify_web_ui.mjs` 129 mục (`S4_08`), `verify_web_style.py` 21 mục (`S4_09`). Chi tiết ở [reports/evidence/stage_S4.md](reports/evidence/stage_S4.md).

Thư mục `app/` là bản Streamlit cũ, giữ làm bản lưu; `app/data/` vẫn là nguồn dữ liệu mà `src/export_for_web.py` đọc.

---

## 5. Cấu trúc thư mục

```text
bigdata-food/
├── data/raw/                # Dữ liệu thô (chỉ đọc, không đưa lên git)
├── data/results/, results/  # Bảng kết quả (hai nơi trùng nhau)
├── src/                     # Mã pipeline (làm sạch, chia, mô hình, phân cụm), xuất dữ liệu và kiểm thử
├── web/                     # Dashboard web tĩnh (dashboard chính)
├── app/                     # Bản Streamlit lưu trữ; app/data/ là nguồn dữ liệu của web
├── reports/evidence/        # Biên bản stage_*.md, STATUS.md, logs/ (log nguyên văn từng lệnh)
├── reports/figures/         # Hình biểu đồ và ảnh chụp giao diện
├── docs/                    # CONTEXT.md, data_contract.md, web_data_contract.md, Q_and_A.md
├── scratch/                 # Script kiểm chứng dùng một lần (chẩn đoán, đối chiếu)
├── docker-compose.yml       # Cụm HDFS và Spark (image ghim theo phiên bản)
├── requirements.txt         # Phiên bản thư viện Python đã chạy thật
└── run_all.ps1              # Chạy toàn bộ pipeline, ghi log từng bước
```

---

## 6. Cài đặt và chạy

### 6.1. Cài đặt

1. Cài Docker Desktop, cấp cho Docker khoảng 16 GB RAM (Settings, Resources).
2. Đặt dữ liệu thô vào `data/raw/`: `food_com/RAW_interactions.csv`, `food_com/RAW_recipes.csv` (Kaggle) và `food_vietnam/foods.csv`, `food_vietnam/ratings.csv` (kho ViFoodRec). Thư mục này được gắn chỉ đọc vào container `namenode`.
3. Cài Python 3.11 và thư viện của máy chủ: `pip install pandas==2.3.3 pyarrow==25.0.1 numpy==2.4.6 pillow==12.3.0`. Cài Node.js 24 nếu muốn chạy kiểm thử giao diện web.
4. Thư viện của pipeline Spark (pyspark, pandas, matplotlib, seaborn) đã có sẵn trong image `quay.io/jupyter/pyspark-notebook:spark-4.2.0`; phiên bản ghi ở `requirements.txt`.

### 6.2. Chạy tất cả

```powershell
.\run_all.ps1                      # toàn bộ: cụm, nạp dữ liệu, làm sạch, mô hình, phân cụm, thực nghiệm mở rộng, xuất web, kiểm thử
.\run_all.ps1 -Fast                # bỏ ba bước nặng: benchmark lưu trữ, thực nghiệm mở rộng, ALS ngầm định
.\run_all.ps1 -WebOnly -ServeWeb   # chỉ phần web (không cần Spark), mở http://localhost:8000/
```

Mỗi bước ghi log nguyên văn vào `reports/evidence/logs/<LogPrefix>NN_<tên bước>.log` (đổi tiền tố bằng `-LogPrefix`) và dừng ngay khi có lỗi; có thể chạy tiếp từ một bước bằng `-StartAt <tên bước>`. Thời gian đo trong lần chạy sạch ở S6: khoảng 38 phút cho 35 bước, trong đó ALS ngầm định chiếm 21,6 phút (`reports/evidence/logs/S6_tong_ket.log`, `S6_tong_ket_tiep_tu_mo_rong_2_worker.log`).

### 6.3. Chạy từng bước

Các bước Spark chạy trong container `bigdata_spark_env`, thư mục `/home/jovyan/work`, theo thứ tự dưới đây (mỗi tệp chạy bằng `docker exec -w /home/jovyan/work bigdata_spark_env /opt/conda/bin/python <tệp>`):

| # | Tệp | Việc làm |
|---|---|---|
| 0 | `docker compose up -d` | Khởi động cụm; nạp dữ liệu thô lên HDFS bằng `hdfs dfs -put` (xem `run_all.ps1`) |
| 1 | `src/smoke_test_cluster.py` | Kiểm tra cụm đọc CSV và ghi Parquet |
| 2 | `src/run_pipeline_p3.py`, `src/verify_clean.py` | Làm sạch cả hai bộ; kiểm tra dữ liệu sạch (6 mục) |
| 3 | `src/storage_benchmark.py`, `src/eda_analysis.py` | So sánh CSV và Parquet; thống kê khám phá |
| 4 | `src/split_data.py`, `src/baseline.py` | Chia 80/10/10 (seed 42); ba mô hình cơ sở |
| 5 | `src/train_als.py`, `src/als_improve.py` | ALS dự đoán điểm; thử lưới mở rộng và ALS ngầm định (chạy `als_improve.py` SAU `train_als.py`, vì `train_als.py` ghi lại bảng so sánh) |
| 6 | `src/kmeans_behavior.py`, `src/relabel_food_com_clusters.py`, `src/vifoodrec_sensitivity.py` | Phân cụm; đổi nhãn cụm Food.com; độ nhạy thang điểm ViFoodRec |
| 7 | `src/scalability_experiment.py` | Đo mở rộng quy mô: chạy với 2 Worker, rồi `docker stop spark-worker-2` và chạy lại để đo 1 Worker, sau đó `docker start spark-worker-2` |
| 8 | `src/export_cluster_top_items.py`, `src/export_for_app.py`, `src/verify_export.py` | Xuất kết quả vào `app/data/` và kiểm tra |
| 9 | `src/export_for_web.py`, `node src/verify_web_ui.mjs`, `src/verify_web.py`, `src/verify_web_style.py` | Chạy trên máy chủ: xuất dữ liệu web và ba bộ kiểm thử |

### 6.4. Mở dashboard web

Nhấp đúp `web/index.html` (không cần mạng), hoặc `.\run_all.ps1 -WebOnly -ServeWeb` rồi mở http://localhost:8000/. Hướng dẫn chi tiết ở `web/README_web.md`.

### 6.5. Chạy thử trên bản sao (kiểm tra người ngoài chạy lại được)

```powershell
git clone <thư mục dự án> bigdata-food-cleanrun
cd bigdata-food-cleanrun
.\run_all.ps1 -CleanRun -LogPrefix S6_    # dùng cụm đang chạy của bản chính, thư mục HDFS riêng /cleanrun, container client riêng
```

Biến môi trường `HDFS_ROOT` (đọc trong `src/config.py`) đặt thư mục gốc trên HDFS; mặc định rỗng. Kết quả đối chiếu bản sao với bản chính ở `reports/evidence/stage_S6.md`.

### 6.6. Chế độ local

`.\run_all.ps1 -StorageMode local` chạy phần ViFoodRec (làm sạch, chia, mô hình cơ sở, ALS, K-means) bằng Spark `local[*]` đọc `data/raw/` trên máy, kết quả Spark ghi vào `data/spark_results/`. Đã kiểm chứng ở S6 cho ViFoodRec (RMSE, MAE, P@10, R@10 trùng chế độ HDFS); chưa chạy chế độ local cho Food.com.

---

## 7. Phiên bản đã ghim

| Thành phần | Phiên bản | Nơi ghim |
|---|---|---|
| Image HDFS | `apache/hadoop:3.3.6` | `docker-compose.yml` |
| Image Spark và client | `quay.io/jupyter/pyspark-notebook:spark-4.2.0` (Spark 4.2.0, Python 3.13.16) | `docker-compose.yml` |
| Thư viện trong container | pandas 2.3.3, pyarrow 25.0.0, numpy 2.5.4, matplotlib 3.11.2, seaborn 0.13.2 | `requirements.txt` |
| Máy chủ | Python 3.11.9, pandas 2.3.3, pyarrow 25.0.1, numpy 2.4.6, pillow 12.3.0, Node.js 24.14.0 | `requirements.txt` |

Image được ghim theo thẻ phiên bản, chưa ghim theo mã băm nội dung (digest).

---

## 8. Nguồn dữ liệu và giấy phép

- **Food.com**: `RAW_interactions.csv`, `RAW_recipes.csv` từ Kaggle. Giấy phép theo trang Kaggle của bộ dữ liệu; **chưa xác nhận** trong phiên làm việc này.
- **ViFoodRec**: Dang, C. T., Dang, T. H. T., Tran Huynh, Q. A., "A New Dataset and Empirical Evaluation for Vietnamese Food Recommendation System", PACLIC 2024; kho GitHub của nhóm tác giả (Trường Đại học Công nghệ Thông tin, ĐHQG TP.HCM). Giấy phép: **chưa xác nhận**; bản sao kho trong máy không nêu giấy phép.
- Không có người dùng chung giữa hai bộ, nên hai bộ chạy riêng qua cùng một pipeline và không gộp.

---

## 9. Hạn chế đã biết

- Cụm Spark và HDFS là giả lập trên một máy; thực nghiệm mở rộng quy mô chỉ tới 706.514 dòng và thời gian không tăng theo dữ liệu, nên chưa kết luận được về khả năng mở rộng (`results/scalability.csv`).
- ViFoodRec chỉ có 101 người dùng, phân phối điểm gần đều trên 11 mức (độ lệch chuẩn 1,5798 so với 1,5811 của phân phối đều lý thuyết, `stage_S2.md`). Nguồn gốc dữ liệu chưa được kiểm chứng.
- Độ tương đồng giữa các món ViFoodRec đều bằng 1,0 (40.000 điểm), nên gợi ý cho người dùng mới ở bộ này không phản ánh khác biệt giữa món (`stage_S4.md`).
- Ba cụm người dùng ViFoodRec không có tên diễn giải vì chênh lệch giữa các cụm nhỏ ở hầu hết đặc trưng (`stage_S3.md` mục 5).
- **Tái lập**: chạy sạch lại từ dữ liệu thô cho RMSE, MAE, P@10, R@10 và cách chia dữ liệu giống hệt bản chính, nhưng K-means Food.com không giống hệt: cùng bốn loại cụm và cùng tên, số người mỗi cụm lệch tới khoảng 1% và Silhouette khác (k = 4: 0,2788 so với 0,2743), vì kết quả phụ thuộc thứ tự dòng đầu vào. Mẫu 5.000 người dùng có gợi ý cho Food.com cũng đổi theo thứ tự dòng (`stage_S6.md` mục 4).
- Hình PCA cụm Food.com (`reports/figures/kmeans_user_clusters_foodcom_pca.png`) còn tên cụm cũ bằng tiếng Anh, không vẽ lại và không dùng.
- Chia train, validation, test theo dòng ngẫu nhiên, không theo thời gian; K-core tính trên toàn bộ dữ liệu trước khi chia.
- Đã kiểm thử web trên Chrome headless, chưa thử Edge, Firefox, Safari.

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
- Giấy phép của dữ liệu ViFoodRec: chưa xác nhận. Khi trích dẫn, ghi nguồn bài báo PACLIC 2024.

---

## 2. Hạ tầng

Cụm giả lập chạy bằng Docker Compose trên một máy Windows (các container dùng chung CPU và RAM của máy, mạng là cầu nối ảo của Docker, không có mạng thật giữa các máy).

- HDFS 3.3.6 (`apache/hadoop:3.3.6`): 1 NameNode, 2 DataNode, `dfs.replication = 2`.
- Spark 4.2.0 chế độ Standalone (`quay.io/jupyter/pyspark-notebook:spark-4.2.0`): 1 Master, 2 Worker, mỗi Worker 2 nhân và 3.500 MB.
- Python 3.13.16 trong container `bigdata_spark_env`.
- Trạng thái kiểm tra ngày 14/10/2026: `hdfs fsck` báo HEALTHY, Under-replicated blocks = 0 (`reports/evidence/logs/S5_03_infra_state.log`).
- Chế độ `STORAGE_MODE=local` có trong `src/config.py` nhưng chưa được kiểm chứng.

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
├── data/raw/                # Dữ liệu thô (chỉ đọc)
├── src/                     # Mã pipeline, xuất dữ liệu và kiểm thử
├── web/                     # Dashboard web tĩnh
├── app/                     # Bản Streamlit lưu trữ và dữ liệu xuất (app/data)
├── results/                 # Bảng kết quả thực nghiệm
├── reports/evidence/        # Biên bản stage_*.md, STATUS.md, nhật ký trong logs/
├── reports/figures/         # Hình biểu đồ và ảnh chụp giao diện
├── docs/                    # CONTEXT.md, data_contract.md, web_data_contract.md, Q_and_A.md
├── docker-compose.yml       # Cụm HDFS và Spark
└── run_all.ps1              # Xuất dữ liệu web, kiểm thử, mở web
```

---

## 6. Chạy

Pipeline nặng (làm sạch, chia dữ liệu, ALS, K-means) chạy trong container `bigdata_spark_env`, thư mục `/home/jovyan/work`. Ví dụ (đã dùng ở stage S3, xem `reports/evidence/stage_S3.md`):

```powershell
docker compose up -d
docker exec -w /home/jovyan/work bigdata_spark_env /opt/conda/bin/python src/smoke_test_cluster.py
docker exec -w /home/jovyan/work bigdata_spark_env /opt/conda/bin/python src/split_data.py --only vietnam
```

Phần xuất dữ liệu và web chạy trên máy chủ, không cần Spark:

```powershell
.\run_all.ps1                 # xuất dữ liệu web, kiểm thử, mở web tại http://localhost:8000/
python src/export_for_web.py
python src/verify_web.py
```

Kịch bản chạy từ đầu đến cuối và thử trên bản sao sạch là việc của stage S6, chưa làm.

---

## 7. Hạn chế đã biết

- Cụm Spark và HDFS là giả lập trên một máy; thực nghiệm mở rộng quy mô chỉ tới 706.514 dòng và thời gian không tăng theo dữ liệu, nên chưa kết luận được về khả năng mở rộng (`results/scalability.csv`).
- ViFoodRec chỉ có 101 người dùng, phân phối điểm gần đều trên 11 mức (độ lệch chuẩn 1,5798 so với 1,5811 của phân phối đều lý thuyết, `stage_S2.md`). Nguồn gốc dữ liệu chưa được kiểm chứng.
- Độ tương đồng giữa các món ViFoodRec đều bằng 1,0 (40.000 điểm), nên gợi ý cho người dùng mới ở bộ này không phản ánh khác biệt giữa món (`stage_S4.md`).
- Ba cụm người dùng ViFoodRec không có tên diễn giải vì chênh lệch giữa các cụm nhỏ ở hầu hết đặc trưng (`stage_S3.md` mục 5).
- Hình PCA cụm Food.com (`reports/figures/kmeans_user_clusters_foodcom_pca.png`) còn tên cụm cũ bằng tiếng Anh, chưa vẽ lại.
- Chia train, validation, test theo dòng ngẫu nhiên, không theo thời gian; K-core tính trên toàn bộ dữ liệu trước khi chia.
- Đã kiểm thử web trên Chrome headless, chưa thử Edge, Firefox, Safari.

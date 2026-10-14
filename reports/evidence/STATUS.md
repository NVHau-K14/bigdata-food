# STATUS: tổng kiểm tra trung thực (sinh lại ở stage S5, cập nhật lần cuối ở stage S6)

- **Ngày lập:** 14/10/2026; cập nhật lần cuối 15/10/2026 sau stage S6 (chạy sạch từ đầu, đóng băng code). Thay bản STATUS cũ (bản cũ chạy ở chế độ chỉ đọc, trước S1 đến S4).
- **Phạm vi:** đối chiếu tài liệu với dữ liệu và mã hiện tại sau các stage S1, S2, S3, S3b, S4, S5 và S6. Các số trong tệp này đọc lại từ file kết quả và log của phiên S5 (`reports/evidence/logs/S5_*.log`) hoặc từ biên bản `stage_S1.md` đến `stage_S4.md`; cột "Nguồn" ghi file cụ thể.
- **Cách đọc cột "Trạng thái":** `ĐÃ CHẠY VÀ KIỂM CHỨNG` = có chạy thật và số truy được về file kết quả hoặc log. `CHƯA ĐẠT` = đã chạy nhưng mục tiêu đặt ra không đạt, hoặc chưa chạy. Lý do ghi ở cột bên cạnh.
- **Quy ước định dạng số:** dấu phẩy thập phân, dấu chấm hàng nghìn.

---

## 1. Hạ tầng thực tế

Cụm HDFS và Spark Standalone chạy trong Docker trên MỘT máy Windows. "Phân tán" ở đây là giả lập: các container dùng chung CPU và RAM của máy, mạng là cầu nối ảo của Docker, không có mạng thật giữa các máy.

Bằng chứng đọc ngày 14/10/2026 (log `reports/evidence/logs/S5_03_infra_state.log`):

| Kiểm tra | Kết quả đọc được |
|---|---|
| `docker ps` | 7 container chạy: `namenode`, `datanode1`, `datanode2`, `spark-master`, `spark-worker-1`, `spark-worker-2`, `bigdata_spark_env`. Spark master, hai worker và `bigdata_spark_env` báo `healthy`. `namenode` và hai `datanode` không khai báo healthcheck nên không hiện trạng thái. |
| Spark Master `/json/` | `spark://spark-master:7077`, 2 worker `ALIVE`, mỗi worker 2 nhân và 3.500 MB |
| Phiên bản | pyspark 4.2.0, Python 3.13.16 trong container (đọc bằng `python -c`); HDFS 3.3.6 (image `apache/hadoop:3.3.6` trong `docker-compose.yml`) |
| `hdfs dfsadmin -report` | 2 DataNode, `Under replicated blocks: 0`, `Missing blocks: 0`, `Blocks with corrupt replicas: 0` |
| `hdfs fsck /data` và `/models` | cả hai `HEALTHY`; `/data` 115 tệp, `/models` 48 tệp; `Average block replication: 2,0`; `Under-replicated blocks: 0` |

Điểm cần nói rõ khi bảo vệ:
- Chế độ `STORAGE_MODE=local`: đã chạy ở S6 cho ViFoodRec (kết quả trùng chế độ HDFS), chưa chạy cho Food.com (xem H5).
- Hai vấn đề hạ tầng của bản STATUS cũ đã xử lý ở S1: `unhealthy` do healthcheck mặc định của image kiểm tra Jupyter; `Under replicated blocks: 144` do client Spark ghi với replication 3 (xem `stage_S1.md`).

---

## 2. Bảng hạng mục

| # | Hạng mục | Trạng thái | Bằng chứng | Điều kiện hoặc lý do |
|---|---|---|---|---|
| 1 | Hạ tầng HDFS và Spark (Docker) | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `stage_S1.md`; log `S1_01` đến `S1_13`; `S5_03` | `compose down` rồi `up` (không xóa volume), `hdfs dfs -count` trước và sau giống hệt (`/data`: 35 thư mục, 115 tệp, 1.165.516.762 byte); `smoke_test_cluster.py` đạt. |
| 2 | Làm sạch dữ liệu, cả hai bộ | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `stage_S2.md`, `reports/evidence/cleaning_log.csv`, log `S2_03`, `S2_04` (`verify_clean.py` 6/6 đạt) | Food.com không chạy lại ở S2 (đã kiểm chứng ở P3). ViFoodRec chạy lại, giữ 11 mức điểm, loại 47 dòng khóa ngoại. K-core hội tụ. |
| 3 | Benchmark lưu trữ CSV và Parquet | **ĐÃ CHẠY VÀ KIỂM CHỨNG** (số liệu); giải thích kỹ thuật là giả thuyết | `data/results/storage_benchmark.csv`, `stage_P4.md` | Không có log lệnh. Truy vấn đo trên bảng 19,11 MB, 3 lần đo sau 1 lần khởi động. Giải thích "CSV đa dòng không chia được split" không áp dụng cho bảng đã đo (giả thuyết chưa kiểm chứng). |
| 4 | EDA | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `results/eda/*.csv`, `stage_S3.md` mục 6, log `S3_10`, `S3_11` | Chạy lại ở S3: 12 file CSV Food.com và ViFoodRec không đổi so với bản sao lưu (`cmp`). `reports/evidence/eda_insights.md` có khối đính chính. |
| 5 | Chia train, validation, test và mô hình cơ sở | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `reports/evidence/split_log.csv` (rò rỉ 0 ở 3 cặp, cả hai bộ), `results/baseline_metrics.csv`, log `S3_02` đến `S3_04` | Chia ngẫu nhiên theo dòng (seed 42), không chia theo thời gian. Rò rỉ ViFoodRec kiểm lại bằng truy vấn độc lập (log `S3_03`). |
| 6 | ALS dự đoán điểm (chạy, tinh chỉnh, xuất kết quả) | **ĐÃ CHẠY VÀ KIỂM CHỨNG** (phần thực thi) | `results/als_tuning_food_com.csv` (8 cấu hình), `results/als_tuning_food_vietnam.csv` (24 cấu hình), `results/model_comparison.csv`, log `S3_05` | Chỉ chọn tham số trên validation. |
| 6b | ALS tốt hơn mô hình cơ sở | **CHƯA ĐẠT** | `results/model_comparison.csv` | Xem mục 6.2. Chấp nhận và báo cáo trung thực theo CONTEXT mục 7.2. |
| 6c | Thử cải thiện: lưới regParam mở rộng, ALS ngầm định | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `stage_S3b.md`, `results/als_improve_s3b.csv`, log `S3b_02` | Lưới mở rộng không cải thiện (Food.com). ALS ngầm định: Food.com xấp xỉ ngang Top món phổ biến, ViFoodRec vẫn thua. Mô hình ngầm định chưa lưu lên HDFS và chưa có gợi ý cho web. |
| 7 | K-means: người dùng Food.com (k = 4), món ViFoodRec (k = 4) | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `results/kmeans_tuning.csv`, `results/cluster_profiles_food_com.csv`, `results/food_cluster_profiles_vietnam.csv` | Silhouette thấp (0,2743 và 0,2334); k chọn theo khả năng diễn giải. Nhãn cụm Food.com đã đổi sang tiếng Việt ở S3 (số không đổi). |
| 7b | K-means: người dùng ViFoodRec (k = 3) | **ĐÃ CHẠY VÀ KIỂM CHỨNG**; cụm ít khác nhau | `results/cluster_profiles_food_vietnam.csv`, `stage_S3.md` mục 5 | Gọi "Cụm 1, 2, 3" theo quyết định của người dùng. Sáu trong bảy đặc trưng chênh dưới 7%; `pct_chay_high` chênh 17,52%. |
| 8 | Thực nghiệm mở rộng quy mô: đo | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `results/scalability.csv` (32 dòng), `stage_P9.md`; chạy lại ở S6 (log `S6_23` đến `S6_26`) | Bản chính không có log lệnh nguyên văn. Chạy lại ở S6 có log; RMSE ALS trùng ở cả bốn mức, thời gian khác và vẫn không tăng theo dữ liệu. Đã sửa `detect_cluster_resource` cho PySpark 4.2. |
| 8b | Thực nghiệm mở rộng quy mô: kết luận "mở rộng được" | **CHƯA ĐẠT** | `results/scalability.csv` | Thời gian tổng gần phẳng và không đơn điệu; dữ liệu chỉ tới 706.514 dòng. Chỉ kết luận được là chưa thấy thời gian tăng theo dữ liệu trong khoảng này. |
| 9 | Xuất kết quả cho dashboard | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | log `S3_12`, `S3_13`, `S3b_03`, `S3b_04` (`verify_export.py` 66/66 đạt), `docs/data_contract.md` | `verify_export.py` kiểm tra tồn tại, schema, số dòng, khóa ngoại; không kiểm đúng sai của số liệu. |
| 10 | Dashboard Streamlit (`app/`) | **ĐÃ CHẠY VÀ KIỂM CHỨNG** (thời điểm P11); là bản lưu | `stage_P11.md` (có khối đính chính), `reports/evidence/test_app_log.txt` | Không cập nhật theo dữ liệu mới. `app/data/` vẫn là nguồn dữ liệu của web. |
| 11 | Dashboard web tĩnh (`web/`) | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `stage_S4.md`; log `S4_07` (`verify_web.py` 122/122), `S4_08` (`verify_web_ui.mjs` 129/129), `S4_09` (`verify_web_style.py` 21/21); ảnh `reports/figures/screenshots/web_v2/` | Chỉ thử trên Chrome headless. `web/config.js` để trống thông tin nhóm (có chủ ý). Không có chế độ gợi ý có nghĩa cho người dùng mới ở ViFoodRec (xem H8). |
| 12 | Đối chiếu bài báo ViFoodRec | **ĐÃ CHẠY VÀ KIỂM CHỨNG** (số trích) | `scratch/paclic_paper_text.txt` dòng 582 đến 586 (Bảng 5), `stage_S3.md` mục 7 | Giao thức khác (bài báo 200 điểm test, nhóm 18.415 điểm). Thang điểm nay trùng nhau. Nguồn bài báo còn nằm ở `scratch/`. |
| 13 | Tài liệu khớp thực tế | **ĐÃ SỬA** ở S5 | `stage_S5.md` | Mục 4 liệt kê từng điểm lệch và cách xử lý. |
| 14 | Chạy sạch từ đầu trên bản sao (`run_all.ps1 -CleanRun`, HDFS `/cleanrun`) | **ĐÃ CHẠY VÀ KIỂM CHỨNG** với một ngoại lệ | `stage_S6.md`; log `S6_01` đến `S6_36`; `S6_tong_ket.log`, `S6_tong_ket_tiep_tu_mo_rong_2_worker.log` | 35 bước đều mã thoát 0, khoảng 38 phút. RMSE, MAE, P@10, R@10 của mọi mô hình, cách chia dữ liệu và rò rỉ (0) trùng bản chính. NGOẠI LỆ: K-means Food.com không trùng hệt (H9). Do chính nhóm chạy trên cùng máy, chưa có người ngoài chạy lại (H6). |
| 15 | Chế độ `STORAGE_MODE=local` | **ĐÃ CHẠY VÀ KIỂM CHỨNG** cho ViFoodRec | `stage_S6.md` mục 2.3; log `S6L_01` đến `S6L_06` | 5 bước, 2,9 phút, kết quả trùng chế độ HDFS. Lần đầu lỗi do trùng đường dẫn, đã sửa trong `config.py`. Food.com chưa chạy ở chế độ local. |

---

## 3. Hạn chế trung thực

**Về dữ liệu**
- **H1. ViFoodRec chỉ có 101 người dùng**, phân phối điểm gần đều trên 11 mức: mỗi mức từ 8,99% đến 9,23% số dòng; độ lệch chuẩn đo được 1,5798 so với 1,5811 của phân phối đều lý thuyết (`stage_S2.md` mục 2). Bài báo nói điền 40% chỗ thiếu bằng trung vị, nhưng chưa nối được lời mô tả đó với phân phối đo được. Nguồn gốc dữ liệu (sinh nhân tạo hay không) là giả thuyết chưa kiểm chứng.
- **H2. Giữ cả điểm 0,0 và 0,5** là quyết định của người dùng (CONTEXT mục 7.1). Bảng nhạy cảm (`results/vifoodrec_sensitivity.csv`) cho thấy ở cả 3 cách xử lý thứ tự RMSE giữa các mô hình không đổi.
- Food.com lệch 5 sao: 78,40% đánh giá (`results/eda/eda_01_food_com_rating_dist.csv`), nên RMSE tổng thể bị kéo bởi lớp 5 sao; Trung bình toàn cục (μ = 4,7146) đã có RMSE 0,6266.
- K-core và các thống kê dùng để lọc tính trên toàn bộ dữ liệu trước khi chia train, validation, test. Chia ngẫu nhiên theo dòng, không có đánh giá theo thời gian dù Food.com có cột `date`.
- Đơn vị nguyên liệu dính chữ ("muỗngl", "muỗngu") nằm trong dữ liệu gốc `foods.csv` (2.568 trong 4.000 món; log `S4_11`). Chỉ báo cáo, không sửa.
- Giấy phép dữ liệu ViFoodRec: người dùng cho biết là dự án công khai, miễn phí trên GitHub; văn bản giấy phép cụ thể chưa đọc được (mục 5).

**Về hạ tầng**
- **H3. Cụm giả lập một máy** (mục 1). Thực nghiệm mở rộng quy mô chỉ tới 706.514 dòng (Parquet sạch 4,56 MB), nên không phải bài toán Big Data theo nghĩa thông thường.
- **H4. Thư mục thừa `/home/jovyan/...` trên HDFS** (kết quả gợi ý ghi nhầm đường dẫn): đã xóa theo quyết định của người dùng (mục 5, log `S5_08`).
- **H5. Chế độ local đã kiểm chứng một phần (S6).** Chạy `run_all.ps1 -StorageMode local` cho ViFoodRec (làm sạch, chia, mô hình cơ sở, ALS, K-means): kết quả trùng chế độ HDFS (`S6L_06`). Lần đầu lỗi vì Spark ghi thư mục Parquet trùng tên tệp bản sao pandas; đã sửa bằng cách ghi kết quả Spark vào `data/spark_results/` ở chế độ local. Food.com chưa chạy ở chế độ local. `data/processed/*.parquet` là bản cũ (K-core một lượt, 735.006 dòng), pipeline hiện tại không dùng. Kết quả nằm ở hai nơi trùng nhau (`results/` và `data/results/`).
- **H6. Chạy sạch trên bản sao đã làm (S6), chưa có người ngoài chạy lại.** Bản sao chạy trên cùng máy và cùng cụm Docker với bản chính, do nhóm tự thực hiện. Chưa thử dựng cụm từ đầu (`docker compose down -v`) vì sẽ xóa volume HDFS của bản chính, và chưa thử trên máy khác.

**Về mô hình**
- **H7. ALS không tốt hơn mô hình cơ sở** ở RMSE, MAE, Precision@10, Recall@10 (ALS dự đoán điểm, cả hai bộ). Phân bố dự đoán của ALS ViFoodRec trên test: trung bình 2,0047, độ lệch chuẩn 0,2142, trong khi điểm thật trung bình khoảng 2,50 và trải đều 0,0 đến 5,0 (log `S3_08`); RMSE của ALS (1,6654) gần RMSE khi luôn dự đoán 2,0 (1,6531). Nguyên nhân sâu hơn (regParam 0,5 nằm ở biên lưới và cả 6 cấu hình có regParam 0,5 cho cùng Validation RMSE 1,6576) là giả thuyết chưa kiểm chứng.
- **H8. Độ tương đồng món ViFoodRec**: cả 40.000 điểm cosine trong `item_neighbors_food_vietnam` bằng 1,0 (`stage_S4.md` mục 3), nên gợi ý cho người dùng mới ở ViFoodRec không phản ánh khác biệt giữa món; web có cảnh báo. Nguyên nhân (regParam lớn làm vector món gần song song) là giả thuyết chưa kiểm chứng.
- **H9. K-means Food.com không tái lập hoàn toàn khi chạy sạch lại (S6).** Cùng bốn loại cụm và cùng tên, nhưng số người mỗi cụm lệch tới 320 (khoảng 1%) và Silhouette ở k = 4 là 0,2788 thay vì 0,2743. Đã kiểm chứng (log `S6_37`): tập train và đặc trưng giống hệt nhau; chạy hai lần trên cùng dữ liệu cho kết quả y hệt; sắp xếp theo `user_id` thì hai bản gần như trùng. Nguyên nhân: kết quả phụ thuộc thứ tự dòng đầu vào. Cơ chế bên trong Spark là giả thuyết chưa kiểm chứng. Mẫu 5.000 người dùng có gợi ý cho Food.com cũng đổi theo thứ tự dòng (`train_als.py` dòng 322, `.limit(5000)` không sắp xếp); với 4.232 người dùng chung, danh sách gợi ý trùng 100%.
- Top món phổ biến của ViFoodRec dùng nhánh dự phòng (xếp theo số đánh giá) vì không món nào có điểm trung bình từ 4,0 trở lên trên train: đã kiểm chứng, điểm trung bình lớn nhất của một món là 3,4848 (log `S5_05_verify_toppop.log`).
- Lưới ALS dự đoán điểm của ViFoodRec và lưới ALS ngầm định chưa mở rộng quá biên 0,5; người dùng quyết định không chạy lại.
- ALS ngầm định ViFoodRec: tham số tốt nhất chọn trên 101 người dùng, các cấu hình khác cách nhau 1 đến 2 lượt trúng, nên tham số chọn được không đáng tin (`stage_S3b.md` mục 3).
- Chưa có baseline "ngẫu nhiên" được đo. Không đo độ đa dạng, độ mới lạ hay thiên kiến phổ biến.
- Gợi ý cho người dùng mới (cosine trên vector nhân tố ẩn của món) chưa có đánh giá định lượng.
- Món tiêu biểu của cụm người dùng ViFoodRec: số lượt giữa các món rất sát nhau (10 đến 11 lượt cho món đứng đầu), chỉ mang tính minh họa.

**Về bằng chứng**
- Khoảng trống bằng chứng ở S6: log các lệnh nạp dữ liệu thô của lần chạy 2 bị xóa khi dọn log; đã nạp lại để có log (`S6_02a`); xem `stage_S6.md` mục 5.
- Các biên bản P4, P5, P6, P7, P8, P9 không chứa log lệnh nguyên văn (CONTEXT §5.2); số liệu vẫn truy được về file kết quả. Từ S1 trở đi, mọi lệnh đều có log trong `reports/evidence/logs/`.
- Hình PCA cụm Food.com (`reports/figures/kmeans_user_clusters_foodcom_pca.png`) còn tên cụm cũ bằng tiếng Anh (quyết định không vẽ lại; không dùng hình này ở web hay báo cáo).

---

## 4. Rà soát: điểm lệch của STATUS cũ và cách xử lý

Cột "Xử lý": **ĐÃ SỬA** = sửa tại nguồn; **ĐÍNH CHÍNH** = biên bản cũ giữ nguyên, thêm khối đính chính ở đầu; **ĐÃ KIỂM CHỨNG** = chạy lệnh và có log; **GIẢ THUYẾT** = ghi là giả thuyết chưa kiểm chứng.

### 4A. Tài liệu hoặc mã mô tả khác thực tế

| ID | Điểm lệch | Xử lý |
|---|---|---|
| A1 | "Spark 3.5" ở README, `export_for_web.py`, web, `web_design_plan.md` | ĐÃ SỬA: README (S5), `export_for_web.py` và web (S4: Spark 4.2.0 đọc từ log). Kiểm tra tự động: `verify_web.py` không còn chuỗi "Spark 3." trong `web/`. `web_design_plan.md`: ĐÍNH CHÍNH. |
| A2 | README ghi số ViFoodRec và Food.com không có trong file nào (3.964 món, 116.184, 24.325, 226.570, 71,0%, 99,963%, 4,68) | ĐÃ SỬA: README viết lại bằng số từ `cleaning_log.csv` và `eda_12_dataset_comparison.csv` (mục 6.1). |
| A3 | `stage_WEB.md` ghi 24.325 người dùng, 5.000 người dùng lên web, độ thưa 99,963%, điểm trung bình 4,68 | ĐÍNH CHÍNH (đúng: 30.836; 1.000 người dùng; 99,97%; 4,71 gộp theo tương tác, 4,68 là trung bình của trung bình từng người dùng). |
| A4 | `docs/web_data_contract.md` ghi catalog 3.055 công thức | ĐÃ SỬA ở S4 (hợp đồng v2.0 mô tả cách tạo catalog, không còn số 3.055). |
| A5 | `docs/Bao_cao_Tien_xu_ly_va_Lam_sach_Du_lieu.md`: "Hoàn thành 100%", 735.006 dòng, 149.467 dòng, "giảm gần 60 lần" | Banner ĐÃ LỖI THỜI; `docs/Bao_cao_cua_gemini.md` cũng có banner. |
| A6 | CONTEXT, `data_contract.md` coi Streamlit là dashboard | ĐÃ SỬA: CONTEXT mục 1, 2, 6 và `data_contract.md` (bản 1.1). Quyết định do người dùng xác nhận (CONTEXT mục 7.3). |
| A7 | Ghi Python 3.11 và 3.12 trong `stage_P2`, `stage_P10`, `stage_P11` | ĐÍNH CHÍNH (đúng: 3.13.16 trong container; 3.11.9 là Python của máy Windows). |
| A8 | `src/config.py` ghi ngưỡng 1440 phút là phân vị 99,9% | ĐÃ SỬA chú thích: 1440 là giá trị chọn tay; phân vị đo được ở P1: 99% = 750 phút, 99,9% = 2.147.483.647 (`stage_P1_audit.md`). |
| A9 | "Replication = 2" không đúng với file do Spark ghi | ĐÃ SỬA ở S1 (`setrep`, cấu hình client); `stage_P2` ĐÍNH CHÍNH; web đọc replication từ `docker-compose.yml`. |
| A10 | `stage_P11` ghi 16 ảnh và tên lệch một chữ số | ĐÍNH CHÍNH (thật: 17 PNG). |
| A11 | Nhật ký làm sạch ghi "100 user" | ĐÃ SỬA ở S2 (`cleaning_log.csv` nay: "còn 101 user và 4,000 món", sinh từ mã). |

### 4B. Số hoặc khẳng định trong biên bản cũ

| ID | Khẳng định cũ | Kết quả kiểm chứng ở S5 | Trạng thái |
|---|---|---|---|
| B1 | Trung bình toàn cục μ = 4,7146 (Food.com) và 2,9981 (ViFoodRec) | Truy vấn trực tiếp tập train (log `S5_01_verify_mu.log`): Food.com 565.420 dòng, μ = 4,714605; ViFoodRec (dữ liệu mới) 146.012 dòng, μ = 2,501157. Cũng suy ra được từ RMSE theo mức điểm (`baseline_rmse_breakdown.csv`: 5 − 0,2854 = 4,7146; 0,0 + 2,5012 = 2,5012). Số 2,9981 thuộc dữ liệu cũ, không truy được. | ĐÃ KIỂM CHỨNG (4,7146 đúng; 2,9981 lỗi thời) |
| B2 | ALS giảm sai số "−19,2%" ở mức 1,0 sao | Tính lại (log `S5_02_verify_numbers.log`): 3,6135 xuống 3,0118 là −16,7% so với Trung bình món làm trơn, −18,9% so với Trung bình toàn cục, −15,2% so với Top món phổ biến. Không ra 19,2%. | ĐÃ KIỂM CHỨNG (sai; ĐÍNH CHÍNH ở `stage_P7`) |
| B3 | "Cụm nhỏ nhất của Food.com là 7,77%" | `cluster_profiles_food_com.csv`: 12,98%; 34,70%; 25,69%; 26,63%. Nhỏ nhất 12,98%. | ĐÃ KIỂM CHỨNG (sai; ĐÍNH CHÍNH ở `stage_P8`) |
| B4 | k = 5 ViFoodRec Users có cụm dưới 10 người dùng | `kmeans_tuning.csv` không lưu kích thước cụm; kết quả K-means ViFoodRec Users đã chạy lại ở S3. | GIẢ THUYẾT (không truy được) |
| B5 | Phần tuần tự theo Amdahl khoảng 35 đến 40%, trần 1,33 lần | Không có phép đo nào tách phần tuần tự. | GIẢ THUYẾT (ghi ở `stage_P9`) |
| B6 | Lượt 10% chậm vì khởi động JVM và JIT | `scalability.csv` chỉ cho thấy lượt 1 chậm hơn lượt 2 ở mức 10% (15,179 so với 8,793 giây với 2 Worker; 13,557 so với 7,610 giây với 1 Worker) và không chậm hơn ở mức 25% và 100% với 2 Worker. Thứ tự chạy không được ghi; không chạy lại thực nghiệm (tốn thời gian, ghi đè kết quả). | GIẢ THUYẾT |
| B7 | Parquet và pushdown loại hoàn toàn nút thắt I/O | Không có thí nghiệm đối chứng trong P9. | GIẢ THUYẾT |
| B8 | Độ trễ "dưới 200 ms", "dưới 0,05 giây", "dưới 100 ms" | Không có phép đo nào trong `reports/evidence/`. | BỎ (ghi "chưa đo" ở `stage_P10`, `stage_P11`) |
| B9 | Parquet nhanh hơn một phần vì "CSV đa dòng không chia được split" | Bảng đo là `interactions_clean` 4 cột, 19,11 MB, không phải CSV đa dòng. | GIẢ THUYẾT |
| B10 | Dữ liệu ViFoodRec "sinh nhân tạo" | Chỉ đo được phân phối gần đều (H1). | GIẢ THUYẾT |
| B11 | Biên bản P4 đến P9 thiếu log nguyên văn | Từ S1 trở đi đều có log. Không dựng lại log cho P4 đến P9. | GHI NHẬN |
| B12 | (mới ở S3) Top món phổ biến ViFoodRec dùng nhánh dự phòng vì không món nào có điểm trung bình từ 4,0 | Truy vấn train: 4.000 món, 0 món có điểm trung bình từ 4,0, điểm lớn nhất 3,4848 (log `S5_05`). | ĐÃ KIỂM CHỨNG |

### 4C. Mâu thuẫn giữa các biên bản

| ID | Nội dung | Kết luận |
|---|---|---|
| C1 | P7 và P11 viết "ALS vượt trội, cá nhân hóa tốt"; `stage_WEB.md` và `model_comparison.csv` cho thấy ALS không thắng | Số liệu ủng hộ `model_comparison.csv`. ĐÍNH CHÍNH ở `stage_P7`, `stage_P11`. |
| C2 | P8 đặt tên diễn giải cho 3 cụm người dùng ViFoodRec | Thay bằng "Cụm 1, 2, 3" (S3). ĐÍNH CHÍNH ở `stage_P8`. |
| C3 | P8: chọn k theo Silhouette cao | Food.com chọn k = 4 (Silhouette 0,2743) trong khi k = 2 đạt 0,5257; chọn theo khả năng diễn giải. ĐÍNH CHÍNH ở `stage_P8`. |
| C4 | CONTEXT §3.4 yêu cầu dừng khi mô hình tệ hơn mô hình cơ sở, P7 vẫn tiếp tục | Người dùng chấp nhận ngày 14/10/2026 (CONTEXT mục 7.2). |

Số dòng sau làm sạch (nhất quán sau S2): Food.com 706.514 (cũ 735.006 là K-core một lượt, không dùng); ViFoodRec 182.631 (cũ 149.431 và 149.467 thuộc quy tắc đã bỏ). Số người dùng Food.com: 30.836 (dữ liệu sạch) và 30.772 (tập train; 64 người dùng không có dòng nào trong train).

---

## 5. Quyết định của người dùng (14/10/2026, sau S5)

1. **Thư mục thừa trên HDFS** `/home/jovyan/work/data/results/` (H4): xóa. Đã xóa (log `S5_08_xoa_thu_muc_thua_hdfs.log`); đó là 4 thư mục Parquet gợi ý và láng giềng (2,4 MB) trùng với `results/` trên máy. Sau khi xóa, `/data` HEALTHY, Under replicated blocks 0, Missing blocks 0.
2. **Chạy lại ALS ViFoodRec với lưới mở rộng:** không chạy lại. H7 và H8 là hạn chế được chấp nhận và ghi trong báo cáo.
3. **Hình PCA cụm Food.com:** không vẽ lại.
4. **Thông tin nhóm trong `web/config.js`:** không cần điền; để trống có chủ ý.
5. **Giấy phép dữ liệu ViFoodRec:** người dùng cho biết đây là dự án công khai, miễn phí trên GitHub. Chưa đọc được văn bản giấy phép cụ thể trong phiên này, nên báo cáo ghi theo đúng điều người dùng nói và ghi giấy phép cụ thể là "chưa xác nhận" nếu kho không nêu.
6. **Chế độ `STORAGE_MODE=local`:** kiểm chứng ở S6 cho ViFoodRec, kết quả trùng chế độ HDFS (H5); Food.com chưa chạy ở chế độ local.

---

## 6. Bảng các con số chính

Mọi số dưới đây đọc lại từ file nguồn trong phiên S5.

### 6.1. Quy mô dữ liệu sau làm sạch

| Chỉ số | Food.com | ViFoodRec | File nguồn |
|---|---:|---:|---|
| Số người dùng | 30.836 | 101 | `results/eda/eda_12_dataset_comparison.csv` |
| Số món có đánh giá | 78.171 | 4.000 | `results/eda/eda_12_dataset_comparison.csv` |
| Số đánh giá sau làm sạch | 706.514 | 182.631 | `reports/evidence/cleaning_log.csv` |
| Số đánh giá thô | 1.132.367 | 182.678 | `reports/evidence/cleaning_log.csv` (dòng `raw_input`) |
| Số dòng bị loại: Food.com rating = 0; K-core | 60.847; 365.006 | không có | `reports/evidence/cleaning_log.csv` |
| Số dòng bị loại: ViFoodRec khóa ngoại (`food_id` = 4000); K-core | không có | 47; 0 | `reports/evidence/cleaning_log.csv` |
| Độ thưa | 99,97% | 54,79% | `results/eda/eda_12_dataset_comparison.csv` |
| Điểm trung bình | 4,71 | 2,50 | `results/eda/eda_12_dataset_comparison.csv` |
| Số người dùng và món trong tập train | 30.772 và 77.960 | 101 và 4.000 | `reports/evidence/split_log.csv` |
| Số dòng train, validation, test | 565.420; 70.002; 70.233 | 146.012; 18.204; 18.415 | `reports/evidence/split_log.csv` |
| Rò rỉ train, validation, test (3 cặp) | 0 | 0 | `reports/evidence/split_log.csv` |
| Dòng cold-start loại khỏi validation, test | 422; 437 | 0; 0 | `reports/evidence/split_log.csv` |

### 6.2. Mô hình trên tập test

Nguồn: `results/model_comparison.csv` (11 dòng). RMSE, MAE 4 chữ số; P@10, R@10 5 chữ số. In đậm là giá trị tốt nhất theo cột trong mỗi bộ (ALS ngầm định chỉ có P@10 và R@10).

| Bộ | Mô hình | RMSE | MAE | P@10 | R@10 |
|---|---|---:|---:|---:|---:|
| Food.com | Trung bình toàn cục | 0,6266 | 0,4468 | 0,00000 | 0,00000 |
| Food.com | Trung bình món làm trơn (m = 5) | **0,6177** | 0,4214 | 0,00048 | 0,00130 |
| Food.com | Top món phổ biến | 0,6568 | **0,4120** | 0,00534 | **0,02170** |
| Food.com | ALS dự đoán điểm (rank 10, regParam 0,2, maxIter 10) | 0,6747 | 0,5094 | 0,00017 | 0,00096 |
| Food.com | ALS ngầm định (điểm từ 4,0) | không áp dụng | không áp dụng | **0,00570** | 0,02118 |
| ViFoodRec | Trung bình toàn cục | **1,5706** | **1,3502** | 0,00000 | 0,00000 |
| ViFoodRec | Trung bình món làm trơn (m = 5) | 1,5873 | 1,3690 | 0,01584 | 0,00321 |
| ViFoodRec | Top món phổ biến | 1,5924 | 1,3723 | **0,02277** | **0,00461** |
| ViFoodRec | ALS dự đoán điểm (rank 10, regParam 0,5, maxIter 10) | 1,6654 | 1,4185 | 0,01386 | 0,00285 |
| ViFoodRec | ALS ngầm định (điểm từ 4,0) | không áp dụng | không áp dụng | 0,01980 | 0,00428 |

- Dòng "ALS Matrix Factorization (lưới mở rộng)" của Food.com trong file nguồn trùng hệt ALS dự đoán điểm nên không liệt kê ở đây.
- Tham số chọn trên validation: Food.com val RMSE 0,6754 (`results/als_tuning_food_com.csv`); ViFoodRec val RMSE 1,6576 (`results/als_tuning_food_vietnam.csv`); lưới mở rộng regParam 0,3 và 0,5 của Food.com cho val RMSE từ 0,6991 đến 0,7961, cao hơn 0,6754 (`results/als_improve_s3b.csv`).
- ALS dự đoán điểm không đứng đầu cột nào. ALS ngầm định chỉ đứng đầu P@10 của Food.com (0,00570 so với 0,00534; R@10 thấp hơn 0,02118 so với 0,02170).
- Bảng nhạy cảm ViFoodRec (`results/vifoodrec_sensitivity.csv`), RMSE của Trung bình toàn cục, Trung bình món làm trơn, ALS: giữ 11 mức (182.631 dòng) 1,5706; 1,5873; 1,6654. Bỏ riêng 0,0 (166.128 dòng) 1,4325; 1,4507; 1,5337. Quy tắc cũ chỉ giữ 1,0 đến 5,0 (149.431 dòng) 1,2895; 1,3058; 1,3929. Thứ tự giữa 3 mô hình không đổi ở cả 3 biến thể.

### 6.3. K-means

| Bài toán | k đã chọn | Silhouette | Silhouette cao nhất trong dải k đã thử | File nguồn |
|---|---:|---:|---|---|
| Người dùng Food.com | 4 | 0,2743 | k = 2: 0,5257 | `results/kmeans_tuning.csv` |
| Người dùng ViFoodRec | 3 | 0,2219 | k = 2: 0,2474 | `results/kmeans_tuning.csv` |
| Món ViFoodRec | 4 | 0,2334 | k = 3: 0,2495 | `results/kmeans_tuning.csv` |

- Cụm người dùng Food.com (`results/cluster_profiles_food_com.csv`): "Người dùng khắt khe" 3.993 (12,98%), "Người chuộng món nấu lâu, nhiều calo" 10.679 (34,70%), "Người chuộng món nấu nhanh, ít calo" 7.905 (25,69%), "Thành viên lâu năm, đánh giá nhiều" 8.195 (26,63%).
- Cụm người dùng ViFoodRec (`results/cluster_profiles_food_vietnam.csv`): Cụm 1 33 người (32,67%), Cụm 2 31 (30,69%), Cụm 3 37 (36,63%); điểm trung bình 2,5381; 2,4996; 2,4691.

### 6.4. Thời gian mở rộng quy mô (tổng thời gian pipeline, trung bình 2 lần chạy, giây)

| Mức dữ liệu | Số dòng | 2 Worker (4 nhân) | 1 Worker (2 nhân) | ALS fit 2W / 1W | ALS test RMSE |
|---|---:|---:|---:|---:|---:|
| 10% | 71.148 | 11,986 | 10,583 | 5,830 / 4,679 | 1,1785 |
| 25% | 176.704 | 8,393 | 7,287 | 3,126 / 3,090 | 0,8884 |
| 50% | 358.296 | 7,166 | 8,238 | 3,697 / 4,142 | 0,7482 |
| 100% | 706.514 | 7,933 | 9,891 | 3,826 / 4,908 | 0,6745 |

- File nguồn: `results/scalability.csv` (cột `avg_time`, dòng "Tổng cộng Pipeline" và "Step 2: Huấn luyện ALS"). Thời gian không tăng theo dữ liệu; chưa đủ để kết luận về khả năng mở rộng (mục 2, dòng 8b).
- RMSE ALS ở mức 100% là 0,6745, khác 0,6747 của `model_comparison.csv` (hai lần huấn luyện riêng).

### 6.5. Số khác hay được hỏi

| Chỉ số | Giá trị | File nguồn |
|---|---:|---|
| Parquet so với CSV, dữ liệu thô đầy đủ (interactions; recipes) | 1,76 lần; 2,34 lần | `data/results/storage_benchmark.csv` |
| Parquet so với CSV, dữ liệu sạch (interactions; recipes) | 4,19 lần; 7,03 lần | `data/results/storage_benchmark.csv` |
| Truy vấn Parquet so với CSV (Q1; Q2; Q3) | 1,71 lần; 2,06 lần; 1,80 lần | `data/results/storage_benchmark.csv` |
| Số dòng Food.com bị loại (thô sang sạch) | 425.853 (60.847 + 365.006) | `reports/evidence/cleaning_log.csv` |
| Điểm trung bình của Global Mean (μ) trên tập train | Food.com 4,7146; ViFoodRec 2,5012 | log `S5_01_verify_mu.log` |
| Phân phối 11 mức điểm ViFoodRec | từ 8,99% đến 9,23% | `stage_S2.md` mục 2 |
| Độ lệch chuẩn điểm ViFoodRec: đo; phân phối đều lý thuyết | 1,5798; 1,5811 | `stage_S2.md` mục 2 |
| Số tương tác sau làm sạch: ViFoodRec so với bản cũ | 182.631 so với 149.431 | `cleaning_log.csv`; `backup_v2_truoc_S2/` |
| Kiểm thử web: `verify_web.py`; `verify_web_ui.mjs`; `verify_web_style.py` | 122/122; 129/129; 21/21 | log `S4_07`, `S4_08`, `S4_09` |
| Replication; khối thiếu bản sao | 2; 0 | log `S5_03_infra_state.log` |
| Chạy sạch trên bản sao (S6): số bước; mã thoát khác 0; thời gian | 35; 0; khoảng 38 phút | `S6_tong_ket.log`, `S6_tong_ket_tiep_tu_mo_rong_2_worker.log` |
| Chạy sạch: `verify_clean.py`; `verify_export.py`; `verify_web_ui.mjs`; `verify_web.py`; `verify_web_style.py` | 6/6; 66/66; 129/129; 122/122; 21/21 | log `S6_13`, `S6_29`, `S6_33`, `S6_34`, `S6_35` |
| Chạy sạch: `fsck` `/cleanrun/data`; `/cleanrun/models` | HEALTHY, 115 tệp; HEALTHY, 48 tệp; Under-replicated 0 | log `S6_30`, `S6_31` |
| K-means Food.com k = 4 khi chạy sạch: Silhouette; cỡ cụm | 0,2788; 3.998 / 10.359 / 8.142 / 8.273 (bản chính 0,2743; 3.993 / 10.679 / 7.905 / 8.195) | `kmeans_tuning.csv`, `cluster_profiles_food_com.csv` của bản sao; `S6_36`, `S6_37` |

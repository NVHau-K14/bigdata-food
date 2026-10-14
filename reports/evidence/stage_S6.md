# Stage S6: chạy sạch từ đầu và đóng băng code

- **Ngày:** 14/10/2026 đến 15/10/2026 (giờ máy chủ).
- **Phạm vi:** viết lại `run_all.ps1` chạy toàn bộ pipeline; chạy trên một BẢN SAO (`bigdata-food-cleanrun`, thư mục HDFS `/cleanrun`, container client riêng) mà không đụng kết quả của bản chính; đối chiếu kết quả hai bản; kiểm chứng chế độ `STORAGE_MODE=local`; viết lại README; cập nhật STATUS; gắn thẻ `code-freeze`.
- **Nguồn số liệu:** log trong `reports/evidence/logs/S6_*.log` và `S6L_*.log`. Số nào ghi kèm tên log thì đọc từ log đó.

---

## 1. Đã làm gì

| Tệp | Thay đổi |
|---|---|
| `run_all.ps1` | Viết lại. 35 bước từ khởi động cụm đến kiểm thử web; mỗi bước ghi log UTF-8 nguyên văn, dừng khi lỗi; tham số `-CleanRun`, `-HdfsRoot`, `-StorageMode`, `-Fast`, `-Skip*`, `-StartAt`, `-WebOnly`, `-ServeWeb` |
| `src/config.py` | Thêm `HDFS_ROOT` (mặc định rỗng, giữ nguyên hành vi cũ); ở chế độ local, kết quả Spark ghi vào `data/spark_results/` (xem mục 5, lỗi 4) |
| `src/storage_benchmark.py` | Thư mục benchmark HDFS không còn viết cứng `hdfs://namenode:9000/data/benchmark`, đi qua `get_path` |
| `src/scalability_experiment.py` | Sửa `detect_cluster_resource` cho PySpark 4.2 (xem mục 5, lỗi 3) |
| `requirements.txt` | Mới: phiên bản thư viện đã chạy thật |
| `.gitignore` | Thêm `data/clean/`, `data/splits/`, `data/spark_results/`, `models/` |
| `README.md` | Viết lại các mục 2, 5 đến 9: kiến trúc, yêu cầu máy, cài đặt, chạy tất cả và từng bước, chạy thử trên bản sao, chế độ local, phiên bản ghim, nguồn và giấy phép dữ liệu, hạn chế |
| `docs/Q_and_A.md` | Câu 9 thêm một câu về khả năng tái lập K-means Food.com |
| `reports/evidence/STATUS.md` | Cập nhật lần cuối (mục 2, 3, 5, 6) |
| `scratch/s6_compare.py`, `scratch/s6_kmeans_repro.py`, `scratch/s6_readme_build.py` | Script đối chiếu, chẩn đoán K-means, dựng README (dùng một lần) |

Thư mục `bigdata-food-cleanrun` nằm ngoài dự án (cùng cấp), không đưa lên git. `data/raw` của bản chính không bị sửa (chỉ đọc qua `/data/raw_host`).

---

## 2. Lệnh đã chạy và kết quả

### 2.1. Chạy sạch trên bản sao

Lệnh (PowerShell, ở thư mục bản sao):

```powershell
git clone bigdata-food bigdata-food-cleanrun
.\run_all.ps1 -CleanRun -LogPrefix S6_
.\run_all.ps1 -CleanRun -LogPrefix S6_ -StartAt mo_rong_2_worker   # chạy tiếp sau khi sửa lỗi 3
```

Cả 35 bước kết thúc với mã thoát 0 (`S6_tong_ket.log` cho bước 1 đến 22, `S6_tong_ket_tiep_tu_mo_rong_2_worker.log` cho bước 23 đến 35). Tổng thời gian khoảng 38 phút (1.955 giây cho bước 1 đến 22 và 336 giây cho bước 23 đến 35, cộng từ hai tệp tổng kết). Bước chậm nhất: ALS ngầm định 1.297,9 giây; ALS dự đoán điểm 227,4 giây; K-means 104,5 giây.

Trích kiểm tra chính:

| Bước | Kết quả trích từ log |
|---|---|
| `S6_10` liệt kê dữ liệu thô | 4 tệp trên `/cleanrun/data/raw` (333,2 MB; 280,9 MB; 6,9 MB; 2,0 MB), replication 2 |
| `S6_12` làm sạch | "HOÀN TẤT TOÀN BỘ PIPELINE P3 TRONG 65.67 GIÂY"; `cleaning_log.csv` của bản sao giống hệt bản chính (`diff` không có khác biệt) |
| `S6_13` `verify_clean.py` | "ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!" (6/6) |
| `S6_16` chia dữ liệu | Food.com 565.420 / 70.002 / 70.233; ViFoodRec 146.012 / 18.204 / 18.415; rò rỉ 0, 0, 0 ở cả hai bộ |
| `S6_29` `verify_export.py` | 66/66 đạt |
| `S6_30`, `S6_31` `fsck` | `/cleanrun/data` HEALTHY, 115 tệp, Under-replicated 0, Missing 0; `/cleanrun/models` HEALTHY, 48 tệp |
| `S6_33` `verify_web_ui.mjs` | 129/129 đạt |
| `S6_34` `verify_web.py` | 122/122 đạt |
| `S6_35` `verify_web_style.py` | 21/21 đạt |

### 2.2. Đối chiếu bản sao với bản chính (`S6_36_so_sanh_ban_chinh_ban_sao.log`)

Công cụ: `scratch/s6_compare.py` (so từng tệp CSV trong `results/`, `reports/evidence/`, `app/data/` và Parquet trong `app/data/`; sắp xếp dòng trước khi so). Tổng hợp từ log: 64 tệp giống số liệu (khác định dạng), 11 tệp giống số dòng, cột và tổng cột số, 13 tệp có khác số liệu, 4 tệp Parquet khác tổng cột số, 2 tệp chỉ khác cột thời gian.

**Giống hệt (đây là điều tiêu chí S6 yêu cầu):**
- `results/baseline_metrics.csv` giống từng byte.
- `results/model_comparison.csv` (11 dòng): RMSE, MAE, P@10, R@10 của mọi mô hình trùng bản chính. ALS Food.com RMSE 0,6747; ALS ViFoodRec RMSE 1,6654.
- `reports/evidence/split_log.csv`: chỉ cột `time_seconds` khác; số dòng và rò rỉ (0) trùng.
- `cleaning_log.csv`, các bảng EDA, `vifoodrec_sensitivity.csv`, `als_improve_s3b.csv`, K-means ViFoodRec (người dùng và món), `scalability.csv` (cột RMSE, số dòng): trùng.
- Thực nghiệm mở rộng, RMSE ALS ở bốn mức dữ liệu: 1,1785; 0,8884; 0,7482; 0,6745, giống bản chính ở cả hai cấu hình Worker.

**Khác, và lý do đã kiểm chứng ở mục 4:**
- Cột thời gian (`train_time_sec`, `total_time_sec`, `time_sec`, `time_seconds`, `avg_time`, `avg_time_sec`) và ghi chú "Parquet nhanh gấp N lần" trong `storage_benchmark.csv` (bản sao 1,61 lần; 2,09 lần; 1,94 lần so với 1,71 lần; 2,06 lần; 1,80 lần của bản chính; kích thước tệp trùng).
- K-means Food.com: `kmeans_tuning.csv`, `cluster_profiles_food_com.csv`, `user_clusters_food_com.parquet`, `cluster_top_items.csv`.
- Mẫu 5.000 người dùng của gợi ý Food.com: `recommendations_food_com.parquet`.

### 2.3. Chế độ `STORAGE_MODE=local` (ViFoodRec)

```powershell
.\run_all.ps1 -StorageMode local -ClientContainer bigdata_spark_cleanrun -LogPrefix S6L_
```

Lần 1 dừng ở bước ALS (`S6L_04a_lan1_loi_xung_dot_duong_dan_local.log`): "`/home/jovyan/work/data/results/recommendations_food_vietnam.parquet là thư mục, cần xử lý thủ công`". Sau khi sửa `config.py` (mục 5, lỗi 4), lần 2 chạy đủ 5 bước, mã thoát 0, 2,9 phút (`S6L_tong_ket.log`). So với kết quả HDFS (`S6L_06_so_sanh_local_voi_hdfs.log`): RMSE, MAE, P@10, R@10 của bốn mô hình ViFoodRec trùng (ví dụ ALS 1,6654; 1,4185; 0,01386; 0,00285), K-means ViFoodRec trùng; chỉ khác cột thời gian. Dòng `model_comparison` 11 so với 8 là do `train_als.py --only vietnam` ghi lại bảng mà không kèm hai dòng ALS ngầm định (sinh bởi `als_improve.py`), đúng với thứ tự bước trong `run_all.ps1`.

---

## 3. Đối chiếu tiêu chí S6

| # | Tiêu chí | Kết quả |
|---|---|---|
| 1 | `run_all.ps1` chạy khởi động cụm, nạp dữ liệu, làm sạch, verify, benchmark, EDA, chia, baseline, ALS, K-means, mở rộng, xuất, xuất web, verify web; có tham số bỏ qua bước nặng | **ĐẠT.** Đã chạy trọn 35 bước; `-WebOnly` đã chạy thử riêng trên bản sao (4 bước, 129/129, 122/122, 21/21, log `S6W_01` đến `S6W_04`); `-Fast` và `-Skip*` có trong mã nhưng CHƯA chạy thử riêng (không có log) |
| 2 | Chạy sạch trên bản sao, thư mục HDFS khác, không xóa kết quả hiện có, dữ liệu thô chỉ đọc | **ĐẠT.** `/cleanrun`; `config.py` hỗ trợ `HDFS_ROOT`; `data/raw` chỉ gắn chỉ đọc |
| 3 | RMSE giống bản chính | **ĐẠT** cho mọi mô hình (mục 2.2). K-means Food.com KHÔNG giống hệt (mục 4) |
| 4 | Log vào `reports/evidence/logs/S6_*.log` | **ĐẠT** (có hai khoảng trống đã nêu ở mục 5, lỗi 1 và 2) |
| 5 | README: kiến trúc đúng thực tế, yêu cầu máy, cài đặt, chạy từng bước và tất cả, mở web, cấu trúc, nguồn và giấy phép, hạn chế, ghim phiên bản | **ĐẠT.** Mức RAM tối thiểu chưa thử, README ghi rõ; giấy phép ghi "chưa xác nhận" |
| 6 | STATUS cập nhật lần cuối; commit; thẻ `code-freeze` | Xem mục cuối biên bản (commit và thẻ làm sau khi biên bản này được ghi) |
| 7 | Cổng kiểm tra: làm theo README trên thư mục sạch | **ĐẠT MỘT PHẦN.** Chạy bằng `run_all.ps1` trên bản sao sạch, nhưng do chính nhóm làm, trên cùng máy và cùng cụm Docker, không phải một người ngoài trên máy khác. Cần bạn cùng nhóm thử lại (mục 4) |

---

## 4. Vì sao K-means Food.com của bản sao khác bản chính

**Quan sát** (`kmeans_tuning.csv`, `cluster_profiles_food_com.csv`): cùng bốn loại cụm và cùng tên cụm, nhưng số thứ tự cụm bị hoán vị và số người mỗi cụm lệch (bản chính: 3.993; 10.679; 7.905; 8.195; bản sao: 3.998; 10.359; 8.142; 8.273, tức lệch tối đa 320 người, 1,04 điểm phần trăm). Silhouette ở k = 4 là 0,2788 (bản sao) so với 0,2743 (bản chính); ở k = 3 là 0,2685 so với 0,2867; k = 8 là 0,2783 so với 0,3045. K = 2 giống nhau (0,5257).

**Kiểm chứng** (`S6_37_kiem_chung_kmeans_food_com.log`, mã `scratch/s6_kmeans_repro.py`, chạy trên dữ liệu thật của cả hai bản):
- A. Tập train Food.com của hai bản giống nhau theo tập hợp dòng: 565.420 dòng, `exceptAll` hai chiều đều bằng 0.
- B. Bảng đặc trưng người dùng giống nhau: 30.772 người dùng cả hai bên, lệch tối đa 4,4e-16 (làm tròn dấu phẩy động).
- C. Trên cùng một dữ liệu, K-means k = 4, seed 42, hai lần liên tiếp cho kết quả y hệt (bản chính: chi phí 144.516,3233, cụm [10940, 7731, 3976, 8125] cả hai lần; bản sao: 144.421,0574, cụm [8109, 8264, 10401, 3998] cả hai lần), nhưng hai bản cho kết quả KHÁC nhau.
- D. Khi sắp xếp theo `user_id` và chia lại 8 phân vùng, hai bản gần như trùng nhau (chi phí 144.420,19 và 144.420,32; kích thước cụm sắp xếp [3998, 8148, 8266, 10360] và [3998, 8138, 8273, 10363]).

**Kết luận đã kiểm chứng:** dữ liệu và đặc trưng giống hệt, nhưng K-means (khởi tạo k-means||) cho cực trị cục bộ khác nhau tùy thứ tự dòng và phân vùng của DataFrame đầu vào; thứ tự này đổi mỗi khi làm sạch ghi lại Parquet. Chưa kiểm chứng: cơ chế bên trong Spark khiến thứ tự ảnh hưởng đến khởi tạo (đây là giả thuyết hợp lý, chưa soi mã nguồn Spark).

**Hệ quả:**
- Số liệu K-means Food.com của bản chính (và trong STATUS, README, Q_and_A, web) vẫn đúng với kết quả bản chính đã lưu; không có lỗi trong pipeline.
- Dashboard web đọc `app/data/` của bản chính, không dùng kết quả của bản sao.
- Gợi ý Food.com: 4.232 trong 5.000 người dùng của mẫu hai bản trùng nhau, và với 4.232 người đó danh sách món gợi ý trùng 100%. Mẫu khác nhau vì `train_als.py` dòng 322 lấy `.limit(5000)` trên DataFrame không sắp xếp, nên phụ thuộc thứ tự dòng (đọc từ mã). ALS tái lập được.
- Đây không phải "kết quả tốt bất thường" hay rò rỉ dữ liệu, nên không chạm điều kiện dừng ở CONTEXT mục 7.9.

---

## 5. Lỗi phát hiện khi chạy và cách xử lý

| # | Lỗi | Bằng chứng | Xử lý |
|---|---|---|---|
| 1 | Lần chạy 1: smoke test đứng trước bước nạp dữ liệu, nên không thấy tệp thô trên `/cleanrun` | `S6_00a_lan1_loi_smoke_test_truoc_khi_nap_du_lieu.log` | Đổi thứ tự trong `run_all.ps1`: nạp dữ liệu trước |
| 2 | Lần chạy 2: smoke test treo ("Initial job has not accepted any resources"). Tên máy container client có dấu gạch dưới, Spark từ chối URL driver `spark://...@bigdata_spark_cleanrun:port` | `S6_00b_lan2_treo_smoke_test_ten_may_co_gach_duoi.log` (cuối log bị cắt vì tôi dừng tiến trình); lỗi gốc đọc trong stderr của executor trên `spark-worker-1`: "Invalid Spark URL" | Đặt `--hostname spark-cleanrun` và bí danh mạng cùng tên |
| 3 | Bước đo mở rộng gãy: `AttributeError: 'SparkExecutorInfo' object has no attribute 'id'` (PySpark 4.2 không còn `id()` và `totalCores()`). Đây là lỗi của mã từ stage P9, chạy ở Spark cũ | `S6_00c_lan3_loi_do_cum_executor_pyspark4.log` | Sửa `detect_cluster_resource`: đếm executor có host khác host driver, lấy nhân từ `spark.executor.cores`, đợi số executor ổn định. Nhãn kết quả vẫn "1 Worker (2 Cores)" và "2 Workers (4 Cores)" như `scalability.csv` cũ |
| 4 | Chế độ local: ALS dừng vì đường dẫn kết quả Spark (`data/results/*.parquet`, ghi dạng thư mục) trùng tệp bản sao pandas | `S6L_04a_lan1_loi_xung_dot_duong_dan_local.log` | Ở chế độ local, `get_path("results", ...)` trả `data/spark_results/`; chế độ hdfs không đổi |

Hai khoảng trống bằng chứng cần nói rõ:
- Log các lệnh `put` nạp dữ liệu thô của lần chạy 2 bị xóa khi tôi dọn log để chạy lại (lệnh `rm` các tệp `S6_NN_*.log`). Dữ liệu vẫn nằm trên `/cleanrun/data/raw`, nên ở lần chạy 3 bước nạp bị bỏ qua (`-test -e` báo đã có). Để có log nguyên văn, tôi xóa thư mục `/cleanrun/data/raw` (do chính S6 tạo) và nạp lại bằng cùng lệnh: `S6_02a_nap_lai_du_lieu_tho_sau_khi_xoa_log_lan_truoc.log`. Bước nạp này nằm ngoài chuỗi 35 bước đã chạy và chạy sau khi làm sạch, nhưng cho cùng nội dung.
- Lần chạy tiếp đầu tiên (từ bước 23 sau khi sửa lỗi 3) ghi số thứ tự lệch một bậc, vì bước tạo container được bỏ qua khi container đã tồn tại. Tôi dừng ngay, xóa một tệp log rỗng vừa sinh ra, kiểm tra tệp `S6_22_do_nhay_vifoodrec.log` còn nguyên (4.647 byte), sửa mã để số thứ tự ổn định rồi chạy lại. Log của bước 1 đến 22 nằm trong `S6_01` đến `S6_22`, log bước 23 đến 35 trong `S6_23` đến `S6_35`.

Việc tôi làm sai và đã sửa trong chế độ local: khi dọn thư mục `data/results/` của bản sao tôi xóa nhầm bốn tệp `*_vietnam.parquet` (kết quả HDFS của bản sao) bằng ký tự đại diện; tôi chép lại đúng bốn tệp đó từ ảnh chụp `results/` đã lưu ngay trước khi chạy chế độ local, rồi mới đối chiếu. Việc này chỉ ảnh hưởng bản sao, không ảnh hưởng bản chính.

---

## 6. Vấn đề còn tồn và giả định

- **Chưa có người ngoài chạy lại** (cổng kiểm tra S6). Phép thử đã làm là chạy trên bản sao sạch, trên cùng máy và cùng cụm Docker. Cần một bạn cùng nhóm làm theo README trên máy khác, hoặc ít nhất `docker compose down -v` rồi dựng lại cụm từ đầu (chưa làm vì sẽ xóa volume HDFS của bản chính).
- `-Fast` và `-Skip*` chưa chạy thử riêng; chỉ cú pháp PowerShell được kiểm tra (`Parser.ParseFile` không báo lỗi). `-WebOnly` đã chạy (`S6W_*`).
- Chế độ local chỉ kiểm chứng cho ViFoodRec; Food.com ở chế độ local chưa chạy.
- Image Docker ghim theo thẻ phiên bản, không theo digest.
- `export_for_web.py` đọc hai log cũ cố định (`S2_03_clean_vietnam.log`, `S3_14_fsck.log`), nên mục "Hệ thống" của web trong bản sao lấy từ log đã có trong git, không phải log của lần chạy sạch.
- Giấy phép Food.com (Kaggle) và ViFoodRec: chưa xác nhận.
- Giả định: số liệu chính thức của đồ án là kết quả của bản chính (đã kiểm chứng ở S2 đến S5). Lần chạy sạch xác nhận mọi chỉ số mô hình, riêng K-means Food.com chỉ tái lập đến mức cùng bốn loại cụm.

---

## 7. Điểm cần hiểu để trả lời phản biện

**1. Chạy lại từ đầu có ra đúng kết quả không?**
Với mọi chỉ số mô hình thì có: RMSE, MAE, P@10, R@10 của năm mô hình ở cả hai bộ trùng bản chính đến chữ số đã ghi, cách chia dữ liệu và số dòng trùng, rò rỉ bằng 0 (`S6_36`, `S6_16`). K-means Food.com không trùng hệt: cùng bốn loại cụm, số người mỗi cụm lệch tới 320 người (khoảng 1%) và Silhouette ở k = 4 là 0,2788 thay vì 0,2743.

**2. Vì sao K-means lệch trong khi seed cố định?**
Dữ liệu đầu vào giống hệt (tập hợp dòng và đặc trưng trùng) nhưng thứ tự dòng khác sau khi làm sạch ghi lại Parquet; K-means nhạy với thứ tự này. Đã chứng minh: chạy hai lần trên cùng một dữ liệu cho kết quả y hệt, còn sắp xếp theo `user_id` thì hai bản gần như trùng (`S6_37`). Cơ chế bên trong Spark chưa được kiểm chứng.

**3. Nếu K-means Food.com không tái lập hoàn toàn thì kết luận về hành vi còn đáng tin không?**
Bốn loại cụm (khắt khe, nấu lâu nhiều calo, nấu nhanh ít calo, thành viên lâu năm) xuất hiện ở cả hai lần chạy và hồ sơ cụm lệch rất ít (ví dụ điểm trung bình cụm khắt khe 3,8319 và 3,8324), nhưng Silhouette thấp (khoảng 0,28) nên không nên nói các cụm "tách bạch". Kết luận có thể nêu: có nhóm người dùng khắt khe nhỏ (khoảng 13%) và ba nhóm còn lại phân biệt chủ yếu theo thời gian nấu, calo và mức độ hoạt động.

**4. Vì sao phải dùng thư mục HDFS khác và container riêng khi chạy thử?**
Để chạy từ đầu mà không ghi đè kết quả chính; cần `HDFS_ROOT` trong `config.py`, và một container client riêng để driver nhìn thấy thư mục bản sao. Dữ liệu thô chỉ đọc qua `/data/raw_host`.

**5. Chạy toàn bộ mất bao lâu?**
Khoảng 38 phút trên máy này (24 GB RAM, Docker 16 GB), trong đó ALS ngầm định 21,6 phút. Đây là thời gian một lần chạy, không phải phép đo lặp; thời gian các bước đổi giữa các lần chạy (ví dụ lần làm sạch 65,7 giây).

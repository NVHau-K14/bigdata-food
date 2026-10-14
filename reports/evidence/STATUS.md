# STATUS — TỔNG KIỂM TRA TRUNG THỰC (P12 rút gọn)

- **Ngày lập:** 14/10/2026
- **Phạm vi:** chỉ đọc và báo cáo. Không chạy lại pipeline, không xóa dữ liệu, không sửa mã/README/biên bản cũ. Các lệnh duy nhất đã chạy là lệnh đọc: `docker ps`, `hdfs dfs -ls/-stat`, `hdfs dfsadmin -report`, `curl` Spark Master `/json/`, `spark-submit --version`, `python --version` (kết quả được nêu ở các mục liên quan bên dưới).
- **Nguồn đối chiếu:** `docs/CONTEXT.md`, mọi `reports/evidence/stage_*.md`, các CSV/Parquet trong `results/` và `data/results/`, `reports/evidence/cleaning_log.csv`, `reports/evidence/split_log.csv`, `src/*.py`, `README.md`, `web/`, `scratch/paclic_paper_text.txt`, và trạng thái Docker/HDFS đọc trực tiếp hôm nay.
- **Cách đọc cột "Trạng thái":** `ĐÃ CHẠY VÀ KIỂM CHỨNG` = có chạy thật và số liệu truy được về file kết quả. `CHƯA ĐẠT` = hoặc chưa chạy/chưa kiểm chứng, hoặc đã chạy nhưng mục tiêu đặt ra của hạng mục không đạt. Lý do luôn ghi ở cột bên cạnh.

---

## 1. Hạ tầng thực tế

**Thực tế đang dùng là cụm HDFS + Spark Standalone chạy trong Docker trên MỘT máy Windows, không phải Spark local + Parquet.**

Bằng chứng đọc hôm nay (14/10/2026):

| Kiểm tra | Kết quả đọc được |
|---|---|
| `docker ps` | 7 container đang chạy: `namenode`, `datanode1`, `datanode2`, `spark-master`, `spark-worker-1`, `spark-worker-2`, `bigdata_spark_env`. Spark master/worker và client hiện hiển thị `unhealthy`/`healthy` hỗn hợp (xem hạn chế H3). |
| Spark Master `/json/` | `spark://spark-master:7077`, 2 worker `ALIVE`, mỗi worker 2 core / 3500 MB |
| `spark-submit --version` | Spark **4.2.0**, Scala 2.13.18, OpenJDK 21.0.12.1 |
| `hdfs dfs -ls -R` | Có đủ `/data/clean/...`, `/data/splits/...`, `/models/.../als_best_model`, `/data/results/...` (mọi thư mục có `_SUCCESS`) |
| `hdfs dfsadmin -report` | 2 DataNode, `Missing blocks: 0`, `Under replicated blocks: 144` (xem H4) |
| `python --version` trong container | 3.13.16 |

Điểm cần nói rõ khi bảo vệ:
- "Phân tán" ở đây là **giả lập trên một máy vật lý** (các container chia sẻ CPU/RAM của cùng máy, mạng là bridge ảo của Docker). Không có mạng thật giữa các máy.
- Chế độ `STORAGE_MODE=local` có trong `src/config.py` nhưng **CHƯA KIỂM CHỨNG** (xem H5). Quy định "cùng một mã chạy được ở cả hai chế độ" trong CONTEXT mới được chứng minh cho chế độ `hdfs`.

---

## 2. Bảng hạng mục

| # | Hạng mục | Trạng thái | Bằng chứng (đường dẫn) | Điều kiện / lý do |
|---|---|---|---|---|
| 1 | Hạ tầng HDFS + Spark (Docker) | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `reports/evidence/stage_P2.md` (lệnh + kết quả nguyên văn: `compose ps`, `dfsadmin -report`, `/json/`, `smoke_test_cluster.py` đếm khớp 1,132,367 dòng); xác nhận lại hôm nay ở mục 1 | Bước thử `compose down/up` giữ dữ liệu (P2 §3.7) chỉ được mô tả, **không có log nguyên văn**. Replication thực tế lệch (H4). |
| 2 | Làm sạch dữ liệu (cả hai bộ) | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `reports/evidence/stage_P3.md` (log chạy + `verify_clean.py` 6/6 ĐẠT nguyên văn), `reports/evidence/cleaning_log.csv`, `reports/evidence/data_profile_food_com.md`, `data_profile_vifoodrec.md`, `reports/evidence/stage_P1_audit.md` | K-core đã hội tụ (min user = 3, min món = 3 với Food.com). Nhưng quyết định loại rating 0.0 và 0.5 của ViFoodRec là **đáng ngờ** (H1). |
| 3 | Benchmark lưu trữ CSV vs Parquet | **ĐÃ CHẠY VÀ KIỂM CHỨNG** (số liệu); giải thích kỹ thuật một phần chưa kiểm chứng | `data/results/storage_benchmark.csv` (= `app/data/storage_benchmark.csv`), `reports/figures/storage_benchmark.png`, `reports/evidence/stage_P4.md` | Số dung lượng/thời gian truy được về CSV. **Không có log lệnh nguyên văn.** Truy vấn chạy trên bảng 19 MB, 3 lần đo sau 1 lần khởi động. Lời giải thích "multiLine split barrier" không áp dụng cho CSV sạch được đo (B9). |
| 4 | EDA | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `results/eda/*.csv` (và bản sao `data/results/eda/`), `reports/figures/eda_01…13_*.png`, `reports/evidence/eda_insights.md`, `reports/evidence/stage_P5.md` | Các số kiểm lại khớp CSV (ví dụ 78.40% = 553,890/706,514; 4.755 vs 4.674 ở `eda_07_food_com_time_groups.csv`). Không có log lệnh. Một số khẳng định về nguồn gốc ViFoodRec là suy đoán (B10). |
| 5 | Chia train/val/test + Baseline | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `reports/evidence/split_log.csv` (leak = 0 ở 3 cặp), `results/baseline_metrics.csv`, `results/baseline_rmse_breakdown.csv`, `reports/evidence/stage_P6.md` | Chia ngẫu nhiên theo dòng (`rand(seed=42)`), không chia theo thời gian. Không có log lệnh; hai giá trị μ (4.7146 và 2.9981) không có trong CSV nào (B1). |
| 6 | ALS (chạy, tuning, xuất kết quả) | **ĐÃ CHẠY VÀ KIỂM CHỨNG** (phần thực thi) | `results/als_tuning_food_vietnam.csv` (24 cấu hình), `results/als_tuning_food_com.csv` (8 cấu hình), `results/model_comparison.csv`, `results/als_rmse_breakdown.csv`, mô hình trên HDFS `/models/*/als_best_model` | Tuning chỉ dùng validation (đúng quy tắc). |
| 6b | ALS **tốt hơn baseline** (mục tiêu của kế hoạch) | **CHƯA ĐẠT** | `results/model_comparison.csv` | Trên cả hai bộ, ALS thua baseline ở RMSE; Food.com thua cả MAE; Precision@10 và Recall@10 thấp hơn baseline Top-N Popular ở cả hai bộ (Food.com P@10: 0.00017 so với 0.00534). Chỉ có RMSE theo từng mức điểm thấp hơn ở 1–4 sao trên Food.com, không phải độ đo tổng. |
| 7 | K-means: người dùng Food.com (k=4) và món ViFoodRec (k=4) | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `results/kmeans_tuning.csv`, `results/cluster_profiles_food_com.csv`, `results/food_cluster_profiles_vietnam.csv`, `results/user_clusters_food_com.parquet` (30,772 dòng), `results/food_clusters_vietnam.parquet` (4,000 dòng), `reports/evidence/stage_P8.md` | Silhouette thấp (0.2743 và 0.2334) và k không chọn theo Silhouette cao nhất (C3). Tên cụm là diễn giải của nhóm. |
| 7b | K-means: người dùng ViFoodRec (k=3) | **CHƯA ĐẠT** | `results/cluster_profiles_food_vietnam.csv` | Ba cụm gần như không khác nhau (điểm TB 3.00 / 2.96 / 3.03; thời gian nấu món chấm cao 32.71 / 32.87 / 32.80 phút). Tên "Convenient / Selective / Active Gourmet Diners" trong file này và trong P8 không có số liệu hỗ trợ (C2). |
| 8 | Thực nghiệm mở rộng quy mô: đo | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `results/scalability.csv` (32 dòng), `reports/figures/scalability_*.png`, `reports/evidence/stage_P9.md` | Số trong biên bản khớp CSV. Không có log lệnh. Thứ tự chạy giữa các cấu hình không được ghi. |
| 8b | Thực nghiệm mở rộng quy mô: **kết luận "mở rộng được"** | **CHƯA ĐẠT** | `results/scalability.csv` | Thời gian tổng gần phẳng và không đơn điệu (2 worker: 11.986 → 8.393 → 7.166 → 7.933 s cho 10/25/50/100%); dữ liệu chỉ tới 706,514 dòng nên bị chi phí cố định che hết. Chỉ chứng minh được "chưa thấy chi phí tăng theo dữ liệu trong khoảng này". Hệ số tăng tốc 1→2 worker: 0.88x, 0.87x, 1.15x, 1.25x. |
| 9 | Xuất kết quả cho dashboard | **ĐÃ CHẠY VÀ KIỂM CHỨNG** | `reports/evidence/stage_P10.md` (log `export_for_app.py` và `verify_export.py` 66/66 nguyên văn), `docs/data_contract.md`, `app/data/` | `verify_export.py` kiểm tồn tại/schema/số dòng/khóa ngoại, **không kiểm đúng sai của số liệu**. |
| 10 | Dashboard Streamlit (`app/`) | **ĐÃ CHẠY VÀ KIỂM CHỨNG** (kiểm thử tự động); đã bị thay thế | `reports/evidence/stage_P11.md`, `reports/evidence/test_app_log.txt` (6/6 OK bằng `AppTest`) | `AppTest` không phải trình duyệt thật. Ảnh chụp có lệch tên (A13). Nội dung giải thích ALS trong P11 mâu thuẫn số liệu (C1). Hiện giữ làm bản lưu. |
| 11 | Dashboard web tĩnh (`web/`) | **ĐÃ CHẠY VÀ KIỂM CHỨNG** (số liệu khớp nguồn) | `reports/evidence/stage_WEB.md` (log `verify_web.py` 32/32 nguyên văn), `reports/evidence/web_contrast.md`, `reports/figures/screenshots/web_v1/` | Kiểm thử "không cuộn trang" và quét mã chạy bằng script trong `scratch/` ; log chỉ nằm trong biên bản, **không có file log riêng**. `web/config.js` để trống thông tin nhóm. Còn lỗi văn bản (A1, A3). |
| 12 | Đối chiếu với bài báo ViFoodRec | **ĐÃ CHẠY VÀ KIỂM CHỨNG** (con số trích) | `scratch/paclic_paper_text.txt` dòng 582–587 (Bảng 5) và dòng ~491, ~569 (200 điểm, tỉ lệ 1:900); `reports/evidence/stage_P7.md` §5 | Số trích đúng. Nhưng giao thức khác (200 điểm test so với 15,080; dữ liệu của nhóm đã lọc 0.0/0.5) nên chỉ mang tính tham khảo. Nguồn nằm ở `scratch/`, chưa chép vào `reports/evidence/`. |

---

## 3. Hạn chế trung thực

**Về dữ liệu**
- **H1. Loại rating 0.0 và 0.5 của ViFoodRec (33,211 dòng, 18.18%).** Đọc trực tiếp `data/raw/food_vietnam/ratings.csv`: 11 mức từ 0.0 đến 5.0, mỗi mức khoảng 16,4xx–16,8xx dòng (0.0: 16,509; 0.5: 16,702; 1.0: 16,420 … 5.0: 16,602). Tức là 0.0 và 0.5 **phân phối y hệt các mức khác**; không có bằng chứng trong file rằng 0.0 là "chưa chấm". Các biên bản P1, P3, P7, P11 gọi 0.0 là "chưa đánh giá/missing" mà không có căn cứ. Quyết định loại này do nhóm đặt ra, ảnh hưởng 18% dữ liệu, và chưa ai xác nhận. `stage_WEB.md` §4 đã tự nhận 0.5 có thể hợp lệ.
- **H2. ViFoodRec chỉ có 101 người dùng**, phân phối điểm đều (mỗi mức trong 9 mức còn lại chiếm 10.99–11.28%). Bài báo gốc nói "điền 40% giá trị thiếu bằng trung vị" (`scratch/paclic_paper_text.txt` dòng ~329–331). Các câu "sinh điểm nhân tạo/mô phỏng" trong P3, P5, P7 là suy đoán của nhóm, chưa kiểm chứng. RMSE của Global Mean (1.2866) gần bằng độ lệch chuẩn lý thuyết của phân phối đều 9 mức (√(15/9) = 1.291), nghĩa là chưa thấy tín hiệu để mô hình học.
- Food.com lệch 5 sao (78.40%), nên RMSE tổng thể của mọi mô hình bị "kéo" bởi lớp 5 sao. Global Mean chỉ có RMSE 0.6266.
- K-core và các thống kê dùng để lọc được tính trên **toàn bộ** dữ liệu trước khi chia train/val/test (thực hành phổ biến nhưng cần nêu).
- Chia train/val/test ngẫu nhiên theo dòng; không có đánh giá theo thời gian dù Food.com có cột `date`.

**Về hạ tầng**
- **H3.** Hôm nay `docker ps` báo `unhealthy` cho `spark-master`, `spark-worker-1`, `spark-worker-2`, trong khi `/json/` báo 2 worker `ALIVE`. Chưa điều tra nguyên nhân (không nằm trong phạm vi chỉ đọc).
- **H4. Replication không đồng nhất.** Cấu hình `dfs.replication=2` và 2 DataNode, nhưng `hdfs dfs -stat "%r"` hôm nay cho: file thô `RAW_interactions.csv` = 2, còn `_SUCCESS` của dữ liệu sạch và smoke test = 3. `dfsadmin -report` hiện có `Under replicated blocks: 144` (P2 ghi 0 ở thời điểm đó). `Missing blocks: 0` nên chưa mất dữ liệu. Nguyên nhân có khả năng là client Spark ghi với `dfs.replication` mặc định = 3 (**đây là suy luận, chưa kiểm chứng**). README và `web/data/system.js` ghi "replication = 2" nên không đúng với các file do Spark ghi.
- **H5. Chế độ local chưa kiểm chứng.** `data/` trên máy chỉ có `raw/`, `processed/`, `results/`. Không có `data/clean/` và `data/splits/` mà `config.get_path()` sẽ tìm ở chế độ local. `data/processed/*.parquet` là **bản cũ** (K-core một lượt, 735,006 dòng, đã bị P1 bác bỏ) và không được pipeline hiện tại dùng.
- Thí nghiệm mở rộng quy mô chỉ tới 706,514 dòng (khoảng vài chục MB Parquet), nên không phải bài toán Big Data theo nghĩa thông thường.

**Về mô hình**
- **ALS không tốt hơn baseline** (mục 2, dòng 6b). Theo CONTEXT §3.4, khi "mô hình tệ hơn baseline" phải **dừng và hỏi người dùng**; biên bản P7 vẫn tiếp tục sang P8 mà không ghi việc đã hỏi.
- Lưới tham số ALS của Food.com tốt nhất ở **biên** (regParam = 0.2 là giá trị lớn nhất được thử), nên chưa chắc đã tối ưu. Lưới rút gọn còn 8 cấu hình.
- Precision@10 của ViFoodRec (0.01386–0.01584) cùng bậc với mức ngẫu nhiên. Ước tính thô của tôi (không phải số đo): mỗi user có ~149 mục test, ~1/3 có điểm ≥ 4 (~50 mục) trên ~2,800 mục chưa xem, nên chọn ngẫu nhiên cho P@10 ≈ 1.8%. Dự án chưa có baseline "ngẫu nhiên" được đo thật.
- Gợi ý "người dùng mới" (cold-start) dùng cosine trên item factor của ALS. Chỉ được kiểm thử bằng 4 ca (`test_app_log.txt`), **chưa có đánh giá định lượng**, và mô hình ALS gốc không thắng baseline.
- Không đo độ đa dạng, độ mới lạ (novelty), hay thiên kiến phổ biến.

**Về bằng chứng**
- Các biên bản P4, P5, P6, P7, P8, P9 **không chứa log lệnh nguyên văn** như CONTEXT §5.2 yêu cầu (chỉ có bảng số). Số liệu vẫn truy được về CSV/Parquet trong `results/` và `data/results/`. Các script kiểm thử web (`scratch/audit_code.py`, `scratch/test_all_scroll.py`) có kết quả chỉ trong `stage_WEB.md`.
- Kết quả hiện nằm ở hai nơi trùng nhau (`results/` và `data/results/`; `diff -rq` chỉ khác 2 file: `split_log.csv`, `storage_benchmark.csv` chỉ có ở `data/results/`). `config.get_path('results')` trỏ vào `data/results/`, nhưng CONTEXT quy ước `results/`.

---

## 4. Rà soát: chỗ mô tả khác thực tế, số không truy được, số mâu thuẫn

Cột "Xử lý": **ĐÁNH DẤU** = đã ghi nhận ở đây, chưa sửa file gốc (vì phạm vi chỉ đọc; thao tác sửa hàng loạt bị chặn). "Sửa đề xuất" là chỗ cần sửa khi người dùng cho phép.

### 4A. Tài liệu hoặc mã mô tả khác thực tế

| ID | Vị trí | Đang viết | Thực tế (nguồn) | Xử lý |
|---|---|---|---|---|
| A1 | `README.md:24`, `src/export_for_web.py:91`, `web/js/charts.js:333,371`, `web/index.html:116`, `web/data/system.js`, `reports/evidence/web_design_plan.md:66` | "Spark 3.5.0 / 3.5" | Spark **4.2.0** (`spark-submit --version` hôm nay; `stage_P2.md`). Dòng `export_for_web.py:91` tự mâu thuẫn: "pyspark-notebook:4.2.0 (Spark 3.5.0)". Chuỗi này đang hiển thị trên giao diện web. | ĐÁNH DẤU. Sửa đề xuất: thay bằng 4.2.0 ở 6 chỗ rồi chạy lại `export_for_web.py`. |
| A2 | `README.md:12–14` | ViFoodRec thô "149.431 đánh giá"; sau sạch "3.964 món, 101 người dùng, 116.184 đánh giá"; Food.com thô "226.570 người dùng"; sau sạch "24.325 người dùng"; độ thưa "71,0%" và "99,963%"; điểm TB "4,68" | ViFoodRec thô **182,678**, sau sạch **4,000 món / 101 user / 149,431** (`cleaning_log.csv`); Food.com sau sạch **30,836** user (`eda_12_dataset_comparison.csv`); độ thưa **63.01%** và **99.97%** (tính lại: 1 − 706,514/(30,836×78,171) = 99.9707%); điểm TB gộp **4.71** (`eda_12`). Các số 3.964 / 116.184 / 24.325 / 226.570 / 71,0% / 99,963% không có trong file nào. 4.68 là trung bình của trung bình từng user (`cluster_profiles_food_com.csv`, dòng Overall). | ĐÁNH DẤU. Sửa đề xuất: thay theo cột "Thực tế". |
| A3 | `reports/evidence/stage_WEB.md` §4.2 và §5 (câu hỏi 4) | "24.325 người dùng"; "5.000 người dùng đầu tiên" lên web; "độ thưa 99,963%"; "điểm TB 4,68" | Người dùng Food.com = 30,836; web nạp **1,000** user (`src/export_for_web.py:226`; đếm `web/data/recs_foodcom.js` = 1,000 user, 10,000 gợi ý); độ thưa 99.97%; điểm TB 4.71. | ĐÁNH DẤU. |
| A4 | `docs/web_data_contract.md` §2.6 | catalog "3,055 công thức" | `web/data/recs_foodcom.js`: catalog **3,011** (recommendations 10,000; user_clusters 1,000; item_neighbors 2,500 khớp). | ĐÁNH DẤU. |
| A5 | `docs/Bao_cao_Tien_xu_ly_va_Lam_sach_Du_lieu.md` | "Hoàn thành 100%", 735,006 dòng sạch, 149,467 dòng ViFoodRec, "K-core = 3", "5.7 MB … giảm gần 60 lần" | Đã bị P1 bác bỏ và P3/P4 thay thế: K-core một lượt không hội tụ; 706,514 và 149,431; so sánh dung lượng không công bằng. **Đây là tài liệu lỗi thời, đừng trích dẫn.** (`docs/Bao_cao_cua_gemini.md`: tôi chỉ đọc phần đầu, cùng thời điểm nên nhiều khả năng cũng lỗi thời; chưa kiểm chi tiết.) | ĐÁNH DẤU. Sửa đề xuất: thêm banner "đã lỗi thời" hoặc chuyển vào thư mục lưu trữ. |
| A6 | `docs/CONTEXT.md` §1, `docs/Ke_hoach_*.md`, `docs/data_contract.md` | Demo/dashboard là Streamlit; Streamlit là quyết định "đã chốt" | Dashboard chính hiện là `web/` (HTML tĩnh); `app/` (Streamlit) chỉ còn làm bản lưu và nguồn CSV. `README.md` và `run_all.ps1` đã nói đúng; ba tài liệu trên chưa cập nhật. Việc đổi có vẻ do người dùng yêu cầu (file `Prompt_web_rieng_dashboard.md`), nhưng CONTEXT §6 cấm đổi quyết định đã chốt khi chưa hỏi. | ĐÁNH DẤU và nêu ở mục 5. |
| A7 | `stage_P2.md` §4 dòng 5, `stage_P10.md` header, `stage_P11.md` header | "cùng Python 3.12"; "Python 3.11" trong container; "Python 3.13 / 3.11" | Container `bigdata_spark_env` hôm nay: **Python 3.13.16** (cả `python` và `/opt/conda/bin/python`). 3.11 là Python của máy Windows. | ĐÁNH DẤU. |
| A8 | `src/config.py` (chú thích phía trên `MAX_MINUTES_THRESHOLD`) | "ngưỡng 99.9% là 1440 phút" | `stage_P1_audit.md` §2.2: phân vị 99% = 750 phút, phân vị 99.9% = 2,147,483,647. 1440 là giá trị chọn tay (24 giờ), không phải phân vị. | ĐÁNH DẤU. |
| A9 | `stage_P2.md` sơ đồ ("Replication = 2"), `README.md` §2, `web/data/system.js` | `replication = 2` | Chỉ đúng với file thô (stat = 2). File do Spark ghi có replication 3 và đang under-replicated (H4). | ĐÁNH DẤU. |
| A10 | `stage_P11.md` §1 dòng 13 và §4 | "16 ảnh"; liệt kê `page_2_user_behavior_1791948823817.png`, `page_2_food_clusters_1791948829504.png` | `reports/figures/screenshots/` có **17** PNG ở cấp trên cùng; tên thật là `..._1791948923817.png` và `..._1791948929504.png` (lệch một chữ số). Bảng §4 liệt kê 11 tên. | ĐÁNH DẤU. |
| A11 | `reports/evidence/cleaning_log.csv` dòng cuối; bản sao ở `app/data/cleaning_log.csv`, `web/data/` | "100 user và 4000 món đều thỏa mãn" | ViFoodRec có **101** user (P3 `verify_clean`, `split_log.csv`: `n_train_users = 101`). Lỗi chữ do mã sinh ra. Không sửa file kết quả. | ĐÁNH DẤU. Sửa đề xuất: sửa chuỗi trong `src/run_pipeline_p3.py` (hoặc `clean_vietnam.py`) rồi sinh lại. |

### 4B. Số trong biên bản không truy được về file kết quả

| ID | Vị trí | Con số / khẳng định | Tình trạng | Xử lý |
|---|---|---|---|---|
| B1 | `stage_P6.md` §3 | Global Mean "μ = 4.7146" (Food.com) và "μ = 2.9981" (ViFoodRec) | Không có trong `baseline_metrics.csv` hay file nào khác; không có log. Giá trị hợp lý nhưng **chưa kiểm chứng**. | ĐÁNH DẤU. |
| B2 | `stage_P7.md` §4.1 | "ALS giảm sai số … (-19.2%)" ở mức 1.0 sao | Tính lại từ `als_rmse_breakdown.csv` và `baseline_rmse_breakdown.csv`: 3.6135 → 3.0118 là **−16.7%** so với Smoothed Item Mean, −18.9% so với Global Mean. Không ra 19.2%. Các mức 2/3/4 sao (−21.0%, −27.3%, −27.0%) khớp. | ĐÁNH DẤU. |
| B3 | `stage_P8.md` §7 | "Cụm nhỏ nhất của Food.com là 7.77% - 12.98%" | Không có cụm 7.77%. `cluster_profiles_food_com.csv`: 12.98 / 34.70 / 25.69 / 26.63%. | ĐÁNH DẤU. |
| B4 | `stage_P8.md` §2 | k=5 ViFoodRec Users "xuất hiện cụm quá nhỏ (<10 users)" | `kmeans_tuning.csv` không lưu kích thước cụm cho k=5. Không truy được. | ĐÁNH DẤU. |
| B5 | `stage_P9.md` §4.2 và Q3 | "phần tuần tự ≈ 35–40%", trần 1.33x | Không có phép đo nào tách phần tuần tự; giá trị được suy ngược từ kết quả 1.25x. Công thức trong biên bản dùng p vừa là phần song song vừa là phần tuần tự. | ĐÁNH DẤU là giải thích sau khi có kết quả, không phải kết luận đã kiểm chứng. |
| B6 | `stage_P9.md` §4.1 | "Lượt 10% chậm vì khởi động JVM/JIT (chạy đầu tiên)" | Không có ghi nhận thứ tự chạy; `scalability.csv` liệt kê 2 worker trước 1 worker, còn biên bản §2.3 nói dừng worker 2 trước. Giả thuyết chưa kiểm chứng. | ĐÁNH DẤU. |
| B7 | `stage_P9.md` §4.4 | "Parquet và Predicate Pushdown loại bỏ hoàn toàn nút thắt I/O" (Step 1 = 0.11–0.17 s) | Không có thí nghiệm đối chứng trong P9 (không so với CSV trên cùng truy vấn). Chưa kiểm chứng. | ĐÁNH DẤU. |
| B8 | `stage_P10.md` Q1/Q3, `stage_P11.md` Q1, tiêu chí 5 | "< 200 ms", "< 0.05 s", "< 0.1 s", "< 100 ms" | Không có phép đo độ trễ nào trong `reports/evidence/`. | ĐÁNH DẤU. |
| B9 | `stage_P4.md` §5 | Parquet nhanh hơn một phần vì "CSV đa dòng không chia được split" | Bảng đo ở thí nghiệm C là `interactions_clean` (4 cột, 19.11 MB), không phải CSV đa dòng thô. Giải thích này không áp dụng cho thí nghiệm đã đo. | ĐÁNH DẤU. |
| B10 | `stage_P3.md` §6 Q3, `stage_P5.md` Q3, `stage_P7.md` §4.2 | ViFoodRec "được tạo qua thuật toán mô phỏng/sinh điểm nhân tạo", "ma trận nhiễu trắng" | Chưa có kiểm định nào (độc lập, tự tương quan). Bài báo nói điền 40% thiếu bằng trung vị. Hiện chỉ có phát hiện phân phối đều; phần còn lại là giả thuyết. | ĐÁNH DẤU. |
| B11 | `stage_P2.md` §3.7 và `stage_P4`–`stage_P9` | Lệnh đã chạy | Không có log nguyên văn (CONTEXT §5.2). | ĐÁNH DẤU. |

### 4C. Số liệu giữa các biên bản (đặc biệt số dòng sau làm sạch)

**Kết luận về số dòng sau làm sạch: nhất quán sau P3.** Các số khác nhau có nguyên nhân giải thích được, nhưng cần nêu rõ khi trích.

| Đại lượng | Giá trị | Xuất hiện ở | Ghi chú |
|---|---|---|---|
| Food.com interactions sạch | **706,514** | `cleaning_log.csv`, P3, P4, P5, P6, P9, P10, `verify_clean` log, `eda_12` | Nhất quán. |
| Food.com 735,006 | 735,006 | P1 (K-core một lượt cũ), `docs/Bao_cao_Tien_xu_ly…`, `data/processed/food_com/interactions.parquet` (file cũ còn trên đĩa) | **Cũ, không dùng.** Chênh 28,492 dòng so với 706,514 (P1). |
| ViFoodRec ratings sạch | **149,431** | `cleaning_log.csv`, P3 trở đi | Nhất quán. |
| ViFoodRec 149,467 | 149,467 | P1, `docs/Bao_cao_Tien_xu_ly…`, dòng trung gian của `cleaning_log.csv` | Là số **trước** khi loại 36 dòng `food_id = 4000`. 182,678 − 33,211 = 149,467; 149,467 − 36 = 149,431. |
| Số user Food.com | **30,836** (dữ liệu sạch) và **30,772** (tập train) | P3/P5/P9 và P6/P7/P8/P10 | Hai giá trị cùng tồn tại; chênh 64 user không có dòng nào trong train. Số món: 78,171 (sạch) và 77,960 (train). |
| K-core Food.com "số vòng" | 8 vòng (P1) và 5 vòng (P3) | `stage_P1_audit.md` §3.1, `cleaning_log.csv` | Vòng 1 khác nhau (735,006 so với 716,239) vì cách định nghĩa "vòng" khác; **điểm hội tụ cuối giống nhau: 706,514.** |
| RMSE ALS Food.com | **0.6747** (P7, `model_comparison.csv`) và **0.6745** (P9, `scalability.csv` mức 100%) | P7, P9 | P9 viết "trùng khớp hoàn hảo" nhưng hai số khác nhau 0.0002 (hai lần huấn luyện riêng). Không đáng kể nhưng không "hoàn hảo". |
| Điểm TB Food.com | 4.71 và 4.68 | `eda_12` và `cluster_profiles_food_com.csv` | Gộp theo tương tác (4.71) so với trung bình của trung bình từng user (4.68). Cần ghi rõ khi trích. |
| Cuộc tranh luận "ALS có vượt baseline không" | **Mâu thuẫn thật giữa các biên bản** | P7 §4.1 và P11 Q3/Q4 ("ALS vượt trội", "học được cá nhân hóa") so với `stage_WEB.md` (ALS không thắng) và `model_comparison.csv` | **Số liệu ủng hộ `stage_WEB.md`.** Xem C1. |

Các mâu thuẫn về kết luận:

| ID | Nội dung | Số liệu thật | Xử lý |
|---|---|---|---|
| C1 | P7 §4.1 "ALS vượt trội áp đảo … giảm sai số 19–27%"; P11 Q3 "ALS vẫn học được các tương quan tiềm ẩn, cho phép xếp hạng cá nhân hóa"; P11 Q4 "ALS giảm mạnh sai số ở dải 1–4 sao" | `model_comparison.csv`: Food.com RMSE ALS 0.6747 > 0.6177 (Smoothed), MAE 0.5094 > 0.4120, P@10 0.00017 < 0.00534, R@10 0.00096 < 0.02170. ViFoodRec RMSE 1.3832 > 1.2866, P@10 0.01386 < 0.01584, R@10 0.00286 < 0.00308. Việc RMSE thấp hơn ở 1–4 sao cho thấy ALS dự đoán phân tán hơn baseline, nhưng tổng thể (RMSE, MAE) vẫn tệ hơn vì mất ở lớp 5 sao (0.5903 so với 0.2854–0.3030). Biên bản không chứng minh được "cá nhân hóa tốt". | ĐÁNH DẤU. Khi bảo vệ, dùng kết luận của `stage_WEB.md`. |
| C2 | P8 §4 đặt tên có nghĩa cho 3 cụm người dùng ViFoodRec; `results/cluster_profiles_food_vietnam.csv`, `user_clusters_food_vietnam.parquet`, `app/` còn mang các tên này; `stage_WEB.md` và web dùng "Cụm 1, 2, 3" vì chênh ≤ 2.42% | Chênh lệch nhỏ (điểm TB 2.96–3.03; thời gian nấu 32.71–32.87 phút). | ĐÁNH DẤU. Dùng tên trung tính. |
| C3 | P8 §2 tiêu chí 1 "Silhouette cao, WSSSE ở khuỷu"; Food.com Users chọn k=4 | Silhouette: k=2 **0.5257** (cao nhất), k=8 0.3045, k=4 **0.2743** (thấp thứ hai trong 7 giá trị). ViFoodRec Foods: k=4 0.2334 < k=3 0.2495 và k=5 0.2460. Chọn k dựa trên diễn giải cụm, chưa nói rõ trong tiêu chí. Silhouette tuyệt đối chỉ 0.23–0.28 (cấu trúc cụm yếu). | ĐÁNH DẤU. |
| C4 | `CONTEXT §3.4` so với P7 | Quy tắc yêu cầu dừng và hỏi khi mô hình tệ hơn baseline | Không có ghi nhận đã hỏi. | Nêu ở mục 5. |

---

## 5. Cần người dùng quyết định (chưa tự ý làm)

1. **Rating 0.0 và 0.5 của ViFoodRec:** giữ nguyên quyết định loại (18% dữ liệu), hay chạy lại P3 với phạm vi [0.0 hoặc 0.5, 5.0] rồi chạy lại P6–P9? (H1)
2. **ALS thua baseline:** chấp nhận và báo cáo trung thực như hiện nay, hay thử thêm (ví dụ ALS implicit, mở rộng lưới regParam cho Food.com vì đang tốt nhất ở biên, hoặc gợi ý lai theo nội dung)?
3. **Streamlit → web tĩnh:** xác nhận đây là thay đổi do bạn yêu cầu, để cập nhật CONTEXT, kế hoạch và `docs/data_contract.md`.
4. **Replication:** chấp nhận `Under replicated blocks: 144` hay chạy `hdfs dfs -setrep -w 2` (và/hoặc đặt `dfs.replication=2` cho client Spark)?
5. **Cho phép sửa văn bản:** các sửa ở A1–A11 là sửa chuỗi/số, rủi ro thấp. Tôi chưa làm vì phạm vi lần này là chỉ đọc. Bạn cho phép thì tôi sửa và ghi lại.

---

## 6. Bảng các con số chính

Mọi con số bên dưới đã được đọc lại từ file nguồn trong phiên này.

### 6.1. Quy mô dữ liệu sau làm sạch

| Chỉ số | Food.com | ViFoodRec | File nguồn |
|---|---:|---:|---|
| Số user | **30,836** | **101** | `results/eda/eda_12_dataset_comparison.csv` |
| Số món (có tương tác) | **78,171** | **4,000** | `results/eda/eda_12_dataset_comparison.csv` |
| Số tương tác sau làm sạch | **706,514** | **149,431** | `reports/evidence/cleaning_log.csv` (dòng `iterative_k_core_convergence` / `foreign_key_join_foods`) và `eda_12_dataset_comparison.csv` |
| Số tương tác thô (để đối chiếu) | 1,132,367 | 182,678 | `reports/evidence/cleaning_log.csv` (dòng `raw_input`) |
| Số user / món trong tập train | 30,772 / 77,960 | 101 / 4,000 | `reports/evidence/split_log.csv` |

### 6.2. Baseline và ALS trên tập test

| Bộ | Mô hình | RMSE | MAE | Precision@10 | Recall@10 |
|---|---|---:|---:|---:|---:|
| Food.com | Global Mean | 0.6266 | 0.4468 | 0.00000 | 0.00000 |
| Food.com | Smoothed Item Mean (m=5) | **0.6177** | 0.4214 | 0.00048 | 0.00130 |
| Food.com | Top-N Popular | 0.6568 | **0.4120** | **0.00534** | **0.02170** |
| Food.com | **ALS (rank 10, regParam 0.2, maxIter 10)** | 0.6747 | 0.5094 | 0.00017 | 0.00096 |
| ViFoodRec | Global Mean | **1.2866** | **1.1073** | 0.00000 | 0.00000 |
| ViFoodRec | Smoothed Item Mean (m=5) | 1.3033 | 1.1261 | **0.01584** | 0.00308 |
| ViFoodRec | Top-N Popular | 1.3094 | 1.1299 | **0.01584** | **0.00331** |
| ViFoodRec | **ALS (rank 10, regParam 0.1, maxIter 10)** | 1.3832 | 1.1752 | 0.01386 | 0.00286 |

- File nguồn: `results/model_comparison.csv` (cả 8 dòng). Tham số ALS tốt nhất chọn trên validation: `results/als_tuning_food_com.csv` (val RMSE 0.6754) và `results/als_tuning_food_vietnam.csv` (val RMSE 1.3779).
- In đậm = giá trị tốt nhất theo cột trong mỗi bộ. **ALS không phải giá trị tốt nhất ở cột nào.**

### 6.3. K-means: k đã chọn và Silhouette

| Bài toán | k đã chọn | Silhouette | Silhouette cao nhất trong dải k đã thử | File nguồn |
|---|---:|---:|---|---|
| Người dùng Food.com | **4** | **0.2743** | k=2: 0.5257 | `results/kmeans_tuning.csv` |
| Người dùng ViFoodRec | **3** | **0.2534** | k=2: 0.2561 | `results/kmeans_tuning.csv` |
| Món ViFoodRec | **4** | **0.2334** | k=3: 0.2495 | `results/kmeans_tuning.csv` |

### 6.4. Thời gian mở rộng quy mô (tổng thời gian pipeline, trung bình 2 lần chạy, giây)

| Mức dữ liệu | Số dòng | 2 Worker (4 core) | 1 Worker (2 core) | ALS fit 2W / 1W | ALS Test RMSE |
|---|---:|---:|---:|---:|---:|
| 10% | 71,148 | 11.986 | 10.583 | 5.830 / 4.679 | 1.1785 |
| 25% | 176,704 | 8.393 | 7.287 | 3.126 / 3.090 | 0.8884 |
| 50% | 358,296 | 7.166 | 8.238 | 3.697 / 4.142 | 0.7482 |
| 100% | 706,514 | 7.933 | 9.891 | 3.826 / 4.908 | 0.6745 |

- File nguồn: `results/scalability.csv` (cột `avg_time`, các dòng `Tổng cộng Pipeline` và `Step 2: Huấn luyện ALS`).
- Thời gian **không tăng theo dữ liệu**; chưa đủ để kết luận về khả năng mở rộng (mục 2, dòng 8b).

### 6.5. Số khác hay được hỏi

| Chỉ số | Giá trị | File nguồn |
|---|---:|---|
| Parquet so với CSV, dữ liệu thô đầy đủ (interactions / recipes) | 1.76x / 2.34x | `data/results/storage_benchmark.csv` |
| Parquet so với CSV, dữ liệu sạch (interactions / recipes) | 4.19x / 7.03x | `data/results/storage_benchmark.csv` |
| Truy vấn Parquet so với CSV (Q1 / Q2 / Q3) | 1.71x / 2.06x / 1.80x | `data/results/storage_benchmark.csv` |
| Số dòng bị loại: Food.com rating = 0 / K-core | 60,847 / 365,006 | `reports/evidence/cleaning_log.csv` |
| Số dòng bị loại: ViFoodRec rating 0.0 / 0.5 / `food_id=4000` | 16,509 / 16,702 / 36 | `reports/evidence/cleaning_log.csv`; đọc lại `data/raw/food_vietnam/ratings.csv` |
| Rò rỉ train/val/test (3 cặp, cả hai bộ) | 0 | `reports/evidence/split_log.csv` |
| Cold-start loại khỏi val / test (Food.com) | 422 / 437 | `reports/evidence/split_log.csv` |
| Độ thưa Food.com / ViFoodRec | 99.97% / 63.01% | `results/eda/eda_12_dataset_comparison.csv` |

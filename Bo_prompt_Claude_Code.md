# BỘ PROMPT CHO CLAUDE CODE: SỬA VÀ CHẠY LẠI ĐỒ ÁN

**Ngày lập:** 14/10/2026
**Mục đích:** tiếp tục dự án hiện có, không làm lại từ dữ liệu thô. Sửa hạ tầng, chạy lại riêng phần ViFoodRec với thang điểm 0,0 đến 5,0, sửa dashboard web, cập nhật tài liệu và đóng băng code. Báo cáo Word và slide chưa nằm trong bộ này.
**Khác với bộ P0 đến P12 cũ:** quy tắc chung nằm trong `docs/CONTEXT.md`, nên mỗi prompt ngắn hơn. Mỗi stage chạy trong một phiên Claude Code mới.

---

## 0. Cách dùng

1. Mở thư mục dự án trong VS Code và chạy Claude Code. Mỗi stage dùng một phiên mới (`/clear`), dán nguyên khối prompt của stage đó.
2. Sau mỗi stage, xem "Cổng kiểm tra" rồi mới sang stage sau. Mỗi stage kết thúc bằng một commit và một tag để quay lại được.
3. Thứ tự: **S0 → S1 → S2 → S3 → (S3b, tùy chọn) → S4 → S5 → S6**.
4. Gõ `/model` để xem tài khoản dùng được model nào. Gợi ý:

| Stage | Model | Effort | Chế độ |
|---|---|---|---|
| S0 tiếp quản | Opus nếu có, không thì Sonnet | Cao | Plan mode, chỉ đọc |
| S1 hạ tầng | Sonnet | Trung bình | Thường |
| S2, S3 ViFoodRec | Sonnet | Cao | Thường |
| S4 web | Sonnet | Cao | Plan mode trước, sửa sau khi duyệt |
| S5, S6 tài liệu, đóng băng | Sonnet | Trung bình | Thường |

Nếu bị kẹt (Claude đã đủ ngữ cảnh, thử nghiêm túc mà vẫn sai) thì đổi sang Opus thay vì chỉ tăng effort.

---

## 1. Việc bạn tự làm trước khi chạy S0

1. **Commit và sao lưu** (trong PowerShell, ở thư mục dự án):
   - `git add -A` rồi `git commit -m "Trước khi chuyển sang Claude Code"` rồi `git tag v1-gemini`
   - Sao chép `results`, `data\results`, `app\data`, `web\data`, `reports` sang thư mục `backup_v1_gemini` nằm ngoài dự án.
2. **Thêm skill frontend-design vào dự án** (dùng ở S4): tải kho `https://github.com/anthropics/skills`, chép thư mục `skills/frontend-design` vào `.claude/skills/frontend-design/` của dự án, rồi commit.
3. **Dán khối sau vào cuối `docs/CONTEXT.md`** (làm mục 7). Từ đây mọi stage sẽ đọc khối này.

````markdown
## 7. Cập nhật ngày 14/10/2026 (người dùng đã xác nhận)
1. ViFoodRec: giữ toàn bộ thang điểm 0,0 đến 5,0 (11 mức, bước 0,5). Chỉ loại NULL, trùng cặp (user, món) và dòng có food_id không có trong danh mục món. Lý do: 0,0 và 0,5 có số dòng ngang các mức khác, không có bằng chứng đó là "chưa chấm".
2. ALS không tốt hơn baseline trên cả hai bộ: đã biết và được chấp nhận, báo cáo trung thực. Quy tắc §3.4 không buộc dừng vì lý do này nữa. Vẫn dừng nếu kết quả tốt bất thường hoặc có rò rỉ dữ liệu.
3. Dashboard chính là web/ (HTML/CSS/JS tĩnh). app/ (Streamlit) giữ làm bản lưu và nguồn dữ liệu, không xóa.
4. Cụm người dùng ViFoodRec: nếu chênh lệch tương đối giữa các cụm ở mọi đặc trưng nhỏ hơn 10% thì gọi "Cụm 1, 2, 3", không đặt tên diễn giải.
5. Mọi lệnh chạy thật phải ghi log nguyên văn vào reports/evidence/logs/ (dùng Tee-Object hoặc tee). Biên bản chỉ trích từ log.
6. Chỉ viết nguyên nhân của một kết quả khi đã kiểm chứng. Nếu chưa, ghi "giả thuyết chưa kiểm chứng".
7. Không xóa hay ghi đè file ngoài phạm vi stage. Sao lưu trước khi ghi đè kết quả. Không đụng data/raw.
8. Trình bày: tiếng Việt viết hoa kiểu câu, không icon, không chú thích tiếng Anh trong ngoặc.
9. Điều kiện dừng và hỏi người dùng: mất hơn 10% dòng ngoài dự kiến; rò rỉ train/test khác 0; kết quả mô hình tốt bất thường; lỗi hạ tầng quá 1 giờ chưa xử lý được; cần xóa dữ liệu không khôi phục được.
````

---

## S0. Tiếp quản (plan mode, chỉ đọc)

````markdown
Đọc docs/CONTEXT.md (kể cả mục 7), reports/evidence/STATUS.md và docs/Q_and_A.md.

NHIỆM VỤ (CHỈ ĐỌC, ở plan mode, không sửa file, không chạy pipeline): tiếp quản dự án.
1. Đọc cấu trúc thư mục, src/*.py, docker-compose.yml, README.md, run_all.ps1, web/ và các reports/evidence/stage_*.md.
2. Báo cáo ngắn (tối đa một trang) ra màn hình: dự án làm gì, đang ở đâu, cách chạy, và bạn hiểu từng stage S1 đến S6 dưới đây như thế nào.
3. Tự kiểm chứng các điểm nghi ngờ bằng lệnh đọc và dán kết quả thật:
   a. Trạng thái container và HDFS (replication, under replicated blocks).
   b. Phân phối rating thật trong data/raw/food_vietnam/ratings.csv.
   c. Trang Hành vi của web, khi chọn Food.com, danh sách "món tiêu biểu của cụm" đang hiện tên món tiếng Việt (Bánh Bò Bông, Bánh Canh Chả Cá Nha Trang). Food.com là ẩm thực Âu Mỹ. Tìm xem tên món lấy từ nguồn nào và nối bằng khóa nào.
   d. Mọi chỗ trong src/, web/, app/, README.md còn chuỗi cứng: "Spark 3.5", "replication", "Convenient Diners", và tên cụm tiếng Anh.
4. Liệt kê chỗ STATUS.md hoặc Q_and_A.md không khớp với mã hoặc dữ liệu thực tế bạn thấy, và câu hỏi cần tôi trả lời trước khi làm S1.
5. Đề xuất thứ tự và ước lượng thời gian cho S1 đến S6.
````

**Cổng kiểm tra S0:** báo cáo của Claude nêu đúng quyết định ở mục 7 của CONTEXT, và đã trả lời được điểm 3c (nguồn tên món).

---

## S1. Sửa hạ tầng (replication và trạng thái unhealthy)

````markdown
Đọc docs/CONTEXT.md, reports/evidence/STATUS.md (mục 1, H3, H4) và reports/evidence/stage_P2.md.

NHIỆM VỤ: sửa hai vấn đề hạ tầng đã ghi trong STATUS. Không chạy lại pipeline, không xóa volume.
1. H3: tìm nguyên nhân spark-master, spark-worker-1, spark-worker-2 báo unhealthy trong khi Spark Master /json/ báo 2 worker ALIVE (đọc healthcheck trong docker-compose.yml, docker inspect, log container). Sửa healthcheck nếu sai. Không đổi cấu hình cụm.
2. H4: xác định vì sao file do Spark ghi có replication 3 trong khi dfs.replication=2. Đặt dfs.replication=2 cho client Spark (trong cấu hình SparkSession ở src/config.py hoặc hdfs-site.xml của client), rồi chạy hdfs dfs -setrep -w 2 -R cho /data và /models. Kiểm tra bằng hdfs fsck và hdfs dfsadmin -report: Under replicated blocks phải bằng 0.
3. Trước khi thử docker compose down (không dùng -v) và up lại, sao lưu /models và /data/clean ra thư mục backup trên máy. Sau khi up lại, xác nhận dữ liệu HDFS còn nguyên (đây là mục P2 §3.7 còn thiếu log).
4. Chạy lại src/smoke_test_cluster.py và ghi log.
Ghi log nguyên văn mọi lệnh vào reports/evidence/logs/S1_*.log. Viết reports/evidence/stage_S1.md (trước và sau của từng vấn đề).
Cuối stage: git commit, tag stage-S1.
````

**Cổng kiểm tra S1:** `dfsadmin -report` cho Under replicated blocks = 0, `docker ps` không còn unhealthy (hoặc nguyên nhân còn lại được giải thích), smoke test chạy đạt.

---

## S2. ViFoodRec: làm sạch lại và kiểm tra nguồn gốc dữ liệu

````markdown
Đọc docs/CONTEXT.md (mục 7), reports/evidence/STATUS.md (H1, H2) và stage_P3.md.

NHIỆM VỤ: chạy lại làm sạch ViFoodRec theo quyết định đã chốt: giữ cả 0,0 và 0,5.

Bước 1. Đối chiếu bài báo và file thật (CHỈ GHI SỰ KIỆN, không suy đoán "dữ liệu sinh nhân tạo"). Đọc scratch/paclic_paper_text.txt và data/raw/food_vietnam/ratings.csv. Lập bảng "bài báo nói / file thật" gồm: thang điểm, số người dùng, số đánh giá mỗi người (bài báo nói khoảng 500, STATUS ghi trung vị 1.469), số dòng, số cặp (user, món) trùng, phân phối 11 mức điểm. Nêu mọi chỗ không khớp và ghi rõ chỗ nào chưa giải thích được.

Bước 2. Sửa mã làm sạch ViFoodRec:
- Thêm tham số trong src/config.py: RATING_MIN_VN = 0.0, RATING_MAX_VN = 5.0, RATING_STEP_VN = 0.5.
- Giữ rating thuộc {0.0, 0.5, ..., 5.0}. Loại NULL, trùng cặp, và dòng có food_id không có trong danh mục món (đã biết 36 dòng food_id = 4000). K-core lặp, K = 3.
- Cập nhật cleaning_log (đổi tên bước lọc điểm cho đúng), verify_clean.py (kiểm tra rating thuộc đúng 11 mức) và docs/data_contract.md. Sửa chuỗi sai trong cleaning_log: "100 user" thành số đúng, sinh từ mã.
- Sao lưu kết quả cũ (data/results, results, app/data, web/data) vào backup_v2_truoc_S2/ trước khi ghi đè.

Kỳ vọng (chưa đo, chỉ để phát hiện bất thường): độ lệch chuẩn của phân phối đều 11 mức xấp xỉ 1,58, nên RMSE của Global Mean sau khi chạy lại có thể khoảng 1,5 đến 1,6. Nếu kết quả khác xa, kiểm tra trước khi kết luận.

Ghi log vào reports/evidence/logs/S2_*.log. Viết reports/evidence/stage_S2.md gồm bảng ở Bước 1, bảng số dòng trước và sau từng khâu, và kết quả verify_clean.py.
Cuối stage: git commit, tag stage-S2.
````

**Cổng kiểm tra S2:** `verify_clean.py` đạt toàn bộ; số dòng ViFoodRec sạch lớn hơn 149.431 (khoảng 182.642 nếu chỉ mất 36 dòng khóa ngoại, đây là ước tính chưa đo); bảng "bài báo nói / file thật" không có kết luận bịa.

---

## S3. ViFoodRec: chia, baseline, ALS, K-means, EDA chạy lại

````markdown
Đọc docs/CONTEXT.md (mục 7), stage_S2.md, stage_P6.md đến stage_P8.md.

NHIỆM VỤ: chạy lại mọi bước phụ thuộc dữ liệu ViFoodRec trên dữ liệu mới của S2. Food.com đã kiểm chứng nên KHÔNG chạy lại, trừ khi một script bắt buộc chạy chung (khi đó ghi lý do).
1. Chia train/validation/test (80/10/10, seed 42), baseline 3 mức, ALS (giữ nguyên lưới, seed và quy tắc "món phù hợp = rating >= 4" để so sánh được với kết quả cũ), K-means người dùng và món, EDA phần ViFoodRec, item_neighbors. Chọn tham số chỉ bằng validation, đo test một lần.
2. Kiểm tra rò rỉ train/validation/test bằng truy vấn thật (kết quả phải bằng 0).
3. K-means người dùng ViFoodRec: áp dụng quy tắc ở CONTEXT mục 7.4, ghi nhãn "Cụm 1", "Cụm 2"... vào chính file kết quả (cluster_profiles_food_vietnam.csv, user_clusters_food_vietnam.parquet). Không dùng tên diễn giải.
4. Đổi tên cụm Food.com sang tiếng Việt viết hoa kiểu câu, không kèm tiếng Anh (ví dụ "Người dùng khắt khe"). Chỉ đổi nhãn, không đổi số, và mỗi tên phải khớp số liệu hồ sơ cụm.
5. Chạy thêm hai biến thể chỉ để đối chiếu, KHÔNG dùng làm kết quả chính: (A) bỏ riêng 0,0; (B) quy tắc cũ chỉ giữ [1, 5]. Dùng tham số ALS đã chọn ở biến thể chính, không tinh chỉnh lại. Ghi RMSE, MAE của Global Mean, Smoothed Item Mean và ALS cho cả 3 biến thể vào results/vifoodrec_sensitivity.csv.
6. Phần đối chiếu bài báo: giữ số trích từ Bảng 5, nhưng ghi rõ giao thức vẫn khác (bài báo 200 điểm test). Thang điểm nay trùng thang bài báo, ghi nhận điều đó.
7. Cập nhật export_for_app.py và verify_export.py nếu còn dùng. Phần web làm ở S4.
Quy tắc dừng: theo CONTEXT mục 7.9. ALS thua baseline KHÔNG phải lý do dừng.

Ghi log vào reports/evidence/logs/S3_*.log. Viết reports/evidence/stage_S3.md: bảng so sánh mô hình mới, bảng nhạy cảm 3 biến thể, so với kết quả cũ (cùng độ đo) và nhận xét có số. Nguyên nhân của kết quả chỉ ghi khi đã kiểm chứng, còn lại ghi "giả thuyết chưa kiểm chứng".
Cuối stage: git commit, tag stage-S3.
````

**Cổng kiểm tra S3:** `model_comparison.csv` có 8 dòng mới; `vifoodrec_sensitivity.csv` có 3 biến thể; rò rỉ bằng 0; tên cụm ViFoodRec là "Cụm 1, 2, 3" nếu chênh lệch dưới 10%.

---

## S3b. (Tùy chọn, mặc định bỏ qua) Thử cải thiện mô hình

Chỉ làm khi bạn muốn thử, và làm **trước S4** vì số liệu sẽ đổi.

````markdown
Đọc docs/CONTEXT.md và stage_S3.md.

NHIỆM VỤ (tùy chọn): (1) mở rộng lưới regParam của Food.com thêm 0.3 và 0.5, vì giá trị tốt nhất 0.2 đang nằm ở biên; (2) thử ALS implicit (implicitPrefs=True) coi rating >= 4 là phản hồi tích cực, đánh giá bằng Precision@10 và Recall@10 theo cùng src/evaluation.py. Chọn tham số bằng validation. Ghi kết quả thành dòng mới trong results/model_comparison.csv, không xóa dòng cũ. Nếu vẫn thua Top-N Popular, ghi trung thực. Viết stage_S3b.md, commit, tag stage-S3b.
````

---

## S4. Web: sửa lỗi dữ liệu, nội dung và thiết kế

Danh sách bên dưới lấy từ 5 ảnh chụp ở 1920 px ngày 14/10/2026 (chưa kiểm tra ở 1366x768).

````markdown
Đọc docs/CONTEXT.md (mục 7), stage_S2.md, stage_S3.md, docs/web_data_contract.md và reports/evidence/web_design_plan.md. Đọc .claude/skills/frontend-design/SKILL.md trước khi thiết kế; nếu chưa có thì dừng và báo tôi.

NHIỆM VỤ: cập nhật dashboard web/ với dữ liệu mới và sửa các lỗi dưới đây. Giữ nguyên khái niệm đã duyệt: thanh điều hướng ngang, mỗi trang vừa một màn hình, một màu xanh lá đậm, không icon, không thẻ có bóng, số kiểu Việt Nam. KHÔNG sửa pipeline hay số liệu. Vào plan mode trước, đưa danh sách thay đổi và chờ tôi duyệt rồi mới sửa.

A. SAI SỰ THẬT HOẶC LỖI DỮ LIỆU (ưu tiên cao nhất)
A1. Trang Hành vi, khi chọn Food.com, panel "món tiêu biểu của cụm" hiện món Việt (Bánh Bò Bông, Bánh Canh Chả Cá Nha Trang). Có khả năng cao là nối nhầm với danh mục ViFoodRec theo id. Tìm nguyên nhân (xem kết quả S0), sửa, và thêm kiểm tra vào verify_web.py: mọi món trong panel của Food.com phải có id thuộc danh mục Food.com.
A2. Trang Gợi ý hiện "Hành vi: Thực khách chuộng bữa nhanh (Convenient Diners)" cho người dùng ViFoodRec, mâu thuẫn trang Hành vi. Dùng nhãn từ dữ liệu S3 ("Cụm 1, 2, 3") ở mọi nơi.
A3. Chuỗi cứng sai: "Spark 3.5" (tiêu đề trang Hệ thống, sơ đồ, chú thích) và "Replication = 2". Phiên bản và replication phải lấy từ dữ liệu hoặc biên bản (Spark 4.2.0; replication theo kết quả S1). Thêm kiểm tra: không có chuỗi "Spark 3." trong web/.
A4. Số bị làm tròn rồi in thừa chữ số: bảng Mô hình hiện P@10 của ALS 0,01390 trong khi nguồn là 0,01386; R@10 hiện 0,00310 trong khi nguồn là 0,00308. Hiển thị đúng giá trị nguồn với số chữ số nhất quán (RMSE, MAE: 4 chữ số thập phân; P@10, R@10: 5). verify_web.py phải đối chiếu theo đúng số chữ số hiển thị, không dùng dung sai che lỗi làm tròn.
A5. Mọi ghi chú về ViFoodRec (phễu làm sạch, mục "Giới hạn dữ liệu", biểu đồ phân phối điểm) phải sinh từ dữ liệu mới của S2: 11 mức điểm, không còn bước loại 0,0 và 0,5. Xóa câu "theo quy chuẩn thiết kế ban đầu".
A6. Nhãn "Món mặn" đang gắn cho chè bí đỏ nước cốt dừa và bánh bò. Kiểm tra cột nguồn: nếu "mặn/chay" trong dữ liệu nghĩa là có thịt hay không, đổi chữ hiển thị cho đúng nghĩa hoặc thêm vào Chú giải, để không bị hiểu là vị mặn.
A7. Bỏ các khẳng định chưa kiểm chứng: tiêu đề trang Mô hình "do dữ liệu khảo sát hạn chế"; đoạn "ALS có xu hướng co cụm dự đoán quanh điểm trung bình"; "baseline cực mạnh"; tiêu đề trang Gợi ý "cá nhân hóa"; tiêu đề trang Hành vi "4 nhóm rõ rệt" (Silhouette Food.com chỉ 0,2743). Thay bằng câu nêu số liệu, sinh từ dữ liệu, ví dụ "ALS không tốt hơn baseline ở độ đo nào" hoặc "4 nhóm khác nhau về điểm trung bình và thời gian nấu".

B. NỘI DUNG THEO QUY TẮC ĐÃ CHỐT
B1. Bỏ chú thích tiếng Anh trong ngoặc ("Data Cleaning Funnel", "Mean Rating", "Critical Reviewers", "Cold-Start", "Matrix Factorization", "Zero-dependency"...). Giữ tên kỹ thuật đã có trong Chú giải (ALS, RMSE, MAE, K-core, Parquet, HDFS, Spark).
B2. Viết hoa kiểu tiếng Việt (chỉ chữ đầu câu và tên riêng) cho tên cụm và tiêu đề panel. Tên món lấy từ dữ liệu giữ nguyên.
B3. Xóa các khối chú thích dài có nhãn tự nhận xét: "Quy tắc trung thực", "Minh bạch kết quả", "Giải thích khoa học", "Minh chứng hạ tầng", "Thuật toán gợi ý", "Đúng hạ tầng thật". Mỗi trang chỉ giữ một dòng nguồn số liệu (tên file và đơn vị). Phần giải thích chuyển vào ngăn Chú giải, mỗi thuật ngữ một câu.
B4. Phễu làm sạch: bỏ dấu âm kép ("Mất -33.211" thành "Loại 33.211 dòng") và ký tự ✓ (là icon dạng chữ); dùng chữ ("Đã hội tụ").

C. THIẾT KẾ
C1. Biểu đồ hai chuỗi (baseline với ALS) đang dùng xanh lá và cam có độ sáng gần nhau, và cam chiếm diện tích lớn. Đổi sang xanh lá đậm và xám trung tính khác nhau rõ về độ sáng. Cam chỉ làm điểm nhấn rất nhỏ (dưới 2% diện tích mỗi trang, đo bằng script). Chữ cam nhỏ phải đạt tương phản 4,5:1 với nền.
C2. Thêm tiêu đề trục y ("RMSE") cho biểu đồ phân rã sai số. Số thập phân dùng dấu phẩy ở mọi nơi, kể cả nhãn trục ("1,0 sao") và thời gian ("2,73 s"); hiện trang Mô hình đang dùng dấu chấm. Mọi định dạng đi qua MỘT hàm; thêm kiểm tra tự động: không có mẫu số dạng chữ số-chấm-chữ số trong văn bản hiển thị.
C3. Cột "Rank" trong bảng tinh chỉnh dễ nhầm với cột "Hạng". Đổi thành "Số nhân tố ẩn".

D. BỐ CỤC
D1. Trang Dữ liệu: nhãn trục dưới biểu đồ phân phối điểm bị cắt. Sửa chiều cao panel. Biểu đồ ViFoodRec nay có 11 cột (0,0 đến 5,0) và nhãn phải đọc được.
D2. Trang Hệ thống: năm khối kiến trúc cao hơn nhiều so với nội dung, nửa dưới cột phải để trống. Co khối theo nội dung và tận dụng khoảng trống (ví dụ tab "Hiệu quả lưu trữ" hiện thêm một biểu đồ cột nhỏ). Không để quá 25% diện tích panel trống.
D3. Trang Hành vi: tiêu đề xuống hai dòng và chạm bộ chọn bên phải; nhãn bộ chọn xuống dòng. Tiêu đề tối đa một dòng ở 1366x768; bộ chọn dùng nhãn ngắn một dòng ("Food.com", "ViFoodRec: người dùng", "ViFoodRec: món").
D4. Trang Gợi ý: danh sách món có thanh cuộn trong, dòng #8 bị cắt. Rút dòng nguyên liệu còn một dòng (cắt bằng dấu ba chấm, bấm vào để xem đủ) để 10 món vừa khung ở 1920x1080; ở 1366x768 chấp nhận cuộn trong danh sách và ghi vào biên bản. Một số đơn vị nguyên liệu có vẻ dính chữ (ví dụ "muỗngl"): kiểm tra có phải từ dữ liệu gốc không; nếu từ dữ liệu gốc thì chỉ báo cáo, không tự sửa dữ liệu.

E. KIỂM THỬ (giữ các kiểm tra cũ, thêm kiểm tra mới)
1. verify_web.py đối chiếu ít nhất 40 con số hiển thị với file nguồn, thêm các kiểm tra A1, A3, A4 và C2. Thoát với mã lỗi khác 0 nếu sai.
2. Không cuộn trang ở 1920x1080 và 1366x768 cho mọi trang và mọi trạng thái chính (hai bộ dữ liệu, hai chế độ gợi ý, các tab).
3. Quét mã: không emoji, không ký tự biểu tượng (kể cả ✓), không text-transform uppercase, không gradient, không box-shadow, không animation tự chạy. Quét văn bản hiển thị: không còn ngoặc tiếng Anh ngoài danh sách tên kỹ thuật cho phép.
4. Tương phản WCAG (chữ chính 7:1; chữ nhỏ 4,5:1; đường biểu đồ 3:1) và kiểm tra thang xám cho các màu biểu đồ.
5. Ảnh chụp từng trang ở hai kích thước vào reports/figures/screenshots/web_v2/; mô phỏng chia sẻ online (thu nhỏ còn 960x540, nén JPEG 60%) và kiểm tra vẫn đọc được. Chạy offline.
6. Luồng demo: chọn một người dùng ViFoodRec xem 10 món; chế độ người dùng mới với 3 bộ món khác nhau; từng bộ lọc; tìm không dấu ("bun bo" ra "Bún bò").
Ghi log vào reports/evidence/logs/S4_*.log. Viết reports/evidence/stage_S4.md, nêu rõ mục nào chưa làm được.
Cuối stage: git commit, tag stage-S4.
````

**Cổng kiểm tra S4 (bạn tự làm):** mở 5 trang, đối chiếu từng mục A1 đến D4 với ảnh mới; thử chọn Food.com ở trang Hành vi và xem tên món có phải món Âu Mỹ không; đọc tiêu đề từng trang xem còn câu nào nêu nguyên nhân chưa kiểm chứng.

---

## S5. Dọn tài liệu, sinh lại STATUS và Q_and_A

````markdown
Đọc docs/CONTEXT.md (mục 7), mọi stage_S*.md và reports/evidence/STATUS.md (bản cũ, mục 4 liệt kê các chỗ lệch A1 đến A11 và B1 đến B11).

NHIỆM VỤ: làm cho tài liệu khớp thực tế, rồi sinh lại STATUS.md và Q_and_A.md.
1. Sửa trực tiếp các chuỗi, số sai còn lại: README.md, src/export_for_web.py, web/, docs/data_contract.md, docs/web_data_contract.md, chú thích trong src/config.py (ngưỡng 1440 phút là giá trị chọn tay, không phải phân vị). Số liệu trong README phải lấy từ file kết quả mới, không chép từ biên bản cũ.
2. Biên bản cũ stage_P3 đến stage_P11 và hai báo cáo cũ của Gemini trong docs/: KHÔNG viết lại. Thêm ở đầu file một khối "ĐÍNH CHÍNH ngày 14/10/2026" nêu điểm sai và trỏ tới stage_S2, stage_S3. Thêm banner "ĐÃ LỖI THỜI" cho hai báo cáo Gemini.
3. Các khẳng định chưa kiểm chứng ở mục 4B của STATUS cũ: với mỗi cái, hoặc kiểm chứng bằng lệnh và dán kết quả, hoặc đổi thành "giả thuyết chưa kiểm chứng". Ưu tiên: giá trị trung bình toàn cục (μ) của Global Mean; con số "19,2%" so với 16,7%; "cụm nhỏ nhất 7,77%"; độ trễ "dưới 200 ms" (đo thật hoặc bỏ); phần tuần tự theo Amdahl (bỏ hoặc ghi là giả thuyết); lý do mức 10% chạy chậm (đổi thứ tự chạy để kiểm tra, hoặc ghi là giả thuyết).
4. Sinh lại reports/evidence/STATUS.md theo cùng cấu trúc cũ (hạ tầng thật, bảng hạng mục, hạn chế, rà soát, quyết định cần người dùng, bảng số chính) và docs/Q_and_A.md (15 câu) từ file kết quả MỚI. Mỗi số kèm file nguồn. Sửa câu về số dòng Food.com bị loại: dùng số đúng tính từ cleaning_log (1.132.367 trừ 706.514), không viết "gần 400 nghìn".
5. Cập nhật docs/CONTEXT.md mục 1 và mục 6: dashboard là web/ thay vì Streamlit.
Viết stage_S5.md. Cuối stage: git commit, tag stage-S5.
````

**Cổng kiểm tra S5:** mở `STATUS.md` mới, chọn ngẫu nhiên 5 con số trong bảng số chính, mở file nguồn đối chiếu; không còn mục "chưa kiểm chứng" nào không có giải thích.

---

## S6. Chạy sạch từ đầu và đóng băng code

````markdown
Đọc docs/CONTEXT.md và STATUS.md mới.

NHIỆM VỤ: kiểm tra người ngoài chạy lại được toàn bộ pipeline, rồi đóng băng code. Đây là P12 đầy đủ.
1. Viết hoặc cập nhật run_all.ps1: khởi động cụm, nạp dữ liệu, làm sạch cả hai bộ, verify, benchmark lưu trữ, EDA, chia dữ liệu, baseline, ALS, K-means, thực nghiệm mở rộng, xuất kết quả, xuất dữ liệu web, verify_web. Có tham số bỏ qua các bước nặng.
2. Chạy sạch trên một BẢN SAO, không xóa kết quả hiện có: clone repo sang thư mục mới, dùng thư mục gốc HDFS khác (ví dụ /cleanrun; nếu src/config.py chưa hỗ trợ thì thêm một tham số nhỏ), dữ liệu thô chỉ đọc. Sau khi chạy xong, so sánh kết quả với bản chính: RMSE phải giống nhau (seed cố định), thời gian có thể khác. Ghi log vào reports/evidence/logs/S6_*.log.
3. README.md: kiến trúc đúng thực tế (cụm giả lập trên một máy), yêu cầu máy, cài đặt, chạy từng bước và chạy tất cả, mở dashboard web, cấu trúc thư mục, nguồn dữ liệu và giấy phép (ghi "chưa xác nhận" nếu repo ViFoodRec không nêu giấy phép), hạn chế đã biết. Ghim phiên bản Docker image và thư viện.
4. Cập nhật STATUS.md lần cuối, rồi git commit và gắn tag code-freeze.
Viết stage_S6.md.
````

**Cổng kiểm tra S6:** làm theo README trên một thư mục sạch (hoặc nhờ bạn cùng nhóm thử). Sau mốc này không sửa mã, trừ lỗi nghiêm trọng.

---

## Lưu ý

1. **Chưa viết báo cáo Word và slide.** Chỉ làm sau `code-freeze`, lấy số từ `STATUS.md` và `docs/Q_and_A.md`.
2. **ALS có thể vẫn thua baseline.** Dữ liệu ViFoodRec có phân phối điểm đều nên khó có tín hiệu để học. Mục đích chạy lại là bỏ một điểm yếu phương pháp (loại 18% dữ liệu không có căn cứ), không phải để ALS thắng.
3. **Cả hai thành viên phải hiểu từng stage.** Mỗi `stage_S*.md` có phần số liệu và nhận xét; đọc và tập trả lời trước khi sang stage sau.
4. **Giấy phép dữ liệu** của ViFoodRec chưa xác nhận. Trích nguồn đầy đủ khi viết báo cáo.

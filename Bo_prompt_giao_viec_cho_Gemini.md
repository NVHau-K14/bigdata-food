# BỘ PROMPT GIAO VIỆC CHO GEMINI (ANTIGRAVITY)

**Đề tài:** Phân tích hành vi ăn uống và gợi ý món ăn
**Phạm vi:** dữ liệu, làm sạch, HDFS, Spark, mô hình, thực nghiệm, dashboard. **Chưa viết báo cáo Word và slide.**
**Hướng đã chốt:** sửa và bổ sung phần Gemini đã làm (không làm lại từ đầu). Chia thành chuỗi prompt nhỏ, mỗi giai đoạn tự kiểm tra. Thử dựng cụm HDFS + Spark trong 3 đến 4 giờ, nếu lỗi thì dùng Spark local + Parquet.

---

## 0. Cách dùng bộ prompt

1. Lưu **Prompt P0** vào file `docs/CONTEXT.md` trong dự án. Mọi prompt sau đều bắt đầu bằng yêu cầu đọc file này.
2. Chạy lần lượt P1 → P12. **Mỗi prompt một cuộc trò chuyện mới** (để Gemini không bị quá tải ngữ cảnh), mở đầu bằng: *"Đọc `docs/CONTEXT.md` và các biên bản mới nhất trong `reports/evidence/` trước khi làm."*
3. Sau mỗi prompt, bạn tự kiểm tra **Cổng kiểm tra** (mục cuối mỗi prompt) trước khi sang prompt kế tiếp. Không dựa vào lời Gemini nói "đã hoàn thành".
4. Nếu Gemini báo lỗi hoặc kết quả đáng ngờ, dùng **prompt sửa lỗi** (mục 14), hoặc gửi biên bản `stage_*.md` cho mình xem.

### Lịch gợi ý theo ngày

| Ngày | Prompt | Mục tiêu cuối ngày |
|---|---|---|
| 1 | P1, P2 | Biết hiện trạng thật. Cụm HDFS + Spark chạy được (hoặc đã chuyển phương án dự phòng) |
| 2 | P3, P4, P5 | Dữ liệu sạch đã kiểm chứng, đo xong lưu trữ, có EDA |
| 3 | P6, P8 | Có tập chia dữ liệu, baseline, K-means |
| 4 | P7 | ALS đã tuning và đánh giá |
| 5 | P9, P10, P11 | Thực nghiệm mở rộng, xuất kết quả, dashboard |
| 6-7 | P12 | Chạy lại từ đầu, README, đóng băng code (báo cáo và slide làm song song) |

---

## 1. Việc bạn tự làm trước khi bắt đầu

1. **Sao lưu hiện trạng:** copy `data/processed` thành `data/processed_v1_backup` và `git init` rồi commit toàn bộ dự án hiện tại (không commit dữ liệu thô nặng, thêm `data/` vào `.gitignore`).
2. **Cấp RAM cho Docker** (máy 24GB): với Docker Desktop dùng WSL2, tạo hoặc sửa file `%UserProfile%\.wslconfig` với mục `[wsl2]` đặt `memory=16GB` và `processors=6` (tùy CPU), rồi chạy `wsl --shutdown` và mở lại Docker Desktop.
3. **Đóng các ứng dụng nặng** khi chạy Spark (trình duyệt nhiều tab, game...).
4. (Nếu được) **dán hai file `src/clean_food_com.py` và `src/clean_vietnam.py` hiện tại** cho mình để đối chiếu với báo cáo.

---

## P0. Bối cảnh chung và quy tắc làm việc (lưu thành `docs/CONTEXT.md`)

````markdown
# BỐI CẢNH DỰ ÁN VÀ QUY TẮC LÀM VIỆC (BẮT BUỘC ĐỌC TRƯỚC MỖI TÁC VỤ)

## 1. Dự án
Đồ án cuối môn "Nhập môn Big Data" của nhóm 2 sinh viên. Đề tài: "Phân tích hành vi ăn uống và gợi ý món ăn".
Nhóm xử lý hai bộ dữ liệu bằng CÙNG MỘT pipeline Spark, KHÔNG gộp dữ liệu vì không có người dùng chung:
- Food.com (Kaggle: RAW_interactions.csv, RAW_recipes.csv): quy mô lớn, dùng để chứng minh khả năng mở rộng và phân tích hành vi theo thời gian.
- ViFoodRec (món Việt Nam: foods.csv, ratings.csv): dùng cho ứng dụng gợi ý món Việt. Lưu ý: chỉ khoảng 100 người dùng, đánh giá do khảo sát, tác giả đã điền một phần giá trị thiếu bằng trung vị, và foods.csv thực tế có 4.000 món.
Mục tiêu kỹ thuật: baseline -> K-means (phân tích hành vi) -> ALS (gợi ý, Spark MLlib, explicit feedback) -> thực nghiệm mở rộng -> dashboard Streamlit.

## 2. Môi trường
- Máy Windows (PowerShell), Docker Desktop, 24GB RAM (cấp cho Docker khoảng 16GB).
- Dữ liệu thô nằm ở data/raw/ (CHỈ ĐỌC, tuyệt đối không sửa hay xóa).
- Thư mục: data/raw, data/processed, src/, notebooks/, app/, reports/, docs/, results/.
- Mọi đường dẫn đọc và ghi dữ liệu phải đi qua src/config.py. Có hai chế độ: STORAGE_MODE=hdfs (đường dẫn hdfs://...) và STORAGE_MODE=local (đường dẫn thư mục). Cùng một mã nguồn phải chạy được ở cả hai chế độ.

## 3. Quy tắc trung thực (QUAN TRỌNG NHẤT)
1. Mọi con số đưa vào báo cáo hoặc biên bản PHẢI đến từ kết quả lệnh thật mà bạn đã chạy. Lưu nguyên văn kết quả lệnh vào reports/evidence/.
2. Nếu chưa chạy hoặc chưa kiểm chứng, ghi rõ "CHƯA CHẠY" hoặc "CHƯA KIỂM CHỨNG". Cấm viết "hoàn thành 100%" khi chưa có bằng chứng.
3. Cấm bịa số liệu, cấm điền số liệu so sánh với bài báo nếu không đọc được nguồn. Để trống và nói rõ.
4. Nếu số liệu bất thường (ví dụ mất hơn 10% dòng ngoài dự kiến, mô hình tệ hơn baseline, kết quả quá hoàn hảo), DỪNG LẠI, mô tả bất thường và đưa ra các cách xử lý để người dùng quyết định. Không tự ý chỉnh cho đẹp.
5. Không dùng dữ liệu kiểm tra (test) để chọn tham số. Chỉ dùng tập validation.

## 4. Quy tắc viết mã
- Python 3, PySpark DataFrame API. Mỗi file có docstring đầu file giải thích mục đích và các bước chính bằng tiếng Việt.
- Chú thích giải thích TẠI SAO làm vậy (không chỉ làm gì). Tên biến, hàm bằng tiếng Anh.
- Tham số (k-core, seed, ngưỡng, siêu tham số) đặt trong src/config.py hoặc config.yaml, không hard-code rải rác. Seed ngẫu nhiên cố định = 42.
- Không over-engineering: ưu tiên chạy đúng và dễ giải thích. Hai sinh viên phải hiểu và giải thích được từng đoạn mã.
- Không cài thêm thư viện nặng không cần thiết. Mọi thư viện phải ghi vào requirements.txt với phiên bản cụ thể.
- Ghi log ra màn hình và vào file reports/evidence/ khi chạy pipeline.

## 5. Biên bản sau mỗi giai đoạn
Sau mỗi tác vụ, tạo reports/evidence/stage_<mã>.md gồm:
1. Đã làm gì (danh sách file tạo hoặc sửa).
2. Các lệnh đã chạy (nguyên văn) và kết quả thật (trích nguyên văn).
3. Kết quả đối chiếu với "Tiêu chí đạt" của tác vụ: ĐẠT hoặc KHÔNG ĐẠT từng mục.
4. Vấn đề còn tồn và giả định đã dùng.
5. "Điểm cần hiểu để trả lời phản biện": 3 đến 5 câu hỏi giảng viên có thể hỏi về phần này kèm câu trả lời ngắn dựa trên kết quả thật.

## 6. Điều cấm
- Cấm sửa data/raw. Cấm xóa file ngoài phạm vi tác vụ. Cấm commit dữ liệu nặng.
- Cấm viết báo cáo Word, slide (chưa làm giai đoạn này).
- Cấm thay đổi quyết định đã chốt (hai bộ dữ liệu, K-core=3, ALS, K-means, Streamlit) khi chưa hỏi người dùng.
````

**Cổng kiểm tra P0:** file `docs/CONTEXT.md` tồn tại và có đủ 6 mục.

---

## P1. Kiểm toán hiện trạng (CHỈ ĐỌC, không sửa gì)

````markdown
Đọc docs/CONTEXT.md trước.

NHIỆM VỤ: kiểm toán độc lập phần làm sạch dữ liệu đã làm trước đây. CHỈ ĐỌC VÀ ĐO, KHÔNG SỬA mã nguồn hay dữ liệu.

Bước 1. Đọc mã nguồn thật trong src/clean_food_com.py và src/clean_vietnam.py. Liệt kê chính xác từng bước xử lý đang có (đọc CSV thế nào, lọc gì, thứ tự lọc, cách lọc K-core...). Đối chiếu với báo cáo cũ (Bao_cao_Tien_xu_ly_va_Lam_sach_Du_lieu.md) và nêu mọi chỗ báo cáo và mã nguồn không khớp.

Bước 2. Chạy các truy vấn Spark đo trên 4 bảng Parquet hiện có (data/processed/...), ghi kết quả thật:
- Số dòng, số cột, schema.
- Số user khác nhau, số món khác nhau, độ thưa = 1 - dòng / (user x món).
- Số giá trị NULL từng cột.
- Phân phối điểm (đếm theo từng giá trị rating).
- Kiểm tra trùng cặp (user, món).
- Kiểm tra K-core: số tương tác nhỏ nhất của một user và của một món trong bảng đã lọc. Mục tiêu: xác nhận mọi user và món có >= 3 tương tác hay không.
- Kiểm tra khóa ngoại: số recipe_id trong interactions không có trong recipes; số food_id trong ratings không có trong foods (và ngược lại).
- Với recipes: phân vị (min, 1%, 50%, 99%, 99.9%, max) của minutes, n_steps, n_ingredients. Số bản ghi minutes <= 0 hoặc quá lớn.
- Với foods ViFoodRec: in schema, 5 dòng mẫu, số NULL và số giá trị khác nhau mỗi cột, tên chính xác của các cột.

Bước 3. Tính LẠI TỪ DỮ LIỆU THÔ, theo từng bước riêng, số dòng bị loại ở mỗi khâu cho cả hai bộ ratings/interactions:
(a) đọc đúng multiLine; (b) bỏ NULL; (c) rating = 0; (d) rating ngoài [1,5]; (e) trùng cặp (user, món); (f) K-core một lượt như mã hiện tại; (g) K-core lặp tới hội tụ. Đặc biệt giải thích ViFoodRec mất khoảng 33.000 dòng (182.678 -> 149.467) là do khâu nào.

Bước 4. Kiểm tra công bằng của so sánh dung lượng: bảng interactions Parquet đã bỏ cột review và mất dòng, nên KHÔNG thể kết luận "Parquet nén 60 lần". Nêu rõ điều này.

ĐẦU RA: reports/evidence/stage_P1_audit.md gồm: bảng "báo cáo cũ nói gì / thực tế đo được", danh sách lỗi và rủi ro xếp theo mức độ (nghiêm trọng, nên sửa, nhỏ), đề xuất sửa. TUYỆT ĐỐI không sửa mã.

TIÊU CHÍ ĐẠT: có đủ số liệu thật cho Bước 2 và 3; có kết luận rõ K-core hiện tại có đúng hay không; có giải thích khoản mất 33.000 dòng của ViFoodRec.
````

**Cổng kiểm tra P1 (bạn tự xem):**
- File `stage_P1_audit.md` có bảng số liệu thật (số user, số món, độ thưa).
- Có kết luận K-core hiện tại **có hay không** thỏa mãn (min số tương tác của user/món).
- Có phân rã khoản mất 33.000 dòng của ViFoodRec.

---

## P2. Hạ tầng: cụm HDFS + Spark trong Docker (giới hạn 3 đến 4 giờ)

````markdown
Đọc docs/CONTEXT.md và reports/evidence/stage_P1_audit.md trước.

NHIỆM VỤ: dựng cụm HDFS + Spark bằng Docker Compose. GIỚI HẠN THỜI GIAN: 3 đến 4 giờ. Nếu hết thời gian mà chưa đạt tiêu chí, DỪNG và chuyển sang phương án dự phòng (cuối prompt).

Yêu cầu:
1. Viết lại docker-compose.yml với các dịch vụ: namenode, 2 datanode, spark-master, 2 spark-worker, và 1 container client (Jupyter/PySpark để chạy spark-submit và Streamlit sau này). Mỗi worker: 2 core, 4GB RAM. Driver/client: tối đa 3GB. Tổng RAM cụm không quá 14GB.
2. KHÔNG dùng tag "latest". Ghi tag phiên bản cụ thể cho mọi image. Phiên bản Spark của master/worker PHẢI TRÙNG với phiên bản Spark của container client (kiểm tra bằng lệnh), và phiên bản Python của driver phải trùng worker (đặt PYSPARK_PYTHON nhất quán). Nếu image client hiện tại không tương thích, đổi image client cho cùng họ với master/worker.
3. Giữ mount thư mục dự án vào client container. Không để lộ token mặc định yếu: đọc JUPYTER_TOKEN từ biến môi trường hoặc file .env (thêm .env.example).
4. Thiết lập replication factor phù hợp với số datanode. Tạo cấu trúc HDFS: /data/raw/food_com, /data/raw/food_vietnam, /data/clean, /data/splits, /data/results, /models.
5. Đưa dữ liệu thô từ data/raw/ vào /data/raw/ trên HDFS (dùng hdfs dfs -put thông qua container namenode hoặc client). Không sửa data/raw trên máy.
6. Tạo src/config.py: đọc biến STORAGE_MODE (hdfs hoặc local), cung cấp hàm trả về đường dẫn cho từng tập dữ liệu (raw, clean, splits, results, models) theo chế độ, cùng hàm tạo SparkSession dùng chung (master spark://spark-master:7077 khi hdfs, local[*] khi local, ansi mode, shuffle partitions hợp lý, cấu hình bộ nhớ).
7. Viết src/smoke_test_cluster.py: đọc một file CSV từ HDFS, đếm dòng, ghi một Parquet nhỏ ra HDFS, đọc lại và so khớp số dòng. Chạy bằng spark-submit tới master.

TIÊU CHÍ ĐẠT (phải có bằng chứng dán nguyên văn kết quả lệnh):
- hdfs dfsadmin -report cho thấy 2 datanode đang sống.
- hdfs dfs -ls -R /data hiển thị đủ thư mục và các file raw.
- smoke test chạy trên cụm: log cho thấy ít nhất 2 executor, kết quả đếm dòng khớp với số đã biết (RAW_interactions 1.132.367 dòng).
- Truy cập được giao diện NameNode (cổng 9870) và Spark master (cổng 8080). Ghi lại cổng thực tế và tên container.
- docker compose down rồi up lại: dữ liệu HDFS vẫn còn (dùng volume).

PHƯƠNG ÁN DỰ PHÒNG (chỉ dùng khi quá 4 giờ mà chưa đạt): dừng lại, ghi reports/evidence/stage_P2_fallback.md mô tả chính xác điều gì lỗi, đã thử gì. Rồi dựng chế độ STORAGE_MODE=local (Spark local[*] + thư mục Parquet trên máy) bằng cùng src/config.py để các prompt sau chạy không phải sửa mã. TUYỆT ĐỐI không được mô tả hệ thống dự phòng là "HDFS".

ĐẦU RA: docker-compose.yml, .env.example, src/config.py, src/smoke_test_cluster.py, reports/evidence/stage_P2.md (kèm sơ đồ kiến trúc ASCII đúng với hệ thống thật).
````

**Cổng kiểm tra P2 (bạn tự làm):**
- Chạy `docker compose ps`: tất cả container ở trạng thái Up.
- Mở trình duyệt: `http://localhost:9870` (NameNode) và `http://localhost:8080` (Spark master), thấy 2 datanode và 2 worker.
- Biên bản có dán kết quả `hdfs dfsadmin -report`.
- Nếu Gemini chuyển sang dự phòng, file `stage_P2_fallback.md` phải ghi rõ nguyên nhân. Cả hai trường hợp đều chấp nhận, miễn là trung thực.

---

## P3. Làm sạch lại dữ liệu và kiểm chứng

````markdown
Đọc docs/CONTEXT.md, reports/evidence/stage_P1_audit.md và stage_P2.md trước.

NHIỆM VỤ: viết lại pipeline làm sạch cho cả hai bộ dữ liệu, sửa các lỗi đã nêu trong audit P1. Đọc dữ liệu thô từ đường dẫn của config.py (HDFS hoặc local), ghi bản sạch ra /data/clean (Parquet).

QUY TẮC CHUNG
- Đọc CSV với schema khai báo tường minh (không inferSchema), multiLine=true, escape đúng. Với mỗi bước lọc, ghi số dòng trước và sau vào bảng nhật ký làm sạch (cleaning_log), lưu thành CSV trong reports/evidence/ và Parquet trong results.
- K-core phải LẶP cho đến khi hội tụ (không còn user hay món nào dưới ngưỡng). K mặc định = 3, lấy từ config. Ghi số vòng lặp.
- Tách kết quả thành bảng tương tác và bảng món, đảm bảo toàn vẹn khóa ngoại: mọi recipe_id/food_id trong bảng tương tác phải có trong bảng món. Món không có tương tác được giữ lại trong bảng món và gắn cờ has_ratings=false.
- Các bảng nhỏ (ViFoodRec) ghi gọn thành 1 file Parquet (coalesce) để tránh quá nhiều file nhỏ.
- Nếu một bước làm mất hơn 10% dòng ngoài dự kiến, DỪNG và báo cáo nguyên nhân.

FOOD.COM
- interactions: ép kiểu user_id, recipe_id (int), rating (float), date chuyển sang kiểu date. Bỏ NULL, bỏ rating = 0 (ghi số lượng), giữ rating trong [1,5]. Nếu trùng cặp (user, recipe), giữ bản ghi có date mới nhất. Bỏ cột review. Sau đó inner join kiểm tra khóa ngoại với recipes sạch, rồi K-core lặp.
- recipes: ép kiểu id thành recipe_id, minutes, n_steps, n_ingredients. Tách cột nutrition thành 7 cột số theo mô tả Kaggle (calories, total_fat_pdv, sugar_pdv, sodium_pdv, protein_pdv, saturated_fat_pdv, carbohydrates_pdv; kiểm tra lại thứ tự theo tài liệu dữ liệu). Chuyển tags và ingredients thành mảng chuỗi. GIỮ cột tags. Ngoại lai: phân tích phân vị của minutes, chọn ngưỡng có căn cứ (ví dụ phân vị 99.9% hoặc ngưỡng nghiệp vụ), ghi ngưỡng vào config, giữ cột gốc minutes và thêm cột minutes_clean (NULL nếu ngoại lai). Bỏ steps và description. Loại bản ghi thiếu id hoặc name, loại trùng recipe_id.

VIFOODREC
- ratings: đổi tên userId -> user_id, foodId -> food_id (làm theo tên cột thật khi đọc schema). Ép kiểu. In phân phối giá trị rating (kể cả 0). Phát hiện đỉnh bất thường tại một mức điểm (tác giả điền thiếu bằng trung vị) và GHI NHẬN, KHÔNG sửa. Loại trùng cặp. Chỉ ghi nhận rating = 0 nếu có, và hỏi người dùng nên giữ hay loại (mặc định: loại giá trị ngoài [1,5] nhưng báo cáo số lượng).
- foods: in schema thật trước khi viết mã. Chuẩn hóa văn bản: Unicode NFC, trim, gộp khoảng trắng, bỏ emoji và thẻ HTML thừa. Chuyển sang số: thời gian nấu (phút), khẩu phần (số người), các cột dinh dưỡng (calo, chất béo, chất xơ, đường, protein...). Chuẩn hóa loại món (mặn hoặc chay). Món trùng (cùng tên, nguyên liệu, cách nấu) chỉ gắn cờ is_duplicate, KHÔNG xóa nếu món đó xuất hiện trong ratings. Tách mảng tags/nguyên liệu nếu có thể.
- K-core ViFoodRec: ghi riêng số dòng mất do từng khâu. Nếu K-core làm mất nhiều dòng, báo cáo số user và số món bị loại và đề xuất có nên giữ K=3 hay không (người dùng sẽ quyết).

KIỂM CHỨNG TỰ ĐỘNG: viết src/verify_clean.py kiểm tra độc lập (bằng truy vấn riêng, không dùng lại logic của pipeline): không NULL ở cột khóa; rating trong [1,5]; không trùng cặp; mọi user và món đạt K-core; khóa ngoại khớp; số dòng khớp cleaning_log; kiểu dữ liệu đúng schema. Script phải thoát với mã lỗi khác 0 nếu có kiểm tra thất bại.

THỐNG KÊ MÔ TẢ (data profile): với mỗi bộ dữ liệu sạch, tạo reports/evidence/data_profile_<tên>.md với số dòng, số user, số món, độ thưa, trung bình và trung vị số đánh giá mỗi user và mỗi món, phân phối điểm, phân vị các cột số của bảng món.

ĐẦU RA: src/clean_food_com.py, src/clean_vietnam.py, src/verify_clean.py, cleaning_log (CSV), data_profile (2 file), stage_P3.md.

TIÊU CHÍ ĐẠT: verify_clean.py chạy xong, mọi kiểm tra ĐẠT; cleaning_log đủ từng khâu cho cả hai bộ; K-core đã hội tụ (min user >= 3, min món >= 3); có bảng khẳng định lại số dòng sạch.
````

**Cổng kiểm tra P3 (bạn tự làm):**
- Chạy lại `verify_clean.py` trên máy mình, đọc dòng cuối.
- Mở `cleaning_log.csv`: tổng số dòng đầu vào phải khớp số dòng thô (1.132.367 và 182.678).
- Biên bản có số user và số món ViFoodRec thật.

---

## P4. Thực nghiệm lưu trữ: CSV với Parquet (công bằng)

````markdown
Đọc docs/CONTEXT.md và các biên bản P1 đến P3 trước.

NHIỆM VỤ: đo công bằng hiệu quả lưu trữ của Parquet so với CSV. Lưu ý: báo cáo cũ so sánh sai vì Parquet đã bỏ cột và bỏ dòng. Lần này so sánh CÙNG NỘI DUNG.

Thực hiện:
1. Thí nghiệm A (dữ liệu thô đầy đủ): chuyển NGUYÊN BẢN RAW_interactions.csv và RAW_recipes.csv sang Parquet, giữ đủ cột và đủ dòng (đọc multiLine đúng). So sánh dung lượng CSV với Parquet (Snappy).
2. Thí nghiệm B (dữ liệu đã làm sạch): ghi cùng bảng sạch dưới hai định dạng (CSV và Parquet) rồi so sánh dung lượng.
3. Thí nghiệm C (thời gian đọc): với cùng bảng sạch, đo thời gian thực hiện 3 truy vấn: (i) đếm dòng, (ii) trung bình rating theo món, (iii) chỉ đọc 3 cột user_id, recipe_id, rating. Mỗi truy vấn chạy 4 lần, bỏ lần đầu (làm nóng), lấy trung bình 3 lần còn lại và độ lệch chuẩn. Đo bằng time.perf_counter quanh một action thật (count hoặc write), tránh lazy evaluation.
4. Ghi rõ điều kiện đo: số worker, core, RAM, chế độ lưu trữ (HDFS hay local). Ghi lưu ý rằng CSV đa dòng không thể chia nhỏ để đọc song song, đây là một lý do CSV chậm.

ĐẦU RA: results/storage_benchmark.csv (cột: thí nghiệm, bộ dữ liệu, định dạng, dung lượng MB, thời gian TB, độ lệch chuẩn), biểu đồ cột reports/figures/storage_benchmark.png, reports/evidence/stage_P4.md. Trong biên bản, nêu kết luận trung thực: mức giảm dung lượng do Parquet thật là bao nhiêu, và mức nào là do bỏ cột/dòng.

TIÊU CHÍ ĐẠT: số đo có độ lệch chuẩn; kết luận không dùng lại con số "60 lần" cũ; biểu đồ có chú thích rõ đơn vị.
````

**Cổng kiểm tra P4:** bảng đo có đủ ba thí nghiệm A, B, C. Kết luận trong biên bản phải phân biệt phần nén do định dạng với phần giảm do bỏ cột và dòng.

---

## P5. Phân tích khám phá (EDA)

````markdown
Đọc docs/CONTEXT.md và các biên bản P1 đến P4 trước.

NHIỆM VỤ: phân tích khám phá bằng Spark trên dữ liệu sạch của cả hai bộ. Mọi phép tổng hợp thực hiện trong Spark; chỉ thu về pandas các bảng đã tổng hợp nhỏ để vẽ biểu đồ (matplotlib). Lưu bảng tổng hợp vào results/eda/ (Parquet hoặc CSV), biểu đồ vào reports/figures/ (PNG, tiêu đề tiếng Việt, có đơn vị trục).

Các phân tích bắt buộc (cho cả hai bộ trừ khi ghi chú):
1. Phân phối điểm đánh giá.
2. Phân phối số đánh giá trên mỗi user và trên mỗi món (thang log), nhận xét đuôi dài.
3. Top 10 món phổ biến nhất (số lượt đánh giá) và top 10 món được chấm cao nhất (chỉ xét món có ít nhất 20 đánh giá). Chỉ ra sự khác nhau giữa hai danh sách.
4. Food.com: số đánh giá theo tháng/năm, theo thứ trong tuần, và xu hướng điểm trung bình theo thời gian.
5. Food.com: quan hệ giữa thời gian nấu (chia nhóm), calo (chia nhóm) và điểm trung bình; top thẻ (tags) và top nguyên liệu phổ biến.
6. ViFoodRec: so sánh món mặn với món chay (số đánh giá, điểm trung bình), theo nhóm thời gian nấu và nhóm calo; top nguyên liệu.
7. Độ thưa của ma trận và so sánh hai bộ trong một bảng (số user, số món, số đánh giá, độ thưa, điểm TB, trung vị đánh giá mỗi user).
8. ViFoodRec: biểu đồ kiểm tra đỉnh bất thường tại mức điểm do điền trung vị, nêu ảnh hưởng có thể có lên mô hình.

Với mỗi biểu đồ, viết 1 đến 2 câu nhận xét DỰA TRÊN SỐ THẬT, lưu trong reports/evidence/eda_insights.md (mỗi nhận xét ghi kèm con số cụ thể và đường dẫn bảng nguồn). Nhận xét không có số liệu hỗ trợ thì không được viết.

TIÊU CHÍ ĐẠT: ít nhất 12 biểu đồ có tiêu đề và đơn vị; mọi nhận xét có con số; không biểu đồ nào dùng dữ liệu mẫu giả; bảng tổng hợp lưu lại để dashboard dùng.
````

**Cổng kiểm tra P5:** mở 3 đến 4 biểu đồ ngẫu nhiên, đối chiếu với con số nêu trong `eda_insights.md`. Biểu đồ phải có nhãn tiếng Việt đọc được.

---

## P6. Chia dữ liệu và mô hình baseline

````markdown
Đọc docs/CONTEXT.md và các biên bản P1 đến P5 trước.

NHIỆM VỤ: chia dữ liệu và xây dựng baseline, cùng khung đánh giá dùng chung cho ALS.

Chia dữ liệu (cho từng bộ riêng):
- Chia ngẫu nhiên tập tương tác thành train 80%, validation 10%, test 10% với seed=42. Lưu ra /data/splits/<bộ>/ (Parquet).
- Loại khỏi validation và test các dòng có user hoặc món không xuất hiện trong train (ghi số dòng bị loại và tỷ lệ).

Khung đánh giá (src/evaluation.py), dùng chung cho mọi mô hình:
- RMSE và MAE trên điểm dự đoán.
- Độ phủ dự đoán (coverage): tỷ lệ dòng test có dự đoán (vì ALS với cold-start drop sẽ bỏ dòng).
- Chỉ số xếp hạng: với mỗi user, tập "món phù hợp" = các món trong test có rating >= 4; gợi ý Top-10 từ các món user CHƯA có trong train; tính Precision@10 và Recall@10, trung bình trên các user có ít nhất 1 món phù hợp.
- RMSE theo từng mức điểm thật (1 đến 5) để thấy mô hình sai ở đâu.

Baseline (3 mức):
1. Trung bình toàn cục.
2. Trung bình theo món có làm trơn (điểm = (tổng điểm + m * trung bình toàn cục) / (số đánh giá + m), với m lấy từ config, mặc định 5). Với món không có trong train, dùng trung bình toàn cục.
3. Top-N món phổ biến cho mọi user (xếp theo số đánh giá, có điều kiện điểm trung bình tối thiểu), loại các món user đã đánh giá trong train.

ĐẦU RA: src/split_data.py, src/evaluation.py, src/baseline.py, results/baseline_metrics.csv (cột: bộ dữ liệu, mô hình, RMSE, MAE, Precision@10, Recall@10, coverage), reports/evidence/stage_P6.md.

TIÊU CHÍ ĐẠT: số dòng train/val/test cộng lại đúng bằng tổng sau khi loại cold-start; không có rò rỉ (không có cặp user-món nào xuất hiện ở cả train và test); baseline có số đo cho cả hai bộ dữ liệu.
````

**Cổng kiểm tra P6:** biên bản có kiểm tra "không rò rỉ dữ liệu giữa train và test" bằng một truy vấn thật.

---

## P7. Mô hình ALS

````markdown
Đọc docs/CONTEXT.md và các biên bản P1 đến P6 trước.

NHIỆM VỤ: huấn luyện, chọn tham số và đánh giá ALS (Spark MLlib, explicit feedback) cho cả hai bộ dữ liệu, dùng đúng tập chia ở P6 và khung đánh giá src/evaluation.py.

Yêu cầu:
1. Lưới tham số nhỏ, hợp lý với thời gian: rank [10, 20, 50], regParam [0.01, 0.05, 0.1, 0.5], maxIter [10, 15]. Chọn tham số tốt nhất bằng RMSE trên tập VALIDATION (không dùng test). Với Food.com, nếu lưới đầy đủ quá lâu, giảm lưới và ghi rõ lý do. coldStartStrategy="drop".
2. Ghi bảng toàn bộ kết quả thử nghiệm (tham số, RMSE validation, thời gian chạy) vào results/als_tuning_<bộ>.csv.
3. Đánh giá mô hình tốt nhất trên TEST: RMSE, MAE, coverage, Precision@10, Recall@10, RMSE theo từng mức điểm. So sánh với 3 baseline của P6 trong một bảng chung results/model_comparison.csv.
4. Phân tích: ALS có tốt hơn baseline không, tốt hơn ở độ đo nào, vì sao (độ thưa, phân phối điểm, đỉnh trung vị của ViFoodRec). Nếu ALS KHÔNG tốt hơn baseline, báo cáo trung thực và nêu nguyên nhân, không chỉnh cho đẹp.
5. Đối chiếu với bài báo ViFoodRec (PACLIC 2024): nếu truy cập được bài báo, lấy kết quả RMSE/MAE của các phương pháp trong bài, ghi rõ bảng nào, và nhấn mạnh cách chia tập kiểm tra khác nhau nên chỉ so sánh tham khảo. Nếu không truy cập được, để trống ô này và ghi "chưa đối chiếu". KHÔNG được bịa số.
6. Lưu mô hình tốt nhất vào /models/als_<bộ>. Xuất:
   - Top-10 món gợi ý cho mọi user của ViFoodRec (kèm tên món, loại món, calo, thời gian nấu); với Food.com, xuất cho một mẫu ngẫu nhiên 5.000 user (seed cố định).
   - Vector đặc trưng ẩn của món. Từ đó tính độ tương đồng cosine giữa các món: ViFoodRec cho toàn bộ 4.000 món (Top-10 món gần nhất mỗi món); Food.com chỉ cho 20.000 món phổ biến nhất (nêu lý do giới hạn).
7. Đo thời gian huấn luyện và thời gian suy luận.

ĐẦU RA: src/train_als.py, results/als_tuning_*.csv, results/model_comparison.csv, results/recommendations_*.parquet, results/item_neighbors_*.parquet, reports/figures/ (biểu đồ so sánh mô hình, RMSE theo mức điểm), reports/evidence/stage_P7.md.

TIÊU CHÍ ĐẠT: lựa chọn tham số chỉ dựa trên validation; bảng so sánh có đủ 3 baseline và ALS cho cả hai bộ; có phân tích nguyên nhân; không có số liệu đối chiếu bài báo bịa đặt.
````

**Cổng kiểm tra P7:** `model_comparison.csv` có cả baseline và ALS cho hai bộ. Phần phân tích trung thực (nếu ALS thua baseline thì ghi rõ). Mọi số trong biên bản truy ra được từ file kết quả.

---

## P8. K-means: phân tích hành vi

````markdown
Đọc docs/CONTEXT.md và các biên bản P1 đến P7 trước.

NHIỆM VỤ: phân cụm hành vi bằng K-means (Spark MLlib), chỉ dùng dữ liệu TRAIN (hoặc toàn bộ dữ liệu sạch, ghi rõ chọn cái nào và lý do) để tránh rò rỉ khi dùng chung với ALS.

Phần 1. Phân cụm người dùng
- Đặc trưng người dùng (tính bằng Spark):
  - Food.com: số đánh giá, điểm trung bình, độ lệch chuẩn điểm, tỷ lệ điểm cao (>=4), thời gian nấu trung bình và calo trung bình của món đã đánh giá, số nguyên liệu trung bình, khoảng thời gian hoạt động (ngày).
  - ViFoodRec: số đánh giá, điểm trung bình, độ lệch chuẩn, tỷ lệ món mặn/chay được chấm cao, calo trung bình và thời gian nấu trung bình của món được chấm cao.
- Xử lý lệch: áp dụng log1p cho các biến đếm, rồi chuẩn hóa (StandardScaler).
- Chọn số cụm k: Food.com thử k từ 2 đến 8, ViFoodRec (khoảng 100 user) thử k từ 2 đến 5. Tính Silhouette (ClusteringEvaluator) và chi phí WSSSE cho mỗi k, vẽ biểu đồ. Chọn k theo quy tắc: Silhouette cao và cụm đủ lớn (không cụm nào nhỏ hơn 3% số user), cụm diễn giải được. Ghi rõ lý do chọn.
- Hồ sơ cụm: kích thước, giá trị trung bình từng đặc trưng (so với trung bình toàn bộ), món tiêu biểu của cụm (top món được chấm cao trong cụm), đặt tên cụm bằng tiếng Việt dễ hiểu dựa trên số liệu thật.

Phần 2. Phân cụm món ăn (ViFoodRec)
- Đặc trưng món: calo, protein, chất béo, đường, thời gian nấu, loại món (mã hóa), số nguyên liệu. Chuẩn hóa, chọn k như trên (k từ 2 đến 8), mô tả cụm bằng ví dụ món thật.

Phần 3. Trực quan hóa: giảm chiều bằng PCA (Spark MLlib) xuống 2 chiều trên một mẫu tối đa 20.000 điểm, vẽ phân tán theo cụm; biểu đồ cột hồ sơ cụm.

ĐẦU RA: src/user_features.py, src/kmeans_behavior.py, results/user_clusters_<bộ>.parquet (user_id, cluster, nhãn), results/cluster_profiles_<bộ>.csv, results/food_clusters_vietnam.parquet, biểu đồ trong reports/figures/, reports/evidence/stage_P8.md (mỗi nhận xét về cụm kèm số thật).

TIÊU CHÍ ĐẠT: có bảng Silhouette và WSSSE theo k; lý do chọn k rõ ràng; mỗi cụm có tên và số liệu hồ sơ; không cụm nào quá nhỏ mà không giải thích.
````

**Cổng kiểm tra P8:** tên cụm phải khớp với số liệu trong hồ sơ (ví dụ cụm "thích món nhanh" thì thời gian nấu TB phải thấp hơn trung bình).

---

## P9. Thực nghiệm mở rộng quy mô

````markdown
Đọc docs/CONTEXT.md và các biên bản P1 đến P8 trước.

NHIỆM VỤ: đo khả năng mở rộng của pipeline trên Food.com (bộ dữ liệu lớn) để chứng minh yêu cầu "Big Data".

Thiết kế thí nghiệm:
- Mẫu dữ liệu: lấy mẫu THEO NGƯỜI DÙNG (không lấy mẫu theo dòng, để giữ nguyên lịch sử mỗi người) với tỷ lệ 10%, 25%, 50%, 100%, seed cố định. Với mỗi tỷ lệ ghi số dòng, user, món thực tế.
- Với mỗi tỷ lệ chạy: (i) đọc dữ liệu sạch và tính thống kê tổng hợp, (ii) huấn luyện ALS với tham số cố định (tham số tốt nhất ở P7), (iii) huấn luyện K-means với k đã chọn ở P8.
- Biến số tài nguyên: nếu cụm chạy: 1 worker so với 2 worker. Nếu ở chế độ local: local[1], local[2], local[4].
- Mỗi cấu hình chạy 2 lần, ghi thời gian từng lần và trung bình; đo bằng time.perf_counter quanh một action thật. Ghi cấu hình tài nguyên và thời điểm đo. Ghi RMSE của ALS ở mỗi tỷ lệ để xem chất lượng có ổn định không.
- Tận dụng kết quả storage_benchmark ở P4 làm một phần của kết luận.

ĐẦU RA: src/scalability_experiment.py, results/scalability.csv (cột: tỷ lệ mẫu, số dòng, tài nguyên, bước, thời gian lần 1, thời gian lần 2, trung bình, RMSE), biểu đồ đường thời gian theo kích thước dữ liệu và theo tài nguyên, reports/evidence/stage_P9.md với kết luận trung thực: thời gian tăng gần tuyến tính hay không, thêm worker có giúp không và vì sao (nếu không giúp hoặc giúp ít, nêu nguyên nhân, ví dụ dữ liệu quá nhỏ so với chi phí phối hợp).

TIÊU CHÍ ĐẠT: đủ 4 mức dữ liệu; có số đo lặp; kết luận bám theo số đo thật, không khẳng định "mở rộng tuyến tính" nếu số liệu không cho thấy.
````

**Cổng kiểm tra P9:** `scalability.csv` đủ dòng, thời gian tăng theo kích thước dữ liệu có thể giải thích được. Kết luận không nói quá so với số đo.

---

## P10. Xuất kết quả cho dashboard (hợp đồng dữ liệu)

````markdown
Đọc docs/CONTEXT.md và các biên bản P1 đến P9 trước.

NHIỆM VỤ: gom mọi kết quả cần cho dashboard thành các file nhỏ trong app/data/ (copy từ HDFS về máy khi cần), để Streamlit đọc bằng pandas mà KHÔNG cần Spark.

Danh sách bắt buộc (mỗi file Parquet hoặc CSV, tổng dung lượng app/data dưới 100MB):
1. foods_vietnam.parquet và recipes_foodcom_sample.parquet: thông tin món (id, tên, loại, calo, dinh dưỡng, thời gian nấu, nguyên liệu dạng chuỗi hiển thị).
2. recommendations_vietnam.parquet (mọi user) và recommendations_foodcom_sample.parquet (5.000 user mẫu).
3. item_neighbors_vietnam.parquet và item_neighbors_foodcom.parquet.
4. user_clusters_*.parquet, cluster_profiles_*.csv, food_clusters_vietnam.parquet.
5. eda tables: thống kê tổng quan mỗi bộ, phân phối điểm, phân phối đánh giá mỗi user và món, xu hướng theo tháng (Food.com).
6. model_comparison.csv, als_tuning_*.csv, scalability.csv, storage_benchmark.csv, cleaning_log.csv.

Viết docs/data_contract.md: bảng mô tả từng file (đường dẫn, cột, kiểu, ý nghĩa, số dòng thật). Viết src/export_for_app.py thực hiện việc xuất, và src/verify_export.py kiểm tra: đủ file, đúng cột, không rỗng, khóa nối (id) khớp giữa các file, tổng dung lượng dưới 100MB.

TIÊU CHÍ ĐẠT: verify_export.py chạy ĐẠT; data_contract.md khớp file thật; không file nào chứa dữ liệu thô nhạy cảm hoặc văn bản review.
````

**Cổng kiểm tra P10:** thư mục `app/data/` có đủ file; `verify_export.py` ĐẠT.

---

## P11. Dashboard Streamlit

````markdown
Đọc docs/CONTEXT.md, docs/data_contract.md và các biên bản trước đó.

NHIỆM VỤ: xây dựng ứng dụng Streamlit (thư mục app/) đọc dữ liệu từ app/data/ bằng pandas, KHÔNG gọi Spark khi chạy (để demo không phụ thuộc cụm). Giao diện tiếng Việt. Ghim phiên bản thư viện trong app/requirements.txt.

Cấu trúc 4 trang (multipage) kèm bộ chọn bộ dữ liệu (mặc định ViFoodRec) ở thanh bên:
1. Tổng quan: số liệu chính hai bộ dữ liệu, sơ đồ kiến trúc thật của hệ thống (đúng với cụm hoặc local đã dựng), kết quả làm sạch (cleaning_log), so sánh CSV với Parquet.
2. Hành vi người dùng: biểu đồ các cụm (PCA), hồ sơ từng cụm, món tiêu biểu mỗi cụm, xu hướng theo thời gian (Food.com), cụm món ăn (ViFoodRec).
3. Gợi ý món: hai chế độ.
   a) Chọn người dùng có sẵn: hiển thị Top-N gợi ý (số N chọn được) kèm tên món, loại, calo, thời gian nấu, nguyên liệu; bộ lọc theo loại món, thời gian nấu tối đa, calo tối đa.
   b) Người dùng mới (cold-start): chọn 3 đến 5 món yêu thích, hệ thống gợi ý các món gần nhất dựa trên độ tương đồng giữa các món (item_neighbors) và hiển thị lý do ("giống món X vì...").
4. Đánh giá mô hình: bảng baseline với ALS, RMSE theo mức điểm, kết quả tuning, biểu đồ mở rộng quy mô.

Yêu cầu giao diện: mỗi biểu đồ có tiêu đề, chú thích đơn vị và 1 câu kết luận ngắn dựa trên số liệu thật (đọc từ file, không gõ cứng); dùng st.cache_data; xử lý trường hợp không có dữ liệu với thông báo rõ; không có lỗi đỏ trên màn hình.

Kiểm thử: dùng streamlit.testing.v1.AppTest để chạy thử từng trang và từng chế độ gợi ý, xác nhận không có exception; lưu log kiểm thử vào reports/evidence/. Nếu có thể dùng trình duyệt, chụp ảnh màn hình mỗi trang lưu vào reports/figures/screenshots/.

Cách chạy: thêm dịch vụ streamlit vào docker-compose (cổng 8501) hoặc chỉ dẫn chạy trực tiếp trên máy; nêu rõ lệnh trong README.

ĐẦU RA: app/ (main app, pages, utils), app/requirements.txt, reports/evidence/stage_P11.md.

TIÊU CHÍ ĐẠT: AppTest không lỗi; mọi số trên dashboard khớp file kết quả; chế độ cold-start trả về gợi ý hợp lý cho ít nhất 3 bộ món chọn thử.
````

**Cổng kiểm tra P11 (bạn tự làm):** chạy ứng dụng, thử cả hai chế độ gợi ý, chọn thử 3 món rồi xem gợi ý có hợp lý (ví dụ chọn món chay thì gợi ý có món chay không). Đọc kỹ các câu kết luận dưới biểu đồ, so với số liệu.

---

## P12. Tổng kiểm tra, README và đóng băng code

````markdown
Đọc docs/CONTEXT.md và mọi biên bản stage_*.md trước.

NHIỆM VỤ: tổng kiểm tra toàn bộ dự án theo hướng người ngoài chạy lại được.

1. Viết một script chạy toàn bộ pipeline (run_all.ps1 cho PowerShell) theo thứ tự: khởi động cụm, nạp dữ liệu, làm sạch, verify, benchmark lưu trữ, EDA, split, baseline, ALS, K-means, thực nghiệm mở rộng, xuất kết quả, kiểm tra xuất. Có tham số để bỏ qua các bước nặng đã chạy.
2. Chạy thử TỪ TRẠNG THÁI SẠCH: xóa data/processed, results, app/data (đã sao lưu), chạy run_all.ps1, xác nhận ra kết quả như cũ (sai khác nhỏ ở thời gian là chấp nhận được, RMSE phải giống nhau do seed cố định). Ghi nhật ký chạy.
3. Viết README.md: mô tả dự án, kiến trúc (đúng thực tế), yêu cầu máy, cách cài đặt, cách chạy từng bước và chạy tất cả, cách mở dashboard, cấu trúc thư mục, nguồn dữ liệu và giấy phép, hạn chế đã biết. Bản requirements.txt tổng hợp. Docker image đều ghim phiên bản.
4. Tạo reports/evidence/STATUS.md: bảng từng hạng mục (hạ tầng, làm sạch, benchmark, EDA, baseline, ALS, K-means, mở rộng, dashboard) với trạng thái "ĐÃ CHẠY VÀ KIỂM CHỨNG" hoặc "CHƯA ĐẠT" kèm bằng chứng (đường dẫn file). Liệt kê trung thực mọi hạn chế và điểm chưa làm được.
5. Rà soát: tìm mọi chỗ trong tài liệu và mã còn mô tả khác thực tế (ví dụ nói HDFS nhưng chạy local), mọi số liệu không truy được về file kết quả. Sửa hoặc đánh dấu.
6. Tạo danh sách 15 câu hỏi phản biện giảng viên có thể hỏi về mã và kết quả, kèm câu trả lời ngắn dựa trên kết quả thật, lưu docs/Q_and_A.md.
7. git commit với thông điệp rõ ràng và gắn tag "code-freeze".

TIÊU CHÍ ĐẠT: chạy sạch từ đầu thành công theo README; STATUS.md không còn mục nào "chưa kiểm chứng" mà không giải thích; Q_and_A.md có số liệu thật.
````

**Cổng kiểm tra P12 (bạn tự làm):** làm theo README trên một thư mục sạch (hoặc nhờ bạn cùng nhóm làm thử). Sau mốc này **không sửa mã** trừ lỗi nghiêm trọng.

---

## 14. Prompt dùng chung khi Gemini làm chưa đạt

### 14.1. Prompt sửa lỗi

````markdown
Đọc docs/CONTEXT.md và reports/evidence/stage_<mã>.md trước.

Tôi kiểm tra và thấy tiêu chí sau CHƯA ĐẠT: <dán nguyên văn mục chưa đạt và triệu chứng, kèm lệnh chạy và kết quả tôi thấy>.

Hãy:
1. Tìm nguyên nhân gốc (không đoán), chạy lệnh để xác nhận và dán kết quả.
2. Sửa tối thiểu cần thiết, không đụng phần đã đạt.
3. Chạy lại phần liên quan và dán kết quả thật.
4. Cập nhật stage_<mã>.md: ghi rõ lần sửa này sửa gì, vì sao.
Nếu không sửa được, nói rõ và nêu các lựa chọn, đừng giả vờ đã xong.
````

### 14.2. Prompt kiểm toán chéo (dùng khi nghi ngờ Gemini nói quá)

````markdown
Đọc docs/CONTEXT.md và reports/evidence/stage_<mã>.md.

Hãy đóng vai người kiểm tra độc lập. Với MỖI con số và MỖI khẳng định trong biên bản này:
1. Chỉ ra file kết quả hoặc log nguồn chứa con số đó.
2. Tự chạy lại một truy vấn hoặc lệnh kiểm tra độc lập để xác nhận.
3. Gắn nhãn: XÁC NHẬN / KHÔNG KHỚP / KHÔNG TRUY ĐƯỢC NGUỒN.
Liệt kê mọi khẳng định bị gắn KHÔNG KHỚP hoặc KHÔNG TRUY ĐƯỢC NGUỒN và sửa biên bản cho đúng thực tế.
````

### 14.3. Khi nào nên gửi lại cho Claude xem

- Gemini báo "xong" nhưng bạn không hiểu kết quả hoặc con số có vẻ lạ.
- ALS thua baseline, hoặc Silhouette thấp bất thường.
- Cụm HDFS lỗi lặp lại và không rõ phải chuyển sang dự phòng chưa.
- Cần chuẩn bị số liệu và nội dung để viết báo cáo (làm sau cùng).

Khi gửi, đính kèm các file `reports/evidence/stage_*.md` liên quan.

---

## 15. Lưu ý quan trọng

1. **Đừng để Gemini viết báo cáo lúc này.** Báo cáo Word và slide làm sau khi code đã đóng băng, dùng số liệu từ `reports/evidence/` và `results/`.
2. **Dùng AI hỗ trợ là được, nhưng cả hai bạn phải hiểu.** Mỗi biên bản có phần "Điểm cần hiểu để trả lời phản biện". Hãy đọc và tập trả lời, vì giảng viên sẽ hỏi cả hai người.
3. **Kết quả xấu vẫn nộp được.** Nếu ALS thua baseline hay K-means cho cụm yếu, giữ kết quả thật và phân tích nguyên nhân. Giảng viên chấm cả khả năng giải thích.
4. **Giữ dữ liệu và mã nguồn phù hợp giấy phép.** Trích nguồn ViFoodRec và Food.com đầy đủ khi viết báo cáo.

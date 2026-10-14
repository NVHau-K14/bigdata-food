# BIÊN BẢN NGHIỆM THU GIAI ĐOẠN P4: THỰC NGHIỆM LƯU TRỮ VÀ HIỆU NĂNG (CSV VS PARQUET CÔNG BẰNG)

- **Thời gian thực hiện:** 13/10/2026
- **Môi trường thực nghiệm:** Cụm phân tán Apache Spark 4.2.0 Standalone (1 Master, 2 Workers: 4 Cores, 7 GB RAM, Driver 2.5 GB RAM) trên nền tảng lưu trữ phân tán HDFS 3.3.6 (`hdfs://namenode:9000/`).
- **Trạng thái giai đoạn:** **HOÀN THÀNH TOÀN DIỆN (ĐẠT 100% TIÊU CHÍ NGHIỆM THU)**

---

## 1. Danh sách file tạo mới và chỉnh sửa

| STT | Đường dẫn file | Thao tác | Mục đích |
|---|---|---|---|
| 1 | `src/storage_benchmark.py` | Tạo mới | Kịch bản thực nghiệm đo lường lưu trữ và hiệu năng truy vấn công bằng giữa CSV và Parquet trên cùng nội dung. |
| 2 | `data/results/storage_benchmark.csv` | Tạo mới | Bảng số liệu đo lường thực tế cả 3 thí nghiệm A, B, C (dung lượng MB, thời gian TB, độ lệch chuẩn). |
| 3 | `reports/figures/storage_benchmark.png` | Tạo mới | Biểu đồ cột kép so sánh dung lượng (MB) và thời gian truy vấn (Latency kèm thanh sai số $\pm \sigma$). |
| 4 | `reports/evidence/stage_P4.md` | Tạo mới | Biên bản nghiệm thu P4 với phân tích phân rã trung thực, minh bạch. |

---

## 2. Bảng kết quả thực nghiệm đo lường thực tế (Thí nghiệm A, B, C)

Trích xuất nguyên văn từ [data/results/storage_benchmark.csv](file:///d:/Documents/BaiTap/BigData/bigdata-food/data/results/storage_benchmark.csv):

| Thí nghiệm | Tập dữ liệu / Truy vấn | Định dạng | Dung lượng (MB) | Thời gian TB (giây) | Độ lệch chuẩn $\sigma$ (giây) | Tỷ lệ nén / Tốc độ vượt trội | Ghi chú kỹ thuật |
|---|---|:---:|:---:|:---:|:---:|:---:|---|
| **Thí nghiệm A** *(Dữ liệu thô đầy đủ)* | Food.com `RAW_interactions` | CSV | 333.25 | — | — | Baseline | 1,132,367 dòng, giữ 100% cột (kể cả review text) |
| **Thí nghiệm A** *(Dữ liệu thô đầy đủ)* | Food.com `RAW_interactions` | Parquet | 189.79 | — | — | **Nén 1.76x** (giảm 43.1%) | Giữ nguyên 100% cột và dòng thô, nén Snappy thuần túy |
| **Thí nghiệm A** *(Dữ liệu thô đầy đủ)* | Food.com `RAW_recipes` | CSV | 280.88 | — | — | Baseline | 231,637 dòng, giữ 100% cột (kể cả steps, description) |
| **Thí nghiệm A** *(Dữ liệu thô đầy đủ)* | Food.com `RAW_recipes` | Parquet | 120.25 | — | — | **Nén 2.34x** (giảm 57.2%) | Giữ nguyên 100% cột và dòng thô, nén Snappy thuần túy |
| **Thí nghiệm B** *(Dữ liệu đã làm sạch)* | Food.com `interactions_clean` | CSV | 19.11 | — | — | Baseline sạch | 706,514 dòng sạch, 4 cột (đã bỏ review) |
| **Thí nghiệm B** *(Dữ liệu đã làm sạch)* | Food.com `interactions_clean` | Parquet | 4.56 | — | — | **Nén 4.19x** (giảm 76.1%) | Cùng 706,514 dòng sạch, 4 cột số/ngày |
| **Thí nghiệm B** *(Dữ liệu đã làm sạch)* | Food.com `recipes_clean` | CSV | 124.92 | — | — | Baseline sạch | 231,636 dòng sạch, 18 cột (đã bỏ steps/desc) |
| **Thí nghiệm B** *(Dữ liệu đã làm sạch)* | Food.com `recipes_clean` | Parquet | 17.78 | — | — | **Nén 7.03x** (giảm 85.8%) | Cùng 231,636 dòng sạch, 18 cột (nén mảng và số) |
| **Thí nghiệm C** *(Hiệu năng truy vấn)* | Q1: Đếm dòng (Full Scan) | CSV | 19.11 | 0.508 | ±0.104 | Baseline | Scan toàn bộ text CSV và đếm dòng |
| **Thí nghiệm C** *(Hiệu năng truy vấn)* | Q1: Đếm dòng (Full Scan) | Parquet | 4.56 | **0.296** | **±0.043** | **Nhanh gấp 1.71x** | Đọc metadata footer & row groups |
| **Thí nghiệm C** *(Hiệu năng truy vấn)* | Q2: GroupBy Rating (Aggregation) | CSV | 19.11 | 0.697 | ±0.099 | Baseline | Parse text -> float -> hash aggregate 78K món |
| **Thí nghiệm C** *(Hiệu năng truy vấn)* | Q2: GroupBy Rating (Aggregation) | Parquet | 4.56 | **0.338** | **±0.005** | **Nhanh gấp 2.06x** | Đọc nhị phân theo cột, vectorize scan |
| **Thí nghiệm C** *(Hiệu năng truy vấn)* | Q3: Chiếu 3 cột (Column Pruning) | CSV | 19.11 | 0.507 | ±0.102 | Baseline | Phải duyệt qua tất cả cột text để tách trường |
| **Thí nghiệm C** *(Hiệu năng truy vấn)* | Q3: Chiếu 3 cột (Column Pruning) | Parquet | 4.56 | **0.281** | **±0.012** | **Nhanh gấp 1.80x** | Bỏ qua hoàn toàn dữ liệu các cột không dùng |

*Ghi chú đo lường Thí nghiệm C:* Mỗi truy vấn được thực thi 4 lần liên tiếp. Lần 1 (Warm-up) bị loại bỏ để tránh ảnh hưởng của việc biên dịch JVM/JIT và nạp kết nối. Thời gian trung bình và độ lệch chuẩn $\sigma$ được tính toán trên 3 lần chạy thực tế tiếp theo.

---

## 3. Biểu đồ trực quan hóa kết quả thực nghiệm

Biểu đồ độ phân giải cao đã được tạo tại [reports/figures/storage_benchmark.png](file:///d:/Documents/BaiTap/BigData/bigdata-food/reports/figures/storage_benchmark.png):

![Biểu đồ so sánh lưu trữ và hiệu năng CSV vs Parquet](file:///d:/Documents/BaiTap/BigData/bigdata-food/reports/figures/storage_benchmark.png)

---

## 4. Phân tích phân rã trung thực: Đập tan ngụy biện "Parquet nén 60 lần"

Trong báo cáo cũ trước đây, có kết luận: *"Parquet nén dữ liệu nhỏ hơn CSV đến 60 lần"*. Qua thực nghiệm P4 trên cùng một tập dữ liệu chuẩn, chúng ta đã chứng minh kết luận đó là **hoàn toàn sai lầm về mặt phương pháp luận** (so sánh bất bình đẳng giữa hai tập dữ liệu khác nhau về cả số dòng lẫn số cột).

Phân tích phân rã chính xác quá trình giảm dung lượng của `interactions` (từ 333.25 MB xuống 4.56 MB, giảm tổng cộng **73.08 lần**):

```text
========================================================================================================
              PHÂN RÃ NGUỒN GỐC GIẢM DUNG LƯỢNG TRONG QUÁ TRÌNH LƯU TRỮ (INTERACTIONS)
========================================================================================================

  [1] RAW_interactions.csv (Dữ liệu thô ban đầu)
      - Dung lượng: 333.25 MB (1,132,367 dòng, 5 cột gồm cột văn bản tự do review)
            │
            │  LÀM SẠCH DỮ LIỆU (Data Cleaning - Giai đoạn P3):
            │  - Lược bỏ cột văn bản dài `review` (chiếm ~85% dung lượng text)
            │  - Lọc bỏ 60,847 tương tác rating = 0
            │  - Lọc 365,006 tương tác qua 5 vòng lặp K-core (K=3)
            ▼
  [2] interactions_clean.csv (Dữ liệu đã làm sạch - lưu dạng CSV)
      - Dung lượng: 19.11 MB (706,514 dòng, 4 cột số và ngày)
      ==> GIẢM 314.14 MB (GIẢM 94.27% DUNG LƯỢNG) HOÀN TOÀN DO BỎ CỘT VÀ BỎ DÒNG!
            │
            │  NÉN VÀ LƯU TRỮ THEO CỘT PARQUET (Storage Format - Giai đoạn P4):
            │  - Lưu trữ dạng cột (Columnar Storage)
            │  - Mã hóa kiểu từ điển (Dictionary Encoding) + Bit-packing cho int/date
            │  - Nén khối Snappy
            ▼
  [3] interactions_clean.parquet (Dữ liệu sạch - lưu dạng Parquet)
      - Dung lượng: 4.56 MB
      ==> GIẢM TIẾP 14.55 MB (GIẢM 76.14% SO VỚI CSV SẠCH, TƯƠNG ĐƯƠNG NÉN 4.19 LẦN).
========================================================================================================
```

### Kết luận khoa học:
1. **Mức nén thực sự của định dạng Parquet Snappy thuần túy:**
   - Trên dữ liệu văn bản thô đầy đủ (Thí nghiệm A): Parquet nén **1.76 lần** (interactions) và **2.34 lần** (recipes).
   - Trên dữ liệu sạch có cấu trúc số học và ngày tháng (Thí nghiệm B): Parquet nén **4.19 lần** (interactions) và **7.03 lần** (recipes).
2. **Nguồn gốc thực sự của mức giảm 73 lần:**
   - **94.3% mức giảm** đến từ **khâu tiền xử lý (bỏ cột review dài và lọc bỏ 425,853 dòng)**.
   - **Chỉ có 4.19 lần (76.1% phần dung lượng còn lại)** là do **hiệu quả nén cột của định dạng Parquet**.
   - Việc đồng nhất toàn bộ 60-70 lần giảm dung lượng cho "công nghệ Parquet" là ngụy biện khoa học nghiêm trọng đã được sửa chữa và làm rõ dứt điểm trong biên bản này.

---

## 5. Phân tích nguyên nhân kỹ thuật về hiệu năng truy vấn (Thí nghiệm C)

1. **Tại sao Parquet nhanh hơn CSV gấp 1.7x - 2.1x?**
   - **Cấu trúc nhị phân (Binary vs Text Parsing):** Khi đọc CSV, Spark Worker phải tốn rất nhiều chu kỳ CPU để parse từng dòng text, tách chuỗi qua dấu phẩy, kiểm tra ký tự escape `\"` và ép kiểu từ String sang Float/Integer. Với Parquet, dữ liệu đã được lưu trữ sẵn ở dạng nhị phân theo kiểu nguyên thủy, nạp trực tiếp vào bộ nhớ RAM qua CPU Vectorized Reader.
   - **Column Pruning (Chiếu chọn theo cột):** Trong truy vấn Q3 (chỉ đọc 3 cột), Parquet chỉ quét đúng các cột cần thiết trên đĩa HDFS và bỏ qua hoàn toàn các cột khác. Trong khi đó, định dạng CSV dạng dòng (Row-oriented) bắt buộc phải đọc qua toàn bộ độ dài của tất cả các cột trên mỗi dòng.
   - **Giới hạn song song của CSV đa dòng (MultiLine Split Barrier):** File CSV chứa dữ liệu đa dòng (`multiLine=True`) không thể được Hadoop chia nhỏ thành nhiều InputSplit độc lập tại các ranh giới block 128MB (vì một dòng có thể bị cắt ngang giữa 2 block). Điều này buộc Spark phải đọc tuần tự hoặc chịu chi phí shuffle cao, trong khi Parquet hỗ trợ chia nhỏ hoàn hảo theo các Row Group độc lập trên từng DataNode.

---

## 6. Điểm cần hiểu để trả lời phản biện (Hội đồng / Giảng viên)

**Câu hỏi 1: Tại sao trong Thí nghiệm A khi nén RAW_interactions (có cột review) thì Parquet chỉ nén được 1.76 lần, nhưng ở Thí nghiệm B trên interactions sạch thì nén được 4.19 lần?**
- *Trả lời:*
  - Cột `review` là văn bản tự do bằng tiếng Anh có độ biến thiên từ vựng rất cao (high cardinality text, ít từ lặp lại liên tiếp). Do đó, thuật toán Dictionary Encoding và RLE của Parquet không thể nén hiệu quả cao đối với văn bản tự do, chỉ dựa vào thuật toán nén khối Snappy nên đạt tỷ lệ ~1.76x.
  - Ngược lại, bảng `interactions_clean` chỉ gồm 4 cột số và ngày (`user_id`, `recipe_id`, `date`, `rating`). Cột `rating` chỉ có 5 giá trị duy nhất (1.0 đến 5.0), cột `date` lặp lại liên tục, cột `user_id` và `recipe_id` là số nguyên liên tiếp. Parquet áp dụng Dictionary Encoding, Bit-Packing và Run-Length Encoding cực kỳ tối ưu cho các kiểu số có miền giá trị hẹp, giúp tỷ lệ nén vọt lên 4.19x.

**Câu hỏi 2: Có phải định dạng Parquet luôn luôn vượt trội hơn CSV trong mọi trường hợp không? Khi nào thì nên dùng CSV?**
- *Trả lời:* Parquet vượt trội áp đảo CSV trong các bài toán Big Data phân tích (OLAP), huấn luyện máy học và lưu trữ kho dữ liệu vì dung lượng nhỏ, đọc nhanh và hỗ trợ schema phân cấp. Tuy nhiên, CSV vẫn có giá trị trong các trường hợp: (1) Dữ liệu trao đổi dung lượng nhỏ giữa các hệ thống phi công nghệ (kế toán, báo cáo Excel); (2) Người dùng cần mở xem ngay bằng các trình soạn thảo văn bản đơn giản (Notepad) mà không cần công cụ chuyên dụng; (3) Dữ liệu log streaming dạng dòng đơn giản trước khi được batch ETL vào Data Lake.

**Câu hỏi 3: Tại sao trong Thí nghiệm C nhóm lại phải chạy 4 lần, bỏ lần đầu (Warm-up) và tính độ lệch chuẩn?**
- *Trả lời:* Trong môi trường Java Virtual Machine (JVM) của Apache Spark và cụm Docker:
  - Lần chạy đầu tiên (Cold Run) luôn bị chậm hơn đáng kể do JVM phải nạp lớp (Class Loading), trình biên dịch JIT (Just-In-Time) phải dịch bytecode sang mã máy, thiết lập kết nối RPC giữa Driver và 2 Executor, và OS File Cache chưa được nạp.
  - Ba lần chạy tiếp theo (Warm Runs) phản ánh đúng tốc độ thực tế của công cụ tính toán khi đã hoạt động ổn định.
  - Việc tính độ lệch chuẩn $\sigma$ chứng minh tính ổn định của cụm và đảm bảo kết quả đo lường là đáng tin cậy, khoa học chứ không phải ngẫu nhiên.

# KẾ HOẠCH VÀ HƯỚNG DẪN THỰC HIỆN ĐỒ ÁN NHẬP MÔN BIG DATA

**Đề tài:** Phân tích hành vi ăn uống và gợi ý món ăn
**Nhóm:** 2 sinh viên (Thành viên A, Thành viên B)
**Căn cứ:** *Yêu cầu chung và kế hoạch thực hiện đồ án* do giảng viên cung cấp
**Phiên bản:** 1.0. File này chỉ gồm kế hoạch và hướng dẫn, **không chứa code**. Phần code sẽ làm ở file `.md` riêng.

---

## 0. Bối cảnh và giả định

| Hạng mục | Nội dung |
|---|---|
| Đề tài | Tự đề xuất, **đã được giảng viên duyệt** |
| Số thành viên | 2 |
| Tiến độ hiện tại | Chưa bắt đầu thực hiện |
| Thời gian còn lại | **7 ngày** đến hạn nộp và thuyết trình. Có thể dời thêm 1 tuần do lớp đông, lớp sẽ bù thêm một buổi |
| Máy tính | RAM 24GB (đủ để chạy Docker gồm HDFS và Spark) |
| Cách làm code | Chủ yếu AI hỗ trợ, nhóm phải **hiểu và giải thích được** mọi đoạn code (xem mục 9) |

**Cách dùng kế hoạch này:** lịch chính là 7 ngày. Nếu thuyết trình được dời, 1 đến 2 ngày thêm vào sẽ là **ngày đệm** (mục 5.2), dùng để sửa lỗi và làm phần mở rộng. Nhóm không nên coi đó là thời gian có sẵn khi lập kế hoạch.

> ⚠️ **Việc cần làm trong 24 giờ đầu:** hỏi lại giảng viên ngày giờ nộp bài và ngày giờ thuyết trình **chính xác**, và gửi tên hai bộ dữ liệu để xin duyệt (xem mục 13). Kế hoạch gốc yêu cầu bộ dữ liệu cũng phải được duyệt.

---

## 1. Các quyết định đã thống nhất

| Nội dung | Quyết định |
|---|---|
| Dữ liệu | **Phương án B**: ViFoodRec (món Việt, là lõi) và Food.com Recipes & Interactions (quy mô lớn, dùng để chứng minh khả năng mở rộng) |
| Quy trình | Một pipeline Spark dùng chung, chạy trên cả hai bộ |
| Mô hình | Baseline → **K-means** (phân tích hành vi) → **ALS** (gợi ý). Bỏ FP-Growth và content-based (chỉ làm nếu có ngày đệm) |
| Hạ tầng | **Docker Compose: HDFS + Spark**. Giới hạn thời gian dựng khoảng nửa ngày, nếu thất bại thì dùng PySpark local và lưu Parquet (mục 10) |
| Định dạng lưu trữ | CSV thô → Parquet (đã làm sạch) |
| Demo | **Streamlit**, đọc kết quả từ Parquet |
| Độ đo | RMSE, MAE (dự đoán điểm); Precision@K, Recall@K (xếp hạng gợi ý); Silhouette (phân cụm) |

### Vai trò của từng bộ dữ liệu

| | ViFoodRec | Food.com |
|---|---|---|
| Quy mô (theo bài báo và mô tả công bố) | Khoảng 5,5 nghìn món, khoảng 180 nghìn đánh giá | Hàng trăm nghìn công thức, hơn 1 triệu lượt đánh giá (**phải kiểm tra lại số liệu thực khi tải về**) |
| Số người dùng | Khoảng 100 | Hàng chục nghìn |
| Bản chất | Đánh giá do người được giao chấm (khảo sát) | Đánh giá do người dùng tự đưa lên mạng, có thời gian |
| Dùng để | Demo gợi ý món Việt, thực nghiệm lõi | Phân tích hành vi theo thời gian, đo hiệu năng và khả năng mở rộng |
| Điểm cần nói rõ trong báo cáo | Chỉ khoảng 100 người dùng, đánh giá không phải hành vi tự nhiên | Là ẩm thực phương Tây, không đại diện cho Việt Nam |

> **Cần trung thực:** hai bộ dữ liệu **không có người dùng chung**, nên không thể gộp hay huấn luyện chung. Báo cáo phải nói rõ lý do dùng hai bộ: ViFoodRec cho tính ứng dụng ở Việt Nam, Food.com cho yêu cầu dữ liệu lớn.

---

## 2. Ánh xạ rubric sang công việc (ưu tiên theo điểm)

| Tiêu chí (điểm) | Nhóm phải thể hiện được | Công việc chính |
|---|---|---|
| Tính ứng dụng của kỹ thuật (1.0) | Bài toán thực tế, kỹ thuật phù hợp | Phát biểu bài toán rõ, giải thích vì sao ALS và K-means hợp bài toán |
| **Lưu trữ và xử lý dữ liệu (2.0)** | HDFS, Spark, làm sạch, kiến trúc | Pipeline đầy đủ, so sánh CSV với Parquet, thống kê trước và sau làm sạch |
| **Mô hình/công nghệ (2.5)** | Mô hình đúng, tham số, đánh giá | Baseline → ALS có tuning, so sánh, phân tích hạn chế |
| **Trực quan hóa/Ứng dụng (2.5)** | Demo thể hiện giá trị từ dữ liệu | Streamlit 4 trang (mục 6, Bước 8) |
| Trình bày báo cáo (1.0) | Đúng cấu trúc, không lỗi chính tả | Theo mục 7, rà soát ở ngày 6 |
| Phân công và phối hợp (1.0) | Bảng việc từng người, minh chứng | Mục 4, nhật ký làm việc, lịch sử Git |

Mô hình, trực quan hóa và lưu trữ/xử lý chiếm tổng cộng 7.0/10 điểm. Nếu thiếu thời gian, hãy bảo vệ ba phần này trước, và đừng sa đà vào làm báo cáo cho đẹp.

---

## 3. Kiến trúc và luồng dữ liệu

```
 [CSV thô: ViFoodRec, Food.com]
            │ nạp
            ▼
 ┌──────────── HDFS ────────────┐
 │ /data/raw/...      (CSV thô) │
 │ /data/clean/...  (Parquet)   │
 │ /data/results/... (Parquet)  │
 └──────────────────────────────┘
            │ đọc/ghi
            ▼
 ┌─────── Spark (master + 2 worker) ───────┐
 │ 1. Làm sạch + tiền xử lý (DataFrame)    │
 │ 2. Phân tích khám phá (thống kê)        │
 │ 3. Đặc trưng hành vi → K-means          │
 │ 4. Baseline + ALS → đánh giá            │
 │ 5. Thực nghiệm mở rộng quy mô           │
 └─────────────────────────────────────────┘
            │ xuất kết quả (Parquet nhỏ)
            ▼
 [Streamlit: tổng quan | hành vi | gợi ý | đánh giá]
```

**Lý do chọn công nghệ (dùng cho báo cáo mục 6 và phần trả lời phản biện):**
- **HDFS:** lưu trữ phân tán, tách dữ liệu thô, dữ liệu sạch và kết quả.
- **Spark DataFrame và MLlib:** xử lý trong bộ nhớ, có sẵn ALS và K-means chạy phân tán, nhanh hơn MapReduce cho thuật toán lặp.
- **Parquet:** lưu theo cột, nén tốt, đọc nhanh hơn CSV. Nhóm sẽ đo thực tế để chứng minh.
- **Streamlit:** nhanh, dùng Python, đọc kết quả đã tính sẵn nên demo không phụ thuộc cụm Spark có đang chạy hay không.

**Cấu hình đề xuất cho máy 24GB:** cấp khoảng 12 đến 16GB cho Docker. Cụm gồm 1 namenode, 2 datanode, 1 Spark master, 2 Spark worker (mỗi worker 2 core và khoảng 3 đến 4GB) và 1 container chạy PySpark/Jupyter. Chi tiết cài đặt sẽ có trong file code riêng.

---

## 4. Phân công

| Mảng việc | Thành viên A | Thành viên B |
|---|---|---|
| Hạ tầng | Dựng Docker, HDFS, Spark (chính) | Hỗ trợ kiểm tra |
| Dữ liệu | ViFoodRec: làm sạch, thống kê | Food.com: làm sạch, thống kê |
| Mô hình | Baseline, ALS, đánh giá, so sánh với bài báo gốc | Đặc trưng hành vi, K-means, diễn giải cụm |
| Thực nghiệm mở rộng | Chạy và ghi thời gian ALS | Chạy và ghi thời gian K-means, CSV với Parquet |
| Demo | Hỗ trợ trang "Gợi ý" | Xây dựng Streamlit (chính) |
| Báo cáo Word | Mục 5, 6 (giới thiệu, lý thuyết phần ALS và HDFS) | Mục 7 (ứng dụng, trực quan hóa), phần K-means |
| Slide và thuyết trình | Nói phần hạ tầng, dữ liệu, mô hình | Nói phần hành vi, demo, kết luận |

**Quy tắc phối hợp để được điểm tiêu chí "phối hợp nhóm":**
- Dùng một kho Git chung, mỗi người commit riêng. Lịch sử commit là minh chứng đóng góp.
- Họp ngắn 15 phút mỗi tối: hôm nay làm được gì, ngày mai làm gì, có bị kẹt không.
- Ghi **nhật ký làm việc thật** vào một file (ngày, người, việc, kết quả). Phần "lịch làm việc hàng tuần" trong báo cáo lấy từ đây. Chỉ ghi những gì đã xảy ra, không viết bù cho các tuần trước.

---

## 5. Lịch thực hiện 7 ngày

### 5.1 Lịch chính

#### Ngày 1: Nền móng
| | Việc cần làm |
|---|---|
| **A** | Dựng Docker (HDFS + Spark). **Giới hạn thời gian 4 giờ.** Mục tiêu: Spark đọc được một file từ HDFS. Nếu hết thời gian mà chưa xong, chuyển sang phương án dự phòng (mục 10) |
| **B** | Tải ViFoodRec (kho GitHub của bài báo) và Food.com (Kaggle). Mở từng file xem cột, số dòng, dung lượng. Kiểm tra giấy phép sử dụng của từng bộ |
| **Cả hai** | Gửi giảng viên email xin duyệt bộ dữ liệu. Tạo kho Git, cấu trúc thư mục. Bắt đầu nhật ký. Viết bản nháp mục "Giới thiệu đề tài" |
| **Sản phẩm** | Môi trường chạy được. Dữ liệu thô nằm trong HDFS. Bản nháp từ điển dữ liệu (tên cột, ý nghĩa, kiểu) |
| **Đạt khi** | Chạy được một lệnh Spark đọc dữ liệu từ HDFS và in ra số dòng |

#### Ngày 2: Làm sạch và khám phá dữ liệu
| | Việc cần làm |
|---|---|
| **A** | Làm sạch ViFoodRec (xem Bước 3). Ghi số dòng trước và sau mỗi thao tác |
| **B** | Làm sạch Food.com, phân tích khám phá theo thời gian và người dùng |
| **Sản phẩm** | Dữ liệu sạch dạng Parquet trên HDFS. Bảng thống kê trước và sau làm sạch. Khoảng 8 đến 10 biểu đồ khám phá |
| **Đạt khi** | Có file Parquet đọc lại được, số dòng khớp với bảng thống kê |
| **Báo cáo** | Viết nháp phần mô tả dữ liệu |

#### Ngày 3: Baseline và đặc trưng hành vi
| | Việc cần làm |
|---|---|
| **A** | Chia tập huấn luyện và kiểm tra. Cài 3 baseline. Viết khung đánh giá dùng chung (RMSE, MAE, Precision@K) |
| **B** | Xây đặc trưng hành vi cho người dùng, chạy K-means, chọn số cụm |
| **Sản phẩm** | Bảng kết quả baseline. Kết quả K-means kèm Silhouette |
| **Báo cáo** | Viết lý thuyết ngắn: HDFS, Spark, ALS, K-means (có ví dụ minh họa nhỏ) |

#### Ngày 4: ALS và diễn giải cụm
| | Việc cần làm |
|---|---|
| **A** | ALS trên ViFoodRec, tuning tham số, so sánh với baseline và với số liệu bài báo gốc |
| **B** | Diễn giải từng cụm hành vi, đặt tên cụm, vẽ hồ sơ cụm. Bắt đầu khung Streamlit |
| **Sản phẩm** | Bảng so sánh mô hình. Hồ sơ các cụm người dùng |
| **Đạt khi** | ALS tốt hơn baseline ít nhất trên một độ đo. Nếu không, vẫn ghi lại và phân tích nguyên nhân (xem Bước 7) |

#### Ngày 5: Mở rộng quy mô và hoàn thiện demo
| | Việc cần làm |
|---|---|
| **A** | Chạy ALS trên Food.com ở các mức dữ liệu (10%, 50%, 100%) và ghi thời gian |
| **B** | Hoàn thiện Streamlit. Chạy K-means trên Food.com. So sánh thời gian đọc CSV và Parquet |
| **Sản phẩm** | Bảng thực nghiệm mở rộng. Demo chạy được từ đầu đến cuối |
| **Đạt khi** | Demo chạy được mà không cần mở Spark |

#### Ngày 6: Hoàn thiện báo cáo và slide, đóng băng code
| | Việc cần làm |
|---|---|
| **Cả hai** | Hoàn thành báo cáo Word theo mục 7 và slide theo mục 8. Chốt số liệu, đối chiếu bảng với kết quả thật. Viết hướng dẫn cài đặt và chạy. Rà chính tả |
| **Quy tắc** | **Sau ngày này không sửa code**, trừ lỗi nghiêm trọng. Không thay đổi số liệu đã đưa vào báo cáo |

#### Ngày 7: Tổng duyệt và nộp bài
| | Việc cần làm |
|---|---|
| **Cả hai** | Chạy thử toàn bộ theo hướng dẫn trên môi trường sạch. Tập thuyết trình 2 lượt có bấm giờ. Luyện trả lời câu hỏi (mục 9). Quay **video demo dự phòng**. Nộp Classroom: source code, file Word, file PPT |

### 5.2 Ngày đệm (nếu thuyết trình dời thêm 1 tuần)

Chỉ dùng khi toàn bộ lịch chính đã xong. Ưu tiên theo thứ tự:
1. Sửa các điểm yếu mà phần tự đánh giá ở ngày 7 phát hiện.
2. Thêm FP-Growth trên nguyên liệu (món hay đi kèm nhau).
3. Thêm gợi ý dựa trên nội dung (nguyên liệu, dinh dưỡng) để xử lý người dùng mới.
4. Tập thuyết trình thêm, thử chạy demo trên máy trình chiếu.

---

## 6. Hướng dẫn theo 9 bước yêu cầu của giảng viên

Chín bước dưới đây tương ứng với mục "Về nội dung thực hiện" trong file yêu cầu.

### Bước 1. Xác định bài toán, phạm vi, đầu vào và đầu ra

- **Bài toán:** phân tích cách người dùng đánh giá món ăn để (1) nhóm họ theo hành vi và (2) gợi ý món phù hợp.
- **Đầu vào:** bảng món ăn (tên, nguyên liệu, calo, thời gian nấu, loại món) và bảng đánh giá (người dùng, món, điểm).
- **Đầu ra:**
  - Các nhóm người dùng kèm mô tả đặc điểm.
  - Danh sách Top-N món gợi ý cho từng người dùng.
  - Danh sách món tương tự khi người dùng chọn vài món yêu thích.
- **Phạm vi (nói rõ trong báo cáo):** không gợi ý theo sức khỏe hay bệnh lý. Không dùng dữ liệu thời gian thực. Chỉ dùng đánh giá tường minh (điểm 0 đến 5).
- **Giá trị dự kiến:** giúp người dùng chọn món nhanh hơn, giúp nhà cung cấp hiểu nhóm khẩu vị.

### Bước 2. Thu thập, mô tả dữ liệu

Lập bảng mô tả cho mỗi bộ dữ liệu, gồm: nguồn, giấy phép, số dòng, số cột, dung lượng, định dạng, ý nghĩa từng cột.

**Gắn với đặc trưng dữ liệu lớn:** thể hiện bằng khối lượng (Food.com), tính đa dạng (văn bản nguyên liệu, số, danh mục), tính thưa của ma trận người dùng với món, và so sánh thời gian xử lý khi tăng dữ liệu.

**Việc cần kiểm tra ngay khi tải dữ liệu (ngày 1):**
- ViFoodRec có đúng 2 file `foods.csv` và `ratings.csv` như bài báo mô tả không, số dòng thực tế là bao nhiêu (bài báo nói 50.000 đánh giá thu được và khoảng 180.000 sau xử lý, hai con số này chưa khớp).
- Food.com có những file nào, cột nào, và cột `rating` có giá trị 0 hay không (cần xử lý riêng vì 0 có thể mang nghĩa khác với điểm thấp).
- Giấy phép của từng bộ. Phải trích nguồn đầy đủ trong báo cáo.

> **Lưu ý:** không sao chép mã nguồn hay kết quả của nhóm tác giả ViFoodRec. Chỉ dùng dữ liệu và trích dẫn họ. Đối chiếu số liệu với bài báo là để so sánh, không phải để chép.

### Bước 3. Khảo sát, làm sạch và tiền xử lý

**ViFoodRec: bảng món ăn**
- Kiểm tra giá trị thiếu theo từng cột, quyết định xóa hay điền.
- Loại các dòng trùng. Theo bài báo, hai món trùng cả tên, nguyên liệu và cách nấu mới coi là trùng, còn trùng tên nhưng khác nguyên liệu là món khác.
- Chuẩn hóa văn bản: chuẩn Unicode tiếng Việt, bỏ khoảng trắng thừa và emoji, sửa lỗi gõ sai thường gặp.
- Biến cột có chữ thành số: khẩu phần ("4 người" → 4), thời gian nấu (phút).
- Phát hiện giá trị ngoại lai ở calo và thời gian nấu (dùng khoảng tứ phân vị hoặc xem biểu đồ phân phối).

**ViFoodRec: bảng đánh giá**
- Kiểm tra mọi `food_id` đều có trong bảng món. Loại các dòng mồ côi.
- Kiểm tra trùng cặp (người dùng, món).
- **Kiểm tra phân phối điểm.** Tác giả bài báo đã điền một phần giá trị thiếu bằng trung vị, nên có thể có đỉnh bất thường ở một mức điểm. Nếu thấy, ghi nhận trong báo cáo như một hạn chế của dữ liệu và phân tích ảnh hưởng đến mô hình.

**Food.com**
- Loại đánh giá không hợp lệ (ví dụ điểm 0 nếu xác định đó là "không chấm điểm").
- Xử lý ngoại lai ở thời gian nấu (có công thức ghi giá trị rất lớn).
- Chuyển các cột dạng danh sách (tag, nguyên liệu, dinh dưỡng) thành cột dùng được.
- Chuẩn hóa cột ngày để phân tích theo thời gian.
- Lọc người dùng và món có quá ít đánh giá (ngưỡng tối thiểu sẽ ghi vào báo cáo) để mô hình ổn định.

**Ghi lại cho mỗi bộ dữ liệu:** bảng "trước và sau làm sạch" (số dòng, số giá trị thiếu, số trùng). Đây là minh chứng quan trọng cho tiêu chí lưu trữ và xử lý (2.0 điểm).

**Phân tích khám phá cần có (đủ để kể được câu chuyện về hành vi):**
- Phân phối điểm đánh giá, số đánh giá trên mỗi người dùng và trên mỗi món (thường có đuôi dài).
- Món phổ biến nhất và món được chấm cao nhất (hai danh sách khác nhau).
- Quan hệ giữa thời gian nấu, calo và điểm đánh giá.
- Food.com: hoạt động theo tháng, theo thứ trong tuần.
- ViFoodRec: so sánh món mặn với món chay, và nhóm thời gian nấu.

### Bước 4. Thiết kế giải pháp lưu trữ và xử lý

- **Cấu trúc thư mục HDFS:** `raw` (CSV nguyên bản, không sửa), `clean` (Parquet đã làm sạch), `results` (kết quả mô hình và bảng thống kê cho demo). Mỗi bộ dữ liệu một thư mục con riêng.
- **Quy ước:** dữ liệu thô chỉ đọc, không ghi đè. Mọi bước xử lý đọc từ thư mục trước và ghi vào thư mục sau.
- **Thực nghiệm lưu trữ cần đo:** dung lượng CSV với Parquet, thời gian đọc cùng một truy vấn trên hai định dạng, trên Food.com.
- **Sơ đồ kiến trúc:** vẽ lại mục 3 bằng công cụ vẽ (draw.io hoặc tương đương) để đưa vào báo cáo và slide.
- **Giải thích lựa chọn:** vì sao HDFS, vì sao Spark thay cho MapReduce, vì sao Parquet. Đây sẽ là câu hỏi giảng viên hỏi đầu tiên.

### Bước 5. Lựa chọn mô hình và kỹ thuật xử lý

**Baseline (3 mức):**
1. Điểm trung bình toàn cục.
2. Điểm trung bình theo từng món (có xử lý món ít đánh giá).
3. Top-N món phổ biến cho gợi ý (mọi người đều nhận cùng danh sách).

**K-means (phân tích hành vi):**
- *Đặc trưng người dùng:* số món đã đánh giá, điểm trung bình, độ phân tán điểm, tỷ lệ món mặn và món chay đã chấm cao, calo trung bình và thời gian nấu trung bình của món họ thích. Với Food.com có thể thêm mức độ hoạt động theo thời gian.
- *Chuẩn hóa đặc trưng* trước khi phân cụm.
- *Chọn số cụm:* thử k từ 2 đến 8, so sánh bằng Silhouette và biểu đồ khuỷu (elbow), cuối cùng chọn k vừa tốt về số liệu vừa **diễn giải được**.
- *Lưu ý:* ViFoodRec chỉ có khoảng 100 người dùng, nên phân cụm người dùng chủ yếu có ý nghĩa trên Food.com. Trên ViFoodRec nên phân cụm **món ăn** (theo calo, thời gian, loại món) bên cạnh việc phân cụm người dùng.

**ALS (gợi ý):**
- Lọc cộng tác dựa trên phân rã ma trận, dùng cho đánh giá tường minh.
- *Tham số cần thử:* số nhân tố tiềm ẩn, hệ số điều chuẩn, số vòng lặp. Dùng kiểm định chéo hoặc tập validation riêng.
- *Người dùng hoặc món mới:* ALS không dự đoán được (vấn đề khởi đầu lạnh). Cách xử lý trong demo: cho người dùng chọn vài món yêu thích rồi tìm món gần nhất trong không gian nhân tố tiềm ẩn của món.

**Viết lý thuyết ngắn cho báo cáo:** mỗi thuật toán 1 đến 2 trang, gồm ý tưởng, công thức chính, ví dụ số nhỏ để minh họa (ví dụ ma trận 4 người dùng × 5 món cho ALS, 6 điểm trên mặt phẳng cho K-means).

### Bước 6. Cài đặt thực nghiệm và quy trình hoàn chỉnh

Cần ghi lại để người khác chạy lại được:
- Phiên bản Docker, Hadoop, Spark, Python và các thư viện.
- Cấu hình cụm (số node, bộ nhớ, số core).
- Thứ tự chạy: nạp dữ liệu → làm sạch → khám phá → baseline → K-means → ALS → thực nghiệm mở rộng → xuất kết quả → chạy demo.
- Đầu vào và đầu ra của từng bước (đường dẫn trong HDFS).
- Tham số cố định, **hạt giống ngẫu nhiên cố định** để kết quả lặp lại được.
- Hướng dẫn cài đặt và chạy ngắn gọn (một file README), đã được thử trên một máy sạch ở ngày 7.

### Bước 7. Đánh giá kết quả

**Bảng đánh giá cần có:**

| So sánh | Độ đo | Ghi chú |
|---|---|---|
| Baseline với ALS (ViFoodRec) | RMSE, MAE, Precision@K, Recall@K | Bảng chính của báo cáo |
| Baseline với ALS (Food.com) | Như trên | Kiểm tra mô hình có ổn định khi dữ liệu lớn |
| Với bài báo gốc ViFoodRec | RMSE, MAE | Bài báo báo cáo User-user Cosine có RMSE khoảng 2,06 và MAE tốt nhất khoảng 1,69. **Cách chia tập kiểm tra khác nhau** (họ dùng 200 điểm), nên chỉ so sánh để tham khảo và phải nói rõ điều này |
| K-means | Silhouette, độ cân bằng kích thước cụm | Kèm đánh giá định tính qua hồ sơ cụm |
| Mở rộng quy mô | Thời gian chạy theo kích thước dữ liệu và số worker | Vẽ biểu đồ đường |

**Phần phân tích bắt buộc:**
- Vì sao kết quả như vậy? Nếu ALS không vượt baseline, giải thích (dữ liệu thưa, ít người dùng, phân phối điểm lệch).
- Hạn chế: ViFoodRec ít người dùng và là dữ liệu khảo sát; Food.com không phải ẩm thực Việt; chưa xét sức khỏe; chưa thử với người dùng thật.
- Hướng phát triển: thêm dữ liệu hành vi thực từ ứng dụng giao đồ ăn, gợi ý có xét dinh dưỡng, mô hình lai giữa lọc cộng tác và nội dung.

> **Nếu kết quả không đẹp:** vẫn nộp kết quả thật và phân tích nguyên nhân. Giảng viên chấm cả khả năng giải thích. Tuyệt đối không chỉnh số liệu cho đẹp.

### Bước 8. Trực quan hóa và ứng dụng minh họa

**Streamlit, 4 trang:**

| Trang | Nội dung | Thể hiện giá trị gì |
|---|---|---|
| 1. Tổng quan | Thống kê dữ liệu, sơ đồ kiến trúc, so sánh CSV với Parquet | Phần lưu trữ và xử lý |
| 2. Hành vi người dùng | Biểu đồ các cụm, hồ sơ từng cụm, hoạt động theo thời gian (Food.com) | Phân tích hành vi |
| 3. Gợi ý món | Chọn người dùng, hoặc chọn vài món thích, rồi nhận Top-N. Bộ lọc theo loại món, thời gian nấu, calo | Giá trị ứng dụng |
| 4. Đánh giá | Bảng so sánh mô hình, biểu đồ thời gian khi tăng quy mô | Minh chứng khoa học |

**Nguyên tắc:** ứng dụng chỉ đọc kết quả đã xuất ra Parquet, không gọi Spark trực tiếp khi demo, để tránh lỗi trước lớp. Mỗi biểu đồ phải có một câu kết luận ("điều này cho thấy..."), vì rubric yêu cầu sản phẩm thể hiện rõ thông tin có giá trị rút ra từ dữ liệu.

### Bước 9. Hoàn thiện sản phẩm nộp

| Sản phẩm | Nội dung |
|---|---|
| Source code | Mã nguồn, README hướng dẫn cài đặt và chạy, cấu hình Docker |
| Dữ liệu | Liên kết tải dữ liệu (không cần nộp file nặng), mô tả cách đặt vào HDFS |
| File Word | Báo cáo theo cấu trúc ở mục 7 |
| File PPT | Slide theo mục 8 |
| Bảng phân công | Việc của từng người và mức đóng góp (có trong báo cáo) |

---

## 7. Cấu trúc báo cáo Word

Giảng viên quy định 10 mục. Gợi ý nội dung và người phụ trách:

| # | Mục | Nội dung gợi ý | Phụ trách |
|---|---|---|---|
| 1 | Trang bìa | Tên trường, môn, đề tài, thành viên, giảng viên | A |
| 2 | Lịch làm việc nhóm hàng tuần | Lấy từ nhật ký **thật**. Ghi những gì đã làm theo từng thời điểm | A |
| 3 | Công việc mỗi thành viên | Bảng phân công và mức đóng góp (mục 4) | B |
| 4 | Mục lục | Tự động tạo | B |
| 5 | Giới thiệu đề tài | Bối cảnh, bài toán, mục tiêu, phạm vi, giá trị (Bước 1) | A |
| 6 | Cơ sở lý thuyết | Big Data, HDFS, Spark, Parquet, ALS, K-means, độ đo đánh giá | A (HDFS, Spark, ALS), B (K-means, độ đo) |
| 7 | Xây dựng ứng dụng, trực quan hóa dữ liệu | Dữ liệu, làm sạch, kiến trúc, mô hình, kết quả, demo (Bước 2 đến 8) | Chia theo phần |
| 8 | Kết luận và định hướng phát triển | Kết quả chính, hạn chế, hướng mở rộng | Cả hai |
| 9 | Tài liệu tham khảo | Bài báo ViFoodRec, nguồn Food.com, tài liệu Spark và Hadoop (mục 12) | B |
| 10 | Phụ lục | Từ điển dữ liệu, hướng dẫn cài đặt, bảng kết quả chi tiết | Cả hai |

**Kiểm tra chất lượng cuối (ngày 6):** cấu trúc đúng 10 mục, không lỗi chính tả, hình và bảng đều có chú thích, số liệu trong báo cáo khớp số liệu trong demo và slide.

---

## 8. Slide và thuyết trình

**Gợi ý khoảng 12 đến 14 slide** (điều chỉnh theo thời gian giảng viên cho):

| # | Slide | Người nói |
|---|---|---|
| 1 | Tiêu đề, thành viên | A |
| 2 | Bài toán và động lực | A |
| 3 | Dữ liệu (hai bộ, vì sao chọn) | A |
| 4 | Kiến trúc và công nghệ | A |
| 5 | Làm sạch và khám phá dữ liệu (số liệu trước và sau) | A |
| 6 | Hành vi người dùng: các cụm | B |
| 7 | Mô hình ALS và baseline | A |
| 8 | Kết quả đánh giá | A |
| 9 | Thực nghiệm mở rộng quy mô | A |
| 10 | **Demo trực tiếp** | B |
| 11 | Hạn chế | B |
| 12 | Kết luận và hướng phát triển | B |
| 13 | Phân công và Hỏi đáp | Cả hai |

**Mẹo:**
- Mỗi slide một thông điệp, nhiều hình hơn chữ.
- Demo chạy 2 đến 3 phút theo kịch bản cố định: chọn người dùng → xem cụm → nhận gợi ý. Luôn có video demo dự phòng.
- Mỗi người phải hiểu phần của người kia, vì giảng viên có thể hỏi bất kỳ ai.

---

## 9. Câu hỏi phản biện dự kiến

Nhóm tự soạn câu trả lời bằng số liệu thật của mình. Dưới đây là hướng trả lời.

| Câu hỏi | Hướng trả lời |
|---|---|
| Dữ liệu của em có thật sự là Big Data không? | Thừa nhận ViFoodRec nhỏ. Dùng Food.com và thực nghiệm mở rộng để chứng minh pipeline xử lý phân tán chạy được ở quy mô lớn hơn |
| Vì sao chọn Spark mà không phải MapReduce? | Thuật toán lặp (ALS, K-means) giữ dữ liệu trong bộ nhớ nên nhanh hơn, và có sẵn thư viện MLlib |
| Vì sao lưu bằng Parquet? | Lưu theo cột, nén tốt, đọc nhanh. Dẫn số đo của nhóm |
| ALS hoạt động thế nào? | Phân rã ma trận người dùng-món thành hai ma trận nhân tố nhỏ, luân phiên cố định một bên và giải bên kia |
| Làm sao biết số cụm k là hợp lý? | Silhouette, elbow, và khả năng diễn giải cụm |
| Xử lý người dùng mới như thế nào? | Nêu hạn chế khởi đầu lạnh của ALS và giải pháp chọn món thích rồi tìm món gần nhất |
| Kết quả có tốt hơn bài báo gốc không? | Chỉ so sánh tham khảo, vì cách chia tập kiểm tra khác nhau. Không khẳng định hơn thua |
| Vì sao đánh giá của ViFoodRec chỉ có khoảng 100 người dùng? | Nêu rõ là dữ liệu khảo sát, và đó là hạn chế |
| Hai bộ dữ liệu không liên quan, vì sao dùng chung? | Dùng chung pipeline, không gộp dữ liệu. Mỗi bộ có vai trò riêng |
| Nếu có dữ liệu thật từ ứng dụng giao đồ ăn thì sao? | Pipeline dùng lại được, có thể thêm dữ liệu theo thời gian và ngữ cảnh |
| Vì sao điểm của em thấp (hoặc cao bất thường)? | Giải thích bằng phân phối dữ liệu, đừng đổ cho "mô hình không tốt" |
| Phần nào do em làm? Em giải thích đoạn code này được không? | Cả hai phải hiểu toàn bộ pipeline. Dùng AI hỗ trợ viết code là được, nhưng phải đọc và hiểu từng bước |

---

## 10. Rủi ro và phương án dự phòng

| Rủi ro | Dấu hiệu | Xử lý |
|---|---|---|
| Docker HDFS không chạy | Quá 4 giờ ngày 1 mà chưa đọc được file | Chuyển sang PySpark local, lưu Parquet ở thư mục máy. Báo cáo nêu rõ "mô phỏng HDFS", trình bày kiến trúc HDFS như thiết kế |
| Thiếu bộ nhớ khi chạy Food.com | Spark báo hết bộ nhớ | Giảm kích thước mẫu (mức 10% và 50%), tăng bộ nhớ cấp cho Docker |
| Dữ liệu thực khác mô tả | Cột hoặc số dòng khác bài báo | Cập nhật báo cáo theo dữ liệu thật, ghi nhận sự khác biệt |
| Giảng viên chưa duyệt dữ liệu | Chưa có phản hồi sau 2 ngày | Vẫn làm tiếp, chuẩn bị giải thích. Nhờ giảng viên xác nhận qua email |
| ALS không tốt hơn baseline | Ngày 4 | Thử đổi tham số và cách chia dữ liệu. Nếu vẫn không, phân tích nguyên nhân và nộp kết quả thật |
| Streamlit lỗi lúc thuyết trình | Lỗi môi trường trên máy lạ | Dùng máy của nhóm, có video demo dự phòng |
| Thành viên bị ốm hoặc bận | Mất 1 ngày công | Mỗi người có bản ghi chú để người kia tiếp tục, đã được dặn ở họp tối |
| Trễ tiến độ | Cuối ngày chưa đạt mục "Đạt khi" | Cắt bớt thực nghiệm mở rộng, bảo vệ phần mô hình và demo |

---

## 11. Checklist nộp bài

**Kỹ thuật**
- [ ] Dữ liệu thô và sạch đã nằm trong HDFS (hoặc phương án dự phòng)
- [ ] Pipeline chạy từ đầu đến cuối trên máy sạch theo README
- [ ] Bảng thống kê trước và sau làm sạch
- [ ] Bảng đánh giá baseline với ALS
- [ ] Kết quả K-means và hồ sơ cụm
- [ ] Bảng thực nghiệm mở rộng quy mô
- [ ] Demo Streamlit chạy được, có video dự phòng

**Nộp trên Classroom**
- [ ] Source code (kèm README và cấu hình Docker)
- [ ] File Word báo cáo (đủ 10 mục)
- [ ] File PPT báo cáo
- [ ] Nộp đúng hạn

**Liêm chính học thuật**
- [ ] Trích dẫn đầy đủ nguồn dữ liệu và bài báo
- [ ] Không sao chép mã nguồn hay kết quả của nhóm khác (điểm 0 theo quy định)
- [ ] Phần việc dùng AI hỗ trợ: cả hai thành viên hiểu và giải thích được
- [ ] Bảng phân công phản ánh đúng thực tế

---

## 12. Tài liệu tham khảo (ban đầu)

> Hãy kiểm tra lại thông tin trích dẫn trước khi đưa vào báo cáo.

1. An Huynh-Quoc Tran, Hong Thi-Thuy Dang, Thanh Chi Dang, Tin Van Huynh. *A New Dataset and Empirical Evaluation for Vietnamese Food Recommendation System.* PACLIC 38, 2024. https://aclanthology.org/2024.paclic-1.4/
2. Kho dữ liệu ViFoodRec: https://github.com/QuocAn55/A-New-Dataset-and-Empirical-Evaluation-for-Vietnamese-Food-Recommendation-System
3. Bộ dữ liệu *Food.com Recipes and Interactions* (Kaggle), ghi rõ tác giả đăng tải và giấy phép khi tải. Bộ này được dùng trong nghiên cứu của Majumder và cộng sự (EMNLP 2019, về công thức cá nhân hóa); cần xác nhận trích dẫn chính xác.
4. Tài liệu Apache Spark: MLlib (ALS, K-means), Spark SQL và DataFrame.
5. Tài liệu Apache Hadoop: HDFS.
6. Tài liệu Apache Parquet.
7. Tài liệu Streamlit.
8. Giáo trình và slide của môn Nhập môn Big Data.

---

## 13. Việc cần làm trong 24 giờ đầu

1. Hỏi giảng viên ngày giờ nộp bài và thuyết trình chính xác (và xác nhận có dời hay không).
2. Gửi giảng viên email xin duyệt hai bộ dữ liệu (tên, nguồn, lý do chọn).
3. Tải hai bộ dữ liệu và kiểm tra cột, số dòng, giấy phép.
4. Dựng kho Git chung và nhật ký làm việc.
5. Bắt đầu dựng Docker (giới hạn 4 giờ).
6. Họp 15 phút cuối ngày để chốt phân công theo mục 4.

---

## Phụ lục: Kế hoạch tiếp theo

File **code riêng** (làm sau, có AI hỗ trợ) sẽ gồm: cài đặt Docker, nạp dữ liệu vào HDFS, từng bước PySpark theo mục 6, và ứng dụng Streamlit. Phần code đó sẽ bám theo đúng cấu trúc thư mục, độ đo và tham số đã mô tả trong file này.

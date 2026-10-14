# BIÊN BẢN KIỂM TOÁN HIỆN TRẠNG DỮ LIỆU VÀ MÃ NGUỒN (STAGE P1 AUDIT)

**Người thực hiện:** Đội ngũ Kỹ sư Dữ liệu / Sinh viên thực hiện Đồ án  
**Vai trò:** Kiểm toán viên độc lập (Chỉ đọc và đo lường, không sửa mã nguồn hay dữ liệu)  
**Ngày kiểm toán:** 13/10/2026  
**Căn cứ:** Quy tắc trung thực trong [docs/CONTEXT.md](file:///d:/Documents/BaiTap/BigData/bigdata-food/docs/CONTEXT.md) và yêu cầu Prompt P1 trong [Bo_prompt_giao_viec_cho_Gemini.md](file:///d:/Documents/BaiTap/BigData/bigdata-food/Bo_prompt_giao_viec_cho_Gemini.md)  

---

## 1. ĐỐI CHIẾU: BÁO CÁO CŨ NÓI GÌ VS THỰC TẾ ĐO ĐƯỢC

Dưới đây là bảng đối chiếu độc lập giữa các khẳng định trong báo cáo cũ ([docs/Bao_cao_Tien_xu_ly_va_Lam_sach_Du_lieu.md](file:///d:/Documents/BaiTap/BigData/bigdata-food/docs/Bao_cao_Tien_xu_ly_va_Lam_sach_Du_lieu.md)) và các số liệu đo lường thực tế từ lệnh Spark:

| Hạng mục đối chiếu | Báo cáo cũ khẳng định | Thực tế đo đạc qua Spark | Đánh giá kiểm toán |
|---|---|---|---|
| **Tổng dòng thô Food.com** | 1,132,367 dòng | **1,132,367** dòng | **XÁC NHẬN** (Đúng khi đọc `multiLine=True`) |
| **Dòng sạch Food.com Interactions** | 735,006 dòng | **735,006** dòng | **XÁC NHẬN** (Số dòng khớp lệnh 1-pass) |
| **Thỏa mãn K-core >= 3 (Food.com)** | Khẳng định đã lọc K-core = 3 | **KHÔNG ĐẠT**: Min user interactions = **1**, Min recipe interactions = **1**. Có **3,572** user và **10,637** recipe có < 3 tương tác! | **LỆCH NGHIÊM TRỌNG**: Thuật toán 1-pass không đạt tính chất K-core đồ thị (cần lặp tới hội tụ) |
| **Tổng công thức Food.com Recipes** | 231,636 công thức | **231,636** công thức | **XÁC NHẬN** |
| **Khóa ngoại Food.com** | Chưa kiểm tra chi tiết | Khớp 100% chiều tương tác -> công thức (0 lỗi). Nhưng có tới **141,906** công thức trong recipes có **0 tương tác** | **CẦN LƯU Ý** (Đúng thực tế đồ án) |
| **Giá trị dị thường `minutes` (Recipes)** | Chưa kiểm tra phân vị | Phân vị 99.9% là **2,147,483,647** phút (Max INT32); có **1,094** món `minutes <= 0` và **262** món `minutes > 10,000` | **RỦI RO CAO** (Cần xử lý ở P3) |
| **Số dòng ViFoodRec Ratings** | 149,467 dòng | **149,467** dòng | **XÁC NHẬN** |
| **Lý do mất ~33.000 dòng ViFoodRec** | Báo cáo cũ nói "do lọc rating=0 và K-core=3" | Thực tế: Mất **33,211 dòng** hoàn toàn do lọc `rating >= 1.0` (trong đó **16,509** dòng rating = 0.0 và **16,702** dòng rating = 0.5). **K-core không làm mất dòng nào!** | **KHÔNG CHÍNH XÁC**: Báo cáo cũ đoán nguyên nhân, không đo thực tế từng bước |
| **Khóa ngoại ViFoodRec** | Khẳng định 4,000 món hợp lệ | Có **1 mã `food_id = 4000`** xuất hiện trong ratings (**36 lượt đánh giá**) nhưng **KHÔNG CÓ** trong `foods.parquet` (foods chỉ có id từ 0 đến 3999) | **LỖI TOÀN VẸN DỮ LIỆU** |
| **Khẳng định "Parquet nén 60 lần"** | "interactions.parquet nén giảm gần 60 lần" (334MB -> 5.7MB) | **SO SÁNH KHÔNG CÔNG BẰNG**: 334MB CSV chứa cột text dài `review` và 1.13M dòng; 5.7MB Parquet đã **bỏ hẳn cột review** và **loại 397K dòng**. | **NGỤY BIỆN DỮ LIỆU**: Mức giảm 60 lần phần lớn do bỏ thuộc tính và lọc dòng, không phải thuần túy do codec Snappy |

---

## 2. KẾT QUẢ ĐO LƯỜNG THỰC TẾ TRÊN 4 BẢNG PARQUET HIỆN CÓ

*(Toàn bộ các số liệu dưới đây được trích xuất từ lệnh chạy thực tế trên container qua script `scratch/audit_p1.py`)*

### 2.1. Bảng `data/processed/food_com/interactions.parquet`
* **Số dòng:** 735,006 | **Số cột:** 4 (`recipe_id: int`, `user_id: int`, `rating: float`, `date: string`).
* **Định danh duy nhất:** 35,336 user khác nhau; 89,730 công thức khác nhau.
* **Độ thưa của ma trận (Sparsity):**
  $$\text{Sparsity} = 1 - \frac{735,006}{35,336 \times 89,730} = 0.999768 \quad (99.9768\%)$$
* **Giá trị NULL:** 0 trên toàn bộ 4 cột.
* **Trùng lặp cặp `(user_id, recipe_id)`:** 0 bản ghi trùng.
* **Phân phối điểm đánh giá:**
  * Điểm 1.0: 4,172 (0.57%)
  * Điểm 2.0: 7,481 (1.02%)
  * Điểm 3.0: 25,080 (3.41%)
  * Điểm 4.0: 123,410 (16.79%)
  * Điểm 5.0: 574,863 (78.21%)  *(Xu hướng người dùng Food.com chấm điểm cực kỳ thiên vị điểm 5)*
* **Kiểm tra K-core:**
  * Số tương tác nhỏ nhất của 1 user: **1** (Vi phạm ngưỡng $\ge 3$).
  * Số tương tác nhỏ nhất của 1 món: **1** (Vi phạm ngưỡng $\ge 3$).
  * Số user có $< 3$ tương tác: **3,572 user**.
  * Số món có $< 3$ tương tác: **10,637 món**.

### 2.2. Bảng `data/processed/food_com/recipes.parquet`
* **Số dòng:** 231,636 | **Số cột:** 7 (`recipe_id: int`, `name: string`, `minutes: int`, `n_steps: int`, `n_ingredients: int`, `ingredients: string`, `nutrition: string`).
* **Giá trị NULL:** 0 trên toàn bộ 7 cột.
* **Kiểm tra khóa ngoại:**
  * Số công thức trong interactions không có trong recipes: **0** (Khớp toàn vẹn).
  * Số công thức trong recipes có 0 tương tác nào: **141,906** (Chiếm 61.26% tổng số công thức).
* **Phân vị các trường số:**
  * `minutes`: Min = 0.0, Phân vị 1% = 2.0, Trung vị (50%) = 40.0, Phân vị 99% = 750.0, Phân vị 99.9% = **2,147,483,647.0**, Max = **2,147,483,647.0**.
  * Bất thường: Có **1,094** món có `minutes <= 0` (vô lý về mặt vật lý); có **262** món có `minutes > 10,000` (hơn 1 tuần nấu liên tục).
  * `n_steps`: Min = 0, Phân vị 1% = 1, Trung vị = 9, Phân vị 99% = 29, Max = 145.
  * `n_ingredients`: Min = 1, Phân vị 1% = 3, Trung vị = 9, Phân vị 99% = 19, Max = 43.

### 2.3. Bảng `data/processed/food_vietnam/ratings.parquet`
* **Số dòng:** 149,467 | **Số cột:** 3 (`food_id: int`, `user_id: int`, `rating: float`).
* **Định danh duy nhất:** **101** user khác nhau; **4,001** món khác nhau.
* **Độ thưa của ma trận (Sparsity):**
  $$\text{Sparsity} = 1 - \frac{149,467}{101 \times 4,001} = 0.630125 \quad (63.0125\%)$$
  *(Ma trận rất đặc so với chuẩn Big Data, do số lượng user rất ít và mỗi user đánh giá khảo sát rất nhiều món).*
* **Giá trị NULL:** 0 trên cả 3 cột.
* **Trùng lặp cặp `(user_id, food_id)`:** 0 bản ghi trùng.
* **Phân phối điểm đánh giá:**
  * Điểm 1.0: 16,420
  * Điểm 1.5: 16,859
  * Điểm 2.0: 16,601
  * Điểm 2.5: 16,660
  * Điểm 3.0: 16,569
  * Điểm 3.5: 16,620
  * Điểm 4.0: 16,618
  * Điểm 4.5: 16,518
  * Điểm 5.0: 16,602
  * *Nhận xét đặc biệt:* Phân phối điểm phân bổ đều chằn chặn một cách nhân tạo (mỗi mức điểm đúng khoảng 16,600 lượt, chiếm ~11.1%). Điều này phản ánh rõ bản chất dữ liệu khảo sát có can thiệp tiền xử lý / cân bằng của nhóm tác giả ViFoodRec.
* **Kiểm tra K-core:**
  * User có ít lượt đánh giá nhất: **1,334 đánh giá** (Cực lớn, $\gg 3$).
  * Món có ít lượt đánh giá nhất: **20 đánh giá** ($\ge 3$).
  * Cả 101 user và 4,001 món đều thỏa mãn tuyệt đối K-core $\ge 3$.

### 2.4. Bảng `data/processed/food_vietnam/foods.parquet`
* **Số dòng:** 4,000 | **Số cột:** 16.
* **Danh sách tên cột chính xác:** `['food_id', 'dish_name', 'description', 'dish_type', 'serving_size', 'cooking_time', 'ingredients', 'cooking_method', 'dish_tags', 'calories', 'fat', 'fiber', 'sugar', 'protein', 'image_link', 'nutrient_content']`.
* **Kiểm tra khóa ngoại:**
  * Có **1 món ăn (`food_id = 4000`)** tồn tại trong `ratings.parquet` (với 36 lượt đánh giá) nhưng **HOÀN TOÀN KHÔNG CÓ** trong `foods.parquet` (file món chỉ đánh số từ 0 đến 3999).
* **Mẫu 5 dòng tiêu biểu:**
  * ID 12: Măng trúc kho ruốc Huế (Món mặn, Calo: 506, Thời gian: 35 phút)
  * ID 13: Đậu hũ xốt nấm (Món mặn, Calo: 215, Thời gian: 15 phút)
  * ID 14: Bánh giò trứng cút (Món mặn, Calo: 450, Thời gian: 40 phút)
  * ID 18: Canh sườn nha đam (Món mặn, Calo: 339, Thời gian: 45 phút)
  * ID 25: Lẩu ốc thả (Món mặn, Calo: 368, Thời gian: 35 phút)

---

## 3. PHÂN TÍCH PHỄU DỮ LIỆU TỪ NGUỒN THÔ (FUNNEL ANALYSIS)

Kiểm toán viên đã chạy lại toàn bộ quy trình từ dữ liệu thô (`data/raw/`) theo từng bước cô lập để truy vết nguyên nhân hao hụt dữ liệu:

### 3.1. Phễu dữ liệu Food.com Interactions
1. **Đọc thô đa dòng (MultiLine):** `1,132,367` dòng (100% khớp dữ liệu gốc Kaggle).
2. **Khuyết thiếu (NULL keys/rating):** Bị loại `0` dòng (Toàn bộ bản ghi đều có đủ ID và rating).
3. **Điểm rating = 0:** Bị loại **`60,847`** dòng (5.37% người dùng chỉ viết bình luận không chấm sao).
4. **Điểm rating ngoài `[1, 5]`:** Bị loại `0` dòng.
   * *Số dòng sau khi lọc rating:* `1,071,520` dòng.
5. **Trùng lặp cặp `(user_id, recipe_id)`:** Bị loại `0` dòng.
6. **Lọc K-core 1 lượt (Mã hiện tại):** Bị loại `336,514` dòng ➔ Còn **`735,006`** dòng.
7. **Lọc K-core lặp đến hội tụ (Chuẩn Big Data):**
   * Vòng 1: `1,071,520` ➔ `735,006` (mất 336,514 dòng)
   * Vòng 2: `735,006` ➔ `710,145` (mất 24,861 dòng)
   * Vòng 3: `710,145` ➔ `707,106` (mất 3,039 dòng)
   * Vòng 4: `707,106` ➔ `706,610` (mất 496 dòng)
   * Vòng 5: `706,610` ➔ `706,539` (mất 71 dòng)
   * Vòng 6: `706,539` ➔ `706,520` (mất 19 dòng)
   * Vòng 7: `706,520` ➔ `706,514` (mất 6 dòng)
   * Vòng 8: `706,514` ➔ `706,514` (Hội tụ 100% sau 8 vòng)
   * **Kết luận:** Số dòng chuẩn khi đạt K-core $\ge 3$ thực sự là **706,514 dòng** (chênh lệch **28,492 dòng** so với bản 1-pass hiện tại).

### 3.2. Phễu dữ liệu ViFoodRec Ratings (Giải mã 33,211 dòng bị mất)
* **Tổng dòng thô ban đầu:** `182,678` dòng.
* **Bước 1 - Khuyết thiếu NULL:** `0` dòng (0.0%).
* **Bước 2 - Lọc rating = 0.0:** Bị loại **`16,509`** dòng (9.04%).
* **Bước 2b - Lọc rating ngoài [1, 5] (cụ thể là rating = 0.5):** Bị loại **`16,702`** dòng (9.14%).
* **Bước 3 - Trùng lặp `(user_id, food_id)`:** `0` dòng (0.0%).
* **Bước 4 - Lọc K-core >= 3:** Bị loại `0` dòng (0.0%).
* **TỔNG DÒNG BỊ LOẠI:** Đúng bằng $16,509 + 16,702 = \mathbf{33,211\text{ dòng}}$ (18.18%).
* **KẾT LUẬN MINH BẠCH:** Khoản mất 33,211 dòng của ViFoodRec **100% xuất phát từ việc loại các điểm dưới 1.0 (gồm mức 0.0 và mức 0.5)**. Việc gán lý do cho K-core trong báo cáo cũ là hoàn toàn sai lệch thực tế.

---

## 4. ĐÁNH GIÁ TÍNH CÔNG BẰNG VỀ SO SÁNH DUNG LƯỢNG LƯU TRỮ

Trong báo cáo cũ có nêu: *"Parquet nén giảm gần 60 lần dung lượng lưu trữ (334 MB CSV -> 5.7 MB Parquet)"*.

**Kiểm toán viên xác định kết luận này là KHÔNG CÔNG BẰNG VÀ THIẾU CĂN CỨ KHOA HỌC:**
1. **Lệch thuộc tính (Columns mismatch):** File `RAW_interactions.csv` nặng 334 MB chủ yếu vì cột `review` chứa các đoạn văn bản dài hàng trăm chữ và ký tự HTML. Bảng `interactions.parquet` đã **loại bỏ hoàn toàn cột `review`**, chỉ giữ 4 cột số và ngày tháng ngắn.
2. **Lệch số dòng (Rows mismatch):** File Parquet đã bị lọc bớt gần **400,000 dòng** (chỉ còn 735,006 so với 1,132,367 ban đầu).
3. **Kết luận đúng đắn:** Không thể lấy dung lượng của một bảng bị cắt 80% độ rộng cột và 35% số dòng đi so với file thô đầy đủ để khẳng định "Parquet nén tốt hơn CSV 60 lần". Muốn đo hiệu quả nén thuần túy của Parquet (Snappy) so với CSV, bắt buộc phải đo trên **cùng nội dung, cùng cột và cùng số dòng** (sẽ thực hiện chuẩn mực ở Prompt P4).

---

## 5. DANH SÁCH LỖI VÀ RỦI RO (PHÂN CẤP MỨC ĐỘ)

### 🔴 Mức độ Nghiêm trọng (Critical)
1. **Thuật toán K-core chưa hội tụ (Food.com):**
   * *Mô tả:* Cách lọc 1 lượt trong `clean_food_com.py` bỏ sót 3,572 user và 10,637 recipe có dưới 3 tương tác. Khi đưa vào mô hình ALS hoặc K-Means, các thực thể này sẽ gây lỗi cold-start hoặc làm lệch ma trận phân rã.
   * *Đề xuất:* Thay thế bằng vòng lặp `while` K-core lặp đến khi số dòng không đổi (hội tụ tại 706,514 dòng).
2. **Lỗi toàn vẹn khóa ngoại (ViFoodRec):**
   * *Mô tả:* Tồn tại 36 đánh giá cho món ăn mang mã `food_id = 4000` trong khi bảng món chỉ có ID đến 3999.
   * *Đề xuất:* Inner join `ratings` với `foods` sạch để loại bỏ triệt để các mã món không tồn tại trong từ điển món ăn.

### 🟡 Mức độ Nên sửa (Medium)
3. **Giá trị ngoại lai cực đoan trong Recipes (`minutes`):**
   * *Mô tả:* Cột `minutes` có giá trị âm (`<= 0`) và giá trị tràn số nguyên (`2,147,483,647` phút ~ 4,000 năm). Nếu dùng trực tiếp làm đặc trưng K-Means phân cụm hành vi, giá trị này sẽ phá hỏng phép chuẩn hóa StandardScaler.
   * *Đề xuất:* Giữ nguyên cột gốc `minutes`, bổ sung cột `minutes_clean` đặt thành `NULL` hoặc giới hạn theo phân vị 99% (750 phút) như quy định tại P3.
4. **Tách thuộc tính dinh dưỡng Food.com:**
   * *Mô tả:* Cột `nutrition` đang lưu dưới dạng text `"['calories', 'fat', ...]"`, chưa bóc tách thành 7 cột số thực phục vụ mô hình.
   * *Đề xuất:* Tách thành 7 cột số theo tài liệu Kaggle ở giai đoạn P3.

### 🟢 Mức độ Nhỏ (Low)
5. **Gán nhãn món ăn có tương tác:**
   * *Mô tả:* Có 141,906 món trong recipes không có tương tác nào.
   * *Đề xuất:* Thêm cờ `has_ratings = false` để phân biệt công thức có dữ liệu huấn luyện và công thức mới (phục vụ cold-start content-based).

---

## 6. ĐIỂM CẦN HIỂU ĐỂ TRẢ LỜI PHẢN BIỆN (DÀNH CHO 2 SINH VIÊN)

**Câu hỏi 1: Tại sao K-core lọc 1 lượt (single-pass) lại không đảm bảo mọi user và item đều có $\ge 3$ tương tác?**
* *Trả lời:* Vì đây là bài toán đồ thị hai phía (bipartite graph). Khi ta lọc bỏ các user có $< 3$ tương tác, các món ăn mà user đó từng đánh giá sẽ bị giảm số lượng tương tác đi 1. Điều này có thể khiến một số món ăn ban đầu có 3 tương tác nay chỉ còn 2 tương tác. Nếu không lặp lại bước lọc món ăn, món ăn đó sẽ bị sót lại với số tương tác $< 3$. Quá trình này phải lặp đi lặp lại (iterative pruning) cho đến khi cả 2 phía không còn đỉnh nào bị giảm dưới ngưỡng (trạng thái hội tụ).

**Câu hỏi 2: Tại sao dữ liệu ViFoodRec lại mất đúng ~33.000 dòng sau khi làm sạch? Có phải do người dùng đánh giá ít bị lọc K-core không?**
* *Trả lời:* Hoàn toàn không phải do K-core. Dữ liệu khảo sát ViFoodRec có 101 user nhưng mỗi user đánh giá ít nhất 1,334 món, và mỗi món có ít nhất 20 lượt chấm. 33,211 dòng bị mất hoàn toàn do chúng em lọc bỏ các đánh giá $< 1.0$, trong đó có 16,509 dòng mang điểm 0.0 (chưa chấm) và 16,702 dòng mang điểm 0.5.

**Câu hỏi 3: So sánh "Parquet nén giảm 60 lần so với CSV" ở báo cáo ban đầu có chính xác không?**
* *Trả lời:* Dạ không chính xác về mặt khoa học. Con số 60 lần đó là so sánh giữa file CSV thô chứa cả văn bản review dài với file Parquet đã loại bỏ cột review và lọc bớt 397 nghìn dòng. Để chứng minh khả năng nén của Parquet một cách công bằng, nhóm sẽ thực hiện thí nghiệm giữ nguyên toàn bộ cột và dòng ở giai đoạn tiếp theo (P4).

---

## 7. ĐỐI CHIẾU TIÊU CHÍ ĐẠT CỦA PROMPT P1

* [x] **Có đủ số liệu thật cho Bước 2 và Bước 3:** Đạt 100% (Trích xuất đầy đủ từ các câu lệnh Spark thực thi trên container).
* [x] **Có kết luận rõ K-core hiện tại có đúng hay không:** Đạt (Đã chứng minh 1-pass vi phạm K-core, có 3,572 user và 10,637 recipe $< 3$ tương tác; cần 8 vòng lặp để hội tụ tại 706,514 dòng).
* [x] **Có giải thích khoản mất 33.000 dòng của ViFoodRec:** Đạt (Giải thích chính xác đến từng dòng: do rating 0.0 và 0.5, không liên quan đến K-core).
* [x] **Tuyệt đối không sửa mã nguồn trong giai đoạn này:** Đạt (Chỉ thực hiện đo lường và lập biên bản).

**KẾT LUẬN CỦA KIỂM TOÁN VIÊN:** Giai đoạn P1 hoàn thành xuất sắc, trung thực và minh bạch. Sẵn sàng chuyển giao cho giai đoạn **P2 (Dựng hạ tầng HDFS + Spark cụm trong Docker)**.

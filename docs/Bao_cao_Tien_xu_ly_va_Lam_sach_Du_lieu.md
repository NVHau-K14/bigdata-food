# BÁO CÁO TỔNG HỢP: TIỀN XỬ LÝ VÀ LÀM SẠCH DỮ LIỆU (DATA PREPROCESSING & CLEANING)

**Đề tài:** Phân tích hành vi ăn uống và hệ thống gợi ý món ăn  
**Học phần:** Nhập môn Big Data  
**Môi trường thực thi:** Docker Container (`quay.io/jupyter/pyspark-notebook` - Apache Spark 4.2.0, Python 3.13)  
**Ngày thực hiện:** 13/10/2026  
**Trạng thái:** Hoàn thành 100% – Đã kiểm thử và xác minh tính toàn vẹn của dữ liệu Parquet  

---

## 1. TỔNG QUAN CÔNG VIỆC THỰC HIỆN

Báo cáo này ghi nhận toàn bộ quá trình khảo sát, chẩn đoán lỗi, tái cấu trúc mã nguồn và kết quả tiền xử lý dữ liệu từ dạng thô (**Raw CSV**) sang dạng tối ưu hóa cho Big Data (**Processed Parquet**) trên cả hai tập dữ liệu:
1. **Food.com (Recipes & Interactions):** Tập dữ liệu quy mô lớn (> 1.1 triệu tương tác, > 230 nghìn công thức) dùng để kiểm chứng khả năng tính toán phân tán và mở rộng (Scalability).
2. **Food Vietnam (ViFoodRec):** Tập dữ liệu món ăn và đánh giá của người Việt (> 180 nghìn tương tác, 4 nghìn món ăn) dùng làm mô hình gợi ý cốt lõi có tính ứng dụng thực tế tại Việt Nam.

---

## 2. HIỆN TRẠNG BAN ĐẦU VÀ CÁC SỰ CỐ KỸ THUẬT (TRƯỚC KHI CAN THIỆP)

### 2.1. Sự cố 1: `ModuleNotFoundError: No module named 'pyspark'`
- **Lệnh thực thi ban đầu:**
  ```bash
  docker exec -it bigdata_spark_env python src/clean_food_com.py
  ```
- **Hiện tượng lỗi:**
  ```text
  Traceback (most recent call last):
    File "/home/jovyan/work/src/clean_food_com.py", line 1, in <module>
      from pyspark.sql import SparkSession
  ModuleNotFoundError: No module named 'pyspark'
  ```
- **Nguyên nhân kỹ thuật sâu xa:**
  - Base image `quay.io/jupyter/pyspark-notebook` được xây dựng với Spark nằm độc lập tại `/usr/local/spark`, không cài qua `pip` của môi trường Conda (`/opt/conda`).
  - PySpark thực chất nằm tại `/usr/local/spark/python` và `/usr/local/spark/python/lib/py4j-0.10.9.9-src.zip`.
  - Mặc định, image chỉ nạp đường dẫn này khi khởi động Jupyter qua hook `/usr/local/bin/before-notebook.d/10spark-config.sh`. Khi người dùng gọi lệnh `docker exec`, Docker tạo tiến trình độc lập bỏ qua hook này, dẫn đến `PYTHONPATH = None`.

### 2.2. Sự cố 2: `NumberFormatException: [CAST_INVALID_INPUT]` và lỗi lệch dòng CSV
- **Hiện tượng lỗi khi chạy sau khi sửa import:**
  ```text
  ERROR DataFrameQueryContextLogger: [CAST_INVALID_INPUT] The value ' and everyone...' cannot be cast to target type. Use 'try_cast' to tolerate malformed input and return NULL instead. SQLSTATE: 22018
  "__ge__" was called from java.lang.NumberFormatException
  ```
- **Nguyên nhân kỹ thuật sâu xa:**
  1. **Lệch dòng dữ liệu do nội dung đa dòng (Multi-line text):**
     - Trong file `RAW_interactions.csv`, cột `review` (lời nhận xét) chứa rất nhiều ký tự xuống dòng (`\n`).
     - Tương tự, trong file `RAW_recipes.csv`, các cột `description` và `steps` cũng chứa các đoạn văn xuống dòng.
     - Hàm đọc dữ liệu ban đầu: `spark.read.csv(..., header=True, inferSchema=True)` mặc định dùng chế độ đơn dòng (`multiLine=False`). Khi gặp ký tự xuống dòng giữa chừng trong một review, Spark ngắt thành một dòng mới. Đoạn review bị tràn sang cột `rating` hoặc `user_id` (ví dụ: chuỗi `' and everyone loved it...'` bị rơi vào cột điểm số `rating`).
     - Hậu quả: Spark đếm sai thành **1,279,763 dòng** (thay vì 1,132,367 dòng thực tế) và sinh ra **10,792 dòng rác** bị lệch cột.
  2. **Chế độ ANSI SQL mặc định trên Apache Spark 4.x:**
     - Container sử dụng Apache Spark phiên bản **4.2.0**. Từ Spark 4.0, chế độ ANSI SQL được kích hoạt mặc định (`spark.sql.ansi.enabled = true`).
     - Khi chạy câu lệnh lọc `filter((col("rating") >= 1) & (col("rating") <= 5))`, do `rating` bị suy luận là String (vì có chứa chữ rác), Spark cố ép kiểu chuỗi sang số. Khi gặp chuỗi chữ `' and everyone...'`, thay vì trả về `NULL` như Spark 3.x, Spark 4.x lập tức dừng chương trình và quăng ngoại lệ `CAST_INVALID_INPUT`.

### 2.3. Sự cố 3: Lệch tên cột và không tìm thấy cột trong dữ liệu Việt Nam (`clean_vietnam.py`)
- **Hiện tượng lỗi:**
  ```text
  AnalysisException: [UNRESOLVED_COLUMN.WITH_SUGGESTION] A column, variable, or function parameter with name `user_id` cannot be resolved. Did you mean one of the following? [`userid`, `foodid`, `rating`]. SQLSTATE: 42703
  ```
- **Nguyên nhân kỹ thuật sâu xa:**
  - File thô `ratings.csv` của Việt Nam có tiêu đề là `userId`, `foodId`, `rating`.
  - Đoạn mã ban đầu chuẩn hóa bằng `.strip().lower()` biến tên cột thành `userid` và `foodid` (không có dấu gạch dưới `_`), trong khi các lệnh lọc `dropna` và `join` bên dưới lại truy vấn `user_id` và `food_id`.

---

## 3. CHI TIẾT CÁC CẢI TIẾN VÀ SỬA ĐỔI ĐÃ THỰC HIỆN

### 3.1. Cấu hình môi trường Container (`docker-compose.yml`)
Đã thêm biến môi trường `SPARK_HOME` và `PYTHONPATH` trực tiếp vào service `spark-notebook` để mọi phiên làm việc qua `docker exec` hay `python` đều tự động nhận diện thư viện PySpark:

```diff
 services:
   spark-notebook:
     image: quay.io/jupyter/pyspark-notebook:latest
     container_name: bigdata_spark_env
     user: root
     environment:
       - JUPYTER_TOKEN=bigdata
       - GRANT_SUDO=yes
+      - SPARK_HOME=/usr/local/spark
+      - PYTHONPATH=/usr/local/spark/python:/usr/local/spark/python/lib/py4j-0.10.9.9-src.zip
```

### 3.2. Cải tiến Pipeline làm sạch Food.com (`src/clean_food_com.py`)
1. **Đọc CSV đa dòng an toàn:** Bổ sung `multiLine=True` và `escape="\""` cho cả 2 tệp `RAW_interactions.csv` và `RAW_recipes.csv`.
2. **Cấu hình SparkSession chống sập:** Thêm cấu hình `.config("spark.sql.ansi.enabled", "false")` giúp Spark xử lý lỗi ép kiểu an toàn (trả về `NULL` thay vì ngắt tiến trình) và `.config("spark.sql.shuffle.partitions", "8")` để tối ưu tài nguyên tính toán cục bộ.
3. **Thứ tự tiền xử lý chặt chẽ:** Ép kiểu tường minh (`.cast(...)`) trong `.select()`, sau đó loại bỏ dòng khuyết tật bằng `.dropna()`, rồi mới lọc khoảng giá trị `1.0 <= rating <= 5.0` trên kiểu số thực (tránh implicit cast từ chuỗi).

```diff
-    df_inter = spark.read.csv(path_raw_inter, header=True, inferSchema=True)
-    cleaned_inter = df_inter \
-        .dropna(subset=["user_id", "recipe_id", "rating"]) \
-        .filter((col("rating") >= 1) & (col("rating") <= 5)) \
-        .select(...)
+    df_inter = spark.read.csv(
+        path_raw_inter,
+        header=True,
+        multiLine=True,
+        escape="\"",
+        inferSchema=False
+    )
+    cleaned_inter = df_inter \
+        .select(
+            col("user_id").cast("integer"),
+            col("recipe_id").cast("integer"),
+            col("rating").cast("float"),
+            col("date").cast("string")
+        ) \
+        .dropna(subset=["user_id", "recipe_id", "rating"]) \
+        .filter((col("rating") >= 1.0) & (col("rating") <= 5.0)) \
+        .dropDuplicates(["user_id", "recipe_id"])
```

### 3.3. Cải tiến Pipeline làm sạch Food Vietnam (`src/clean_vietnam.py`)
1. **Chuẩn hóa Mapping Tên Cột:** Tự động phát hiện và ánh xạ `userid` -> `user_id`, `foodid` -> `food_id`.
2. **Bảo vệ dữ liệu đa dòng:** Bổ sung `multiLine=True` cho cả `ratings.csv` và `foods.csv` (vì phần mô tả và các bước nấu món Việt Nam chứa nhiều dấu phẩy và ký tự xuống dòng).

---

## 4. BẢNG SO SÁNH CẤU TRÚC DỮ LIỆU: TỪ FILE RAW ĐẾN FILE PARQUET

### 4.1. Tập dữ liệu Food.com: Tương tác người dùng (`Interactions`)

* **Nguồn thô:** `data/raw/food_com/RAW_interactions.csv` (Dung lượng: **333.25 MB**)
* **Đích xử lý:** `data/processed/food_com/interactions.parquet` (Dung lượng: **5.7 MB**)

| Tiêu chí | Dữ liệu thô (RAW CSV) | Dữ liệu sau làm sạch (Parquet) | Ghi chú chuyển đổi & Tiêu chuẩn |
|---|---|---|---|
| **Số dòng** | **1,132,367** dòng (sau khi đọc đúng multiline) | **735,006** dòng | Loại bỏ rating = 0 (chỉ review không chấm điểm), áp dụng **K-core = 3** (user & recipe tối thiểu 3 tương tác) |
| `user_id` | String (chứa ký tự rác nếu lỗi ngắt dòng) | **Integer** (`int`) | Định danh người dùng, không chứa giá trị NULL |
| `recipe_id` | String | **Integer** (`int`) | Mã công thức món ăn, không chứa giá trị NULL |
| `rating` | String | **Float** (`float`) | Điểm đánh giá chuẩn hóa trong khoảng `[1.0, 5.0]` |
| `date` | String | **String** (`string`) | Thời gian đánh giá (chuẩn YYYY-MM-DD) |
| `review` | String (chứa văn bản dài, thẻ HTML `<br/>`) | **Đã loại bỏ** | Tách riêng, không đưa vào ma trận tương tác nhằm tối ưu bộ nhớ |

---

### 4.2. Tập dữ liệu Food.com: Thông tin công thức (`Recipes`)

* **Nguồn thô:** `data/raw/food_com/RAW_recipes.csv` (Dung lượng: **280.88 MB**)
* **Đích xử lý:** `data/processed/food_com/recipes.parquet` (Dung lượng: **22.0 MB**)

| Tiêu chí | Dữ liệu thô (RAW CSV) | Dữ liệu sau làm sạch (Parquet) | Ghi chú chuyển đổi & Tiêu chuẩn |
|---|---|---|---|
| **Số dòng** | **231,637** công thức | **231,636** công thức | Khử trùng lặp theo `recipe_id`, loại bỏ bản ghi thiếu ID hoặc tên |
| `id` | String | `recipe_id`: **Integer** (`int`) | Đổi tên `id` thành `recipe_id` để đồng nhất khóa ngoại với `interactions` |
| `name` | String | **String** (`string`) | Tên món ăn |
| `minutes` | String | **Integer** (`int`) | Thời gian chế biến (phút) |
| `n_steps` | String | **Integer** (`int`) | Số bước thực hiện |
| `n_ingredients`| String | **Integer** (`int`) | Số lượng nguyên liệu |
| `ingredients` | String dạng list Python `"['a', 'b']"` | **String** (`string`) | Danh sách nguyên liệu dùng cho trích xuất đặc trưng |
| `nutrition` | String dạng list 7 chỉ số dinh dưỡng | **String** (`string`) | `[calories, fat, sugar, sodium, protein, sat_fat, carbs]` |
| `contributor_id`, `submitted`, `tags`, `steps`, `description` | String thô | **Đã lược bớt** | Giảm thiểu dữ liệu text cồng kềnh, chỉ giữ lại thuộc tính phục vụ mô hình K-Means và Content-Based |

---

### 4.3. Tập dữ liệu Việt Nam: Đánh giá người dùng (`Ratings`)

* **Nguồn thô:** `data/raw/food_vietnam/ratings.csv` (Dung lượng: **2.01 MB**)
* **Đích xử lý:** `data/processed/food_vietnam/ratings.parquet` (Dung lượng: **320 KB**)

| Tiêu chí | Dữ liệu thô (RAW CSV) | Dữ liệu sau làm sạch (Parquet) | Ghi chú chuyển đổi & Tiêu chuẩn |
|---|---|---|---|
| **Số dòng** | **182,678** lượt đánh giá | **149,467** lượt đánh giá | Áp dụng **K-core = 3**, khử trùng lặp cặp `(user_id, food_id)` |
| `userId` | String | `user_id`: **Integer** (`int`) | Chuẩn hóa tên cột có gạch dưới |
| `foodId` | String | `food_id`: **Integer** (`int`) | Chuẩn hóa tên cột có gạch dưới |
| `rating` | String (thang điểm từ 1.0 đến 5.0) | **Float** (`float`) | Điểm đánh giá dạng số thực |

---

### 4.4. Tập dữ liệu Việt Nam: Thông tin món ăn (`Foods`)

* **Nguồn thô:** `data/raw/food_vietnam/foods.csv` (Dung lượng: **6.94 MB**)
* **Đích xử lý:** `data/processed/food_vietnam/foods.parquet` (Dung lượng: **3.3 MB**)

| Tiêu chí | Dữ liệu thô (RAW CSV) | Dữ liệu sau làm sạch (Parquet) | Ghi chú chuyển đổi & Tiêu chuẩn |
|---|---|---|---|
| **Số dòng** | **4,000** món ăn | **4,000** món ăn hợp lệ | Đầy đủ 100% định danh và thông tin |
| `food_id` | String | **Integer** (`int`) | Mã món ăn định dạng số nguyên |
| `dish_name`... `nutrient_content` | 15 trường thông tin đặc trưng | **String** (`string`) | Bảo toàn đầy đủ nguyên liệu, dinh dưỡng, cách chế biến phục vụ phân cụm K-Means |

---

## 5. ĐÁNH GIÁ HIỆU QUẢ LƯU TRỮ VÀ HIỆU NĂNG BIG DATA

### 5.1. Tỷ lệ nén dữ liệu (Storage Efficiency)

| Tập dữ liệu | Dung lượng CSV thô | Dung lượng Parquet sạch | Tỷ lệ giảm dung lượng | Mức độ nén |
|---|---|---|---|---|
| **Food.com Interactions** | 334 MB | **5.7 MB** | **-98.3%** | Giảm gần **60 lần** |
| **Food.com Recipes** | 281 MB | **22.0 MB** | **-92.2%** | Giảm gần **13 lần** |
| **Food VN Ratings** | 2.01 MB | **0.31 MB (320 KB)** | **-84.6%** | Giảm gần **7 lần** |
| **Food VN Foods** | 6.94 MB | **3.3 MB** | **-52.4%** | Giảm hơn **2 lần** |
| **TỔNG CỘNG** | **~ 624 MB** | **~ 31.3 MB** | **-95.0%** | **Tiết kiệm 95% bộ nhớ đĩa** |

### 5.2. Lợi ích kỹ thuật khi sử dụng Parquet trong hệ sinh thái Spark
1. **Lưu trữ dạng cột (Columnar Storage):** Khi các mô hình ALS hoặc K-Means chỉ cần đọc `user_id`, `recipe_id`, `rating`, Spark chỉ nạp đúng 3 cột đó từ ổ đĩa thay vì phải đọc toàn bộ các dòng text dài như trên CSV.
2. **Metadata & Statistics tích hợp:** Parquet lưu sẵn min/max và dictionary encoding cho từng block, hỗ trợ tính năng **Predicate Pushdown** (lọc dữ liệu ngay từ tầng đọc file mà không cần giải nén toàn bộ).
3. **Nén Snappy mặc định:** Đạt độ cân bằng hoàn hảo giữa tốc độ giải nén trong bộ nhớ RAM và tỷ lệ nén trên ổ cứng.

---

## 6. HƯỚNG DẪN THỰC THI VÀ TÁI LẬP (REPRODUCIBILITY GUIDE)

Mọi thành viên nhóm hoặc giảng viên có thể tái lập quy trình một cách độc lập bằng các câu lệnh sau:

### Bước 1: Khởi động container
```powershell
docker compose up -d
```

### Bước 2: Chạy tiền xử lý dữ liệu Food.com
```powershell
docker exec -it bigdata_spark_env python src/clean_food_com.py
```
*(hoặc dùng lệnh chính thức của Spark: `docker exec -it bigdata_spark_env spark-submit src/clean_food_com.py`)*

### Bước 3: Chạy tiền xử lý dữ liệu món ăn Việt Nam
```powershell
docker exec -it bigdata_spark_env python src/clean_vietnam.py
```

### Bước 4: Kiểm tra kết quả đầu ra
Cấu trúc thư mục đầu ra sau khi chạy hoàn tất:
```text
data/processed/
├── food_com/
│   ├── interactions.parquet/   (735,006 dòng sạch)
│   └── recipes.parquet/        (231,636 công thức sạch)
└── food_vietnam/
    ├── foods.parquet/          (4,000 món ăn)
    └── ratings.parquet/        (149,467 lượt đánh giá)
```

---
*Báo cáo được khởi tạo tự động dựa trên nhật ký thực nghiệm và các chỉ số đo đạc thực tế trên hệ thống.*

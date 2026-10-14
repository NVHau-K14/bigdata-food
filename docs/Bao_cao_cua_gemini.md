> **ĐÃ LỖI THỜI (đánh dấu ngày 14/10/2026).** Báo cáo này do công cụ trước đó viết ở giai đoạn đầu (khảo sát, thiết lập hệ thống, kế hoạch) và chưa được đối chiếu lại với kết quả thật. Số liệu, sơ đồ thư mục (ví dụ `app/` là dashboard Streamlit) và kế hoạch trong đó có thể không còn đúng. Dashboard chính nay là `web/`. Số liệu hiện hành nằm ở `reports/evidence/STATUS.md`, `docs/Q_and_A.md` và các biên bản `stage_S*.md`. Không trích dẫn từ báo cáo này. Xem [reports/evidence/stage_S5.md](../reports/evidence/stage_S5.md).

# BÁO CÁO KỸ THUẬT: KHẢO SÁT, THIẾT LẬP HỆ THỐNG VÀ TIỀN XỬ LÝ DỮ LIỆU
**HỌC PHẦN: NHẬP MÔN BIG DATA**

---

* **Đề tài:** Phân tích hành vi ăn uống và Gợi ý món ăn cá nhân hóa (Nghiên cứu đối chiếu: Food.com vs ViFoodRec)
* **Đối tượng nghiên cứu:** 
  * Bộ dữ liệu quốc tế: *Food.com Recipes and Interactions* (Kaggle)
  * Bộ dữ liệu Việt Nam: *ViFoodRec Dataset* (PACLIC 2024 / GitHub)
* **Công nghệ cốt lõi:** Apache Spark (PySpark), Docker Containerization, Parquet Columnar Storage

---

## MỤC LỤC
1. [Tổng quan mục tiêu & Chiến lược đề tài](#1-tổng-quan-mục-tiêu--chiến-lược-đề-tài)
2. [Cấu trúc tổ chức thư mục dự án](#2-cấu-trúc-tổ-chức-thư-mục-dự-án)
3. [Khảo sát chi tiết dữ liệu thô (Raw Data Structure)](#3-khảo-sát-chi-tiết-dữ-liệu-thô-raw-data-structure)
4. [Các quy tắc tiền xử lý và làm sạch dữ liệu](#4-các-quy-tắc-tiền-xử-lý-và-làm-sạch-dữ-liệu)
5. [Nhật ký kỹ thuật: Các lỗi phát sinh và giải pháp khắc phục](#5-nhật-ký-kỹ-thuật-các-lỗi-phát-sinh-và-giải-pháp-khắc-phục)
6. [Cấu trúc dữ liệu chuẩn hóa đầu ra (.parquet)](#6-cấu-trúc-dữ-liệu-chuẩn-hóa-đầu-ra-parquet)
7. [Mã nguồn hoàn chỉnh và Hướng dẫn thực thi](#7-mã-nguồn-hoàn-chỉnh-và-hướng-dẫn-thực-thi)
8. [Kế hoạch các bước tiếp theo](#8-kế-hoạch-các-bước-tiếp-theo)

---

## 1. Tổng quan mục tiêu & Chiến lược đề tài

### 1.1. Mục tiêu kỹ thuật
Đồ án hướng tới việc giải quyết bài toán gợi ý món ăn theo phương pháp lọc cộng tác (Collaborative Filtering) thông qua thuật toán phân rã ma trận **ALS (Alternating Least Squares)** của thư viện **Spark MLlib**, kết hợp phân tích đối chiếu hành vi tiêu dùng giữa hai nền văn hóa ẩm thực (phương Tây và Việt Nam).

Mô hình phân rã ma trận tương tác $R \in \mathbb{R}^{m \times n}$ thành tích của 2 ma trận ẩn:
$$R \approx U \times V^T$$
Trong đó:
* $U \in \mathbb{R}^{m \times k}$: Ma trận biểu diễn vector đặc trưng của người dùng (Users).
* $V \in \mathbb{R}^{n \times k}$: Ma trận biểu diễn vector đặc trưng của món ăn (Items).
* $k$: Số chiều ẩn (Latent Factor Rank).

Mô hình tối ưu hóa hàm mất mát có điều chuẩn:
$$\mathcal{L} = \sum_{(u, i) \in R} (r_{ui} - u_u^T v_i)^2 + \lambda \left( \sum_u \|u_u\|_2^2 + \sum_i \|v_i\|_2^2 \right)$$

Chất lượng mô hình được đo lường thông qua sai số căn bậc hai trung bình (RMSE):
$$RMSE = \sqrt{\frac{1}{|T|} \sum_{(u, i) \in T} (r_{ui} - \hat{r}_{ui})^2}$$

### 1.2. Chiến lược xử lý: Nghiên cứu đối chiếu (Comparative Study)
* Không thực hiện trộn dữ liệu (tránh xung đột cấu trúc dữ liệu, độ lệch phân phối và khác biệt văn hóa).
* Xử lý độc lập 2 luồng dữ liệu song song từ giai đoạn làm sạch, lưu trữ Parquet đến huấn luyện mô hình ALS và thống kê mô tả (EDA).

---

## 2. Cấu trúc tổ chức thư mục dự án

Toàn bộ dự án được cấu trúc theo mô hình chuẩn của các hệ thống xử lý dữ liệu lớn:

```text
bigdata-food/
│
├── data/
│   ├── raw/                              # Dữ liệu gốc nguyên bản (ReadOnly)
│   │   ├── food_com/
│   │   │   ├── RAW_interactions.csv     # File đánh giá món ăn quốc tế
│   │   │   └── RAW_recipes.csv          # File thông tin công thức quốc tế
│   │   └── food_vietnam/
│   │       ├── ratings.csv              # File đánh giá món ăn Việt Nam
│   │       └── foods.csv                # File thông tin món ăn Việt Nam
│   │
│   └── processed/                        # Dữ liệu sau tiền xử lý dạng Parquet
│       ├── food_com/
│       │   ├── interactions.parquet/    # Tương tác Food.com đã lọc
│       │   └── recipes.parquet/         # Món ăn Food.com đã chuẩn hóa
│       └── food_vietnam/
│           ├── ratings.parquet/         # Tương tác Việt Nam đã lọc
│           └── foods.parquet/           # Món ăn Việt Nam đã chuẩn hóa
│
├── docker-compose.yml                    # Cấu hình container chạy Spark
│
├── src/                                  # Mã nguồn Python/PySpark xử lý chính
│   ├── clean_food_com.py                # Pipeline làm sạch dữ liệu Food.com
│   └── clean_vietnam.py                 # Pipeline làm sạch dữ liệu Việt Nam
│
├── notebooks/                            # Thư mục lưu Jupyter Notebook nháp
├── app/                                  # Mã nguồn Web Dashboard (Streamlit)
└── reports/                              # Tài liệu báo cáo, slide thuyết trình
```

---

## 3. Khảo sát chi tiết dữ liệu thô (Raw Data Structure)

### 3.1. Bộ dữ liệu Food.com (Kaggle)
* **Quy mô:** Hơn 1.1 triệu bản ghi tương tác và hơn 230.000 công thức nấu ăn.
* **Các file sử dụng:**
  * `RAW_interactions.csv`: Lịch sử người dùng đánh giá món ăn.
  * `RAW_recipes.csv`: Thuộc tính công thức nấu ăn.
* *(Ghi chú loại trừ):* Các file phụ như `PP_recipes.csv`, `PP_users.csv`, `ingr_map.pkl`, `interactions_train.csv` bị loại bỏ vì được tiền xử lý sẵn cho mô hình NLP riêng của tác giả gốc, không phản ánh quy trình xử lý Big Data từ dữ liệu thô.

#### Bảng cấu trúc chi tiết: `RAW_interactions.csv`
| Tên cột | Kiểu dữ liệu gốc | Ý nghĩa | Vấn đề chất lượng dữ liệu |
| :--- | :--- | :--- | :--- |
| `user_id` | Integer | ID định danh người dùng | Một số dòng bị lệch cột do ký tự xuống dòng. |
| `recipe_id` | Integer | ID định danh món ăn | Tồn tại các món không còn tồn tại trong bảng recipes. |
| `date` | String (YYYY-MM-DD) | Thời điểm gửi đánh giá | Định dạng text thuần. |
| `rating` | Integer | Điểm số từ 0 đến 5 | **Nhiều dòng mang giá trị 0** (chỉ viết nhận xét, không chấm sao). |
| `review` | String | Văn bản nhận xét | **Chứa ký tự ngắt dòng `\n`, dấu phẩy, dấu nháy kép** gây lỗi đọc CSV. |

#### Bảng cấu trúc chi tiết: `RAW_recipes.csv`
| Tên cột | Kiểu dữ liệu gốc | Ý nghĩa | Vấn đề chất lượng dữ liệu |
| :--- | :--- | :--- | :--- |
| `name` | String | Tên món ăn | Chứa giá trị rỗng (Null). |
| `id` | Integer | ID món ăn | Trùng lặp khóa chính ở một số trường hợp. |
| `minutes` | Integer | Thời gian chế biến (phút) | Có giá trị ngoại lệ phi thực tế (hàng nghìn giờ). |
| `contributor_id`| Integer | ID người đóng góp | Không dùng cho bài toán gợi ý. |
| `submitted` | String | Ngày đăng công thức | Không bắt buộc dùng. |
| `tags` | String (List text) | Thẻ phân loại món | Dạng chuỗi biểu diễn danh sách (`['easy', ...]`). |
| `nutrition` | String (List float)| Calo, chất béo, đường,... | Chuỗi mảng 7 phần tử dinh dưỡng. |
| `n_steps` | Integer | Số bước thực hiện | Cần kiểm tra giá trị âm hoặc 0. |
| `steps` | String (List text) | Chi tiết các bước nấu | Văn bản rất dài, có dấu xuống dòng. |
| `description` | String | Mô tả món ăn | Nhiều giá trị Null. |
| `ingredients` | String (List text) | Danh sách nguyên liệu | Dạng chuỗi mảng text. |
| `n_ingredients`| Integer | Số lượng nguyên liệu | Cần bảo đảm là số nguyên dương. |

---

### 3.2. Bộ dữ liệu Việt Nam (ViFoodRec)
* **Nguồn gốc:** Nghiên cứu khoa học ViFoodRec (ĐH Công nghệ Thông tin - ĐHQG-HCM).
* **Đặc điểm:** Tác giả cung cấp 2 thư mục:
  * `Raw Dataset`: Dữ liệu thô cào tự động từ *Cooky.vn* và *MonNgonMoiNgay*, lẫn mã HTML và cấu trúc chưa chuẩn hóa.
  * `Clean Dataset`: Dữ liệu đã được gộp và chuẩn hóa về 2 file chuẩn `ratings.csv` và `foods.csv`.
* **Quyết định sử dụng:** Nhóm chọn dữ liệu từ `Clean Dataset` để tiến hành chuẩn hóa Big Data sang định dạng Parquet.

#### Bảng cấu trúc chi tiết: `ratings.csv` (Việt Nam)
| Tên cột | Kiểu dữ liệu gốc | Ý nghĩa | Vấn đề chất lượng dữ liệu |
| :--- | :--- | :--- | :--- |
| `user_id` | Integer | ID người dùng | Độ thưa rất cao (nhiều user chỉ tương tác 1 lần). |
| `food_id` | Integer | ID món ăn Việt Nam | Cần đồng bộ khóa ngoại với bảng foods. |
| `rating` | Float / Integer | Điểm số đánh giá (1-5) | Cần lọc biên giá trị ngoài khoảng $[1, 5]$. |

#### Bảng cấu trúc chi tiết: `foods.csv` (Việt Nam)
| Tên cột | Kiểu dữ liệu gốc | Ý nghĩa | Vấn đề chất lượng dữ liệu |
| :--- | :--- | :--- | :--- |
| `food_id` | Integer | ID món ăn | Một số tên cột có khoảng trắng hoặc viết hoa/thường lộn xộn. |
| `title` / `name`| String | Tên món ăn | Chứa ký tự Unicode tiếng Việt có dấu. |
| `ingredients` | String | Danh sách nguyên liệu | Văn bản tiếng Việt mô tả nguyên liệu. |
| `instructions` | String | Hướng dẫn chế biến | Văn bản hướng dẫn chi tiết. |

---

## 4. Các quy tắc tiền xử lý và làm sạch dữ liệu

Nhằm đảm bảo mô hình ALS hội tụ chính xác và dữ liệu có thể tính toán phân tán hiệu quả, nhóm đã thống nhất và áp dụng 4 quy tắc cốt lõi:

### Quy tắc 1: Loại bỏ đánh giá $rating = 0$
* **Bối cảnh:** Thuật toán ALS trong Spark MLlib hoạt động trên cơ chế **Explicit Feedback** (phản hồi tường minh), xem điểm số phản ánh mức độ ưa thích từ thấp đến cao.
* **Xử lý:** Bộ dữ liệu Food.com chứa số lượng lớn bản ghi có $rating = 0$ do người dùng chỉ bình luận mà không bấm sao. Nếu giữ lại, mô hình sẽ coi đây là đánh giá "cực kỳ ghét", gây lệch hàm mất mát. Do đó, toàn bộ dòng có $rating = 0$ bị loại bỏ, chỉ giữ lại thang điểm hợp lệ:
$$rating \in [1, 5]$$

### Quy tắc 2: Lọc giảm độ thưa ma trận (K-Core Filtering với $K = 3$)
* **Bối cảnh:** Hiện tượng "người dùng ma" (chỉ đánh giá 1 món rồi rời bỏ) và "món ăn cô lập" (chỉ có 1 người chấm điểm) dẫn đến ma trận tương tác có độ thưa (sparsity) vượt quá 99.98%, gây ra lỗi Cold-Start nghiêm trọng và làm sai số $RMSE$ tăng vọt.
* **Xử lý:** Áp dụng lọc K-core hai chiều:
  $$\text{Count}(interactions)_{user} \ge 3 \quad \text{và} \quad \text{Count}(interactions)_{recipe} \ge 3$$

### Quy tắc 3: Xử lý giá trị rỗng ($Null/NaN$) và Trùng lặp ($Duplicates$)
* Loại bỏ tất cả các dòng thiếu khóa chính hoặc thiếu biến mục tiêu:
  $$\text{dropna}(\text{subset} = [user\_id, recipe\_id, rating])$$
* Loại bỏ các đánh giá trùng lặp từ cùng một người dùng trên cùng một món ăn:
  $$\text{dropDuplicates}([user\_id, recipe\_id])$$

### Quy tắc 4: Chuẩn hóa kiểu dữ liệu nghiêm ngặt
* Ép kiểu trường khóa sang `Integer` để tối ưu hóa bộ nhớ và tương thích thuật toán ALS.
* Ép kiểu trường điểm số sang `Float`.
* Chuẩn hóa tên các cột về dạng chữ thường không dấu (`lower()`, `strip()`).

---

## 5. Nhật ký kỹ thuật: Các lỗi phát sinh và giải pháp khắc phục

Trong quá trình thực nghiệm trên môi trường Docker và Spark, nhóm đã ghi nhận và giải quyết 4 nhóm lỗi kỹ thuật quan trọng:

```text
[Lỗi 1: Compose Trống] ──> [Lỗi 2: Thiếu PySpark] ──> [Lỗi 3: Lỗi Chính Tả Code] ──> [Lỗi 4: Ngắt Dòng Multi-line]
       │                            │                            │                            │
       ▼                            ▼                            ▼                            ▼
 Lưu file yml             Khai báo PYTHONPATH         Sửa .cast(), .mode()       Bật multiLine=True & tắt ANSI
```

### Lỗi 1: Docker báo lỗi `empty compose file`
* **Hiện tượng:** Khi chạy `docker compose up -d`, Terminal thông báo `empty compose file`.
* **Nguyên nhân:** File `docker-compose.yml` được tạo nhưng chưa lưu nội dung (dung lượng 0 bytes) trước khi thực thi lệnh.
* **Giải pháp khắc phục:** Cập nhật đầy đủ cấu hình service `spark-notebook` và lưu file (`Ctrl + S`).

### Lỗi 2: `ModuleNotFoundError: No module named 'pyspark'`
* **Hiện tượng:** Chạy lệnh `docker exec -it bigdata_spark_env python src/clean_food_com.py` bị văng lỗi không tìm thấy thư viện `pyspark`.
* **Nguyên nhân:** Image `quay.io/jupyter/pyspark-notebook` cài đặt Apache Spark độc lập tại `/usr/local/spark` thay vì cài vào thư viện Python mặc định của hệ thống Linux. Lệnh `python` độc lập không nhận diện được đường dẫn Spark nếu không khởi tạo từ Jupyter.
* **Giải pháp khắc phục:** Cập nhật biến môi trường trực tiếp vào `docker-compose.yml`:
  ```yaml
  environment:
    - SPARK_HOME=/usr/local/spark
    - PYTHONPATH=/usr/local/spark/python:/usr/local/spark/python/lib/py4j-0.10.9.9-src.zip
  ```

### Lỗi 3: Các lỗi chính tả cú pháp (Typo) trong file script
* **Hiện tượng:** Script dừng đột ngột ở các giai đoạn xử lý DataFrame.
* **Các vị trí đã sửa đổi:**
  * Dòng 52: Sửa `.moxle("overwrite")` thành `.mode("overwrite")`.
  * Dòng 58: Sửa `subsel=["id", "name"]` thành `subset=["id", "name"]`.
  * Dòng 65: Sửa `.casl("integer")` thành `.cast("integer")`.

### Lỗi 4: `NumberFormatException: The value 'too.' cannot be cast to BIGINT`
* **Hiện tượng:** Quá trình quét DataFrame dừng tại dòng 28 với thông báo giá trị chuỗi `'too.'` không thể chuyển thành số nguyên lớn.
* **Nguyên nhân:**
  1. Trong cột `review`, người dùng gõ phím *Enter* tạo ký tự ngắt dòng `\n`. Trình đọc CSV mặc định ngắt dòng tại ký tự này, khiến từ `'too.'` bị đẩy sang đầu dòng tiếp theo và rơi vào cột `user_id`.
  2. Spark ở chế độ **ANSI SQL Mode** mặc định (`spark.sql.ansi.enabled = true`) sẽ tự động ngắt chương trình khi gặp dữ liệu không khớp kiểu thay vì gán giá trị `NULL`.
* **Giải pháp khắc phục triệt để:**
  1. Bật tính năng đọc văn bản đa dòng và ký tự thoát:
     ```python
     spark.read.csv(..., multiLine=True, escape='"')
     ```
  2. Tắt chế độ ANSI nghiêm ngặt khi khởi tạo SparkSession để các giá trị rác tự động chuyển về `NULL` và bị loại bỏ an toàn qua `dropna()`:
     ```python
     .config("spark.sql.ansi.enabled", "false")
     ```

---

## 6. Cấu trúc dữ liệu chuẩn hóa đầu ra (.parquet)

### 6.1. Tại sao chuyển đổi sang định dạng Parquet?
* **Tối ưu hóa lưu trữ:** Parquet là định dạng lưu trữ dạng cột (Columnar Storage), tự động tích hợp thuật toán nén Snappy giúp giảm từ **60% đến 80% dung lượng** so với CSV gốc.
* **Hiệu năng truy vấn phân tán:** Khi nạp vào Spark để huấn luyện mô hình ALS, cơ chế nạp theo cột (Projection Pushdown) và lọc phân vùng (Predicate Pushdown) giúp Spark chỉ đọc đúng các cột `user_id`, `recipe_id`, `rating` mà không cần đọc toàn bộ văn bản review, tăng tốc độ xử lý lên gấp nhiều lần.

### 6.2. Schema chuẩn của các bảng Parquet sau làm sạch

#### 1. Bảng `interactions.parquet` (Food.com)
* Lưu trữ tại: `data/processed/food_com/interactions.parquet`
* Cấu trúc:
  ```text
  root
   |-- user_id: integer (nullable = true)
   |-- recipe_id: integer (nullable = true)
   |-- rating: float (nullable = true)
   |-- date: string (nullable = true)
  ```

#### 2. Bảng `recipes.parquet` (Food.com)
* Lưu trữ tại: `data/processed/food_com/recipes.parquet`
* Cấu trúc:
  ```text
  root
   |-- recipe_id: integer (nullable = true)
   |-- name: string (nullable = true)
   |-- minutes: integer (nullable = true)
   |-- n_steps: integer (nullable = true)
   |-- n_ingredients: integer (nullable = true)
   |-- ingredients: string (nullable = true)
   |-- nutrition: string (nullable = true)
  ```

#### 3. Bảng `ratings.parquet` (Việt Nam)
* Lưu trữ tại: `data/processed/food_vietnam/ratings.parquet`
* Cấu trúc:
  ```text
  root
   |-- user_id: integer (nullable = true)
   |-- food_id: integer (nullable = true)
   |-- rating: float (nullable = true)
  ```

#### 4. Bảng `foods.parquet` (Việt Nam)
* Lưu trữ tại: `data/processed/food_vietnam/foods.parquet`
* Cấu trúc: Chứa mã món ăn `food_id`, tên món và danh sách nguyên liệu tiếng Việt đã được làm sạch và loại bỏ trùng lặp.

---

## 7. Mã nguồn hoàn chỉnh và Hướng dẫn thực thi

### 7.1. Cấu hình Docker Compose (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  spark-notebook:
    image: quay.io/jupyter/pyspark-notebook:latest
    container_name: bigdata_spark_env
    user: root
    environment:
      - JUPYTER_TOKEN=bigdata
      - GRANT_SUDO=yes
      - SPARK_HOME=/usr/local/spark
      - PYTHONPATH=/usr/local/spark/python:/usr/local/spark/python/lib/py4j-0.10.9.9-src.zip
    ports:
      - "8888:8888"   # Cổng giao diện Web Jupyter Notebook
      - "4040:4040"   # Cổng giám sát tác vụ Spark Web UI
    volumes:
      - ./:/home/jovyan/work
    working_dir: /home/jovyan/work
```

---

### 7.2. Script tiền xử lý dữ liệu Food.com (`src/clean_food_com.py`)

```python
"""
PIPELINE TIỀN XỬ LÝ VÀ CHUẨN HÓA DỮ LIỆU FOOD.COM
Học phần: Nhập môn Big Data
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count

def clean_food_com():
    print("=" * 60)
    print(">>> [1/5] KHỞI TẠO SPARK SESSION VỚI CẤU HÌNH TỐI ƯU...")
    print("=" * 60)
    
    spark = SparkSession.builder \
        .appName("Clean_Food_Com_Parquet") \
        .config("spark.driver.memory", "4g") \
        .config("spark.executor.memory", "4g") \
        .config("spark.sql.ansi.enabled", "false") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")

    # Đường dẫn tệp dữ liệu
    raw_inter_path = "data/raw/food_com/RAW_interactions.csv"
    raw_recipes_path = "data/raw/food_com/RAW_recipes.csv"
    
    out_inter_path = "data/processed/food_com/interactions.parquet"
    out_recipes_path = "data/processed/food_com/recipes.parquet"

    # ---------------------------------------------------------
    # GIAI ĐOẠN A: XỬ LÝ INTERACTIONS (LỊCH SỬ ĐÁNH GIÁ)
    # ---------------------------------------------------------
    print("\n>>> [2/5] ĐỌC VÀ LÀM SẠCH RAW_INTERACTIONS...")
    df_inter = spark.read.csv(
        raw_inter_path, 
        header=True, 
        inferSchema=True, 
        multiLine=True, 
        escape='"'
    )
    
    raw_count = df_inter.count()
    print(f"    * Tổng số dòng ban đầu: {raw_count:,}")

    # Lọc giá trị rỗng, lọc thang điểm [1, 5] và loại bỏ bản ghi trùng lặp
    cleaned_inter = df_inter \
        .dropna(subset=["user_id", "recipe_id", "rating"]) \
        .filter((col("rating") >= 1) & (col("rating") <= 5)) \
        .select(
            col("user_id").cast("integer"),
            col("recipe_id").cast("integer"),
            col("rating").cast("float"),
            col("date").cast("string")
        ) \
        .dropDuplicates(["user_id", "recipe_id"])

    # Lọc K-Core = 3 (Giữ lại User và Recipe có >= 3 đánh giá)
    print("    * Áp dụng bộ lọc K-Core (k >= 3)...")
    user_counts = cleaned_inter.groupBy("user_id").agg(count("recipe_id").alias("user_cnt"))
    valid_users = user_counts.filter(col("user_cnt") >= 3).select("user_id")

    recipe_counts = cleaned_inter.groupBy("recipe_id").agg(count("user_id").alias("recipe_cnt"))
    valid_recipes = recipe_counts.filter(col("recipe_cnt") >= 3).select("recipe_id")

    final_inter = cleaned_inter \
        .join(valid_users, on="user_id", how="inner") \
        .join(valid_recipes, on="recipe_id", how="inner")

    clean_count = final_inter.count()
    print(f"    * Số lượng bản ghi sau làm sạch và lọc K-core: {clean_count:,}")

    print(f">>> [3/5] GHI DỮ LIỆU INTERACTIONS RA PARQUET: {out_inter_path}")
    final_inter.write.mode("overwrite").parquet(out_inter_path)

    # ---------------------------------------------------------
    # GIAI ĐOẠN B: XỬ LÝ RECIPES (THÔNG TIN CÔNG THỨC MÓN ĂN)
    # ---------------------------------------------------------
    print("\n>>> [4/5] ĐỌC VÀ LÀM SẠCH RAW_RECIPES...")
    df_recipes = spark.read.csv(
        raw_recipes_path, 
        header=True, 
        inferSchema=True, 
        multiLine=True, 
        escape='"'
    )

    cleaned_recipes = df_recipes \
        .dropna(subset=["id", "name"]) \
        .select(
            col("id").cast("integer").alias("recipe_id"),
            col("name").cast("string"),
            col("minutes").cast("integer"),
            col("n_steps").cast("integer"),
            col("n_ingredients").cast("integer"),
            col("ingredients").cast("string"),
            col("nutrition").cast("string")
        ) \
        .dropDuplicates(["recipe_id"])

    recipes_count = cleaned_recipes.count()
    print(f"    * Số lượng công thức hợp lệ: {recipes_count:,}")

    print(f">>> [5/5] GHI DỮ LIỆU RECIPES RA PARQUET: {out_recipes_path}")
    cleaned_recipes.write.mode("overwrite").parquet(out_recipes_path)

    print("\n" + "=" * 60)
    print("HOÀN TẤT THÀNH CÔNG QUY TRÌNH TIỀN XỬ LÝ FOOD.COM!")
    print("=" * 60)
    spark.stop()

if __name__ == "__main__":
    clean_food_com()
```

---

### 7.3. Script tiền xử lý dữ liệu Việt Nam (`src/clean_vietnam.py`)

```python
"""
PIPELINE TIỀN XỬ LÝ VÀ CHUẨN HÓA DỮ LIỆU MÓN ĂN VIỆT NAM (VIFOODREC)
Học phần: Nhập môn Big Data
"""

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count

def clean_food_vietnam():
    print("=" * 60)
    print(">>> [1/4] KHỞI TẠO SPARK CHO DỮ LIỆU VIỆT NAM...")
    print("=" * 60)

    spark = SparkSession.builder \
        .appName("Clean_Food_VN_Parquet") \
        .config("spark.driver.memory", "2g") \
        .config("spark.sql.ansi.enabled", "false") \
        .getOrCreate()
        
    spark.sparkContext.setLogLevel("WARN")

    raw_ratings_path = "data/raw/food_vietnam/ratings.csv"
    raw_foods_path = "data/raw/food_vietnam/foods.csv"
    
    out_ratings_path = "data/processed/food_vietnam/ratings.parquet"
    out_foods_path = "data/processed/food_vietnam/foods.parquet"

    # ---------------------------------------------------------
    # GIAI ĐOẠN A: XỬ LÝ RATINGS VIỆT NAM
    # ---------------------------------------------------------
    print("\n>>> [2/4] XỬ LÝ RATINGS.CSV...")
    df_ratings = spark.read.csv(raw_ratings_path, header=True, inferSchema=True)

    # Chuẩn hóa tên cột
    for c in df_ratings.columns:
        df_ratings = df_ratings.withColumnRenamed(c, c.strip().lower())

    cleaned_ratings = df_ratings \
        .dropna(subset=["user_id", "food_id", "rating"]) \
        .filter((col("rating") >= 1) & (col("rating") <= 5)) \
        .select(
            col("user_id").cast("integer"),
            col("food_id").cast("integer"),
            col("rating").cast("float")
        ) \
        .dropDuplicates(["user_id", "food_id"])

    # Lọc K-Core = 3
    user_counts = cleaned_ratings.groupBy("user_id").agg(count("food_id").alias("user_cnt"))
    valid_users = user_counts.filter(col("user_cnt") >= 3).select("user_id")

    food_counts = cleaned_ratings.groupBy("food_id").agg(count("user_id").alias("food_cnt"))
    valid_foods = food_counts.filter(col("food_cnt") >= 3).select("food_id")

    final_ratings = cleaned_ratings \
        .join(valid_users, on="user_id", how="inner") \
        .join(valid_foods, on="food_id", how="inner")

    print(f"    * Số lượng đánh giá Việt Nam sau làm sạch: {final_ratings.count():,}")
    print(f"    * Lưu kết quả vào: {out_ratings_path}")
    final_ratings.write.mode("overwrite").parquet(out_ratings_path)

    # ---------------------------------------------------------
    # GIAI ĐOẠN B: XỬ LÝ FOODS VIỆT NAM
    # ---------------------------------------------------------
    print("\n>>> [3/4] XỬ LÝ FOODS.CSV...")
    df_foods = spark.read.csv(raw_foods_path, header=True, inferSchema=True)
    for c in df_foods.columns:
        df_foods = df_foods.withColumnRenamed(c, c.strip().lower())

    id_col = "food_id" if "food_id" in df_foods.columns else df_foods.columns[0]
    cleaned_foods = df_foods.dropna(subset=[id_col]).dropDuplicates([id_col])

    print(f"    * Số lượng món ăn Việt Nam hợp lệ: {cleaned_foods.count():,}")
    print(f"    * Lưu kết quả vào: {out_foods_path}")
    cleaned_foods.write.mode("overwrite").parquet(out_foods_path)

    print("\n" + "=" * 60)
    print("HOÀN TẤT THÀNH CÔNG QUY TRÌNH TIỀN XỬ LÝ FOOD VIỆT NAM!")
    print("=" * 60)
    spark.stop()

if __name__ == "__main__":
    clean_food_vietnam()
```

---

### 7.4. Hướng dẫn các bước vận hành hệ thống

Mở cửa sổ Terminal tại thư mục gốc `bigdata-food` trên máy tính và thực hiện tuần tự:

* **Bước 1: Khởi động cụm container Spark:**
  ```bash
  docker compose up -d
  ```
* **Bước 2: Chạy tiến trình làm sạch tập dữ liệu quốc tế Food.com:**
  ```bash
  docker exec -it bigdata_spark_env python src/clean_food_com.py
  ```
* **Bước 3: Chạy tiến trình làm sạch tập dữ liệu Việt Nam:**
  ```bash
  docker exec -it bigdata_spark_env python src/clean_vietnam.py
  ```
* **Bước 4: Kiểm tra kết quả tạo ra trên máy tính:**
  Kiểm tra thư mục `data/processed/`, đảm bảo cả 4 thư mục Parquet (`interactions.parquet`, `recipes.parquet`, `ratings.parquet`, `foods.parquet`) đã được sinh ra đầy đủ các file dữ liệu phân mảnh dạng cột (`part-*.snappy.parquet`) cùng file `_SUCCESS`.

---

## 8. Kế hoạch các bước tiếp theo

| Tuần | Nội dung triển khai | Kết quả dự kiến |
| :---: | :--- | :--- |
| **Tuần 6 – 7** | • Xây dựng mô hình Baseline (gợi ý theo độ phổ biến / trung bình rating).<br>• Phân tích EDA ban đầu (so sánh phân phối điểm, thói quen ăn uống giữa 2 nền ẩm thực).<br>• Hoàn thiện báo cáo tiến độ Giai đoạn 1. | • Mã nguồn Baseline Model.<br>• File báo cáo tiến độ nộp đợt 1. |
| **Tuần 8 – 9** | • Huấn luyện mô hình ALS trên Spark MLlib với các tham số `rank`, `regParam`, `maxIter`.<br>• Đo lường sai số $RMSE$, $MAE$ và so sánh hiệu năng giữa Food.com và ViFoodRec.<br>• Xây dựng giao diện Web Dashboard tương tác bằng Streamlit. | • File model ALS đã lưu.<br>• Dashboard hoàn chỉnh chạy cổng 8501.<br>• Bản thảo Báo cáo cuối kỳ (Word) & Slide. |
| **Tuần 10** | • Chạy thử nghiệm toàn bộ hệ thống, chuẩn bị kịch bản thuyết trình và phản biện đồ án. | • Buổi thuyết trình đồ án trước hội đồng. |
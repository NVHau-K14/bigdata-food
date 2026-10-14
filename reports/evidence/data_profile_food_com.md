# HỒ SƠ DỮ LIỆU SẠCH (DATA PROFILE): FOOD.COM RECIPES & INTERACTIONS

- **Tập dữ liệu:** Food.com (Kaggle Recipes with Ratings and Reviews)
- **Giai đoạn:** Sau làm sạch chuẩn hóa P3 (K-core lặp K=3, khử trùng lặp, chuẩn hóa dinh dưỡng)
- **Định dạng lưu trữ:** Parquet Snappy trên HDFS (`hdfs://namenode:9000/data/clean/food_com/`)

---

## 1. Thống kê tổng quan ma trận tương tác

| Chỉ số | Giá trị đo được | Ghi chú |
|---|---|---|
| **Số lượng tương tác sạch (`interactions_clean`)** | **706,514** dòng | Giảm từ 1,132,367 dòng thô (loại 60,847 rating=0 và 365,006 dòng qua 5 vòng K-core) |
| **Số User duy nhất (`user_id`)** | **30,836** users | Mỗi user có tối thiểu 3 đánh giá |
| **Số Món duy nhất có tương tác (`recipe_id`)** | **78,171** recipes | Mỗi món có tối thiểu 3 lượt đánh giá |
| **Tổng số món trong danh mục (`recipes_clean`)** | **231,636** recipes | Gồm 78,171 món có rating (`has_ratings=true`) và 153,465 món chưa có rating (`has_ratings=false`) |
| **Độ thưa của ma trận (Sparsity)** | **99.9707%** | $1 - \frac{706,514}{30,836 \times 78,171} = 0.9997069$ (ma trận cực thưa) |

---

## 2. Phân phối điểm đánh giá (Rating Distribution)

Toàn bộ các bản ghi rating = 0 (tương tác không chấm điểm) và điểm ngoài khoảng [1, 5] đã được loại bỏ.

| Mức điểm (Rating) | Số lượng bản ghi | Tỷ lệ phần trăm | Biểu đồ thanh |
|:---:|:---:|:---:|---|
| **1.0 ⭐** | 3,735 | 0.53% | █ |
| **2.0 ⭐** | 6,998 | 0.99% | ██ |
| **3.0 ⭐** | 23,799 | 3.37% | ████ |
| **4.0 ⭐** | 118,092 | 16.71% | ████████████████ |
| **5.0 ⭐** | 553,890 | **78.40%** | ██████████████████████████████████████████████████ |
| **Tổng** | **706,514** | **100.0%** | Điểm trung bình: **4.71 ⭐** |

> **Nhận xét nghiệp vụ:** Dữ liệu Food.com có độ lệch dương cực mạnh (skewed towards 5-star ratings). Gần 78.4% lượt tương tác đạt điểm tối đa 5 sao. Đây là đặc trưng tâm lý phổ biến trên các nền tảng ẩm thực (người dùng chỉ chủ động đánh giá khi thử nghiệm món thành công hoặc thích thú).

---

## 3. Thống kê mức độ hoạt động của User và Món ăn

| Tiêu chí | Min (K-core) | Phân vị 25% | **Trung vị (50%)** | Trung bình (Mean) | Phân vị 75% | Phân vị 90% | Phân vị 99% | Max |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Số tương tác / User** | **3** | 4 | **6** | 22.91 | 14 | 36 | 310 | 3,952 |
| **Số tương tác / Recipe** | **3** | 3 | **5** | 9.04 | 8 | 16 | 74 | 1,138 |

- **User hoạt động nhiều nhất:** User ID có 3,952 lượt đánh giá.
- **Recipe phổ biến nhất:** Recipe ID có 1,138 lượt đánh giá.
- Cả hai chiều đều thỏa mãn điều kiện $K \ge 3$, giải quyết triệt để vấn đề "Cold Start" cho thuật toán Collaborative Filtering (ALS).

---

## 4. Phân vị các thuộc tính số của bảng công thức nấu ăn (`recipes_clean`)

Ngưỡng ngoại lai `minutes_clean` được quy định tại `src/config.py` với `MAX_MINUTES_THRESHOLD = 1440` (24 giờ). Các bản ghi thời gian nấu $\le 0$ hoặc $> 1440$ phút được chuyển thành `NULL` ở cột `minutes_clean` nhưng vẫn lưu giá trị gốc ở `minutes`.

| Thuộc tính | Đơn vị | Min | 1% | 25% | **Trung vị (50%)** | 75% | 99% | Ngưỡng lọc |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `minutes_clean` | Phút | 1 | 2 | 20 | **40** | 65 | 505 | 1,440 |
| `n_steps` | Bước | 1 | 1 | 6 | **9** | 12 | 30 | Không lọc |
| `n_ingredients` | Nguyên liệu | 1 | 3 | 6 | **9** | 11 | 20 | Không lọc |
| `calories` | kcal | 0.0 | 18.3 | 174.3 | **313.4** | 519.6 | 3,505.6 | Không lọc |
| `total_fat_pdv` | % PDV | 0.0 | 0.0 | 8.0 | **20.0** | 41.0 | 301.0 | Không lọc |
| `sugar_pdv` | % PDV | 0.0 | 0.0 | 9.0 | **25.0** | 68.0 | 1,135.0 | Không lọc |
| `protein_pdv` | % PDV | 0.0 | 0.0 | 7.0 | **18.0** | 51.0 | 187.0 | Không lọc |

---

## 5. Cấu trúc Schema bảng Parquet

### `interactions_clean.parquet`
```text
root
 |-- user_id: integer (nullable = true)
 |-- recipe_id: integer (nullable = true)
 |-- date: date (nullable = true)
 |-- rating: float (nullable = true)
```

### `recipes_clean.parquet`
```text
root
 |-- recipe_id: integer (nullable = true)
 |-- name: string (nullable = true)
 |-- minutes: integer (nullable = true)
 |-- minutes_clean: integer (nullable = true)
 |-- contributor_id: integer (nullable = true)
 |-- submitted: date (nullable = true)
 |-- n_steps: integer (nullable = true)
 |-- n_ingredients: integer (nullable = true)
 |-- calories: float (nullable = true)
 |-- total_fat_pdv: float (nullable = true)
 |-- sugar_pdv: float (nullable = true)
 |-- sodium_pdv: float (nullable = true)
 |-- protein_pdv: float (nullable = true)
 |-- saturated_fat_pdv: float (nullable = true)
 |-- carbohydrates_pdv: float (nullable = true)
 |-- tags: array (nullable = true)
 |    |-- element: string (containsNull = true)
 |-- ingredients: array (nullable = true)
 |    |-- element: string (containsNull = true)
 |-- has_ratings: boolean (nullable = false)
```

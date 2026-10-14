# Hồ sơ dữ liệu sạch: ViFoodRec (món ăn Việt Nam)

- **Tập dữ liệu:** ViFoodRec (danh mục món ăn và đánh giá món Việt Nam).
- **Giai đoạn:** sau làm sạch lại ở stage S2 (14/10/2026): giữ toàn bộ thang điểm 0,0 đến 5,0; chỉ loại dòng có `food_id` không có trong danh mục món; chuẩn hóa dinh dưỡng và văn bản.
- **Định dạng lưu trữ:** Parquet Snappy trên HDFS (`hdfs://namenode:9000/data/clean/food_vietnam/`, lưu dạng `coalesce(1)`).
- **Nguồn số liệu:** `reports/evidence/logs/S2_05_stats_clean.log` (tính từ `ratings_clean.parquet` và `foods_clean.parquet`) và `reports/evidence/cleaning_log.csv`. Mục 4 và 5 (món ăn, schema) giữ từ bản P3 vì bảng `foods_clean` không đổi.
- Bản P3 cũ (loại 0,0 và 0,5, 149.431 dòng) nằm ở `backup_v2_truoc_S2/reports_evidence/`.

---

## 1. Thống kê tổng quan ma trận tương tác

| Chỉ số | Giá trị đo được | Ghi chú |
|---|---|---|
| Số đánh giá sạch (`ratings_clean`) | **182.631** dòng | Từ 182.678 dòng thô: loại 47 dòng có `food_id` = 4000 (không có trong danh mục) |
| Số người dùng (`user_id`) | **101** | `user_id` từ 0 đến 100 |
| Số món có đánh giá (`food_id`) | **4.000** | `food_id` từ 0 đến 3999; mọi món trong danh mục đều có đánh giá |
| Số món trong danh mục (`foods_clean`) | **4.000** | Cờ `has_ratings` đều đúng |
| Độ thưa của ma trận | **54,7943%** | 1 − 182.631 / (101 × 4.000) |

---

## 2. Phân phối điểm đánh giá

Dữ liệu sạch có đủ 11 mức điểm (0,0 đến 5,0, bước 0,5). Mỗi mức chiếm từ 8,99% đến 9,23% số dòng.

| Mức điểm | Số dòng | Tỷ lệ |
|:---:|---:|---:|
| 0,0 | 16.503 | 9,04% |
| 0,5 | 16.697 | 9,14% |
| 1,0 | 16.418 | 8,99% |
| 1,5 | 16.849 | 9,23% |
| 2,0 | 16.596 | 9,09% |
| 2,5 | 16.654 | 9,12% |
| 3,0 | 16.568 | 9,07% |
| 3,5 | 16.615 | 9,10% |
| 4,0 | 16.615 | 9,10% |
| 4,5 | 16.516 | 9,04% |
| 5,0 | 16.600 | 9,09% |
| **Tổng** | **182.631** | điểm trung bình 2,4996; độ lệch chuẩn 1,5798 |

Nhận xét có số: phân phối gần đều trên 11 mức. Độ lệch chuẩn của phân phối đều lý thuyết trên 11 mức bước 0,5 là 1,5811; giá trị đo được 1,5798. Chưa có kiểm định nào về cách dữ liệu được tạo ra, nên không kết luận về nguồn gốc (xem `stage_S2.md`, mục 2).

---

## 3. Thống kê mức độ hoạt động của người dùng và món ăn

| Tiêu chí | Nhỏ nhất | Phân vị 25% | **Trung vị** | Trung bình | Phân vị 75% | Phân vị 90% | Phân vị 99% | Lớn nhất |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Số đánh giá mỗi người dùng | 1.641 | 1.733 | **1.795** | 1.808,2 | 1.875 | 1.953 | 1.985 | 1.989 |
| Số đánh giá mỗi món | 27 | 42 | **46** | 45,66 | 49 | 52 | 58 | 68 |

- Mỗi người dùng đánh giá trung bình khoảng 1.808 món (khoảng 45% danh mục 4.000 món).
- Cả hai chiều vượt xa ngưỡng K-core = 3 (1.641 và 27), nên K-core hội tụ ngay ở vòng 1 và không loại thêm dòng nào.

---

## 4. Phân loại món ăn và thống kê thuộc tính số (`foods_clean`)

### 4.1. Phân bố loại món (`dish_type`)

| Loại món | Số lượng món | Tỷ lệ (%) |
|---|:---:|:---:|
| **Món mặn** | 3,805 | 95.12% |
| **Món chay** | 195 | 4.88% |
| **Tổng** | **4,000** | **100.0%** |

### 4.2. Phân vị các thuộc tính dinh dưỡng và định lượng

| Thuộc tính | Đơn vị | Min | 1% | 25% | **Trung vị (50%)** | 75% | 99% | Max |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| `cooking_time_min` | Phút | 10 | 15 | 25 | **35** | 45 | 50 | 60 |
| `serving_size_num` | Người | 1 | 1 | 2 | **4** | 4 | 8 | 10 |
| `calories` | kcal | 100.0 | 184.0 | 286.0 | **386.0** | 494.0 | 596.0 | 600.0 |
| `fat` | gam | 5.0 | 10.0 | 17.0 | **25.0** | 33.0 | 40.0 | 50.0 |
| `fiber` | gam | 1.0 | 3.0 | 5.0 | **6.0** | 8.0 | 10.0 | 15.0 |
| `sugar` | gam | 5.0 | 10.0 | 15.0 | **20.0** | 25.0 | 30.0 | 40.0 |
| `protein` | gam | 2.0 | 5.0 | 13.0 | **23.0** | 32.0 | 40.0 | 50.0 |

---

## 5. Cấu trúc Schema bảng Parquet

### `ratings_clean.parquet`
```text
root
 |-- user_id: integer (nullable = true)
 |-- food_id: integer (nullable = true)
 |-- rating: float (nullable = true)
```

### `foods_clean.parquet`
```text
root
 |-- food_id: integer (nullable = true)
 |-- dish_name: string (nullable = true)
 |-- description: string (nullable = true)
 |-- dish_type: string (nullable = true)
 |-- serving_size: string (nullable = true)
 |-- serving_size_num: integer (nullable = true)
 |-- cooking_time: string (nullable = true)
 |-- cooking_time_min: integer (nullable = true)
 |-- ingredients: string (nullable = true)
 |-- cooking_method: string (nullable = true)
 |-- dish_tags: array (nullable = true)
 |    |-- element: string (containsNull = true)
 |-- calories: float (nullable = true)
 |-- fat: float (nullable = true)
 |-- fiber: float (nullable = true)
 |-- sugar: float (nullable = true)
 |-- protein: float (nullable = true)
 |-- image_link: string (nullable = true)
 |-- nutrient_content: string (nullable = true)
 |-- is_duplicate: boolean (nullable = false)
 |-- has_ratings: boolean (nullable = false)
```

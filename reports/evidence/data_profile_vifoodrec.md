# HỒ SƠ DỮ LIỆU SẠCH (DATA PROFILE): VIFOODREC (MÓN ĂN VIỆT NAM)

- **Tập dữ liệu:** ViFoodRec (Tập dữ liệu đánh giá và danh mục món ăn Việt Nam)
- **Giai đoạn:** Sau làm sạch chuẩn hóa P3 (Loại bỏ điểm < 1.0, loại bỏ lỗi khóa ngoại food_id=4000, chuẩn hóa dinh dưỡng và văn bản)
- **Định dạng lưu trữ:** Parquet Snappy trên HDFS (`hdfs://namenode:9000/data/clean/food_vietnam/`, lưu dạng `coalesce(1)`)

---

## 1. Thống kê tổng quan ma trận tương tác

| Chỉ số | Giá trị đo được | Ghi chú |
|---|---|---|
| **Số lượng đánh giá sạch (`ratings_clean`)** | **149,431** dòng | Giảm từ 182,678 dòng thô (loại 33,211 dòng rating 0.0 & 0.5; loại 36 dòng lỗi ngoại lai food_id=4000) |
| **Số User duy nhất (`user_id`)** | **101** users | User ID từ 0 đến 100 |
| **Số Món ăn có tương tác (`food_id`)** | **4,000** món | Food ID từ 0 đến 3999 (100% món trong danh mục đều có đánh giá) |
| **Tổng số món trong danh mục (`foods_clean`)** | **4,000** món | Toàn bộ 4,000 món đều có cờ `has_ratings = true` |
| **Độ thưa của ma trận (Sparsity)** | **63.0121%** | $1 - \frac{149,431}{101 \times 4,000} = 0.630121$ (ma trận dày, mật độ tương tác rất cao) |

---

## 2. Phân phối điểm đánh giá (Rating Distribution)

Sau khi loại bỏ 16,509 dòng rating 0.0 và 16,702 dòng rating 0.5 (tổng 33,211 dòng điểm $< 1.0$), tập dữ liệu còn lại 9 mức điểm phân bố hoàn toàn đồng đều:

| Mức điểm (Rating) | Số lượng bản ghi | Tỷ lệ phần trăm | Biểu đồ thanh |
|:---:|:---:|:---:|---|
| **1.0 ⭐** | 16,418 | 10.99% | ███████████ |
| **1.5 ⭐** | 16,849 | 11.28% | ███████████ |
| **2.0 ⭐** | 16,596 | 11.11% | ███████████ |
| **2.5 ⭐** | 16,654 | 11.14% | ███████████ |
| **3.0 ⭐** | 16,568 | 11.09% | ███████████ |
| **3.5 ⭐** | 16,615 | 11.12% | ███████████ |
| **4.0 ⭐** | 16,615 | 11.12% | ███████████ |
| **4.5 ⭐** | 16,516 | 11.05% | ███████████ |
| **5.0 ⭐** | 16,600 | 11.11% | ███████████ |
| **Tổng** | **149,431** | **100.0%** | Điểm trung bình: **3.00 ⭐** |

> **Phát hiện quan trọng về dữ liệu ViFoodRec:**
> Phân phối điểm của ViFoodRec là **phân phối đều tuyệt đối (Uniform Distribution)** với bước nhảy 0.5 sao. Mỗi mức điểm chiếm chính xác ~11.1% tổng số bản ghi. Đây là minh chứng rõ ràng cho thấy dữ liệu đánh giá này được sinh bằng thuật toán mô phỏng (Synthetic Data / Simulation) hoặc bộ sinh điểm đồng đều của nhóm tác giả đề tài nghiên cứu ViFoodRec, khác biệt hoàn toàn với phân phối tự nhiên thiên lệch 5 sao của Food.com.

---

## 3. Thống kê mức độ hoạt động của User và Món ăn

| Tiêu chí | Min (K-core) | Phân vị 25% | **Trung vị (50%)** | Trung bình (Mean) | Phân vị 75% | Phân vị 90% | Phân vị 99% | Max |
|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Số đánh giá / User** | **1,334** | 1,420 | **1,469** | 1,479.5 | 1,534 | 1,596 | 1,633 | 1,651 |
| **Số đánh giá / Food** | **20** | 34 | **37** | 37.36 | 41 | 44 | 49 | 55 |

- Mỗi user đánh giá trung bình **1,480 món ăn** (chiếm ~37% toàn bộ menu 4,000 món).
- Mỗi món ăn có trung bình **37.4 lượt đánh giá** (tối thiểu 20 lượt, tối đa 55 lượt).
- Cả hai chiều đều vượt xa ngưỡng K-core = 3 ($1,334 \gg 3$ và $20 \gg 3$), do đó thuật toán K-core hội tụ ngay tại vòng lặp 1 mà không làm mất thêm bất kỳ bản ghi nào!

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

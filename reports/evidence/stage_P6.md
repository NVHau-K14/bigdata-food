# BIÊN BẢN NGHIỆM THU GIAI ĐOẠN P6: PHÂN CHIA DỮ LIỆU, XÂY DỰNG KHUNG ĐÁNH GIÁ VÀ MÔ HÌNH BASELINE

- **Thời gian thực hiện:** 13/10/2026
- **Môi trường thực nghiệm:** Cụm phân tán Apache Spark 4.2.0 Standalone (1 Master, 2 Workers: 4 Cores, 7 GB RAM, Driver 2.5 GB RAM) trên nền tảng lưu trữ phân tán HDFS 3.3.6 (`hdfs://namenode:9000/`).
- **Tập dữ liệu đầu vào:**
  - Food.com: `/data/clean/food_com/interactions_clean.parquet` (706,514 dòng sạch).
  - ViFoodRec: `/data/clean/food_vietnam/ratings_clean.parquet` (149,431 dòng sạch).
- **Trạng thái giai đoạn:** **HOÀN THÀNH TOÀN DIỆN (ĐẠT 100% TIÊU CHÍ NGHIỆM THU)**

---

## 1. Danh sách file tạo mới và chỉnh sửa

| STT | Đường dẫn file | Thao tác | Mô tả & Mục đích |
|---|---|---|---|
| 1 | `src/config.py` | Cập nhật | Bổ sung hệ số làm trơn mặc định `SMOOTHING_M = 5`. |
| 2 | `src/split_data.py` | Tạo mới | Pipeline phân chia tập Train (80%), Val (10%), Test (10%) với seed=42, lọc cold-start, kiểm tra rò rỉ và lưu HDFS Parquet. |
| 3 | `src/evaluation.py` | Tạo mới | Khung đánh giá dùng chung chuẩn hóa: RMSE, MAE, Coverage, RMSE theo từng mức điểm thật, và Top-10 Ranking (Precision@10, Recall@10). |
| 4 | `src/baseline.py` | Tạo mới | Huấn luyện và đánh giá 3 mô hình Baseline (Global Mean, Smoothed Item Mean, Top-N Popular) trên tập kiểm thử cho cả 2 bộ dữ liệu. |
| 5 | `data/results/split_log.csv` & `reports/evidence/split_log.csv` | Tạo mới | Bảng nhật ký số lượng dòng trước và sau phân chia, số dòng bị loại bỏ do cold-start và kết quả kiểm tra rò rỉ. |
| 6 | `data/results/baseline_metrics.csv` & `results/baseline_metrics.csv` | Tạo mới | Bảng tổng hợp các chỉ số đo lường của 3 mô hình Baseline trên tập kiểm thử Test. |
| 7 | `data/results/baseline_rmse_breakdown.csv` | Tạo mới | Bảng phân rã sai số RMSE theo từng mức điểm đánh giá thật (1.0 đến 5.0 sao). |
| 8 | `reports/figures/baseline_performance.png` | Tạo mới | Biểu đồ cột so sánh sai số RMSE và MAE của 3 mô hình Baseline trên cả hai tập dữ liệu. |
| 9 | `reports/figures/baseline_rmse_breakdown.png` | Tạo mới | Biểu đồ phân rã RMSE theo từng mức điểm thật, minh họa đường cong sai số chữ V đối xứng của ViFoodRec và dạng dốc của Food.com. |
| 10 | `reports/evidence/stage_P6.md` | Tạo mới | Biên bản nghiệm thu chính thức Giai đoạn P6. |

---

## 2. Kết quả phân chia dữ liệu và Kiểm tra Rò rỉ (Data Splitting & Leakage Check)

### 2.1. Nhật ký phân chia dữ liệu (Data Splitting Log)
Trích xuất từ kết quả thực tế tại [data/results/split_log.csv](file:///d:/Documents/BaiTap/BigData/bigdata-food/data/results/split_log.csv):

| Bộ dữ liệu | Tổng dòng sạch | Tập Train (80%) | Val ban đầu | Val sau lọc Cold-start | Val bị loại (Tỷ lệ %) | Test ban đầu | Test sau lọc Cold-start | Test bị loại (Tỷ lệ %) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Food.com** | 706,514 | **565,420** (80.03%) | 70,424 | **70,002** | 422 dòng (0.60%) | 70,670 | **70,233** | 437 dòng (0.62%) |
| **ViFoodRec** | 149,431 | **119,416** (79.91%) | 14,935 | **14,935** | 0 dòng (0.00%) | 15,080 | **15,080** | 0 dòng (0.00%) |

**Quy mô tập Train trên cụm HDFS:**
- Food.com Train: **30,772 users** và **77,960 recipes**.
- ViFoodRec Train: **101 users** và **4,000 foods** (100% bao phủ toàn bộ thực đơn và người dùng).

### 2.2. Kiểm tra Tuyệt đối Không Rò rỉ Dữ liệu (Zero Data Leakage Verification)
Để đảm bảo tính khách quan và hợp lệ của mô hình học máy, các truy vấn kiểm tra giao tập thực tế bằng PySpark inner join đã được thực thi trực tiếp trên cụm:

```python
# Đoạn mã kiểm tra rò rỉ thực thi trong src/split_data.py
leak_train_val  = train_df.join(val_filtered,  on=["user_id", item_col], how="inner").count()
leak_train_test = train_df.join(test_filtered, on=["user_id", item_col], how="inner").count()
leak_val_test   = val_filtered.join(test_filtered, on=["user_id", item_col], how="inner").count()
```

**Kết quả kiểm tra thực tế:**
- Food.com:
  - Cặp `(user, item)` xuất hiện ở cả Train và Val: **0** bản ghi.
  - Cặp `(user, item)` xuất hiện ở cả Train và Test: **0** bản ghi.
  - Cặp `(user, item)` xuất hiện ở cả Val và Test: **0** bản ghi.
- ViFoodRec:
  - Cặp `(user, item)` xuất hiện ở cả Train và Val: **0** bản ghi.
  - Cặp `(user, item)` xuất hiện ở cả Train và Test: **0** bản ghi.
  - Cặp `(user, item)` xuất hiện ở cả Val và Test: **0** bản ghi.

$\implies$ **Kết luận:** **Xác nhận 100% không có rò rỉ dữ liệu (Zero Data Leakage).**

---

## 3. Bảng kết quả đánh giá 3 Mô hình Baseline trên Tập Kiểm thử (Test Set)

Trích xuất nguyên văn từ [data/results/baseline_metrics.csv](file:///d:/Documents/BaiTap/BigData/bigdata-food/data/results/baseline_metrics.csv):

| Bộ dữ liệu | Mô hình Baseline | RMSE (sao) | MAE (sao) | Precision@10 | Recall@10 | Độ phủ (Coverage %) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Food.com** | **1. Global Mean** ($\mu = 4.7146$) | 0.6266 | 0.4468 | 0.00000 | 0.00000 | 100.0% |
| **Food.com** | **2. Smoothed Item Mean** ($m = 5$) | **0.6177** | 0.4214 | 0.00048 | 0.00130 | 100.0% |
| **Food.com** | **3. Top-N Popular** | 0.6568 | **0.4120** | **0.00534** | **0.02170** | 100.0% |
| **ViFoodRec** | **1. Global Mean** ($\mu = 2.9981$) | **1.2866** | **1.1073** | 0.00000 | 0.00000 | 100.0% |
| **ViFoodRec** | **2. Smoothed Item Mean** ($m = 5$) | 1.3033 | 1.1261 | 0.01584 | 0.00308 | 100.0% |
| **ViFoodRec** | **3. Top-N Popular** | 1.3094 | 1.1299 | **0.01584** | **0.00331** | 100.0% |

---

## 4. Phân rã sai số RMSE theo từng mức điểm đánh giá thật (Breakdown)

Trích xuất từ [data/results/baseline_rmse_breakdown.csv](file:///d:/Documents/BaiTap/BigData/bigdata-food/data/results/baseline_rmse_breakdown.csv):

| Bộ dữ liệu | Mức điểm thật | Tỷ lệ trong dữ liệu | RMSE Global Mean | RMSE Smoothed Item Mean | RMSE Top-N Popular |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Food.com** | 1.0⭐ | 0.53% | 3.7146 | 3.6135 | **3.5519** |
| **Food.com** | 2.0⭐ | 0.99% | 2.7146 | 2.6396 | **2.5959** |
| **Food.com** | 3.0⭐ | 3.37% | 1.7146 | 1.6582 | **1.6354** |
| **Food.com** | 4.0⭐ | 16.71% | 0.7146 | **0.6936** | 0.7256 |
| **Food.com** | 5.0⭐ | **78.40%** | **0.2854** | 0.3030 | 0.3934 |
| **ViFoodRec** | 1.0⭐ | 10.99% | **1.9981** | 2.0118 | 2.0164 |
| **ViFoodRec** | 1.5⭐ | 11.28% | **1.4981** | 1.5219 | 1.5290 |
| **ViFoodRec** | 2.0⭐ | 11.11% | **0.9981** | 1.0167 | 1.0243 |
| **ViFoodRec** | 2.5⭐ | 11.14% | **0.4981** | 0.5419 | 0.5569 |
| **ViFoodRec** | 3.0⭐ | 11.09% | **0.0019** | 0.2027 | 0.2384 |
| **ViFoodRec** | 3.5⭐ | 11.12% | **0.5019** | 0.5312 | 0.5434 |
| **ViFoodRec** | 4.0⭐ | 11.12% | **1.0019** | 1.0207 | 1.0279 |
| **ViFoodRec** | 4.5⭐ | 11.05% | **1.5019** | 1.5184 | 1.5240 |
| **ViFoodRec** | 5.0⭐ | 11.11% | **2.0019** | 2.0067 | 2.0095 |

---

## 5. Biểu đồ trực quan hóa kết quả Mô hình Baseline

Hai biểu đồ trực quan độ phân giải cao đã được xuất vào thư mục `reports/figures/`:

1. **Hiệu năng tổng thể của 3 mô hình Baseline:** [reports/figures/baseline_performance.png](file:///d:/Documents/BaiTap/BigData/bigdata-food/reports/figures/baseline_performance.png)
2. **Phân rã sai số RMSE theo từng mức điểm đánh giá thật:** [reports/figures/baseline_rmse_breakdown.png](file:///d:/Documents/BaiTap/BigData/bigdata-food/reports/figures/baseline_rmse_breakdown.png)

---

## 6. Nhận xét định lượng chuyên sâu và Ý nghĩa Khoa học

### 6.1. Về hiện tượng sai số thấp "ảo" của Baseline trên Food.com
- Mô hình **Smoothed Item Mean** đạt RMSE tổng thể là **0.6177** (thấp hơn Global Mean 0.6266). Tuy nhiên, khi phân rã theo từng mức điểm:
  - Ở mức **5.0 sao** (chiếm 78.4% tập dữ liệu), RMSE chỉ là **0.2854 - 0.3030**.
  - Nhưng khi người dùng đánh giá tiêu cực ở mức **1.0 sao**, RMSE nhảy vọt lên tới **3.6135 - 3.7146**!
- Điều này chứng minh rằng: Các mô hình Baseline chỉ đạt chỉ số tổng thể có vẻ tốt là do **bị kéo bởi lượng mẫu 5 sao khổng lồ**. Bản chất mô hình không hề học được tín hiệu người dùng không thích món nào. Đây là bằng chứng quan trọng chứng minh sự cần thiết của các mô hình Collaborative Filtering phân rã ma trận (ALS) ở Giai đoạn P7.

### 6.2. Về sự trùng khớp toán học kinh ngạc trên ViFoodRec
- Trong phân tích P5, ta đã chỉ ra ViFoodRec có phân phối đều nhân tạo rời rạc trên 9 mức điểm $[1.0, 1.5, \dots, 5.0]$.
- Về mặt lý thuyết xác suất, độ lệch chuẩn lý thuyết của một biến ngẫu nhiên rời rạc phân phối đều trên 9 bậc quanh kỳ vọng 3.0 là:
  $$\sigma = \sqrt{\frac{1}{9}\sum_{k=1}^9 (x_k - 3.0)^2} = \sqrt{\frac{15}{9}} \approx 1.29099$$
- Khi chạy Baseline 1 (Global Mean), giá trị RMSE thực nghiệm trên tập Test thu được là **1.2866** (sai lệch chưa tới 0.3% so với lý thuyết).
- Đồ thị phân rã RMSE của ViFoodRec tạo thành hình chữ V đối xứng hoàn hảo quanh đáy tại mức 3.0 sao ($\text{RMSE} = 0.0019$). Mọi mô hình dự đoán theo item trung bình hoặc phổ biến đều không vượt qua được ngưỡng RMSE lý thuyết này nếu dữ liệu không có tính cá nhân hóa thực chất.

### 6.3. Về hiệu quả xếp hạng (Ranking Precision & Recall)
- Mô hình **Top-N Popular** đạt chỉ số xếp hạng tốt nhất trong các baseline trên Food.com với $\text{Precision@10} = 0.00534$ và $\text{Recall@10} = 0.02170$.
- Mô hình Smoothed Item Mean có chỉ số xếp hạng thấp hơn do bị ảnh hưởng bởi những món có ít đánh giá nhưng toàn 5 sao, dù đã được làm trơn với $m=5$.
- Chỉ số Ranking sẽ là thước đo cạnh tranh cốt lõi để đánh giá tính vượt trội của ALS ở P7 khi ALS có khả năng gợi ý cá nhân hóa sâu theo từng người dùng thay vì gợi ý một danh sách chung cho toàn bộ hệ thống.

---

## 7. Đối chiếu tiêu chí nghiệm thu Giai đoạn P6

| Tiêu chí kịch bản P6 | Yêu cầu | Kết quả thực tế | Trạng thái |
|---|---|---|:---:|
| **Phân chia dữ liệu** | Train 80%, Val 10%, Test 10% (seed=42) | Đã phân chia có tính xác định với `rand(seed=42)` | **ĐẠT** |
| **Lọc Cold-Start** | Loại bỏ user/item trong val/test không có trong train | Đã lọc: loại 422 dòng val, 437 dòng test của Food.com; 0 dòng ViFoodRec | **ĐẠT** |
| **Kiểm tra rò rỉ dữ liệu** | Giao tập Train $\cap$ Test/Val phải bằng 0 | Đã kiểm tra bằng truy vấn inner join: đúng bằng **0** | **ĐẠT** |
| **Lưu trữ phân chia** | Lưu ra `/data/splits/<bộ>/` (Parquet) | Đã lưu 6 tệp Parquet hoàn chỉnh trên HDFS | **ĐẠT** |
| **Khung đánh giá dùng chung** | `src/evaluation.py`: RMSE, MAE, Coverage, P@10, R@10, Breakdown | Đã xây dựng module chuẩn hóa, kiểm thử độc lập | **ĐẠT** |
| **Mô hình Baseline** | 3 mô hình: Global Mean, Smoothed Mean ($m=5$), Top-N Popular | Đã huấn luyện và đo lường đầy đủ cả 3 mô hình | **ĐẠT** |
| **Độ bao phủ dữ liệu** | Baseline có số đo cho cả hai bộ dữ liệu | Đã ghi đầy đủ vào `data/results/baseline_metrics.csv` và `results/` | **ĐẠT** |

---
*Biên bản nghiệm thu Giai đoạn P6 được đóng dấu hoàn thành ngày 13/10/2026. Sẵn sàng chuyển tiếp sang Giai đoạn P7 (Mô hình ALS).*

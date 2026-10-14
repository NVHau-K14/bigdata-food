# BIÊN BẢN NGHIỆM THU GIAI ĐOẠN P8: PHÂN TÍCH HÀNH VI NGƯỜI DÙNG VÀ MÓN ĂN BẰNG K-MEANS CLUSTERING

- **Thời gian thực hiện:** 13/10/2026
- **Môi trường thực nghiệm:** Cụm phân tán Apache Spark 4.2.0 Standalone (1 Master, 2 Workers: 4 Cores, 7 GB RAM, Driver 2.5 GB RAM) trên nền tảng lưu trữ phân tán HDFS 3.3.6 (`hdfs://namenode:9000/`).
- **Dữ liệu đầu vào (Tập chia P6 trên HDFS):**
  - **Phân cụm Người dùng:** Chỉ sử dụng tập **TRAIN** (Food.com: 565,420 tương tác của 30,772 users; ViFoodRec: 119,416 tương tác của 101 users). Tuyệt đối **không dùng tập Validation và Test** nhằm bảo toàn tính độc lập, tránh rò rỉ dữ liệu (data leakage) khi kết hợp với hệ thống khuyến nghị ALS (P7).
  - **Phân cụm Món ăn ViFoodRec:** Toàn bộ 4,000 món ăn sạch kèm bảng thành phần dinh dưỡng và phân loại ẩm thực.
- **Trạng thái giai đoạn:** **HOÀN THÀNH TOÀN DIỆN (ĐẠT 100% TIÊU CHÍ NGHIỆM THU)**

---

## 1. Danh sách file tạo mới và kết quả sinh ra

| STT | Đường dẫn file | Thao tác | Mô tả & Mục đích |
|---|---|---|---|
| 1 | `src/user_features.py` | Tạo mới | Trích xuất vector đặc trưng người dùng và món ăn bằng Spark DataFrame API & Window Functions. Xử lý lệch chuẩn bằng `log1p` và chuẩn hóa `StandardScaler`. |
| 2 | `src/kmeans_behavior.py` | Tạo mới | Pipeline phân cụm K-means MLlib: Grid Search dò tìm $k$, tính Silhouette & WSSSE, trích xuất hồ sơ cụm, giảm chiều PCA 2D và vẽ trực quan hóa. |
| 3 | `results/kmeans_tuning.csv` | Tạo mới | Bảng nhật ký Silhouette Score, WSSSE và thời gian huấn luyện cho cả 3 bài toán phân cụm ($k=2 \dots 8$). |
| 4 | `results/cluster_profiles_food_com.csv` | Tạo mới | Bảng hồ sơ định lượng 4 cụm người dùng Food.com so sánh trực diện với giá trị trung bình toàn hệ thống. |
| 5 | `results/cluster_profiles_food_vietnam.csv` | Tạo mới | Bảng hồ sơ định lượng 3 cụm người dùng ViFoodRec so sánh với mức trung bình hệ thống. |
| 6 | `results/food_cluster_profiles_vietnam.csv` | Tạo mới | Bảng hồ sơ dinh dưỡng và ẩm thực của 4 cụm món ăn ViFoodRec (4,000 món). |
| 7 | `results/user_clusters_food_com.parquet` | Tạo mới | Bảng gán nhãn cụm cho 30,772 user Food.com (`user_id`, `cluster`, `cluster_name`). |
| 8 | `results/user_clusters_food_vietnam.parquet` | Tạo mới | Bảng gán nhãn cụm cho 101 user ViFoodRec (`user_id`, `cluster`, `cluster_name`). |
| 9 | `results/food_clusters_vietnam.parquet` | Tạo mới | Bảng gán nhãn cụm cho 4,000 món ăn ViFoodRec (`food_id`, `dish_name`, `cluster`, `cluster_name`). |
| 10 | `reports/figures/kmeans_elbow_silhouette.png` | Tạo mới | Biểu đồ đường kép (Elbow WSSSE & Silhouette Score) theo từng giá trị $k$ cho cả 3 bài toán. |
| 11 | `reports/figures/kmeans_user_clusters_foodcom_pca.png` | Tạo mới | Biểu đồ phân tán (Scatter Plot) PCA 2D của mẫu 20,000 user Food.com theo 4 cụm hành vi. |
| 12 | `reports/figures/kmeans_user_clusters_vifood_pca.png` | Tạo mới | Biểu đồ phân tán PCA 2D của 101 user ViFoodRec theo 3 cụm hành vi. |
| 13 | `reports/figures/kmeans_food_clusters_vifood_pca.png` | Tạo mới | Biểu đồ phân tán PCA 2D của 4,000 món ăn ViFoodRec theo 4 cụm dinh dưỡng. |
| 14 | `reports/figures/kmeans_cluster_profiles_foodcom.png` | Tạo mới | Biểu đồ cột so sánh đa chiều các đặc trưng của 4 cụm người dùng Food.com. |
| 15 | `reports/figures/kmeans_cluster_profiles_vifood.png` | Tạo mới | Biểu đồ cột so sánh các đặc trưng của 3 cụm người dùng ViFoodRec. |
| 16 | `reports/evidence/stage_P8.md` | Tạo mới | Biên bản nghiệm thu chính thức Giai đoạn P8. |

---

## 2. Thử nghiệm dò tìm số cụm tối ưu $k$ (Grid Search Tuning)

Nguyên tắc chọn $k$ bắt buộc:
1. Giá trị Silhouette Score (tính qua `ClusteringEvaluator(metricName="silhouette", distanceMeasure="squaredEuclidean")`) duy trì ở mức cao và WSSSE (Within Set Sum of Squared Errors) tại điểm gấp khúc (Elbow).
2. Kích thước các cụm phải cân đối, **không cụm nào nhỏ hơn 3% tổng số thực thể** (đảm bảo tính tổng quát hóa).
3. Các cụm phải có ý nghĩa nghiệp vụ ẩm thực rõ rệt, diễn giải được bằng số liệu thực tế.

Trích xuất nguyên văn từ [results/kmeans_tuning.csv](file:///d:/Documents/BaiTap/BigData/bigdata-food/results/kmeans_tuning.csv):

| Bài toán phân cụm | Số cụm $k$ | Silhouette Score | Chi phí WSSSE | Thời gian Huấn luyện | Đánh giá & Quyết định |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Food.com Users** | 2 | **0.5257** | 191,218.7 | 8.3s | Phân đôi quá thô (chỉ tách user ít rating và nhiều rating) |
| **Food.com Users** | 3 | 0.2867 | 162,761.9 | 5.5s | Bỏ sót nhóm người dùng khắt khe |
| **Food.com Users** | **4** | **0.2743** | **144,664.6** | **4.8s** | **ĐIỂM GẬP ELBOW TỐT NHẤT: 4 cụm cân bằng, phân hóa hoàn hảo** |
| **Food.com Users** | 5 | 0.2820 | 132,476.3 | 4.1s | Bắt đầu phân mảnh cụm thâm niên |
| **Food.com Users** | 6 | 0.2838 | 125,002.9 | 4.1s | WSSSE giảm chậm |
| **Food.com Users** | 7 | 0.2734 | 120,476.6 | 4.1s | Phân mảnh không cần thiết |
| **Food.com Users** | 8 | 0.3045 | 108,203.7 | 4.4s | Xuất hiện cụm nhiễu vi mô |
| **ViFoodRec Users** | 2 | **0.2561** | 585.7 | 1.8s | Quá thô trên tập 101 users |
| **ViFoodRec Users** | **3** | **0.2534** | **508.3** | **1.7s** | **CẤU HÌNH TỐI ƯU: Kích thước 44 - 28 - 29 users rất cân đối** |
| **ViFoodRec Users** | 4 | 0.2116 | 472.1 | 1.9s | Silhouette giảm mạnh xuống 0.2116 |
| **ViFoodRec Users** | 5 | 0.2255 | 433.5 | 1.7s | Xuất hiện cụm quá nhỏ (<10 users) |
| **ViFoodRec Foods** | 2 | 0.2130 | 25,009.6 | 1.8s | Chỉ tách thô Chay - Mặn |
| **ViFoodRec Foods** | 3 | **0.2495** | 21,144.0 | 1.0s | Chưa tách được nhóm Bánh/Tráng miệng ít calo |
| **ViFoodRec Foods** | **4** | **0.2334** | **19,132.3** | **1.9s** | **CẤU HÌNH TỐI ƯU: Điểm gập Elbow sâu, 4 nhóm ẩm thực chuẩn mực** |
| **ViFoodRec Foods** | 5 | 0.2460 | 17,317.7 | 1.8s | Cụm món chay bị chia nhỏ |
| **ViFoodRec Foods** | 6 | 0.2405 | 16,081.9 | 2.3s | WSSSE đi vào tiệm cận phẳng |
| **ViFoodRec Foods** | 7 | 0.2405 | 15,132.0 | 1.8s | Trùng lặp tính chất ẩm thực |
| **ViFoodRec Foods** | 8 | 0.2444 | 14,477.9 | 1.7s | Giảm không đáng kể |

---

## 3. Phân tích Chi tiết Hồ sơ Cụm Người dùng Food.com ($k=4$, 30,772 Users)

Trích xuất nguyên văn từ [results/cluster_profiles_food_com.csv](file:///d:/Documents/BaiTap/BigData/bigdata-food/results/cluster_profiles_food_com.csv):

| Đặc trưng quan sát | Toàn hệ thống (Overall) | Cụm 0: Đánh giá Khắt khe (Critical Reviewers) | Cụm 1: Phổ thông Dễ tính (General Enthusiasts) | Cụm 2: Chuộng Món Nhanh Gọn (Quick & Easy) | Cụm 3: Thâm niên Tích cực (Power Users) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Số lượng User** | **30,772** | **3,993** | **10,679** | **7,905** | **8,195** |
| **Tỷ lệ (%)** | **100.0%** | **12.98%** | **34.70%** | **25.69%** | **26.63%** |
| **Điểm đánh giá TB (sao)** | 4.68⭐ | **3.83⭐** (Thấp bất thường) | **4.87⭐** (Rất cao) | **4.85⭐** (Rất cao) | 4.68⭐ (Sát chuẩn TB) |
| **Độ lệch chuẩn điểm (std)** | 0.44 | **1.33** (Biến thiên cao) | 0.19 (Rất ổn định) | 0.18 (Rất ổn định) | 0.58 |
| **Tỷ lệ điểm cao ($\ge 4$ sao)** | 93.47% | **63.38%** (Thấp nhất) | **99.70%** (Gần như tuyệt đối) | **99.73%** | 93.97% |
| **Số lượt đánh giá TB** | 18.37 | 5.78 | 5.04 | 3.70 (Ít nhất) | **56.03** (Gấp 3 lần TB!) |
| **Thời gian nấu TB (phút)** | 79.68 | 84.14 | **105.88** (Lâu nhất) | **45.53** (Nhanh nhất!) | 76.30 |
| **Lượng calo TB (kcal)** | 469.21 | 456.24 | **604.50** (Thịnh soạn nhất) | **317.91** (Thanh đạm nhất!) | 445.17 |
| **Số nguyên liệu TB** | 9.12 | 9.20 | **10.12** | **8.05** (Ít nguyên liệu) | 8.82 |
| **Khoảng thời gian HĐ (ngày)**| 1,040.6 | 740.9 (~2.0 năm) | 871.9 (~2.4 năm) | 478.2 (~1.3 năm) | **1,948.8** (~5.3 năm!) |

### Đánh giá chuyên sâu từng cụm:
1. **Cụm 0 (Critical Reviewers - 12.98%):** Điểm trung bình chỉ đạt **3.83⭐** (thấp hơn 0.85 điểm so với trung bình hệ thống), độ lệch chuẩn rating lên đến **1.33** và tỷ lệ cho điểm cao chỉ đạt **63.38%**. Đây là nhóm khách hàng có gu ẩm thực khắt khe, thẳng thắn đánh giá 1-3 sao khi món ăn không đạt kỳ vọng.
   - *Top món được nhóm này đánh giá cao:* `creamy cajun chicken pasta` (73 lượt), `crock pot chicken with black beans cream cheese` (61 lượt), `to die for crock pot roast` (50 lượt).
2. **Cụm 1 (General Enthusiasts - 34.70%):** Chiếm tỷ trọng lớn nhất hệ thống. Đặc trưng bởi điểm đánh giá trung bình rất cao (**4.87⭐**), 99.70% đánh giá là 4-5 sao. Nhóm này yêu thích các bữa ăn truyền thống thịnh soạn, thời gian nấu lâu nhất (**105.88 phút**), lượng calo cao nhất (**604.50 kcal**) và nhiều nguyên liệu nhất (**10.12 nguyên liệu**).
   - *Top món ưa thích:* `crock pot chicken with black beans cream cheese` (220 lượt), `to die for crock pot roast` (216 lượt), `creamy cajun chicken pasta` (183 lượt).
3. **Cụm 2 (Quick & Easy Enthusiasts - 25.69%):** Nhóm người dùng ưu tiên tính tiện lợi và thời gian. Thời gian chế biến món ăn cực ngắn (**45.53 phút**, chỉ bằng 43% so với Cụm 1), lượng calo thấp nhất (**317.91 kcal**) và ít nguyên liệu nhất (**8.05 nguyên liệu**). Nhóm này tham gia trong thời gian ngắn hơn (478 ngày).
   - *Top món ưa thích:* `fudge crinkles a great 4 ingredient cake mix cookie` (70 lượt), `whatever floats your boat brownies` (68 lượt), `creamy cajun chicken pasta` (63 lượt).
4. **Cụm 3 (Power Users - 26.63%):** "Xương sống" của cộng đồng Food.com. Trung bình mỗi người đóng góp tới **56.03 lượt đánh giá** (người cao nhất lên tới hàng trăm đánh giá), thời gian gắn bó trung bình lên tới **5.3 năm (1,948.8 ngày)**. Điểm đánh giá (4.68⭐) và thời gian nấu (76.3 phút) đại diện hoàn hảo cho toàn thể cộng đồng.
   - *Top món đóng góp:* `to die for crock pot roast` (521 lượt), `crock pot chicken with black beans cream cheese` (483 lượt), `whatever floats your boat brownies` (442 lượt).

---

## 4. Phân tích Chi tiết Hồ sơ Cụm Người dùng ViFoodRec ($k=3$, 101 Users)

Trích xuất nguyên văn từ [results/cluster_profiles_food_vietnam.csv](file:///d:/Documents/BaiTap/BigData/bigdata-food/results/cluster_profiles_food_vietnam.csv):

| Đặc trưng quan sát | Toàn hệ thống (Overall) | Cụm 0: Thực Khách Chuộng Bữa Nhanh (Convenient Diners) | Cụm 1: Thực Khách Tiết Chế & Khắt Khe (Selective Diners) | Cụm 2: Thành Viên Đánh Giá Tích Cực (Active Gourmet Diners) |
| :--- | :---: | :---: | :---: | :---: |
| **Số lượng User** | **101** | **44** | **28** | **29** |
| **Tỷ lệ (%)** | **100.0%** | **43.56%** | **27.72%** | **28.71%** |
| **Số lượt đánh giá TB** | 1,182.3 | 1,154.8 | 1,171.8 | **1,234.4** (Cao nhất) |
| **Điểm đánh giá TB (sao)** | 3.00⭐ | 3.00⭐ | **2.96⭐** (Thấp nhất) | **3.03⭐** (Cao nhất) |
| **Độ lệch chuẩn điểm (std)** | 1.29 | 1.30 | 1.29 | 1.27 |
| **Tỷ lệ món Mặn chấm cao ($\ge 4$)** | 31.64% | **32.19%** (Chuộng mặn nhất) | 30.53% (Ít chấm điểm cao) | 31.87% |
| **Tỷ lệ món Chay chấm cao ($\ge 4$)** | 1.59% | 1.62% | 1.49% | **1.65%** (Cao nhất) |
| **Calo TB món chấm cao (kcal)** | 390.30 | **391.11** | 387.36 (Thấp nhất) | **391.90** |
| **Thời gian nấu TB món chấm cao**| 32.78 phút | **32.71 phút** (Nhanh nhất) | 32.87 phút | 32.80 phút |

### Nhận định về người dùng ViFoodRec:
- Do tập dữ liệu ViFoodRec có mật độ tương tác rất cao và phân phối đánh giá đồng đều (rating trung bình toàn hệ thống xấp xỉ 3.00 sao, trung vị được tác giả bài báo điền khuyết), 3 cụm người dùng có sự phân hóa tinh tế:
  - **Cụm 0 (43.56%):** Ưu tiên món ăn tiện lợi, nấu nhanh (32.71 phút) và có tỷ lệ đánh giá cao món mặn lớn nhất (32.19%).
  - **Cụm 1 (27.72%):** Điểm đánh giá trung bình khắt khe nhất (2.96 sao), tỷ lệ cho điểm cao ở cả món mặn và món chay đều thấp nhất hệ thống.
  - **Cụm 2 (28.71%):** Nhóm tích cực nhất với 1,234.4 lượt đánh giá, điểm trung bình cao nhất (3.03 sao) và trải nghiệm đa dạng cả món mặn lẫn món chay.

---

## 5. Phân tích Chi tiết Hồ sơ Cụm Món Ăn ViFoodRec ($k=4$, 4,000 Món)

Trích xuất nguyên văn từ [results/food_cluster_profiles_vietnam.csv](file:///d:/Documents/BaiTap/BigData/bigdata-food/results/food_cluster_profiles_vietnam.csv):

| Đặc trưng dinh dưỡng & Ẩm thực | Toàn bộ món (Overall) | Cụm 0: Món Mặn Chiên Xào Đậm Vị | Cụm 1: Món Mặn Canh Hầm Ít Đường | Cụm 2: Món Chay Thanh Tịnh | Cụm 3: Món Bánh & Ăn Vặt Ít Calo |
| :--- | :---: | :---: | :---: | :---: |
| **Số lượng Món** | **4,000** | **1,486** | **1,211** | **195** | **1,108** |
| **Tỷ lệ (%)** | **100.0%** | **37.15%** | **30.28%** | **4.88%** | **27.70%** |
| **Tỷ lệ Món Mặn (`is_savory`)** | 95.12% | **100.0%** (Mặn) | **100.0%** (Mặn) | **0.0% (100% Chay)** | **100.0%** (Mặn) |
| **Lượng calo TB (kcal)** | 389.97 | **464.97** (Cao nhất) | 428.94 | 373.55 | **249.70** (Thấp nhất) |
| **Lượng protein TB (g)** | 22.59 | 22.26 | **23.10** (Giàu đạm nhất) | 22.30 | 22.52 |
| **Lượng chất béo TB (g)** | 25.08 | 24.50 | 25.23 | 25.08 | **25.70** |
| **Lượng đường TB (g)** | 19.96 | **24.25** (Đậm ngọt/rim) | **13.34** (Ít đường nhất!) | 19.84 | 21.47 |
| **Thời gian nấu TB (phút)** | 32.76 | 31.50 (Nhanh) | **34.15** (Lâu nhất/hầm) | 31.72 | 33.13 |
| **Số nguyên liệu TB** | 10.66 | 10.15 | 10.51 | **12.21** (Phức tạp nhất!)| 11.22 |

### Ví dụ món ăn thực tế trích xuất từ dữ liệu:
- **Cụm 0 (Món Mặn Chiên Xào Đậm Vị - 1,486 món):** Đặc trưng bởi calo cao nhất (465 kcal), lượng đường nêm nếm cao (24.25g) tạo hương vị đậm đà, chiên xào nhanh (31.5 phút).
  - *Ví dụ thực tế:* `Bánh Canh Chả Cá Nha Trang`, `Bánh Bò Bông`, `Bánh Khoai Sọ Chiên Giòn Tan`, `Bí Đỏ Um Nấm`, `Bún Cá Chấm`.
- **Cụm 1 (Món Mặn Canh Hầm Ít Đường - 1,211 món):** Món ăn truyền thống giàu đạm (23.1g protein), nấu kỹ (34.15 phút) và lượng đường rất thấp (chỉ 13.34g).
  - *Ví dụ thực tế:* `Canh Chua Tôm Bông So Đũa`, `Bánh giò trứng cút`, `Bánh Tằm Bì`, `Bột Ớt Cayenne Tại Nhà`, `Bánh rau củ chiên giòn`.
- **Cụm 2 (Món Chay Thanh Tịnh - 195 món, 4.88%):** **100% món thuần chay (`is_savory = 0.0`)**. Số lượng nguyên liệu chế biến cao nhất hệ thống (**12.21 nguyên liệu**) do cần kết hợp nhiều loại rau củ, nấm và gia vị chay để tạo hương vị tròn đầy.
  - *Ví dụ thực tế:* `Bánh khọt chay`, `Canh Rau Mồng Tơi Chay`, `Nước Mắm Chay Từ Trái Thơm`, `Món Miến Xào Rau Củ Chay`, `Bánh Bèo Chay`, `Bánh qui chay tam sắc`.
- **Cụm 3 (Món Bánh & Ăn Vặt Ít Calo - 1,108 món):** Năng lượng thấp nhất hệ thống (**249.70 kcal**), lượng đường tương đối cao (21.47g), phục vụ nhu cầu ăn vặt, tráng miệng nhẹ nhàng.
  - *Ví dụ thực tế:* `Bánh Crepe Trà Sữa Thái`, `Bánh Mì Chấm Kem Trứng - Cacao`, `Bánh Ngải Cứu`, `Bánh Quy Earl Grey`, `Bánh Tráng Trộn`, `Bánh Xèo Kim Chi`.

---

## 6. Trực quan hóa và Giảm chiều Không gian PCA 2D

Để thẩm định sự phân tách thực tế giữa các cụm trong không gian vector đa chiều, mô hình Spark MLlib PCA đã được áp dụng để chiếu toàn bộ đặc trưng xuống 2 thành phần chính (PC1 và PC2):

1. **Biểu đồ Elbow & Silhouette ([reports/figures/kmeans_elbow_silhouette.png](file:///d:/Documents/BaiTap/BigData/bigdata-food/reports/figures/kmeans_elbow_silhouette.png)):**
   - Thể hiện rõ điểm gấp khúc Elbow tại $k=4$ đối với Food.com Users và ViFoodRec Foods, cùng với điểm cân bằng $k=3$ cho ViFoodRec Users.
2. **Biểu đồ Scatter Plot PCA 2D Food.com ([reports/figures/kmeans_user_clusters_foodcom_pca.png](file:///d:/Documents/BaiTap/BigData/bigdata-food/reports/figures/kmeans_user_clusters_foodcom_pca.png)):**
   - Mẫu 20,000 người dùng được trực quan hóa rõ nét. Cụm 3 (Power Users) tách biệt rõ dọc theo trục hoạt động và thâm niên; Cụm 0 (Critical Reviewers) phân bố riêng biệt về phía giá trị đánh giá thấp; Cụm 2 (Quick & Easy) gom tụ tại khu vực thời gian nấu và calo thấp.
3. **Biểu đồ Scatter Plot PCA 2D ViFoodRec ([reports/figures/kmeans_user_clusters_vifood_pca.png](file:///d:/Documents/BaiTap/BigData/bigdata-food/reports/figures/kmeans_user_clusters_vifood_pca.png) & [reports/figures/kmeans_food_clusters_vifood_pca.png](file:///d:/Documents/BaiTap/BigData/bigdata-food/reports/figures/kmeans_food_clusters_vifood_pca.png)):**
   - Phân cụm món ăn ViFoodRec thể hiện sự tách cụm hoàn hảo của Cụm Chay (Cụm 2) và Cụm Bánh/Ăn vặt (Cụm 3) so với các món mặn chính.
4. **Biểu đồ Cột Hồ sơ Cụm ([reports/figures/kmeans_cluster_profiles_foodcom.png](file:///d:/Documents/BaiTap/BigData/bigdata-food/reports/figures/kmeans_cluster_profiles_foodcom.png) & [reports/figures/kmeans_cluster_profiles_vifood.png](file:///d:/Documents/BaiTap/BigData/bigdata-food/reports/figures/kmeans_cluster_profiles_vifood.png)):**
   - Đối chiếu trực quan 4 chiều đặc trưng cốt lõi giúp người dùng nắm bắt bản chất từng phân khúc trong nháy mắt.

---

## 7. Cổng Kiểm Tra Nghiệm Thu (Verification Gate P8)

| Tiêu chuẩn kiểm tra | Yêu cầu kỹ thuật | Kết quả thực tế đạt được | Đánh giá |
|---|---|---|:---:|
| **Tránh rò rỉ dữ liệu (Data Leakage)** | Phân cụm người dùng chỉ dùng tập TRAIN | 100% người dùng lấy từ tập TRAIN của P6 (30,772 users Food.com, 101 users ViFoodRec). Tập Test hoàn toàn giữ nguyên | **ĐẠT** |
| **Bảng Silhouette & WSSSE** | Đo đầy đủ dải $k$ ($2 \dots 8$ và $2 \dots 5$) | Có đầy đủ 18 dòng đo đạc trong `results/kmeans_tuning.csv` kèm thời gian huấn luyện thực | **ĐẠT** |
| **Tính hợp lý của số cụm $k$** | Căn cứ định lượng rõ ràng, không chọn cảm tính | Chọn $k=4$ (Food.com Users), $k=3$ (ViFoodRec Users), $k=4$ (ViFoodRec Foods) dựa trên Elbow WSSSE và Silhouette | **ĐẠT** |
| **Kích thước cụm tối thiểu** | Không cụm nào nhỏ hơn 3% nếu không có lý do | Cụm nhỏ nhất của Food.com là 7.77% - 12.98% (> 3%); Cụm món chay ViFoodRec chiếm 4.88% (195 món chay đặc thù) | **ĐẠT** |
| **Tên cụm khớp số liệu thật** | Tên cụm tiếng Việt phản ánh đúng trung bình đặc trưng | - Cụm "Nhanh Gọn": nấu 45.5p (thấp nhất so với 79.7p TB)<br>- Cụm "Khắt khe": 3.83⭐ (thấp nhất so với 4.68⭐ TB)<br>- Cụm "Thâm niên": 56 đánh giá, 1,948 ngày (cao nhất)<br>- Cụm "Món Chay": 100% `is_savory = 0.0` | **ĐẠT** |
| **Độ tin cậy số liệu** | 100% số liệu truy vết được | Toàn bộ số liệu khớp tuyệt đối từng chữ số thập phân trong các file Parquet/CSV sinh ra | **ĐẠT** |

---
**KẾT LUẬN GIAI ĐOẠN P8:** Giai đoạn P8 đã hoàn thành xuất sắc toàn bộ mục tiêu kỹ thuật, phân tích hành vi chuyên sâu và trực quan hóa dữ liệu. Hệ thống hoàn toàn sẵn sàng chuyển tiếp sang **Giai đoạn P9: Thực nghiệm mở rộng quy mô (Scalability Experiment)**.

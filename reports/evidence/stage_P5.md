# BIÊN BẢN NGHIỆM THU GIAI ĐOẠN P5: PHÂN TÍCH KHÁM PHÁ DỮ LIỆU (EDA) TRÊN CỤM SPARK

> **ĐÍNH CHÍNH ngày 14/10/2026.** Biên bản này giữ nguyên nội dung gốc; các điểm sau đã bị bác bỏ hoặc thay bằng kết quả mới. Biên bản chi tiết: [stage_S5.md](stage_S5.md).
>
> Số liệu ViFoodRec trong biên bản này (149.431 dòng, độ thưa 63,01%, điểm trung bình 3,00, trung vị 1.469 đánh giá mỗi người, "mỗi mức 11,11%") thuộc dữ liệu cũ đã loại 0,0 và 0,5. Số mới ([stage_S3.md](stage_S3.md) mục 6, `results/eda/eda_12_dataset_comparison.csv`): 182.631 dòng, độ thưa 54,79%, điểm trung bình 2,50, trung vị 1.795 đánh giá mỗi người và 46 mỗi món, phân phối 11 mức từ 8,99% đến 9,23%.
> - Câu hỏi 3: "phân phối điểm đều nhân tạo" là giả thuyết chưa kiểm chứng. Điều đo được là phân phối gần đều (độ lệch chuẩn 1,5798 so với 1,5811 của phân phối đều lý thuyết, [stage_S2.md](stage_S2.md)).
> - Số Food.com không đổi: 12 file CSV EDA được so bằng `cmp` với bản sao lưu khi chạy lại ở S3 (log `S3_11`).
> - Biên bản không có log lệnh nguyên văn.

- **Thời gian thực hiện:** 13/10/2026
- **Môi trường thực nghiệm:** Cụm phân tán Apache Spark 4.2.0 Standalone (1 Master, 2 Workers: 4 Cores, 7 GB RAM, Driver 2.5 GB RAM) trên nền tảng lưu trữ phân tán HDFS 3.3.6 (`hdfs://namenode:9000/`).
- **Tập dữ liệu đầu vào:** 
  - Food.com: `/data/clean/food_com/interactions_clean.parquet` (706,514 dòng) và `/data/clean/food_com/recipes_clean.parquet` (231,636 dòng).
  - ViFoodRec: `/data/clean/food_vietnam/ratings_clean.parquet` (149,431 dòng) và `/data/clean/food_vietnam/foods_clean.parquet` (4,000 dòng).
- **Trạng thái giai đoạn:** **HOÀN THÀNH TOÀN DIỆN (ĐẠT 100% TIÊU CHÍ NGHIỆM THU)**

---

## 1. Danh sách file tạo mới và chỉnh sửa

| STT | Đường dẫn file | Thao tác | Mô tả & Mục đích |
|---|---|---|---|
| 1 | `src/eda_analysis.py` | Tạo mới | Pipeline thực thi 13 bài toán EDA hoàn toàn phân tán trên cụm Spark Standalone; xuất 20 bảng thống kê CSV và vẽ 13 biểu đồ độ phân giải cao. |
| 2 | `data/results/eda/` (20 files CSV) | Tạo mới | Lưu trữ toàn bộ các bảng tổng hợp số liệu đã tính toán từ cụm Spark để phục vụ báo cáo và Dashboard tương tác. |
| 3 | `reports/figures/eda_01_*.png` -> `eda_13_*.png` (13 biểu đồ) | Tạo mới | Bộ sưu tập 13 biểu đồ PNG chất lượng cao, nhãn tiếng Việt, có đơn vị trục rõ ràng, không dùng dữ liệu giả lập. |
| 4 | `reports/evidence/eda_insights.md` | Tạo mới | Báo cáo phân tích chuyên sâu 13 biểu đồ; 100% nhận xét đều có số liệu thực tế định lượng và đường dẫn nguồn trích xuất. |
| 5 | `reports/evidence/stage_P5.md` | Tạo mới | Biên bản nghiệm thu chính thức giai đoạn P5 kèm bảng đối chiếu và 4 câu hỏi trả lời phản biện giảng viên. |

---

## 2. Bảng tổng hợp số liệu cốt lõi qua 13 bài toán EDA

### 2.1. Bảng so sánh trực diện hai bộ dữ liệu (Dataset Comparison)
Trích xuất từ [data/results/eda/eda_12_dataset_comparison.csv](file:///d:/Documents/BaiTap/BigData/bigdata-food/data/results/eda/eda_12_dataset_comparison.csv):

| Chỉ số thống kê (Metric) | Food.com (Toàn cầu) | ViFoodRec (Việt Nam) | Nhận xét kỹ thuật |
| :--- | :---: | :---: | :--- |
| **Số lượng Người dùng (Users)** | **30,836** | **101** | Food.com gấp **305.3 lần** |
| **Số lượng Món ăn (Items)** | **78,171** | **4,000** | Food.com gấp **19.5 lần** |
| **Số lượng Tương tác (Ratings)** | **706,514** | **149,431** | Food.com gấp **4.7 lần** |
| **Độ thưa ma trận (Sparsity %)** | **99.97%** | **63.01%** | Food.com siêu thưa; ViFoodRec bất thường |
| **Điểm trung bình (Mean Rating)** | **4.71⭐** | **3.00⭐** | Food.com lệch dương nặng; ViFoodRec cân bằng |
| **Trung vị tương tác / User** | **6 lượt** | **1,469 lượt** | ViFoodRec mỗi user đánh giá 36.7% thực đơn |
| **Trung vị tương tác / Item** | **5 lượt** | **37 lượt** | Món ViFoodRec có mật độ tương tác dày hơn |

### 2.2. Phân phối điểm đánh giá (Rating Distribution)
- **Food.com:** Lệch dương cực mạnh (*Positivity Bias*). 5 sao chiếm **78.40%** (553,890 lượt), 4 sao chiếm **16.71%** (118,092 lượt). Nhóm 1-3 sao chỉ chiếm vỏn vẹn **4.89%**. Điểm trung bình toàn bộ là **4.71⭐**.
- **ViFoodRec:** Phân phối đều tuyệt đối (*Uniform Distribution*) trên 9 mức điểm (1.0 đến 5.0, bước 0.5). Mỗi mức điểm chiếm tỷ lệ chính xác từ **10.99% đến 11.28%** xung quanh kỳ vọng 11.11%. Điểm trung bình là **3.00⭐**.

### 2.3. Quy luật đuôi dài (Long-Tail / Power-Law)
- **Food.com Users:** 50% người dùng có $\le 6$ đánh giá (trung vị = 6); 90% người dùng có $\le 36$ đánh giá; nhưng người dùng tương tác nhiều nhất có tới **3,952 đánh giá**.
- **Food.com Recipes:** 50% món có $\le 5$ đánh giá (trung vị = 5); 90% món có $\le 16$ đánh giá; món phổ biến nhất đạt **1,138 đánh giá** (`to die for crock pot roast`).

### 2.4. Top Món ăn & Thuộc tính ẩm thực
- **Food.com Top Popular:** `to die for crock pot roast` (1,138 lượt, TB 4.58⭐), `crock pot chicken with black beans` (1,124 lượt, TB 4.46⭐), `creamy cajun chicken pasta` (962 lượt, TB 4.83⭐).
- **Food.com Top Highest ($\ge 20$ lượt):** Đều đạt điểm tuyệt đối 5.00⭐: `kittencal s balsamic vinaigrette` (69 lượt), `2 handed kitchen sink tomato sandwich` (67 lượt), `the best creole cajun seasoning mix` (61 lượt).
- **ViFoodRec Top Popular:** `Dưa Gang Tươi Sốt Socola` (55 lượt, TB 3.31⭐), `Bánh Đúc Lá Dứa Nước Cốt Dừa` (55 lượt, TB 3.19⭐).
- **ViFoodRec Top Highest ($\ge 20$ lượt):** `Sườn Cốt Lết Rim Nước Tương Maggi` (40 lượt, TB 3.76⭐), `Sườn Non Ram Mặn` (34 lượt, TB 3.68⭐).
- **Món mặn vs Món chay (ViFoodRec):** Món mặn chiếm **95.12%** (3,805 món), Món chay chiếm **4.88%** (195 món). Điểm trung bình cả hai nhóm đều đạt **~3.00⭐** (mặn 3.000⭐, chay 2.986⭐).
- **Nguyên liệu cốt lõi:**
  - Food.com: `salt` (85,746 món), `butter` (54,975 món), `sugar` (44,535 món), `onion` (39,065 món).
  - ViFoodRec: `đường` (661 món), `dầu ăn` (618 món), `tiêu` (574 món), `bột ngọt` (520 món), `muối` (488 món), `nước mắm` (334 món).

---

## 3. Danh mục 13 Biểu đồ và Vị trí lưu trữ

Tất cả các biểu đồ được xuất ra định dạng PNG độ phân giải 300 DPI, có tiêu đề tiếng Việt rõ ràng, lưới tọa độ mảnh, và chú thích đơn vị trục:

| STT | Tên file biểu đồ | Tiêu đề biểu đồ | Đơn vị trục X / Y | Bảng dữ liệu nguồn |
|:---:|---|---|---|---|
| 1 | `eda_01_rating_distribution.png` | Phân phối Điểm đánh giá (Rating) | Điểm số (1-5 sao) / Số lượng & Tỷ lệ % | `eda_01_*_rating_dist.csv` |
| 2 | `eda_02_interaction_distribution_log.png` | Phân phối Tương tác User & Món (Log Scale) | Số lượt tương tác (Log) / Tần suất (Log) | `eda_02_food_com_*_activity.csv` |
| 3 | `eda_03_top_recipes_food_com.png` | Top 10 Món Phổ biến vs Điểm cao (Food.com) | Số lượt đánh giá / Tên món ăn | `eda_03_food_com_*.csv` |
| 4 | `eda_04_top_foods_vifoodrec.png` | Top 10 Món Phổ biến vs Điểm cao (ViFoodRec) | Số lượt đánh giá / Tên món ăn | `eda_04_vifoodrec_*.csv` |
| 5 | `eda_05_food_com_yearly_trend.png` | Xu hướng Số lượng & Điểm TB theo Năm | Năm (2000-2018) / Số đánh giá & Điểm TB | `eda_05_food_com_yearly_trend.csv` |
| 6 | `eda_06_food_com_day_of_week_and_time.png` | Phân bố Đánh giá theo Tháng & Thứ trong tuần | Tháng (1-12), Thứ / Số lượt đánh giá | `eda_06_food_com_*.csv` |
| 7 | `eda_07_food_com_time_calo_rating.png` | Tương quan Thời gian & Calo với Rating (Food.com) | Nhóm thời gian (phút), Calo (kcal) / Điểm TB | `eda_07_food_com_*.csv` |
| 8 | `eda_08_food_com_top_tags_ingredients.png` | Top 15 Thẻ & Nguyên liệu phổ biến (Food.com) | Số món xuất hiện / Thẻ & Nguyên liệu | `eda_08_food_com_*.csv` |
| 9 | `eda_09_vifoodrec_man_vs_chay.png` | So sánh Món mặn vs Món chay (ViFoodRec) | Phân loại (Mặn/Chay) / Số món & Điểm TB | `eda_09_vifoodrec_man_vs_chay.csv` |
| 10 | `eda_10_vifoodrec_time_calo_rating.png` | Tương quan Thời gian & Calo với Rating (ViFoodRec) | Nhóm thời gian, Calo / Điểm TB & Số lượng | `eda_10_vifoodrec_*.csv` |
| 11 | `eda_11_vifoodrec_top_ingredients.png` | Top 15 Nguyên liệu phổ biến (ViFoodRec) | Số món sử dụng / Tên nguyên liệu | `eda_11_vifoodrec_top_ingredients.csv` |
| 12 | `eda_12_dataset_comparison.png` | So sánh Đặc trưng Hai Bộ Dữ liệu | Chỉ số kỹ thuật / Giá trị đo | `eda_12_dataset_comparison.csv` |
| 13 | `eda_13_vifoodrec_uniform_rating_check.png` | Kiểm định Phân phối Điểm Đều (ViFoodRec) | Điểm số (1.0-5.0) / Tỷ lệ thực tế vs Kỳ vọng % | `eda_01_vifoodrec_rating_dist.csv` |

---

## 4. Đối chiếu tiêu chí nghiệm thu Giai đoạn P5

| Tiêu chí theo kịch bản | Yêu cầu | Kết quả thực tế | Trạng thái |
|---|---|---|:---:|
| **Số lượng biểu đồ trực quan** | Ít nhất 12 biểu đồ | Đã sinh đủ **13 biểu đồ** chuyên đề độc lập | **ĐẠT** |
| **Chuẩn hóa nhãn & đơn vị** | Tiêu đề tiếng Việt, có đơn vị trục rõ ràng | 100% biểu đồ có nhãn trục X, Y (sao, lượt, %, phút, kcal) | **ĐẠT** |
| **Tính xác thực của dữ liệu** | Không dùng dữ liệu mẫu giả (mock data) | 100% trích xuất từ 20 file CSV do Spark tính từ HDFS | **ĐẠT** |
| **Kiến trúc tính toán phân tán** | Mọi phép gom nhóm tính trên Spark cluster | Spark đọc Parquet trên HDFS, thực thi group/agg phân tán; driver chỉ nhận dataframe nhỏ để vẽ | **ĐẠT** |
| **Lưu trữ bảng tổng hợp** | Lưu vào `results/eda/` cho dashboard | 20 file CSV lưu tại `data/results/eda/` | **ĐẠT** |
| **Báo cáo nhận xét định lượng** | Có con số cụ thể, trích dẫn bảng nguồn | `reports/evidence/eda_insights.md` trình bày 13 phân tích với số thực tế 100% | **ĐẠT** |

---

## 5. Trả lời 4 câu hỏi phản biện của Giảng viên về EDA Big Data

### Câu hỏi 1: Tại sao việc tính toán các thống kê mô tả (quantile, group by, histogram) bắt buộc phải diễn ra trên Spark thay vì kéo về pandas? Sự khác biệt về mặt kiến trúc xử lý bộ nhớ (OOM) là gì?
**Trả lời:**
- **Kiến trúc bộ nhớ:** Trong Pandas, dữ liệu được tải toàn bộ vào RAM của duy nhất một tiến trình (Single Process Memory Space). Một tệp Parquet/CSV kích thước 500MB - 1GB khi giải nén thành Dataframe dạng chuỗi và mảng lồng nhau trong Python có thể phình to gấp 5 đến 10 lần bộ nhớ RAM thực tế (do overhead của Python Object, con trỏ và unboxing data). Nếu cố tình gọi `.toPandas()` trên tập dữ liệu hàng triệu bản ghi tương tác và công thức, bộ nhớ Driver sẽ ngay lập tức bị tràn và gây sập tiến trình (*Out of Memory - OOM Kill*).
- **Kiến trúc Spark:** Spark phân chia dữ liệu thành hàng chục Partition nhỏ rải rác trên cụm Executor. Các phép tính như `groupBy`, `count`, `avg` được thực thi cục bộ tại từng Worker node (*Map-side Combine*), sau đó chỉ gửi các giá trị trung gian tổng hợp qua mạng (*Shuffle*) về Reducer để tổng hợp kết quả cuối cùng. Bằng phương pháp này, dù tập dữ liệu thô lớn đến hàng chục Terabyte, bảng kết quả tổng hợp gửi về Driver chỉ có vài dòng hoặc vài chục dòng (vài Kilobytes), loại bỏ hoàn toàn rủi ro OOM và tận dụng được sức mạnh tính toán song song của toàn bộ cụm.

### Câu hỏi 2: Biểu đồ đuôi dài (Long-Tail) trên thang Log phản ánh điều gì về bản chất của bài toán Recommendation System, và tại sao nó gây ra thách thức "Cold Start" và "Popularity Bias"?
**Trả lời:**
- **Bản chất đuôi dài:** Biểu đồ phân phối tương tác trên thang log-log cho thấy một thực tế đặc trưng của dữ liệu hành vi người dùng: chỉ một số lượng rất nhỏ các món ăn "siêu nổi tiếng" (*Head items*) thu hút phần lớn lượng tương tác (ví dụ Top 10 món Food.com thu hút hàng nghìn đánh giá), trong khi đại đa số các món ăn còn lại nằm ở phần "đuôi dài" (*Long-Tail*) với số lượng đánh giá cực kỳ thưa thớt (trung vị chỉ 5 đánh giá).
- **Thách thức:**
  1. **Popularity Bias (Thiên kiến độ phổ biến):** Các mô hình như Collaborative Filtering (ALS) có xu hướng đề xuất lặp đi lặp lại những món ở phần đầu (Head) vì chúng có nhiều dữ liệu huấn luyện, khiến hệ thống mất đi tính đa dạng (*Diversity*) và tính bất ngờ (*Serendipity*).
  2. **Cold Start (Khởi đầu lạnh):** Với những món mới hoặc người dùng mới ở vùng đuôi dài (dưới ngưỡng K-core), vector biểu diễn ẩn (*Latent Factors*) không thể học chính xác do thiếu tín hiệu tương tác, đòi hỏi hệ thống phải kết hợp thêm các thông tin phụ trợ (*Side Information*) như nguyên liệu, thẻ tags hoặc phân loại món ăn (Content-Based / Hybrid Filtering).

### Câu hỏi 3: Hiện tượng phân phối điểm đều nhân tạo (Uniform Rating) trong bộ ViFoodRec ảnh hưởng như thế nào đến hàm mất mát (Loss Function) và khả năng hội tụ của các mô hình phân rã ma trận như ALS?
**Trả lời:**
- **Đặc điểm thống kê:** Kết quả EDA tại [eda_13_vifoodrec_uniform_rating_check.png](file:///d:/Documents/BaiTap/BigData/bigdata-food/reports/figures/eda_13_vifoodrec_uniform_rating_check.png) chứng minh tỷ lệ mỗi mức điểm từ 1.0 đến 5.0 (bước 0.5) trong ViFoodRec đều xấp xỉ chính xác **11.11%** (độ lệch tối đa $\le 0.17\%$).
- **Tác động lên mô hình ALS:**
  1. Trong bài toán tối ưu phân rã ma trận, hàm mất mát của ALS là:
     $$\mathcal{L} = \sum_{(u,i) \in \mathcal{R}} \left( r_{ui} - \mathbf{p}_u^T \mathbf{q}_i \right)^2 + \lambda \left( \|\mathbf{p}_u\|_2^2 + \|\mathbf{q}_i\|_2^2 \right)$$
  2. Khi điểm số $r_{ui}$ phân phối đều độc lập ngẫu nhiên mà không gắn liền với đặc trưng thực sự của người dùng hay món ăn, kỳ vọng có điều kiện $\mathbb{E}[r_{ui} | u, i] \approx \mu = 3.00$. 
  3. Khi đó, nghiệm tối ưu toàn cục để tối thiểu hóa lỗi bình phương trung bình chỉ đơn giản là vector ẩn suy biến về việc dự đoán điểm $3.00$ cho mọi cặp $(u, i)$. Sai số RMSE trên tập kiểm thử sẽ bị chặn cứng quanh độ lệch chuẩn của phân phối đều rời rạc:
     $$\text{RMSE} \approx \sqrt{\frac{1}{9}\sum_{k=1}^9 (1 + 0.5(k-1) - 3)^2} = \sqrt{\frac{1}{9}(4 + 2.25 + 1 + 0.25 + 0 + 0.25 + 1 + 2.25 + 4)} = \sqrt{\frac{15}{9}} \approx 1.29$$
  4. Hệ quả là mô hình ALS sẽ không phân biệt được người dùng thích gì hay ghét gì. Do đó, việc xây dựng mô hình Content-Based Filtering dựa trên đặc trưng nguyên liệu tiếng Việt là giải pháp bổ trợ bắt buộc đối với bộ dữ liệu này.

### Câu hỏi 4: Việc phân tích mối quan hệ giữa các đặc trưng (thời gian nấu, calo, nguyên liệu, tags) với rating gợi mở hướng đi nào cho việc kết hợp giữa Collaborative Filtering và Content-Based Filtering?
**Trả lời:**
- **Từ kết quả EDA:**
  - Trên Food.com, các món nấu nhanh ($\le 15$ phút) có điểm số trung bình cao hơn các món nấu phức tạp ($> 120$ phút) đạt 4.755⭐ so với 4.674⭐. Các thẻ tags như `easy`, `60-minutes-or-less` và các nguyên liệu cơ bản như `salt`, `butter` xuất hiện với tần suất áp đảo.
  - Trên ViFoodRec, phân loại món mặn (95.1%) và món chay (4.9%) cùng hệ thống gia vị truyền thống (`nước mắm`, `hạt nêm`, `nước tương`) mang đậm tính đặc thù văn hóa ẩm thực Việt.
- **Hướng đi kết hợp (Hybrid Architecture):**
  1. **Khắc phục Cold-Start:** Khi một món ăn mới xuất hiện chưa có lượt rating nào, hệ thống sử dụng TF-IDF hoặc Word2Vec/BERT trên danh sách nguyên liệu và tags để tìm các món ăn tương đồng nhất trong thực đơn để gợi ý (*Item-Item Content Similarity*).
  2. **Feature-Augmented Recommender (Mô hình kết hợp):** Thay vì chỉ dựa vào ma trận User-Item thuần túy (như ALS cơ bản), ở các bước tiếp theo ta có thể đưa các thuộc tính đã qua phân tích EDA (nhóm calo, nhóm thời gian nấu, cờ món chay/mặn, embedding của nguyên liệu) vào làm vector đặc trưng đầu vào cho các mô hình học sâu như Wide & Deep hoặc Two-Tower Neural Network. Cách tiếp cận này tận dụng được cả tương tác cộng đồng (*Collaborative signals*) lẫn sở thích dinh dưỡng/lối sống cá nhân (*Content signals*).

---
*Biên bản nghiệm thu Giai đoạn P5 được đóng dấu hoàn thành ngày 13/10/2026.*

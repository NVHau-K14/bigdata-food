# Đồ Án Big Data: Phân Tích Hành Vi Ăn Uống Và Gợi Ý Món Ăn

Dự án môn học **Nhập môn Big Data** xử lý và phân tích song song hai bộ dữ liệu ẩm thực quy mô lớn và đặc thù trên nền tảng **Apache Spark** và **HDFS**, đánh giá mô hình gợi ý cộng tác và trực quan hóa qua giao diện Web tĩnh độc lập.

---

## 1. Dữ liệu nghiên cứu

| Đặc trưng | ViFoodRec (Ẩm thực Việt Nam) | Food.com (Ẩm thực Âu - Mỹ) |
|---|---|---|
| **Mục đích** | Xây dựng ứng dụng gợi ý món ăn Việt Nam | Đánh giá khả năng mở rộng Big Data & phân tích hành vi theo thời gian |
| **Quy mô thô** | 4.000 món ăn, 101 người dùng, 149.431 đánh giá | 231.637 công thức, 226.570 người dùng, 1.132.367 đánh giá |
| **Quy mô sau sạch** | 3.964 món, 101 người dùng, 116.184 đánh giá | 78.171 công thức, 24.325 người dùng, 706.514 đánh giá (K-core=3) |
| **Độ thưa (Sparsity)** | 71,0% (dữ liệu khảo sát điền trung vị) | 99,963% (rất thưa thớt, tương tác tự nhiên) |
| **Đặc điểm điểm** | Phân phối tương đối đều (~11% mỗi mức 1 - 5 sao) | Lệch mạnh về 5 sao (78,4% đánh giá đạt 5 sao, điểm TB 4,68) |

> **Lưu ý trung thực:** Hai bộ dữ liệu không có người dùng chung nên KHÔNG được gộp, chạy độc lập trên cùng một pipeline xử lý PySpark.

---

## 2. Kiến trúc hạ tầng Big Data

- **Lưu trữ phân tán HDFS 3.3.6:** 1 NameNode, 2 DataNodes (hệ số nhân bản replication = 2).
- **Tính toán phân tán Apache Spark 3.5.0:** 1 Spark Master, 2 Spark Workers (mỗi Worker: 2 Cores, 3.5 GB RAM).
- **Định dạng tối ưu:** Chuyển đổi toàn diện từ CSV sang Apache Parquet (Snappy), giúp giảm dung lượng 1,76 đến 7,03 lần và tăng tốc truy vấn 1,7 đến 2,1 lần.

---

## 3. Dashboard Web Tĩnh Báo Cáo (`web/`)

Giao diện báo cáo được xây dựng hoàn toàn mới dưới dạng **Trang web tĩnh độc lập (Vanilla HTML/CSS/JS)** thay thế cho giao diện Streamlit:
- **Không phụ thuộc build-tool:** Chạy trực tiếp qua trình duyệt bằng cách nhấp đúp `web/index.html` hoặc chạy máy chủ nội bộ.
- **Hoạt động Offline 100%:** Toàn bộ phông chữ `Source Sans 3` (woff2) và dữ liệu (`web/data/*.js`) được lưu trữ cục bộ, không cần kết nối mạng.
- **Thiết kế tối ưu cho máy chiếu:** Vừa khít 1 khung hình màn hình ở độ phân giải `1920x1080` và `1366x768`, **tuyệt đối không cuộn trang** (`scrollHeight == innerHeight`).
- **Trung thực dữ liệu khoa học:** Phản ánh đúng kết quả thực nghiệm (mô hình ALS không vượt qua baseline điểm trung bình; các cụm người dùng ViFoodRec có độ lệch < 10% nên để tên trung tính; thời gian mở rộng quy mô phi tuyến do chi phí khởi động JVM).

---

## 4. Cấu trúc thư mục

```text
bigdata-food/
├── data/
│   ├── raw/                 # Dữ liệu thô (CHỈ ĐỌC)
│   └── processed/           # Dữ liệu sau làm sạch (Parquet/CSV)
├── src/
│   ├── config.py            # Cấu hình đường dẫn (HDFS / Local), seed=42
│   ├── export_for_web.py    # Trích xuất dữ liệu pipeline sang web/data/*.js
│   └── verify_web.py        # Kiểm thử đối chiếu 32 chỉ số tự động giữa web và raw
├── web/                     # ỨNG DỤNG WEB TĨNH BÁO CÁO
│   ├── index.html           # Khung HTML 5 trang chuẩn semantic
│   ├── config.js            # Thông tin nhóm sinh viên
│   ├── serve.ps1            # Kịch bản khởi chạy máy chủ cục bộ
│   ├── css/                 # CSS chuẩn thiết kế (style.css, fonts.css)
│   ├── js/                  # JS ứng dụng (app.js, charts.js, format.js)
│   ├── fonts/               # Phông Source Sans 3 woff2 cục bộ
│   └── data/                # Dữ liệu tĩnh đã xuất (summary, system, behavior, models, recs)
├── results/                 # Bảng kết quả thực nghiệm, so sánh mô hình, chỉ số
├── reports/                 # Báo cáo, biên bản thực hiện, ảnh chụp kiểm thử
│   ├── evidence/            # Biên bản thực thi stage_*.md, web_design_plan.md, web_contrast.md
│   └── figures/screenshots/ # Ảnh chụp kiểm thử giao diện các trang ở 2 độ phân giải
├── docs/                    # Tài liệu đặc tả (CONTEXT.md, data_contract.md, web_data_contract.md)
├── app/                     # Bản lưu trữ giao diện Streamlit cũ và nguồn dữ liệu CSV
├── docker-compose.yml       # Cấu hình cụm HDFS và Spark
└── run_all.ps1              # Kịch bản chạy toàn diện pipeline và khởi chạy web
```

---

## 5. Hướng dẫn khởi chạy

### Cách 1: Chạy nhanh qua kịch bản PowerShell
```powershell
.\run_all.ps1
```
Kịch bản sẽ tự động:
1. Xuất dữ liệu mới nhất từ kết quả thực nghiệm (`src/export_for_web.py`).
2. Chạy kiểm thử đối chiếu 32 chỉ số (`src/verify_web.py`).
3. Khởi chạy máy chủ nội bộ phục vụ web tại `http://localhost:8000/`.

### Cách 2: Mở thủ công không cần server (Offline hoàn toàn)
Vào thư mục `web/` và nhấp đúp vào tệp `index.html`.

### Cách 3: Xuất và xác minh dữ liệu thủ công
```powershell
python src/export_for_web.py
python src/verify_web.py
```

---

## 6. Phím tắt trình chiếu
- **Phím 1 đến 5:** Chuyển nhanh giữa 5 trang (Dữ liệu -> Hệ thống -> Hành vi -> Gợi ý -> Mô hình).
- **Phím Esc:** Đóng ngăn trượt Chú giải thuật ngữ hoặc hộp thoại Tinh chỉnh mô hình.
- **Nút Segmented:** Chuyển đổi giữa bộ dữ liệu Món Việt (ViFoodRec) và Món Âu Mỹ (Food.com).

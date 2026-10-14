# KẾ HOẠCH THIẾT KẾ DASHBOARD WEB TĨNH (WEB DESIGN PLAN)

- **Mục tiêu:** Xây dựng dashboard tĩnh (HTML/CSS/JS thuần), chuẩn mực báo cáo kỹ thuật, mỗi trang vừa đúng một màn hình (1920x1080 và 1366x768), không cuộn dọc, thay thế hoàn toàn giao diện Streamlit cũ.
- **Phong cách:** Nghiêm túc, thanh lịch, kỷ luật, lấy cảm hứng từ in ấn kỹ thuật và đồ họa thông tin khoa học (Information Design).

---

## 1. Bảng Design Tokens Cốt Lõi

### 1.1. Bảng màu (Tối giản, kiểm soát độ chói & tương phản WCAG)

| Mã Hex | Tên Token | Ý nghĩa & Vùng áp dụng | Độ chói tương đối (Luminance) | Tương phản với nền trắng |
|---|---|---|:---:|:---:|
| `#FFFFFF` | `--bg-main` | Nền trang chính, vùng trống thông thoáng | 1.000 | 1:1 |
| `#F5F7F5` | `--bg-subtle` | Nền phụ, hàng xen kẽ trong bảng, ô nhập | 0.941 | 1.06:1 |
| `#D8DFD8` | `--border` | Đường kẻ phân vùng 1px sắc nét | 0.725 | 1.36:1 |
| `#182218` | `--text-primary` | Màu chữ chính, tiêu đề, số liệu quan trọng | 0.016 | **15.9:1** (Vượt chuẩn AAA 7:1) |
| `#364336` | `--text-secondary` | Nhãn phụ, nguồn dữ liệu, ghi chú trục | 0.054 | **10.1:1** (Vượt chuẩn AAA 7:1) |
| `#1A5336` | `--brand-green` | **Màu chủ đạo duy nhất**: Nút bấm, tab kích hoạt, cột dữ liệu chính | 0.076 | **8.33:1** (Vượt chuẩn AAA 7:1) |
| `#C85A17` | `--accent-orange` | **Điểm nhấn tối thiểu (< 2%)**: Đánh dấu giá trị tốt nhất, cảnh báo | 0.165 | **4.88:1** (Vượt chuẩn AA 4.5:1) |

### 1.2. Bảng màu biểu đồ (Phân biệt rõ ràng theo độ sáng ở thang xám)

Nhằm phục vụ máy chiếu độ phân giải thấp và bản in đơn sắc, 4 sắc thái được thiết kế với khoảng cách độ sáng rõ rệt:
1. **Sắc thái 1 (Rất đậm):** `#1A5336` (Độ chói: 0.076) — Nhóm chính / Món mặn / ViFoodRec.
2. **Sắc thái 2 (Trung bình đậm):** `#4B735B` (Độ chói: 0.165) — Nhóm thứ 2 / Baseline.
3. **Sắc thái 3 (Trung bình sáng):** `#86A391` (Độ chói: 0.355) — Nhóm thứ 3 / Food.com.
4. **Sắc thái 4 (Sáng):** `#C5D6CC` (Độ chói: 0.632) — Nhóm thứ 4 / Món chay.
5. **Điểm nhấn đặc biệt:** `#C85A17` (Độ chói: 0.165, độ bão hòa cao) — Mô hình tối ưu / Điểm dị biệt.

### 1.3. Thang kích thước chữ (Typography Scale - Offline Source Sans 3)

- **Họ phông:** `'Source Sans 3', system-ui, -apple-system, "Segoe UI", Roboto, sans-serif`
- **Đặc tính số:** `font-variant-numeric: tabular-nums` (Căn thẳng hàng theo cột dọc tuyệt đối).
- **Quy định cỡ chữ tối thiểu trên màn hình máy chiếu (1920x1080):**
  - Tiêu đề phát hiện trang (`<h1>`): `22px` (semibold, tối đa 90 ký tự).
  - Tiêu đề khối / mục (`<h2>`): `18px` (semibold).
  - Thân văn bản / Nhãn thao tác: `17px` (regular, đảm bảo máy chiếu đọc rõ).
  - Dữ liệu trong bảng: `16px` (regular/tabular-nums).
  - Nhãn trục biểu đồ & chú thích: `14px` (regular).
  - Dòng nguồn dữ liệu: `13px` (regular).

### 1.4. Khoảng cách & Lưới (Spacing & Grid)

- Lưới 12 cột bất đối xứng, rãnh lưới (gap): `16px` ở 1920x1080, `12px` ở 1366x768.
- Thanh điều hướng trên cùng: Cao cố định `52px`, đường kẻ dưới `1px solid var(--border)`.
- Vùng nội dung: `height: calc(100vh - 52px)`, không cuộn trang ở độ phân giải $\ge 1280 \times 720$.
- Phân cách bằng đường kẻ `1px solid var(--border)` và khoảng trắng có tính toán. Tuyệt đối không dùng đổ bóng (`box-shadow`), không dùng nền chuyển màu (`gradient`).
- Bo góc: Tối đa `3px` và chỉ áp dụng cho ô nhập (`input`, `select`) và nút bấm (`button`). Toàn bộ khung bảng, khung biểu đồ sắc nét (0px border-radius).

---

## 2. Bố Cục Chi Tiết 5 Trang (1 Màn Hình, Không Cuộn)

### Trang 1: Dữ liệu (`#/du-lieu`)
- **Tiêu đề phát hiện:** *"Hai bộ dữ liệu có đặc tính đối lập: ViFoodRec dày đặc nhưng quy mô nhỏ, Food.com mở rộng nhưng cực thưa"* (89 ký tự).
- **Cột trái (7 cột):** Phễu làm sạch dữ liệu trực quan (Data Cleaning Funnel) dựng bằng thanh ngang tỷ lệ:
  - Nhánh ViFoodRec: 182.678 dòng thô $\rightarrow$ Loại 33.211 điểm ngoài [1,5] (gồm 16.509 điểm 0 và 16.702 điểm 0,5) $\rightarrow$ Loại 36 khóa ngoại mồ côi $\rightarrow$ Còn 149.431 dòng sạch (K-core hội tụ ngay vòng 1).
  - Nhánh Food.com: 1.132.367 tương tác thô $\rightarrow$ Loại 60.847 điểm 0 $\rightarrow$ Lọc K-core lặp 5 vòng loại 365.006 dòng $\rightarrow$ Còn 706.514 tương tác sạch.
- **Cột phải (5 cột):**
  - Nửa trên: Bảng đối chiếu 2 bộ (7 hàng: Người dùng, Món ăn, Tương tác, Độ thưa ma trận, Điểm trung bình, Trung vị tương tác/người, Nguồn dữ liệu).
  - Nửa dưới: Hai biểu đồ cột mini phân phối điểm đánh giá đặt cạnh nhau cùng trục hoành [1.0, 5.0], chỉ rõ ViFoodRec phân bổ đều (~11% mỗi bậc điểm) trong khi Food.com lệch cực mạnh về 5 sao (78,4%).
- **Dưới cùng:** 3 dòng giới hạn dữ liệu ngắn gọn và dòng nguồn file CSV.

### Trang 2: Hệ thống (`#/he-thong`)
- **Tiêu đề:** *"Hạ tầng cụm phân tán Docker HDFS và Spark 3.5; Parquet nén dữ liệu sạch 4 đến 7 lần và tăng tốc truy vấn"* (88 ký tự).
- **Cột trái (7 cột):** Sơ đồ kiến trúc SVG chuẩn kỹ thuật phản ánh đúng cụm Docker thật (1 NameNode, 2 DataNodes replication=2, 1 Spark Master, 2 Spark Workers x 2 Cores/3.5GB RAM = 4 Cores/7GB RAM, 1 Client Container). Dưới sơ đồ là bảng thông số cụm đo đạc thực tế.
- **Cột phải (5 cột):** Hai tab chuyển đổi:
  - *Tab Lưu trữ:* So sánh dung lượng CSV vs Parquet (Dữ liệu thô: 1,76x và 2,34x; Dữ liệu sạch: 4,19x và 7,03x) kèm bảng độ trễ truy vấn (Parquet nhanh hơn 1,7x đến 2,1x, có độ lệch chuẩn $\sigma$).
  - *Tab Mở rộng quy mô:* Biểu đồ đường thời gian theo tỷ lệ dữ liệu (10%, 25%, 50%, 100%) so sánh 1 Worker vs 2 Workers. Trình bày trung thực: thời gian không tăng tuyến tính (10% chậm hơn 100% do chi phí khởi tạo JVM/Driver).

### Trang 3: Hành vi (`#/hanh-vi`)
- **Tiêu đề:** *"Người dùng Food.com chia 4 nhóm rõ rệt theo mức độ khắt khe và thời gian; ViFoodRec chưa phân hóa"* (87 ký tự).
- **Bộ điều khiển:** Bộ chọn dữ liệu (ViFoodRec / Food.com) và phân loại đối tượng (Người dùng / Món ăn cho ViFoodRec).
- **Cột trái (7 cột):** Biểu đồ thanh ngang so sánh độ lệch phần trăm của các cụm so với trung bình hệ thống trên các đặc trưng chính.
  - Áp dụng quy tắc trung thực: Với cụm người dùng ViFoodRec, do độ lệch mọi chiều đều < 10% (điểm TB 3,00 / 2,96 / 3,03), giao diện hiển thị thông báo "Các cụm chưa phân biệt rõ" và chỉ đánh số Cụm 1, 2, 3, không dùng tên gán ghép.
- **Cột phải (5 cột):** Danh sách hồ sơ định lượng của từng cụm và bảng món ăn tiêu biểu của cụm đang chọn. Nút mở bảng Silhouette / WSSSE trong ngăn chú giải.

### Trang 4: Gợi ý (`#/goi-y`) — Tâm điểm thiết kế
- **Tiêu đề:** *"Trình diễn gợi ý thực đơn cá nhân hóa từ mô hình ALS và giải quyết Cold-Start bằng ma trận tương đồng"* (88 ký tự).
- **Cột trái (4 cột):** Thanh điều khiển:
  - Bộ dữ liệu (ViFoodRec / Food.com).
  - Chế độ: [Người dùng có sẵn] hoặc [Người dùng mới].
  - Bộ lọc: Loại món (Tất cả / Mặn / Chay), Thời gian nấu tối đa, Calo tối đa, Số món cần gợi ý (Top-N).
  - Nút "Xóa bộ lọc".
- **Cột phải (8 cột):** Danh sách kết quả trình bày dạng **HÀNG THỰC ĐƠN (Menu List Item)**:
  - Mỗi món một hàng tinh tế, tên món in đậm bên trái, thông số dinh dưỡng/thời gian/loại món căn thẳng hàng bên phải.
  - Chế độ Cold-Start: Dòng giải thích trực quan: *"Tương đồng 98,3% với 'Bún bò Huế' và 2 món khác bạn chọn"*.
  - Khi bộ lọc làm số món ít hơn N: Nêu rõ số lượng còn lại và gợi ý nới lỏng bộ lọc.

### Trang 5: Mô hình (`#/mo-hinh`)
- **Tiêu đề:** *"Mô hình ALS không vượt qua baseline về RMSE và Precision@10 do tập dữ liệu lệch điểm mạnh"* (85 ký tự).
- **Cột trái (6 cột):** Bảng so sánh 3 mô hình Baseline và ALS trên tập Test. Giá trị tốt nhất mỗi cột được in đậm và gạch chân (không chỉ dùng màu). Phía dưới là bảng Grid Search tinh chỉnh tham số ALS.
- **Cột phải (6 cột):** Biểu đồ cột nhóm so sánh sai số RMSE của ALS với Baseline (Global Mean, Item Mean) phân rã theo từng mức điểm đánh giá thật (1 đến 5 sao), chỉ rõ ALS dự đoán co cụm quanh điểm trung bình.

---

## 3. Tự Rà Soát và Khử Bỏ Khuôn Mẫu (Self-Audit & Pattern Elimination)

Bảng đối chiếu nghiêm ngặt với các lỗi bị từ chối và thói quen thiết kế mặc định:

| # | Yếu tố bị cấm / Khuôn mẫu xấu | Trạng thái trong thiết kế này | Biện pháp kỹ thuật loại trừ |
|:---:|---|:---:|---|
| 1 | Biểu tượng cảm xúc (emoji), icon tròn, icon địa cầu, icon SVG | **HOÀN TOÀN KHÔNG CÓ (0)** | Thanh điều hướng, nút bấm, bảng biểu chỉ dùng chữ thuần túy. SVG chỉ dùng cho biểu đồ và sơ đồ hệ thống. |
| 2 | Thẻ chỉ số "số to + nhãn nhỏ" (Metric Cards) | **ĐÃ LOẠI BỎ** | Thông tin được cấu trúc thành bảng số liệu khoa học và phễu trực quan. |
| 3 | Nền đen, nền kem, màu neon, viền phát sáng | **ĐÃ LOẠI BỎ** | Nền trắng `#FFFFFF` và xám nhạt `#F5F7F5`. Không phát sáng, không viền neon. |
| 4 | Nền chuyển màu (`linear-gradient`, `radial-gradient`) | **HOÀN TOÀN KHÔNG CÓ (0)** | Toàn bộ CSS không chứa bất kỳ hàm `gradient` nào. |
| 5 | Đổ bóng mờ (`box-shadow`) | **HOÀN TOÀN KHÔNG CÓ (0)** | Phân định vùng bằng đường kẻ 1px sắc nét `#D8DFD8` và khoảng trắng. |
| 6 | Chữ IN HOA giãn khoảng cách (`uppercase`) | **HOÀN TOÀN KHÔNG CÓ (0)** | `text-transform: none`. Toàn bộ tuân thủ viết hoa ngữ pháp tiếng Việt (chữ đầu câu và tên riêng). |
| 7 | Đoạn văn dài, khối "kết luận khoa học", khối "giải thích người xem" | **ĐÃ LOẠI BỎ** | Mỗi trang chỉ có 1 dòng tiêu đề phát hiện ($\le 90$ ký tự) và dòng nguồn số liệu. |
| 8 | Thuật ngữ gây rối mắt trên màn hình chính | **ĐÃ CHUYỂN VÀO NGĂN CHÚ GIẢI** | Mở bằng nút "Chú giải" hoặc phím `Esc` để đóng. Mỗi thuật ngữ chỉ 1 câu ngắn gọn. |
| 9 | Dấu chấm giữa "A · B", mũi tên "→" trên nút, tô màu riêng một chữ | **HOÀN TOÀN KHÔNG CÓ** | Nút bấm chỉ dùng động từ tiếng Việt ("Xóa bộ lọc", "Chú giải", "Lưu trữ"). |
| 10 | Đánh số thứ tự 01, 02, 03 nhân tạo | **HOÀN TOÀN KHÔNG CÓ** | Không đánh số các khối độc lập. |
| 11 | Chuyển động tự chạy (counter, fade-in liên tục) | **HOÀN TOÀN KHÔNG CÓ** | Không có CSS animation vô tận. Chỉ có chuyển trạng thái hover 120ms. |

---

## 4. Kế Hoạch Triển Khai và Điểm Dừng Duyệt

1. **Bước 1:** Dựng khung ứng dụng dùng chung (`index.html`, `css/style.css`, `js/app.js`, `js/charts.js`, `js/format.js`, `config.js`).
2. **Bước 2:** Dựng hoàn chỉnh **Trang 1: Dữ liệu (`#/du-lieu`)** với Phễu làm sạch 2 nhánh và Bảng đối chiếu + Biểu đồ phân phối điểm.
3. **Bước 3:** Chụp ảnh màn hình ở độ phân giải `1920x1080` và `1366x768`, kiểm tra không cuộn trang (`document.documentElement.scrollHeight <= window.innerHeight`).
4. **Bước 4 (ĐIỂM DỪNG DUYỆT):** Dừng lại, trình bày kết quả và ảnh chụp để người dùng duyệt giao diện trước khi triển khai tiếp các trang 2, 3, 4, 5.

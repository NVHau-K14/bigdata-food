# HƯỚNG DẪN SỬ DỤNG VÀ VẬN HÀNH DASHBOARD WEB TĨNH

Tài liệu hướng dẫn mở, trình chiếu, kiểm thử và cập nhật dữ liệu cho giao diện dashboard tĩnh (`web/`) của đồ án Big Data: **"Phân tích hành vi ăn uống và gợi ý món ăn"**.

---

## 1. Tổng quan kiến trúc
- **Công nghệ:** HTML5, Vanilla CSS3, JavaScript thuần (ES6).
- **Không phụ thuộc build-tool:** Không dùng Node.js, Webpack, Vite, React, Vue, hay Tailwind.
- **Biểu đồ & Sơ đồ:** 100% Pure SVG tự vẽ qua module `web/js/charts.js`, không dùng thư viện ngoài cồng kềnh.
- **Phông chữ:** `Source Sans 3` (các tệp woff2 lưu trữ cục bộ tại `web/fonts/`), hỗ trợ đầy đủ tiếng Việt và số đều chiều rộng (`tabular-nums`), hoạt động hoàn toàn **Offline** khi không có Internet.
- **Chuẩn thiết kế:** Vừa khít 1 khung hình màn hình ở độ phân giải máy chiếu (`1920x1080`) và laptop (`1366x768`), **tuyệt đối không cuộn trang** (`0px vertical scroll`).

---

## 2. Cách mở và trình chiếu

### Cách 1: Chạy trực tiếp từ tệp (Offline 100%)
Nhấp đúp chuột trực tiếp vào tệp `web/index.html` trong File Explorer (đường dẫn `file:///.../web/index.html`).
- Toàn bộ dữ liệu được nạp qua thẻ `<script src="data/...">`, không dùng `fetch()` bất đồng bộ nên không bị trình duyệt chặn CORS/file protocol.
- Đầy đủ tính năng phân tích, lọc thực đơn gợi ý, chuyển trang, mở chú giải thuật ngữ.

### Cách 2: Chạy qua máy chủ nội bộ (Khuyến nghị khi trình chiếu)
Mở PowerShell tại thư mục dự án và chạy:
```powershell
.\web\serve.ps1
```
Hoặc chạy lệnh Python chuẩn:
```powershell
python -m http.server 8000 --directory web
```
Sau đó mở trình duyệt tại: `http://localhost:8000/`

---

## 3. Phím tắt và điều hướng khi thuyết trình

| Phím / Thao tác | Chức năng |
|---|---|
| **Phím 1** | Chuyển đến **Trang 1: Dữ liệu** (`#/du-lieu`) |
| **Phím 2** | Chuyển đến **Trang 2: Hệ thống** (`#/he-thong`) |
| **Phím 3** | Chuyển đến **Trang 3: Hành vi** (`#/hanh-vi`) |
| **Phím 4** | Chuyển đến **Trang 4: Gợi ý** (`#/goi-y`) |
| **Phím 5** | Chuyển đến **Trang 5: Mô hình** (`#/mo-hinh`) |
| **Nút "Chú giải"** | Mở ngăn trượt bên phải giải thích 18 thuật ngữ, mỗi thuật ngữ một câu |
| **Phím Esc** | Đóng ngăn "Chú giải" hoặc đóng hộp thoại "Thông số tinh chỉnh" |
| **Thanh chọn Segmented** | Chuyển giữa ViFoodRec và Food.com (trang Hành vi có thêm ViFoodRec theo món) |

---

## 4. Cấu hình thông tin nhóm sinh viên
Mở tệp `web/config.js` để điền thông tin nhóm và trường (mặc định để trống để không bịa thông tin):
```javascript
window.WEB_CONFIG = {
    institution: "Đại học ...",
    course: "Nhập môn Big Data",
    groupName: "Nhóm 02",
    members: [
        { name: "Họ và tên SV 1", id: "MSSV1" },
        { name: "Họ và tên SV 2", id: "MSSV2" }
    ]
};
```

---

## 5. Quy trình cập nhật dữ liệu khi pipeline Spark chạy lại
Nếu bạn huấn luyện lại mô hình Spark hoặc cập nhật pipeline tiền xử lý:

1. Đảm bảo các tệp kết quả mới nằm trong `app/data/` (chạy `src/export_for_app.py` trong container). Món tiêu biểu theo cụm người dùng
   do `src/export_cluster_top_items.py` sinh ra `app/data/cluster_top_items.csv` (chạy trong container, chỉ đọc dữ liệu).
2. Chạy lệnh xuất dữ liệu chuẩn hóa cho web:
   ```powershell
   python src/export_for_web.py
   ```
   Mọi số và chữ hiển thị đến từ các tệp trong `web/data/` (không viết cứng trong JS):
   - `labels.js`: bảng nhãn hiển thị duy nhất (nguồn `src/web_labels.py`: "Món mặn" hiển thị là "Không chay", tên mô hình).
   - `summary.js`: phễu làm sạch, bảng so sánh hai bộ, phân phối điểm (~6 KB).
   - `system.js`: phiên bản và cấu hình cụm đọc từ `docker-compose.yml` và log fsck, đo lưu trữ, mở rộng quy mô (~2 KB).
   - `behavior.js`: hồ sơ cụm, nhật ký chọn k, món tiêu biểu theo từng bộ (~13 KB).
   - `models.js`: so sánh mô hình (kể cả ALS ngầm định), phân rã RMSE, tinh chỉnh (~13 KB).
   - `recs_vietnam.js`: gợi ý và độ tương đồng món Việt (~1,8 MB).
   - `recs_foodcom.js`: gợi ý cho 1.000 người dùng Food.com và danh mục các món liên quan (~4,8 MB).
3. Kiểm thử tự động (theo thứ tự):
   ```powershell
   node src/verify_web_ui.mjs      # Chrome hoặc Edge headless: không cuộn trang ở 1920x1080 và 1366x768, luồng demo, ảnh chụp
   python src/verify_web.py        # đối chiếu số hiển thị với tệp nguồn (cần tệp văn bản do lệnh trên ghi)
   python src/verify_web_style.py  # quét mã, tương phản, thang xám, diện tích màu cam, ảnh chia sẻ
   ```
   Cả ba lệnh phải thoát với mã 0. Ảnh chụp nằm ở `reports/figures/screenshots/web_v2/`.
4. Tải lại trang web (F5 hoặc Ctrl+F5) để hiển thị số liệu mới nhất.

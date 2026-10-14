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
| **Nút "Chú giải"** | Mở ngăn trượt bên phải giải thích 9 thuật ngữ kỹ thuật ngắn gọn |
| **Phím Esc** | Đóng ngăn "Chú giải" hoặc đóng hộp thoại "Thông số tinh chỉnh" |
| **Thanh chọn Segmented** | Chuyển đổi linh hoạt giữa bộ dữ liệu **ViFoodRec (Món Việt)** và **Food.com (Âu Mỹ)** |

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

1. Đảm bảo các tệp kết quả mới nằm trong `app/data/` và `results/`.
2. Chạy lệnh xuất dữ liệu chuẩn hóa cho web:
   ```powershell
   python src/export_for_web.py
   ```
   Lệnh sẽ tự động nén, cấu trúc hóa và ghi ra các tệp dữ liệu tĩnh trong `web/data/`:
   - `summary.js`: Tổng quan dữ liệu & phễu làm sạch (~5.7 KB).
   - `system.js`: Benchmark dung lượng lưu trữ & khả năng mở rộng (~10.0 KB).
   - `behavior.js`: Cấu hình cụm K-means & điều chỉnh số cụm k (~8.5 KB).
   - `models.js`: Đối chiếu độ đo các mô hình & chi tiết RMSE theo sao (~10.8 KB).
   - `recs_vietnam.js`: Dữ liệu gợi ý và tương đồng món Việt (~1.91 MB).
   - `recs_foodcom.js`: Dữ liệu gợi ý chọn lọc cho 5.000 người dùng Food.com (~2.41 MB).
3. Kiểm tra tính toàn vẹn và khớp số liệu tự động:
   ```powershell
   python src/verify_web.py
   ```
   *(Cần đảm bảo 32/32 chỉ số đều báo `PASSED` và mã thoát bằng `0`).*
4. Tải lại trang web (F5 hoặc Ctrl+F5) để hiển thị số liệu mới nhất.

# PROMPT XÂY DỰNG DASHBOARD WEB RIÊNG (THAY STREAMLIT)

**Mục đích:** giao cho Gemini (Antigravity) dựng lại toàn bộ giao diện thành một trang web tĩnh (HTML/CSS/JS), thiết kế mới hoàn toàn, nghiêm túc, mỗi trang vừa một màn hình, không cuộn.
**Cách dùng:** mở một cuộc trò chuyện mới, dán nguyên khối prompt ở mục 2. Cho phép Gemini suy nghĩ lâu và dùng nhiều token (prompt đã yêu cầu lập kế hoạch và tự phê bình).
**Không đụng đến:** pipeline Spark, mô hình, số liệu.

---

## 1. Ba phát hiện trong dữ liệu thật mà bạn cần biết (không phụ thuộc giao diện)

Mình đã đọc các file kết quả bạn gửi. Ba điểm sau ảnh hưởng đến báo cáo và đã được đưa vào prompt để giao diện **trình bày trung thực**:

| # | Phát hiện | Bằng chứng | Việc cần quyết định |
|---|---|---|---|
| 1 | **ALS không thắng baseline ở độ đo nào** trên cả hai bộ | `model_comparison.csv`: ViFoodRec RMSE ALS 1,3832 so với Trung bình toàn cục 1,2866; Food.com RMSE ALS 0,6747 so với Trung bình theo món 0,6177; Precision@10 của ALS thấp hơn Top-N phổ biến ở cả hai bộ | Không cần sửa. Giữ kết quả thật và phân tích nguyên nhân trong báo cáo (giảng viên chấm cả khả năng giải thích). Food.com lệch mạnh về 5 sao (điểm TB 4,68; 93% từ 4 sao trở lên) nên baseline rất mạnh |
| 2 | **Các cụm người dùng ViFoodRec gần như không khác nhau** | `cluster_profiles_food_vietnam.csv`: điểm TB 3,00 / 2,96 / 3,03; thời gian nấu của món được chấm cao 32,7 / 32,9 / 32,8 phút. Tên cụm như "Chuộng bữa nhanh" **không có số liệu hỗ trợ** | Giao diện sẽ không gọi đó là nhóm hành vi rõ rệt. Phân tích hành vi nên dựa vào Food.com (4 cụm có khác biệt thật) và cụm **món ăn** của ViFoodRec |
| 3 | **ViFoodRec bị loại 16.702 đánh giá 0,5 sao** vì "ngoài [1,5]" | `cleaning_log.csv`: 33.211 dòng bị loại, gồm 16.509 điểm 0,0 và 16.702 điểm 0,5 | 0,5 sao có vẻ là điểm hợp lệ trên thang 0 đến 5 (chưa xác nhận). Mặc định trong bộ prompt P3 của mình đã loại cả hai, **đây là sai sót từ phía mình**. Nếu muốn sửa, phải chạy lại P3 đến P11. Nếu hết thời gian, ghi rõ đây là hạn chế |

Ngoài ra: thí nghiệm lưu trữ đã công bằng (Parquet nhỏ hơn CSV 1,76 lần với dữ liệu thô, 4,19 lần và 7,03 lần với dữ liệu sạch, không còn "60 lần"). Thí nghiệm mở rộng quy mô cho thấy thời gian **gần như phẳng và không đơn điệu** (10% dữ liệu mất 11,99 giây, 100% mất 7,93 giây), nên không được viết "mở rộng tuyến tính".

---

## 2. Prompt cho Gemini

````markdown
Đọc docs/CONTEXT.md trước.

# NHIỆM VỤ
Xây dựng lại dashboard thành một TRANG WEB TĨNH RIÊNG (HTML, CSS, JavaScript thuần), thay hoàn toàn giao diện Streamlit. Thiết kế hoàn toàn mới, nghiêm túc, chuyên nghiệp, dùng để thuyết trình với giảng viên. KHÔNG sửa pipeline Spark, mô hình hay bất kỳ số liệu nào. KHÔNG dùng Streamlit nữa.

Thời gian suy nghĩ và số token không bị giới hạn: hãy lập kế hoạch kỹ, tự phê bình, rồi mới viết mã. Bản làm trước đây (giao diện nền đen, sau đó chỉ đổi sang nền sáng) đã BỊ TỪ CHỐI vì giữ nguyên bố cục cũ, nhiều biểu tượng, khối "kết luận" thừa và trông như sản phẩm sinh tự động. Không được tái hiện lại bất cứ thứ gì sau đây:
- biểu tượng cảm xúc (emoji), biểu tượng, nhãn tròn "VN", hình quả địa cầu, hoặc bất kỳ icon nào;
- thẻ chỉ số lớn "số to + nhãn nhỏ", thanh bên, màu neon, nền chuyển màu, viền phát sáng;
- khối "Kết luận khoa học từ dữ liệu thật", khối "Giải thích thuật ngữ (Dành cho người xem)", và mọi đoạn văn chú thích dài;
- tên "Big Data Food AI" và lời tự quảng cáo;
- lỗi chữ lạ như "arr" trước tiêu đề khối thu gọn.

# 1. ĐỌC TRƯỚC KHI LÀM (bắt buộc)
1. docs/data_contract.md, mọi file trong app/data/ (chỉ đọc), và các file results/*.csv, reports/evidence/cleaning_log*.csv.
2. reports/evidence/stage_P2.md (hoặc stage_P2_fallback.md) và STATUS.md nếu có: để biết HẠ TẦNG THẬT là HDFS + cụm Spark hay Spark local. Sơ đồ kiến trúc trên web PHẢI đúng với hệ thống thật. Nếu chưa xác nhận được, ghi "chưa xác nhận", không vẽ HDFS cho đẹp.
3. Mã Streamlit cũ trong app/ (pages, utils): để PORT lại logic lọc món, gợi ý cho người dùng có sẵn, gợi ý cold-start theo món tương đồng. Không sửa các file này, chỉ đọc.
4. Ảnh chụp giao diện cũ (nếu có trong reports/figures/screenshots/) để biết cái gì phải bỏ.

# 2. SỰ THẬT VỀ DỮ LIỆU MÀ GIAO DIỆN PHẢI PHẢN ÁNH TRUNG THỰC
Các điều sau đã được kiểm tra từ file kết quả. Giao diện phải thể hiện đúng, không tô vẽ, không dùng từ như "vượt trội", "tối ưu", "đột phá". Mọi con số phải ĐỌC TỪ FILE, không gõ cứng; hãy kiểm tra lại từng điều với file thật trước khi dùng.
- model_comparison.csv: ALS KHÔNG tốt hơn baseline ở RMSE, MAE, Precision@10, Recall@10 trên cả hai bộ. Phải hiển thị đúng điều này, kể cả khi không có lợi cho nhóm. Độ phủ (coverage) 100%.
- cluster_profiles_food_vietnam.csv: ba cụm người dùng ViFoodRec gần như giống hệt nhau trên mọi đặc trưng (điểm TB 3,00 / 2,96 / 3,03). Quy tắc: nếu chênh lệch tương đối giữa các cụm trên mọi đặc trưng nhỏ hơn 10% thì hiển thị một dòng nêu rõ "các cụm chưa phân biệt rõ" và KHÔNG dùng các tên diễn giải kiểu "chuộng bữa nhanh" (dùng "Cụm 1, 2, 3"). Việc quyết định này phải do mã tự tính từ dữ liệu, không gõ cứng.
- cluster_profiles_food_com.csv: bốn cụm Food.com có khác biệt thật (ví dụ điểm TB 3,83 so với khoảng 4,7 đến 4,9; thời gian nấu TB 45,5 phút so với 105,9 phút); tên cụm hiện khớp số liệu, được dùng.
- scalability.csv: thời gian chạy KHÔNG tăng tuyến tính và không đơn điệu (10% dữ liệu chậm hơn 100% ở bước ALS, nhiều khả năng do chi phí khởi động). Không được kết luận "mở rộng tuyến tính". Cần ghi rõ cấu hình đo (số worker, core) lấy từ file.
- storage_benchmark.csv: so sánh công bằng. Dữ liệu thô đầy đủ: Parquet nhỏ hơn CSV 1,76 lần (interactions) và 2,34 lần (recipes). Dữ liệu sạch: 4,19 lần và 7,03 lần. Thời gian truy vấn Parquet nhanh hơn khoảng 1,7 đến 2,1 lần. Không dùng lại con số "60 lần" cũ.
- cleaning_log.csv: ViFoodRec mất 33.211 đánh giá ở bước lọc thang điểm (16.509 điểm 0,0 và 16.702 điểm 0,5), 36 dòng ở bước khóa ngoại. Food.com mất 60.847 dòng điểm 0 và 365.006 dòng ở bước K-core (5 vòng lặp). Phải hiển thị rõ nguồn gốc từng khoản mất, đây là phần minh chứng cho tiêu chí "lưu trữ và xử lý dữ liệu".
- ViFoodRec chỉ có 101 người dùng và là dữ liệu khảo sát; Food.com là ẩm thực phương Tây. Hai bộ không gộp được. Giới hạn này phải xuất hiện ở trang Dữ liệu dưới dạng một mục ngắn, không phải đoạn văn dài.

# 3. BRIEF THIẾT KẾ
- Đối tượng: giảng viên chấm đồ án và bạn cùng lớp. Trình bày bằng MÁY CHIẾU và chia sẻ màn hình online (Meet/Zoom/Teams). Một người điều khiển.
- Việc chính: nhìn mỗi trang trong 5 giây hiểu trang nói gì; demo gợi ý món chạy trơn trong 2 đến 3 phút.
- Không khí: nghiêm túc, chuyên nghiệp, gọn, giống một bản báo cáo phân tích dữ liệu được dàn trang kỹ, không giống ứng dụng tiêu dùng. Ngôn ngữ thiết kế đến từ in ấn kỹ thuật và phân tích dữ liệu: lưới rõ, chữ làm việc chính, đường kẻ mảnh phân vùng, số liệu căn thẳng hàng.
- Màu: nền trắng và xám rất nhạt; XANH LÁ ĐẬM là màu chủ đạo DUY NHẤT (nút, mục đang chọn, dữ liệu chính); CAM chỉ làm điểm nhấn rất nhỏ (chiếm dưới 2% diện tích mỗi trang, ví dụ đánh dấu giá trị tốt nhất hoặc một điểm dữ liệu cần chú ý). Chữ gần đen, tương phản chữ chính với nền tối thiểu 7:1. Không dùng vàng làm chữ. Không nền kem, không màu nâu đất nung, không nền đen.
- Chữ: MỘT họ chữ có đầy đủ dấu tiếng Việt, tải file font (woff2, giấy phép mở) về web/fonts/ để chạy OFFLINE, có font hệ thống dự phòng. Ứng viên: IBM Plex Sans, Source Sans 3 (hãy kiểm tra dấu tiếng Việt hiển thị đúng rồi chọn một). Số dùng chữ số đều chiều rộng (tabular-nums). Không dùng chữ đơn cách (monospace) cho nhãn nhỏ, không IN HOA, không giãn chữ.
- Quy tắc cứng:
  1. KHÔNG có biểu tượng nào (emoji, font biểu tượng, SVG biểu tượng). SVG chỉ dùng cho biểu đồ và sơ đồ. Nút và điều hướng chỉ có chữ.
  2. KHÔNG thẻ (card) bo tròn có bóng. Vùng nội dung phân tách bằng khoảng trắng và đường kẻ 1px, không đổ bóng, không nền chuyển màu. Bo góc tối đa 3px và chỉ áp cho ô nhập và nút.
  3. KHÔNG chuyển động tự chạy (không đếm số, không hiện dần từng phần). Chỉ chuyển trạng thái 120 đến 160ms khi người dùng thao tác.
  4. Viết hoa kiểu tiếng Việt: chỉ chữ đầu câu và tên riêng.
  5. Không đoạn văn giải thích. Mỗi trang chỉ có: một tiêu đề nêu phát hiện (tối đa 90 ký tự), một dòng nguồn số liệu dưới mỗi biểu đồ/bảng (tên file và đơn vị), nhãn trục, và chữ cần cho thao tác. Giải thích thuật ngữ chỉ xuất hiện khi người dùng bấm nút "Chú giải" (ngăn trượt ẩn mặc định, mỗi thuật ngữ một câu bằng tiếng thường: độ thưa, K-core, ALS, RMSE, MAE, Precision@10, Recall@10, Silhouette, cold-start).
  6. Định dạng số kiểu Việt Nam, thống nhất qua MỘT hàm: 149.431; 63,0%; 1,3832. Không viết tắt "K".
- Cỡ chữ cho máy chiếu và chia sẻ online (hình bị nén, nét mảnh bị mờ): chữ nội dung tối thiểu 17px ở 1920x1080, chữ trong bảng tối thiểu 16px, nhãn biểu đồ tối thiểu 14px, không chữ xám nhạt, không đường kẻ mảnh hơn 1px, các màu biểu đồ khác nhau rõ về ĐỘ SÁNG (phân biệt được ở thang xám). Giảm kích thước theo cửa sổ bằng clamp()/đơn vị tương đối nhưng KHÔNG xuống dưới các mức tối thiểu trên.

# 4. KHUNG ỨNG DỤNG
- Thư mục web/ (index.html, css/, js/, data/, fonts/, vendor/). KHÔNG dùng bước build (không Node, React, Vue, Tailwind). Chạy được bằng cách nhấp đúp index.html HOẶC một lệnh phục vụ cục bộ (web/serve.ps1 dùng python -m http.server). Vì trình duyệt chặn fetch và ES module khi mở bằng file://, hãy nạp dữ liệu bằng thẻ <script> (mỗi tập dữ liệu là một file .js gán vào một đối tượng toàn cục) và dùng script thường. Không cần internet khi chạy.
- Biểu đồ: dùng một thư viện nhỏ đặt cục bộ trong web/vendor/ (ví dụ Chart.js hoặc ECharts, ghi rõ phiên bản và giấy phép) hoặc tự vẽ SVG bằng một module nhỏ. Chọn một cách, ưu tiên cách hai sinh viên đọc và giải thích được. Tất cả biểu đồ dùng chung một cấu hình (font, màu, lưới, lề).
- Điều hướng: thanh ngang trên cùng, chỉ chữ: tên đề tài ở bên trái ("Phân tích hành vi ăn uống và gợi ý món ăn"), các mục bên phải. Điều hướng theo hash (#/du-lieu, #/he-thong, #/hanh-vi, #/goi-y, #/mo-hinh) để chia sẻ và tải lại không mất vị trí. Phím 1 đến 5 chuyển trang cho người thuyết trình, Esc đóng ngăn "Chú giải". Mục đang chọn có gạch dưới màu xanh đậm.
- Bộ chọn bộ dữ liệu (ViFoodRec: món Việt / Food.com: món Âu Mỹ): kiểu nút chọn bằng chữ (segmented), chỉ hiện ở trang cần, ghi nhớ khi chuyển trang. Mặc định ViFoodRec.
- Tên thành viên và trường: đặt trong web/config.js với giá trị trống để nhóm tự điền. KHÔNG bịa tên.

# 5. BỐ CỤC TỪNG TRANG
Nền tảng: màn hình 1920x1080, lưới 12 cột bất đối xứng, MỖI TRANG VỪA MỘT MÀN HÌNH, KHÔNG CUỘN ở 1920x1080 và 1366x768 (cuộn chỉ được phép dưới 1280x720). Vùng nội dung cao calc(100vh - chiều cao thanh trên). Tuyệt đối không xếp mọi thứ thành một cột dọc. Hình ASCII chỉ mô tả bố cục, không phải thiết kế cuối.

## Trang 1: Dữ liệu (#/du-lieu, trang mở đầu)
```
[Tiêu đề nêu phát hiện]
+------------------------------------------+----------------------------------+
| Phễu làm sạch (thanh ngang, 2 nhóm):     | Bảng đối chiếu hai bộ (7 hàng:   |
|  ViFoodRec: thô -> từng bước loại ->     |  người dùng, món, tương tác,     |
|  sạch; Food.com tương tự. Mỗi bước ghi  |  độ thưa, điểm TB, trung vị      |
|  số dòng bị loại và lý do (cleaning_log) |  đánh giá/người, nguồn)          |
|                                          |----------------------------------|
|                                          | Phân phối điểm: hai biểu đồ cột  |
|                                          |  nhỏ cạnh nhau, chung thang      |
+------------------------------------------+----------------------------------+
[Mục "Giới hạn dữ liệu": 3 dòng ngắn]   [dòng nguồn]
```
Điểm nhấn của trang là phễu làm sạch (hiển thị minh bạch dữ liệu đi đâu), không phải thẻ chỉ số.

## Trang 2: Hệ thống (#/he-thong)
```
[Tiêu đề]
+------------------------------------------+----------------------------------+
| Sơ đồ kiến trúc ngang (SVG): dữ liệu     | [Lưu trữ | Mở rộng quy mô] (tab    |
|  thô -> lưu trữ -> xử lý -> kết quả ->   |  chữ)                            |
|  giao diện; mỗi khối ghi công nghệ và vai| Lưu trữ: so sánh dung lượng CSV với|
|  trò; ĐÚNG hạ tầng thật.                  |  Parquet (3 thí nghiệm) + thời   |
| Dưới sơ đồ: cấu hình cụm đo (worker,     |  gian truy vấn (có độ lệch chuẩn)|
|  core, RAM) lấy từ file/biên bản.        | Mở rộng: đường thời gian theo tỷ lệ|
|                                          |  dữ liệu, 2 đường (1 và 2 worker) |
+------------------------------------------+----------------------------------+
```

## Trang 3: Hành vi (#/hanh-vi)
```
[Tiêu đề]  [Bộ dữ liệu] [Người dùng | Món ăn (chỉ ViFoodRec)]
+------------------------------------------+----------------------------------+
| Biểu đồ chính: so sánh các cụm trên các  | Danh sách cụm (mỗi cụm một hàng):|
|  đặc trưng, hiển thị độ lệch so với mức  |  tên, số người và tỷ lệ, 2 đến 3|
|  trung bình chung (thanh ngang cùng thang)|  đặc trưng nổi bật kèm số        |
|                                          |----------------------------------|
|                                          | Món tiêu biểu của cụm đang chọn  |
+------------------------------------------+----------------------------------+
[dòng nguồn]  [liên kết chữ "Cách chọn số cụm" mở bảng Silhouette/WSSSE từ kmeans_tuning.csv]
```
Áp dụng quy tắc ở mục 2 cho cụm ViFoodRec. Nếu không có tọa độ PCA trong dữ liệu đã xuất thì KHÔNG vẽ biểu đồ phân tán; nếu cần thì viết bước xuất bổ sung từ kết quả có sẵn (không tạo số liệu mới).

## Trang 4: Gợi ý (#/goi-y) - điểm nhấn thiết kế của cả ứng dụng
```
+--------------------------+-------------------------------------------------+
| Điều khiển (4 cột):      | Kết quả (8 cột) trình bày như THỰC ĐƠN:        |
|  Bộ dữ liệu              |  mỗi món một hàng, tên món nổi bật bên trái,    |
|  Chế độ: [Người dùng có  |  bên phải thẳng hàng: loại (Mặn/Chay bằng chữ), |
|   sẵn | Người dùng mới]  |  calo, thời gian nấu; dòng phụ: nguyên liệu chính|
|  - có sẵn: chọn mã người |  (rút gọn); ở chế độ người dùng mới: dòng lý do |
|    dùng + hiện cụm của họ|  "gần với: A (0,98), B (0,95)"                  |
|  - người dùng mới: ô tìm |                                                 |
|    món (tìm KHÔNG DẤU),  |                                                 |
|    chọn 3 đến 5 món      |                                                 |
|  Bộ lọc: loại món, thời  |                                                 |
|   gian tối đa, calo tối  |                                                 |
|   đa, số món (N); nút    |                                                 |
|   "Xóa bộ lọc"           |                                                 |
+--------------------------+-------------------------------------------------+
```
- Trình bày kết quả như hàng thực đơn có hệ thống thông tin nhất quán, dễ quét mắt từ xa, KHÔNG phải lưới thẻ giống hệt nhau.
- Chế độ người dùng mới: điểm món = tổng độ tương đồng từ các món đã chọn (dùng item_neighbors), loại các món đã chọn.
- Khi bộ lọc làm còn ít món hơn N: hiển thị số món còn lại và một dòng hướng dẫn nới lỏng bộ lọc (không xin lỗi chung chung).
- Không hiển thị đánh giá của mô hình lên trang này. Trang Mô hình chịu trách nhiệm nói ALS thua baseline.

## Trang 5: Mô hình (#/mo-hinh)
```
[Tiêu đề nêu mô hình tốt nhất theo từng độ đo, sinh từ dữ liệu]  [Bộ dữ liệu]
+------------------------------------------+----------------------------------+
| Bảng mô hình x độ đo (RMSE, MAE, P@10,   | RMSE theo mức điểm thật (1 đến 5)|
|  R@10, độ phủ). Ô tốt nhất mỗi cột: chữ  |  biểu đồ cột nhóm: baseline so   |
|  đậm + gạch chân (không chỉ dựa vào màu) |  với ALS (từ *_rmse_breakdown)   |
|  Chú thích hướng: RMSE/MAE thấp hơn tốt  |                                  |
|---------------------------------------- |----------------------------------|
| Tinh chỉnh ALS: cấu hình được chọn và 5  | Mốc tham chiếu: đường Trung bình  |
|  cấu hình tốt nhất (als_tuning_*.csv)    |  toàn cục                        |
+------------------------------------------+----------------------------------+
```
Tiêu đề phải do mã chọn từ số thật (hàm tìm mô hình tốt nhất theo từng độ đo), nêu đúng sự thật dù ALS không đứng đầu. Có thể thêm một dòng nguồn ghi rõ mô hình dùng tập kiểm tra nào.

# 6. DỮ LIỆU CHO WEB
- Viết src/export_for_web.py: đọc app/data/ và results/, ghi ra web/data/*.js (mỗi file một đối tượng toàn cục). Chỉ giữ cột cần cho hiển thị. Với Food.com, KHÔNG nạp 78.171 công thức đầy đủ: chỉ nạp các công thức xuất hiện trong gợi ý (5.000 người) và trong danh sách láng giềng, với các cột id, tên, calo, thời gian, nguyên liệu (rút gọn 6 mục đầu).
- Ngân sách: nạp ban đầu tối đa 3 MB; mỗi tập nạp chậm (theo trang/bộ dữ liệu) tối đa 12 MB; tổng web/data tối đa 40 MB. Nạp chậm khi người dùng chọn bộ dữ liệu hoặc mở trang.
- Viết docs/web_data_contract.md: mỗi file (tên, đối tượng toàn cục, trường, số dòng thật, nguồn).
- KHÔNG gõ cứng con số trong HTML/JS. Mọi số trên giao diện lấy từ web/data.

# 7. QUY TRÌNH LÀM VIỆC
1. Lập kế hoạch vào reports/evidence/web_design_plan.md: bảng token (màu 4 đến 6 mã hex có tên, thang chữ, khoảng cách, bảng màu biểu đồ có độ sáng khác nhau rõ), bố cục từng trang (có thể tinh chỉnh các hình ASCII ở mục 5, nhưng KHÔNG đổi khái niệm: lưới bất đối xứng, một màn hình, điều hướng ngang, không cuộn, không thẻ, không icon), và phần TỰ RÀ SOÁT: đối chiếu với danh sách "không được tái hiện" ở đầu prompt và danh sách mẫu quen thuộc (nền kem/đất nung, nền đen và một màu neon, thẻ giống hệt nhau bóng xám, nhãn IN HOA giãn chữ, dấu chấm giữa "A · B", mũi tên "→" trên nút, tô màu riêng một chữ trong tiêu đề, đánh số 01/02/03 khi nội dung không phải chuỗi bước). Phần nào giống mẫu mặc định thì SỬA và ghi lại đã đổi gì.
2. Tiêu hết sự táo bạo ở MỘT chỗ (trang Gợi ý dạng thực đơn, và phễu làm sạch ở trang Dữ liệu). Mọi phần còn lại giữ im lặng, kỷ luật. Trước khi chốt mỗi trang, bỏ bớt một thứ trang trí.
3. Xây khung chung (thanh điều hướng, lưới, chữ, màu, hàm định dạng số, biểu đồ chung) và TRANG 1 trước. Chụp ảnh trang 1 ở 1920x1080 và 1366x768, tự phê bình rồi sửa.
4. ĐIỂM DỪNG DUYỆT: sau khi xong khung chung và trang 1, DỪNG LẠI, đính kèm ảnh chụp và nói rõ đã làm gì để người dùng duyệt hướng thiết kế. Chỉ làm tiếp 4 trang còn lại khi người dùng trả lời "tiếp tục".
5. Với mỗi trang còn lại: dựng, chụp ảnh ở hai kích thước, liệt kê lỗi bố cục thấy được (chữ cắt, tràn, chồng nhau, cuộn dọc), sửa, chụp lại.

# 8. KIỂM THỬ VÀ BẰNG CHỨNG (tự động hóa, dán kết quả thật vào reports/evidence/stage_WEB.md)
1. Kiểm tra không cuộn: với mỗi trang và mỗi trạng thái chính (hai bộ dữ liệu, hai chế độ gợi ý, các tab), ở 1920x1080 và 1366x768, document.documentElement.scrollHeight không vượt chiều cao cửa sổ. Báo bảng đạt/không đạt.
2. Kiểm tra mã nguồn bằng lệnh tìm kiếm: không có emoji hay ký tự biểu tượng, không font biểu tượng, không thẻ <svg> dùng làm icon (chỉ SVG của biểu đồ/sơ đồ), không text-transform: uppercase, không box-shadow (trừ ngăn Chú giải nếu cần), không linear-gradient/radial-gradient, không animation tự chạy. Số lượng vi phạm phải bằng 0.
3. Đối chiếu số liệu: viết src/verify_web.py đọc web/data và đối chiếu ít nhất 25 con số hiển thị (số dòng, điểm TB, RMSE, số cụm, kích thước tệp) với file nguồn gốc (CSV/Parquet). Thoát với mã lỗi khác 0 nếu sai.
4. Tương phản WCAG cho mọi cặp màu chữ-nền và thành phần giao diện (chữ chính từ 7:1; chữ lớn và đường biểu đồ từ 3:1). Ghi bảng vào reports/evidence/web_contrast.md.
5. Mô phỏng chia sẻ online: thu nhỏ mỗi ảnh chụp 1920x1080 còn khoảng 960x540 và nén JPEG khoảng 60%; chữ nội dung, số trong bảng và nhãn trục vẫn phải đọc được. Mô phỏng máy chiếu: chuyển sang thang xám, các màu phân loại vẫn phân biệt được.
6. Chạy OFFLINE (ngắt mạng): font, biểu đồ, mọi trang vẫn hoạt động. Mở được bằng nhấp đúp index.html và bằng web/serve.ps1.
7. Kiểm thử luồng demo bằng trình duyệt tự động: chọn một người dùng ViFoodRec và xem 10 món; chế độ người dùng mới chọn 3 bộ món khác nhau (ví dụ một món chay, một món nhanh, một món nhiều calo) và xác nhận gợi ý hợp lý, có lý do; áp dụng từng bộ lọc.
8. Tìm kiếm không dấu hoạt động ("bun bo" tìm ra "Bún bò").

# 9. ĐẦU RA
- web/ (index.html, css/, js/, data/, fonts/, vendor/, serve.ps1, config.js), src/export_for_web.py, src/verify_web.py, docs/web_data_contract.md, web/README_web.md (cách mở, cách cập nhật dữ liệu).
- reports/evidence/web_design_plan.md, stage_WEB.md (theo mẫu biên bản trong CONTEXT.md, có phần "Điểm cần hiểu để trả lời phản biện" về cách web đọc dữ liệu và cách gợi ý cold-start hoạt động), web_contrast.md, thư mục reports/figures/screenshots/web_v1/ (ảnh từng trang, hai kích thước).
- Cập nhật README.md và run_all.ps1: bỏ bước Streamlit, thêm bước xuất dữ liệu cho web. KHÔNG xóa thư mục app/ (giữ làm bản lưu và nguồn dữ liệu app/data/) cho đến khi người dùng đồng ý xóa.

# 10. TIÊU CHÍ ĐẠT
- Mọi trang vừa một màn hình ở 1920x1080 và 1366x768, không cuộn; không có biểu tượng, thẻ có bóng, nền chuyển màu, chữ IN HOA; không còn khối "kết luận" hay đoạn giải thích dài.
- Giao diện thể hiện đúng sự thật ở mục 2 (ALS không thắng baseline, cụm ViFoodRec chưa phân biệt rõ, mở rộng quy mô không tuyến tính, nguồn gốc các khoản mất dòng).
- verify_web.py ĐẠT; đối chiếu số liệu không sai lệch; tương phản đạt ngưỡng; chạy offline được.
- Biên bản trung thực: nêu rõ mục nào chưa làm được, không viết "hoàn thành 100%".
````

---

## 3. Cách dùng và điều cần lưu ý

1. **Điểm dừng duyệt:** prompt yêu cầu Gemini dừng sau khung chung và trang 1 để bạn xem ảnh chụp. Đây không phải bản dựng thử riêng, mà là trang thật đầu tiên. Nếu hướng đúng, bạn trả lời "tiếp tục". Nếu chưa ổn, chỉ ra chỗ sai (ví dụ "khoảng cách quá chật", "màu xanh quá đậm") để Gemini chỉnh trước khi làm 4 trang còn lại.
2. **Nếu Gemini lại giữ bố cục cũ:** đây là lỗi lần trước. Gửi cho mình ảnh chụp kết quả, mình sẽ viết prompt sửa cụ thể.
3. **Nếu bạn muốn sửa vấn đề đánh giá 0,5 sao của ViFoodRec:** làm việc đó **trước hoặc sau** phần web đều được, vì web đọc dữ liệu qua `export_for_web.py`. Chạy lại pipeline xong chỉ cần chạy lại bước xuất.
4. **Kết quả ALS thua baseline** không cần sửa. Hãy giữ nguyên và phân tích nguyên nhân trong báo cáo.

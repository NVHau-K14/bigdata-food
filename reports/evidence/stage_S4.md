# Biên bản stage S4: cập nhật dashboard web với dữ liệu mới và sửa lỗi A1 đến D4

Ngày: 14/10/2026. Log nguyên văn: `reports/evidence/logs/S4_*.log`. Ảnh chụp: `reports/figures/screenshots/web_v2/` (28 ảnh ở 1920x1080 và 1366x768; ảnh mô phỏng chia sẻ ở thư mục con `chia_se_960x540/`).

## 1. Đã làm gì

Quyết định của người dùng trước khi sửa: (1) tạo dữ liệu dẫn xuất mới cho món tiêu biểu của cụm người dùng; (2) đổi chữ "Món mặn" thành "Không chay" chỉ trên web, dữ liệu giữ nguyên; (3) trang Mô hình hiện ALS ngầm định (S3b) và bỏ dòng "lưới mở rộng" trùng.

Dữ liệu và xuất dữ liệu:
- [src/export_cluster_top_items.py](../../src/export_cluster_top_items.py) (mới, chỉ đọc): 10 món có điểm từ 4 trở lên nhiều lượt nhất trong tập train theo từng cụm người dùng của Food.com và ViFoodRec, ghi `app/data/cluster_top_items.csv` (70 dòng, 0 dòng thiếu tên món; log `S4_01`). Không sửa `export_for_app.py` (khác kế hoạch ban đầu): script mới ghi thẳng vào `app/data`.
- [src/web_labels.py](../../src/web_labels.py) (mới): bảng nhãn hiển thị duy nhất, dùng chung cho xuất dữ liệu và kiểm thử.
- [src/export_for_web.py](../../src/export_for_web.py) (viết lại): mọi số và chữ hiển thị sinh từ dữ liệu; phiên bản và cấu hình cụm đọc từ `docker-compose.yml`, log fsck S3 và log chạy Spark; thêm `labels.js`, `facts`, `top_items`, `neighbor_stats`; sửa lỗi danh mục Food.com thiếu các món láng giềng (log `S4_02`).

Giao diện: [web/index.html](../../web/index.html), [web/css/style.css](../../web/css/style.css), [web/js/format.js](../../web/js/format.js), [web/js/charts.js](../../web/js/charts.js), [web/js/app.js](../../web/js/app.js) viết lại; cập nhật [docs/web_data_contract.md](../../docs/web_data_contract.md), [web/README_web.md](../../web/README_web.md), [run_all.ps1](../../run_all.ps1).

Kiểm thử (mới): [src/verify_web_ui.mjs](../../src/verify_web_ui.mjs) (Chrome headless qua giao thức CDP, không cài thêm gói), [src/verify_web.py](../../src/verify_web.py) (viết lại), [src/verify_web_style.py](../../src/verify_web_style.py).

Lệnh chạy chính:

```text
docker exec bigdata_spark_env /opt/conda/bin/python src/export_cluster_top_items.py   # S4_01
python src/export_for_web.py                                                          # S4_02
node src/verify_web_ui.mjs                                                            # S4_08 (129 mục)
python src/verify_web.py                                                              # S4_07 (122 mục)
python src/verify_web_style.py                                                        # S4_09 (21 mục)
```

## 2. Kết quả theo từng mục của prompt

| Mục | Nội dung | Kết quả | Bằng chứng |
|---|---|---|---|
| A1 | Panel món của cụm dùng đúng bộ dữ liệu | ĐẠT. Nguyên nhân đã kiểm chứng: `app.js` dùng `representative_foods_vn[id cụm]` (cụm MÓN ViFoodRec) cho mọi bộ dữ liệu. Nay món theo khóa của chính bộ dữ liệu; 20 món Food.com đều có id thuộc danh mục Food.com, tên khớp danh mục, không món nào trùng tên món ViFoodRec | `verify_web.py` nhóm 5; `verify_web_ui.mjs`: không tên món có dấu tiếng Việt ở Food.com |
| A2 | Nhãn cụm của người dùng ViFoodRec | ĐẠT: "Cụm hành vi: Cụm 3" ở trang Gợi ý, "Cụm 1, 2, 3" ở trang Hành vi | `S4_08` (demo), `S4_07` nhóm 4 |
| A3 | Phiên bản và replication | ĐẠT: HDFS 3.3.6, Spark 4.2.0, Replication 2, fsck HEALTHY lấy từ dữ liệu; không còn "Spark 3." trong `web/` | `S4_07` nhóm 2 |
| A4 | Chữ số của P@10 và R@10 | ĐẠT: RMSE, MAE 4 chữ số; P@10, R@10 5 chữ số; ALS dự đoán điểm ViFoodRec hiển thị 0,01386 và 0,00285. Kiểm thử đối chiếu chuỗi hiển thị, không dùng dung sai | `S4_07` nhóm 3 |
| A5 | Ghi chú ViFoodRec sinh từ dữ liệu mới | ĐẠT: phễu 11 mức điểm, loại 47 dòng khóa ngoại, không còn bước loại 0,0 và 0,5; biểu đồ phân phối 11 cột; "Giới hạn dữ liệu" sinh từ số; câu "theo quy chuẩn thiết kế ban đầu" đã xóa | `S4_07` nhóm 1 |
| A6 | Nhãn "Món mặn" | ĐẠT: web hiển thị "Không chay" (và "Món không chay ..." ở tên cụm món); Chú giải giải thích "gồm cả món ngọt và bánh, không có nghĩa là vị mặn". Căn cứ: cột `dish_type` chỉ có "Món mặn" (3.805) và "Món chay" (195), chè bí đỏ và bánh bò bông đều là "Món mặn" | `src/web_labels.py`, `S4_07` nhóm 0 |
| A7 | Bỏ khẳng định chưa kiểm chứng | ĐẠT: tiêu đề trang Mô hình, Hành vi, Gợi ý sinh từ số liệu; không còn "do dữ liệu khảo sát hạn chế", "co cụm dự đoán", "cực mạnh", "cá nhân hóa", "rõ rệt" | `S4_07` nhóm 4 |
| B1 | Bỏ tiếng Anh trong ngoặc | ĐẠT (quét văn bản hiển thị ở 14 trạng thái x 2 kích thước) | `S4_08` |
| B2 | Viết hoa kiểu câu | ĐẠT (xem ảnh chụp) | ảnh `web_v2` |
| B3 | Xóa khối tự nhận xét | ĐẠT: mỗi trang một dòng nguồn; trang Dữ liệu giữ mục "Giới hạn dữ liệu" (A5 yêu cầu sinh lại mục này); giải thích đưa vào Chú giải (18 thuật ngữ, mỗi thuật ngữ một câu). Ngăn Chú giải trước đây không hoạt động vì `index.html` thiếu phần tử; nay hoạt động | `S4_08` (trạng thái glossary) |
| B4 | Phễu làm sạch | ĐẠT: "Loại N dòng", "Đã hội tụ sau N vòng", không còn "Mất -" và dấu ✓ | ảnh `1366x768_du-lieu.png` |
| C1 | Màu biểu đồ | ĐẠT: xanh lá đậm (xám 63/255) và xám trung tính (xám 136/255); cam chiếm tối đa 0,459% diện tích một ảnh. Chữ cam nhỏ đo được 4,26:1 trên nền trắng (bảng thiết kế cũ ghi 4,88:1, không đúng), nên đã đổi cam thành `#B24E10` (5,26:1 trên nền trắng, 4,89:1 trên nền phụ) | `S4_09` |
| C2 | Dấu phẩy và một hàm định dạng | ĐẠT: mọi số qua `FormatUtils.fmt`; không còn `toFixed` ngoài `format.js`; không có mẫu chữ số-chấm-chữ số trong văn bản hiển thị; biểu đồ phân rã RMSE có tiêu đề trục y "RMSE" | `S4_07` nhóm 6; `S4_08` |
| C3 | Cột "Rank" | ĐẠT: đổi thành "Số nhân tố ẩn" | ảnh trang Mô hình |
| D1 | Trang Dữ liệu: nhãn trục | ĐẠT: biểu đồ ViFoodRec 11 cột, nhãn "0,0" đến "5,0" đọc được ở hai kích thước | ảnh `1366x768_du-lieu.png` |
| D2 | Trang Hệ thống: khối kiến trúc, panel trống | ĐẠT: khối co theo nội dung (phóng theo chiều cao khung), panel trống tối đa 24,0% ở 1920x1080 và 17,2% ở 1366x768 (cả hai tab); tab lưu trữ có biểu đồ tỷ lệ nén | `S4_08` (mục "mỗi panel trống không quá 25%") |
| D3 | Trang Hành vi: tiêu đề một dòng | ĐẠT: tiêu đề tối đa một dòng ở 1366x768 (và không quá 90 ký tự ở mọi trang); nhãn bộ chọn "Food.com", "ViFoodRec: người dùng", "ViFoodRec: món" | `S4_08` |
| D4 | Trang Gợi ý: danh sách món | ĐẠT một phần: 10 món vừa khung, không cuộn trong ở 1920x1080 (cả chế độ người dùng có sẵn và người dùng mới); dòng nguyên liệu một dòng, bấm để mở. Ở 1366x768 chế độ người dùng mới có cuộn trong danh sách (được chấp nhận theo prompt) | `S4_08` |
| E1 | `verify_web.py` đối chiếu ít nhất 40 số | ĐẠT: 122 mục (phần lớn là số hiển thị đối chiếu với tệp nguồn), thoát mã 0; kiểm thử thử nghiệm đột biến: sửa 2 chuỗi trong tệp văn bản thì 4 mục báo không đạt và thoát mã 1 | `S4_07`, `S4_10` |
| E2 | Không cuộn trang ở 1920x1080 và 1366x768 | ĐẠT: 14 trạng thái x 2 kích thước (5 trang, hai bộ dữ liệu, hai chế độ gợi ý, các tab, ngăn Chú giải, hộp chọn số cụm) | `S4_08` |
| E3 | Quét mã và văn bản | ĐẠT: không emoji, không ký tự biểu tượng, không `text-transform` khác none, không gradient, không box-shadow, không animation tự chạy | `S4_09` nhóm 1 |
| E4 | Tương phản và thang xám | ĐẠT: chữ chính 16,40:1, chữ phụ 10,43:1, chữ xanh lá 9,00:1, cột biểu đồ 9,00:1 và 3,52:1 | `S4_09` nhóm 2, 3 |
| E5 | Ảnh chụp và mô phỏng chia sẻ | ĐẠT một phần: ảnh chụp đủ 2 kích thước; ảnh 960x540 JPEG 60% đã tạo (trung bình 41 KB). Chữ nhỏ không đọc được ở kích thước này (mục 3) | `S4_09` nhóm 5 |
| E6 | Luồng demo | ĐẠT: người dùng ViFoodRec 70 xem đủ 10 món khác nhau; người dùng mới với 3 bộ món cho 3 danh sách khác nhau; từng bộ lọc (loại món, thời gian, calo, số món, xóa bộ lọc) đúng; tìm không dấu "bun bo" ra "Bún bò giò heo" | `S4_08` |

## 3. Hạn chế và việc chưa làm được

- **Mô phỏng chia sẻ online (E5).** Sau khi thu nhỏ còn 960x540, chỉ khoảng 6% đến 36% số ký tự trên mỗi trang còn cỡ chữ từ 9 px trở lên (tiêu đề, tên mục, số trong bảng ở mức vừa; dòng nguyên liệu, nhãn trục thì không đọc được). Ảnh vẫn đọc được ở cấp tiêu đề và hình dạng biểu đồ, nhưng không đọc được chi tiết. Khuyến nghị: chia sẻ ảnh gốc 1920x1080 hoặc ảnh cắt từng panel.
- **Độ tương đồng món ViFoodRec (phát hiện mới, chưa sửa).** Cả 40.000 điểm cosine trong `item_neighbors_food_vietnam` đều là 1,0 (nhỏ nhất 1,0), nên ở chế độ người dùng mới của ViFoodRec thứ tự gợi ý không phản ánh khác biệt giữa các món; web hiện cảnh báo dựa trên `neighbor_stats`. Ở Food.com (toàn bộ 20.000 món có láng giềng) điểm nằm từ 0,838 đến 1,0 (trung vị 0,9973), 22,8% từ 0,999 trở lên. Nguyên nhân (regParam 0,5 ở biên lưới của ALS ViFoodRec làm vector món gần song song) là giả thuyết chưa kiểm chứng. Sửa tận gốc cần chạy lại ALS ViFoodRec (ngoài phạm vi S4).
- **Đơn vị nguyên liệu dính chữ (D4).** Lỗi nằm trong dữ liệu gốc `data/raw/food_vietnam/foods.csv` (log `S4_11`): 2.568 trong 4.000 món có "muỗng" dính liền chữ khác ("muỗngl" 1.734 lần, "muỗngu" 7.084 lần, "muỗngi" 348 lần). Chỉ báo cáo, không sửa dữ liệu.
- **Món tiêu biểu của cụm người dùng ViFoodRec.** Số lượt giữa các món rất sát nhau (10 đến 11 lượt cho món đứng đầu mỗi cụm), nên danh sách này chỉ mang tính minh họa.
- **Trình duyệt đã kiểm thử:** Chrome headless trên Windows. Chưa chạy Edge, Firefox, Safari.
- **Cuộn trong ở 1366x768:** danh sách gợi ý chế độ người dùng mới có cuộn trong (được chấp nhận theo prompt); các panel khác không cuộn.
- **Thay đổi so với bản duyệt cũ:** bảng mô hình bỏ cột "Độ phủ" (mọi mô hình có điểm là 100%, ALS ngầm định không áp dụng) và nhãn "Mô hình đề xuất"; phễu dùng thang riêng cho từng nhánh (so với số dòng thô của chính bộ); trang Hành vi có thêm bộ chọn "ViFoodRec: món".
- `reports/evidence/eda_insights.md`, các biên bản P3, P5, P7, P8, P11 và `docs/Q_and_A.md` chưa đính chính; làm ở S5.

## 4. Điểm cần hiểu để trả lời phản biện

1. **Vì sao trước đây Food.com hiện món Việt ở trang Hành vi?** Web lấy danh sách món của cụm MÓN ViFoodRec theo id cụm (0 đến 3) và dùng cho mọi bộ dữ liệu; id cụm người dùng Food.com cũng là 0 đến 3 nên bị nối nhầm. Nay danh sách món của từng cụm người dùng được tính từ tập train (điểm từ 4 trở lên) và khóa theo bộ dữ liệu.
2. **"Không chay" khác "mặn" ở chỗ nào?** Dữ liệu gốc chỉ có hai giá trị; nhãn "Món mặn" cũng gắn cho chè và bánh. Web hiển thị "Không chay" để không bị hiểu là vị mặn; dữ liệu gốc không đổi.
3. **Vì sao tiêu đề trang Mô hình đổi?** Tiêu đề sinh từ model_comparison.csv: ở ViFoodRec không mô hình ALS nào đứng đầu độ đo nào; ở Food.com ALS ngầm định đứng đầu P@10 (0,00570 so với 0,00534 của Top món phổ biến) nhưng R@10, RMSE và MAE thuộc mô hình cơ sở.
4. **Gợi ý cho người dùng mới ở ViFoodRec có đáng tin không?** Chưa: mọi điểm tương đồng đều bằng 1,0, nên thứ tự món là ngẫu nhiên theo thứ tự lưu trữ. Web cảnh báo điều này; cách sửa là chạy lại ALS ViFoodRec.
5. **Làm sao biết số trên web đúng?** `verify_web.py` đối chiếu chuỗi thực sự hiển thị (do Chrome đọc) với số tính lại từ tệp nguồn theo đúng số chữ số; kiểm thử đột biến cho thấy sửa một chữ số trên trang làm kiểm thử báo lỗi và thoát mã 1.

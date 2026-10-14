# BỐI CẢNH DỰ ÁN VÀ QUY TẮC LÀM VIỆC (BẮT BUỘC ĐỌC TRƯỚC MỖI TÁC VỤ)

## 1. Dự án
Đồ án cuối môn "Nhập môn Big Data" của nhóm 2 sinh viên. Đề tài: "Phân tích hành vi ăn uống và gợi ý món ăn".
Nhóm xử lý hai bộ dữ liệu bằng CÙNG MỘT pipeline Spark, KHÔNG gộp dữ liệu vì không có người dùng chung:
- Food.com (Kaggle: RAW_interactions.csv, RAW_recipes.csv): quy mô lớn, dùng để chứng minh khả năng mở rộng và phân tích hành vi theo thời gian.
- ViFoodRec (món Việt Nam: foods.csv, ratings.csv): dùng cho ứng dụng gợi ý món Việt. Lưu ý: chỉ khoảng 100 người dùng, đánh giá do khảo sát, tác giả đã điền một phần giá trị thiếu bằng trung vị, và foods.csv thực tế có 4.000 món.
Mục tiêu kỹ thuật: baseline -> K-means (phân tích hành vi) -> ALS (gợi ý, Spark MLlib, explicit feedback) -> thực nghiệm mở rộng -> dashboard Streamlit.

## 2. Môi trường
- Máy Windows (PowerShell), Docker Desktop, 24GB RAM (cấp cho Docker khoảng 16GB).
- Dữ liệu thô nằm ở data/raw/ (CHỈ ĐỌC, tuyệt đối không sửa hay xóa).
- Thư mục: data/raw, data/processed, src/, notebooks/, app/, reports/, docs/, results/.
- Mọi đường dẫn đọc và ghi dữ liệu phải đi qua src/config.py. Có hai chế độ: STORAGE_MODE=hdfs (đường dẫn hdfs://...) và STORAGE_MODE=local (đường dẫn thư mục). Cùng một mã nguồn phải chạy được ở cả hai chế độ.

## 3. Quy tắc trung thực (QUAN TRỌNG NHẤT)
1. Mọi con số đưa vào báo cáo hoặc biên bản PHẢI đến từ kết quả lệnh thật mà bạn đã chạy. Lưu nguyên văn kết quả lệnh vào reports/evidence/.
2. Nếu chưa chạy hoặc chưa kiểm chứng, ghi rõ "CHƯA CHẠY" hoặc "CHƯA KIỂM CHỨNG". Cấm viết "hoàn thành 100%" khi chưa có bằng chứng.
3. Cấm bịa số liệu, cấm điền số liệu so sánh với bài báo nếu không đọc được nguồn. Để trống và nói rõ.
4. Nếu số liệu bất thường (ví dụ mất hơn 10% dòng ngoài dự kiến, mô hình tệ hơn baseline, kết quả quá hoàn hảo), DỪNG LẠI, mô tả bất thường và đưa ra các cách xử lý để người dùng quyết định. Không tự ý chỉnh cho đẹp.
5. Không dùng dữ liệu kiểm tra (test) để chọn tham số. Chỉ dùng tập validation.

## 4. Quy tắc viết mã
- Python 3, PySpark DataFrame API. Mỗi file có docstring đầu file giải thích mục đích và các bước chính bằng tiếng Việt.
- Chú thích giải thích TẠI SAO làm vậy (không chỉ làm gì). Tên biến, hàm bằng tiếng Anh.
- Tham số (k-core, seed, ngưỡng, siêu tham số) đặt trong src/config.py hoặc config.yaml, không hard-code rải rác. Seed ngẫu nhiên cố định = 42.
- Không over-engineering: ưu tiên chạy đúng và dễ giải thích. Hai sinh viên phải hiểu và giải thích được từng đoạn mã.
- Không cài thêm thư viện nặng không cần thiết. Mọi thư viện phải ghi vào requirements.txt với phiên bản cụ thể.
- Ghi log ra màn hình và vào file reports/evidence/ khi chạy pipeline.

## 5. Biên bản sau mỗi giai đoạn
Sau mỗi tác vụ, tạo reports/evidence/stage_<mã>.md gồm:
1. Đã làm gì (danh sách file tạo hoặc sửa).
2. Các lệnh đã chạy (nguyên văn) và kết quả thật (trích nguyên văn).
3. Kết quả đối chiếu với "Tiêu chí đạt" của tác vụ: ĐẠT hoặc KHÔNG ĐẠT từng mục.
4. Vấn đề còn tồn và giả định đã dùng.
5. "Điểm cần hiểu để trả lời phản biện": 3 đến 5 câu hỏi giảng viên có thể hỏi về phần này kèm câu trả lời ngắn dựa trên kết quả thật.

## 6. Điều cấm
- Cấm sửa data/raw. Cấm xóa file ngoài phạm vi tác vụ. Cấm commit dữ liệu nặng.
- Cấm viết báo cáo Word, slide (chưa làm giai đoạn này).
- Cấm thay đổi quyết định đã chốt (hai bộ dữ liệu, K-core=3, ALS, K-means, Streamlit) khi chưa hỏi người dùng.

## 7. Cập nhật ngày 14/10/2026 (người dùng đã xác nhận)
1. ViFoodRec: giữ toàn bộ thang điểm 0,0 đến 5,0 (11 mức, bước 0,5). Chỉ loại NULL, trùng cặp (user, món) và dòng có food_id không có trong danh mục món. Lý do: 0,0 và 0,5 có số dòng ngang các mức khác, không có bằng chứng đó là "chưa chấm".
2. ALS không tốt hơn baseline trên cả hai bộ: đã biết và được chấp nhận, báo cáo trung thực. Quy tắc §3.4 không buộc dừng vì lý do này nữa. Vẫn dừng nếu kết quả tốt bất thường hoặc có rò rỉ dữ liệu.
3. Dashboard chính là web/ (HTML/CSS/JS tĩnh). app/ (Streamlit) giữ làm bản lưu và nguồn dữ liệu, không xóa.
4. Cụm người dùng ViFoodRec: nếu chênh lệch tương đối giữa các cụm ở mọi đặc trưng nhỏ hơn 10% thì gọi "Cụm 1, 2, 3", không đặt tên diễn giải.
5. Mọi lệnh chạy thật phải ghi log nguyên văn vào reports/evidence/logs/ (dùng Tee-Object hoặc tee). Biên bản chỉ trích từ log.
6. Chỉ viết nguyên nhân của một kết quả khi đã kiểm chứng. Nếu chưa, ghi "giả thuyết chưa kiểm chứng".
7. Không xóa hay ghi đè file ngoài phạm vi stage. Sao lưu trước khi ghi đè kết quả. Không đụng data/raw.
8. Trình bày: tiếng Việt viết hoa kiểu câu, không icon, không chú thích tiếng Anh trong ngoặc.
9. Điều kiện dừng và hỏi người dùng: mất hơn 10% dòng ngoài dự kiến; rò rỉ train/test khác 0; kết quả mô hình tốt bất thường; lỗi hạ tầng quá 1 giờ chưa xử lý được; cần xóa dữ liệu không khôi phục được.

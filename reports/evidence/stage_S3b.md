# Biên bản stage S3b: thử cải thiện mô hình

Ngày: 14/10/2026. Log nguyên văn: `reports/evidence/logs/S3b_*.log`. Nhật ký tinh chỉnh: `results/als_improve_s3b.csv`; tham số tốt nhất: `results/als_improve_s3b_best.json`.

## 1. Đã làm gì

- Viết [src/als_improve.py](../../src/als_improve.py) (mới), chạy một lần: `docker exec bigdata_spark_env /opt/conda/bin/python src/als_improve.py` (log `S3b_02`, khoảng 30 phút).
- Sao lưu trước khi ghi: `backup_v4_truoc_S3b/` (`results`, `app/data`, `model_comparison.csv`), nằm trong `.gitignore`.
- Thêm dòng mới vào `results/model_comparison.csv` (bản sao ở `data/results/`, `reports/evidence/`), không xóa dòng cũ. File có 11 dòng (8 dòng cũ và 3 dòng mới).
- Làm mới `app/data` bằng `export_for_app.py`; `verify_export.py` đạt 66/66 (log `S3b_03`, `S3b_04`). Các ô RMSE, MAE, coverage của mô hình ngầm định để trống; `web/data` chưa làm mới, để S4 (mã web cần chịu được ô trống).
- Không ghi đè mô hình hay kết quả của S3 ở HDFS: các mô hình mới không được lưu.

Các bộ tách train, validation, test giữ nguyên của S3 (Food.com từ trước, ViFoodRec từ S3). Tham số chọn chỉ bằng validation, test đo một lần.

## 2. Phần 1: Food.com, lưới regParam mở rộng (log `S3b_02`)

Thêm regParam 0,3 và 0,5 cho mọi cặp (rank, maxIter) của lưới cũ (10 và 10; 20 và 10; 20 và 15; 50 và 10), tức 8 cấu hình mới. Validation RMSE:

| rank | maxIter | regParam 0,2 (cũ) | regParam 0,3 | regParam 0,5 |
|---:|---:|---:|---:|---:|
| 10 | 10 | 0,6754 | 0,7004 | 0,7958 |
| 20 | 10 | không có trong lưới cũ | 0,7010 | 0,7961 |
| 20 | 15 | không có trong lưới cũ | 0,6991 | 0,7945 |
| 50 | 10 | không có trong lưới cũ | 0,7007 | 0,7961 |

- Cả 8 cấu hình mới đều có Validation RMSE cao hơn 0,6754. Tham số tốt nhất vẫn là rank 10, regParam 0,2, maxIter 10, nên giá trị 0,2 không còn là biên bị cắt: RMSE tăng khi regParam lên 0,3 và 0,5.
- Điểm không đối xứng: lưới cũ chỉ thử regParam 0,2 với rank 10, nên các cặp rank 20 và 50 chưa có giá trị 0,2 để so với 0,3. Chưa thử regParam trong khoảng giữa 0,2 và 0,3.
- Mô hình được huấn luyện lại với cùng tham số và đo test: RMSE 0,6747, MAE 0,5094, P@10 0,00017, R@10 0,00096, giống hệt dòng ALS cũ. Cũng là kiểm tra rằng quy trình đánh giá trong script này trùng với `train_als.py`.
- Dòng mới "ALS Matrix Factorization (lưới mở rộng)" vì vậy trùng số với dòng ALS cũ của Food.com. Kết luận: mở rộng lưới không cải thiện.

## 3. Phần 2: ALS ngầm định (log `S3b_02`)

Cách làm: chỉ dùng dòng train có điểm >= 4,0 làm phản hồi tích cực (giá trị 1,0). Lưới: rank 10, 20, 50; regParam 0,01, 0,1; alpha 1, 10, 40; maxIter 10 (18 cấu hình mỗi bộ). Chọn bằng Precision@10 trên validation (món phù hợp trong validation là điểm >= 4,0, loại món đã có trong train). Test: Precision@10 và Recall@10 bằng `src/evaluation.py`.

Số món ứng viên lấy từ mô hình trước khi loại món đã xem (`fetch_k`): Food.com 300, ViFoodRec 4.000 (mỗi người đã xem hơn 1.400 trong 4.000 món). Kiểm tra: 0,00% người dùng có dưới 10 món sau khi loại món đã xem, ở cả hai bộ.

Số dòng tích cực: Food.com 537.845 trong 565.420 dòng train; ViFoodRec 39.988 trong 146.012 dòng train.

| Bộ | Tham số tốt nhất theo validation | Validation P@10 |
|---|---|---:|
| ViFoodRec | rank 20, regParam 0,01, alpha 1, maxIter 10 | 0,02277 |
| Food.com | rank 10, regParam 0,01, alpha 10, maxIter 10 | 0,00604 |

Kết quả test (xếp hạng; RMSE và MAE không áp dụng vì mô hình ngầm định không dự đoán điểm):

| Bộ | Mô hình | P@10 | R@10 | Người dùng đánh giá |
|---|---|---:|---:|---:|
| Food.com | Top món phổ biến | 0,00534 | 0,02170 | |
| Food.com | ALS dự đoán điểm | 0,00017 | 0,00096 | |
| Food.com | ALS ngầm định | 0,00570 | 0,02118 | 15.902 |
| ViFoodRec | Top món phổ biến | 0,02277 | 0,00461 | |
| ViFoodRec | ALS dự đoán điểm | 0,01386 | 0,00285 | |
| ViFoodRec | ALS ngầm định | 0,01980 | 0,00428 | 101 |

Nhận xét có số:

- So với ALS dự đoán điểm, ALS ngầm định tốt hơn rõ về xếp hạng: Food.com P@10 từ 0,00017 lên 0,00570, R@10 từ 0,00096 lên 0,02118; ViFoodRec P@10 từ 0,01386 lên 0,01980, R@10 từ 0,00285 lên 0,00428.
- Food.com: P@10 của ALS ngầm định (0,00570) cao hơn Top món phổ biến (0,00534) khoảng 0,00036, còn R@10 thấp hơn (0,02118 so với 0,02170). Chênh lệch nhỏ theo cả hai chiều; chưa kiểm định ý nghĩa thống kê, nên chỉ kết luận là xấp xỉ ngang nhau, không phải vượt trội.
- ViFoodRec: ALS ngầm định vẫn thua Top món phổ biến (P@10 0,01980 so với 0,02277; R@10 0,00428 so với 0,00461). Ghi trung thực: vẫn thua.
- Với ViFoodRec, mẫu rất nhỏ: chỉ 101 người dùng, nên mỗi 0,00099 chênh P@10 tương ứng 1 lượt trúng trên 1.010 gợi ý (nếu đủ 101 người dùng có món phù hợp ở validation; chưa đếm số người dùng này). Điểm chọn tham số trên validation dao động theo mức đó (ví dụ rank 20, regParam 0,01, alpha 1 có 0,02277, cao nhất, nhưng nhiều cấu hình khác nằm trong khoảng 0,0178 đến 0,0218), nên tham số tốt nhất ở bộ này không đáng tin.
- Chưa tìm hiểu vì sao ALS dự đoán điểm xếp hạng rất kém trên Food.com (P@10 0,00017); đây là số đo, nguyên nhân là giả thuyết chưa kiểm chứng. Về mục tiêu huấn luyện: ALS dự đoán điểm giảm sai số điểm, còn ALS ngầm định học xếp hạng; đây là khác biệt thiết kế, chưa đủ để kết luận nguyên nhân.

## 4. Tiêu chí đạt

| Mục | Kết quả |
|---|---|
| Mở rộng lưới regParam Food.com thêm 0,3 và 0,5 | ĐẠT, không cải thiện (tham số tốt nhất vẫn là 0,2) |
| ALS ngầm định, đánh giá P@10 và R@10 theo `src/evaluation.py` | ĐẠT (cả hai bộ) |
| Chọn tham số bằng validation, đo test một lần | ĐẠT |
| Ghi thành dòng mới trong `model_comparison.csv`, không xóa dòng cũ | ĐẠT (8 dòng cũ giữ nguyên, thêm 3 dòng) |
| Nếu vẫn thua Top món phổ biến, ghi trung thực | ĐẠT (ViFoodRec thua; Food.com xấp xỉ ngang) |

## 5. Còn tồn và giả định

- Dòng "ALS Matrix Factorization (lưới mở rộng)" trùng hoàn toàn dòng ALS cũ của Food.com; có thể bỏ khỏi bảng hiển thị ở web.
- Mô hình ngầm định chỉ đánh giá xếp hạng, nên ở các bảng dùng RMSE hoặc MAE cần chịu được ô trống (kiểm tra ở S4).
- Lưới ALS ngầm định ViFoodRec và regParam của ViFoodRec (tốt nhất 0,5 ở biên lưới, ghi ở S3) chưa được mở rộng thêm; ngoài phạm vi prompt.
- Mô hình ngầm định chưa được lưu lên HDFS và không có file gợi ý Top 10 cho web; nếu muốn dùng làm mô hình hiển thị ở web thì cần thêm bước xuất (chưa làm).

## 6. Điểm cần hiểu để trả lời phản biện

1. **Vì sao thêm regParam 0,3 và 0,5 mà kết quả không đổi?** Vì Validation RMSE tăng khi regParam vượt 0,2 (0,7004 ở 0,3; 0,7958 ở 0,5), nên 0,2 là tối ưu trong các giá trị đã thử, không phải biên bị cắt.
2. **ALS ngầm định khác ALS dự đoán điểm ở đâu?** Nó coi điểm >= 4 là tín hiệu "thích" và học xếp hạng, không dự đoán điểm; vì vậy không có RMSE.
3. **Vì sao RMSE và MAE để trống?** Mô hình ngầm định tạo độ ưu tiên, không phải điểm trên thang 1 đến 5 hay 0 đến 5.
4. **Mô hình ngầm định có thắng Top món phổ biến không?** Food.com: P@10 cao hơn một chút (0,00570 so với 0,00534), R@10 thấp hơn một chút (0,02118 so với 0,02170); ViFoodRec: thua (0,01980 so với 0,02277).
5. **Vì sao `fetch_k` lớn?** Mô hình ngầm định hay gợi ý lại món đã xem; ViFoodRec mỗi người đã xem hơn 1.400 trong 4.000 món nên phải lấy toàn bộ 4.000 món ứng viên, rồi mới loại món đã xem. Kiểm tra: 0% người dùng thiếu món.

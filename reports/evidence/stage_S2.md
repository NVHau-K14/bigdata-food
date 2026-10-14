# Biên bản stage S2: ViFoodRec làm sạch lại và kiểm tra nguồn gốc dữ liệu

Ngày: 14/10/2026. Log nguyên văn nằm trong `reports/evidence/logs/S2_*.log`.

## 1. Đã làm gì

- Đối chiếu bài báo (`scratch/paclic_paper_text.txt`) với `data/raw/food_vietnam/ratings.csv` và `foods.csv` (log `S2_01`; script `scratch/s2_profile_raw_vifoodrec.py`).
- Sao lưu kết quả cũ vào `backup_v2_truoc_S2/` (log `S2_02`): `data/results`, `results`, `app/data`, `web/data`, `cleaning_log.csv`, `data_profile_vifoodrec.md`, và hai thư mục HDFS bị ghi đè (`/data/clean/food_vietnam`, `/data/results/cleaning_log.parquet`). Thư mục này nằm trong `.gitignore` (mẫu `backup_*/`).
- Sửa [src/config.py](../../src/config.py): thêm `RATING_MIN_VN = 0.0`, `RATING_MAX_VN = 5.0`, `RATING_STEP_VN = 0.5`.
- Sửa [src/clean_vietnam.py](../../src/clean_vietnam.py): bước lọc điểm giữ 11 mức 0,0 đến 5,0 (đổi tên bước thành `filter_rating_scale_0_to_5_step_half`); chuỗi nhật ký khóa ngoại và K-core lấy số từ dữ liệu, không viết cứng ("100 user và 4000 món" đổi thành "còn 101 user và 4,000 món").
- Sửa [src/run_pipeline_p3.py](../../src/run_pipeline_p3.py): thêm tham số `--only vietnam` để chỉ chạy lại ViFoodRec. Lý do: ghi lại Parquet Food.com sẽ đổi thứ tự dòng và có thể làm đổi cách chia train/validation/test theo seed ở S3, trong khi Food.com đã được kiểm chứng. Các dòng Food.com trong `cleaning_log.csv` được giữ nguyên từ bản cũ.
- Sửa [src/verify_clean.py](../../src/verify_clean.py): kiểm tra rating ViFoodRec thuộc đúng danh sách 11 mức (so khớp từng giá trị, không dùng khoảng), in các mức có trong dữ liệu.
- Chạy lại làm sạch ViFoodRec và `verify_clean.py` (log `S2_03`, `S2_04`); tính thống kê dữ liệu sạch (log `S2_05`; script `scratch/s2_stats_clean.py`).
- Viết lại mục 1 đến 3 của [data_profile_vifoodrec.md](data_profile_vifoodrec.md), bỏ câu kết luận "dữ liệu sinh nhân tạo" (chưa kiểm chứng). Thêm mục 5 vào [docs/data_contract.md](../../docs/data_contract.md).

## 2. Bước 1: bài báo nói và file thật

Chỉ ghi sự kiện. Cột "Nguồn" là dòng trong `scratch/paclic_paper_text.txt` hoặc log.

| Hạng mục | Bài báo nói | File thật | Khớp? |
|---|---|---|---|
| Thang điểm | 0,0 (rất không thích) đến 5,0, bước 0,5 (dòng 272 đến 275) | 11 mức 0,0; 0,5; ...; 5,0, không có giá trị lệch bước (log `S2_01`) | Khớp |
| Số người dùng | "tối đa 100" (dòng 267) | 101 (`userId` 0 đến 100) | Lệch 1 |
| Số món trong danh mục | bảng foods "5509 món" (dòng 247), tóm tắt "hơn 5000" (dòng 32); nhóm ratings dùng "4.000 món" (dòng 270) | `foods.csv` có 4.000 dòng, `food_id` 0 đến 3999 | Không khớp với 5509; khớp với 4.000 |
| Số đánh giá | bản đầu khoảng 50.000 (dòng 271); sau điền giá trị thiếu khoảng 180.000 (dòng 335) | 182.678 dòng | Khớp con số khoảng 180.000 |
| Số đánh giá mỗi người | bản đầu 436 đến 566 (dòng 277); sau xử lý "1641 đến 1989" (dòng 336) | nhỏ nhất 1.641, lớn nhất 1.989, trung vị 1.795, trung bình 1.808,7 | Khớp với số sau xử lý; không khớp "khoảng 500" |
| Số đánh giá mỗi món | bản đầu 2 đến 26 (dòng 276); sau xử lý "27 đến 68" (dòng 337) | nhỏ nhất 27, lớn nhất 68, trung vị 46 | Khớp với số sau xử lý |
| Số cặp (người dùng, món) trùng | có, giữ bản mới nhất (dòng 323 đến 326) | 0 cặp trùng (182.678 cặp phân biệt trên 182.678 dòng) | File đã khử trùng |
| Giá trị thiếu | điền 40% chỗ thiếu bằng trung vị (dòng 329 đến 331) | 0 dòng NULL | Không đối chiếu được |
| Phân phối 11 mức điểm | biểu đồ "trước và sau khi điền" (hình 4, không có số) | mỗi mức 16.420 đến 16.859 dòng (8,99% đến 9,23%): 0,0: 16.509; 0,5: 16.702; 1,0: 16.420; 1,5: 16.859; 2,0: 16.601; 2,5: 16.660; 3,0: 16.569; 3,5: 16.620; 4,0: 16.618; 4,5: 16.518; 5,0: 16.602 | Không có số trong bài để đối chiếu |
| `food_id` ngoài danh mục | không nêu | 47 dòng có `food_id` = 4000 (danh mục chỉ đến 3999) | Không nêu trong bài |
| Số dòng thô | không nêu số chính xác | 182.678 | |

Các chỗ chưa giải thích được (không suy đoán nguyên nhân):

1. Bài báo nói điền 40% chỗ thiếu bằng trung vị, nhưng trong file không có mức điểm nào chiếm nhiều bất thường: mức cao nhất 9,23% (1,5), thấp nhất 8,99% (1,0). Chưa rõ cách điền cụ thể, nên chưa kết nối được lời mô tả trong bài với phân phối đo được.
2. Số món: bài báo nêu 5509 (và "hơn 5000"), file chỉ có 4.000.
3. Số người dùng: 101 so với "tối đa 100".
4. Từ khoảng 50.000 đánh giá (bản đầu) lên 182.678 dòng (file), bài báo không nêu số dòng được thêm mỗi bước.
5. Trước đây `STATUS.md` ghi "trung vị 1.469 đánh giá mỗi người". Số đó đo trên dữ liệu đã loại 0,0 và 0,5 (149.431 dòng). Trên file thô, trung vị là 1.795 (log `S2_01`).

Thống kê phân phối so với phân phối đều: độ lệch chuẩn đo được 1,5798 (dữ liệu thô, log `S2_01`), độ lệch chuẩn lý thuyết của phân phối đều trên 11 mức bước 0,5 là 1,5811. Đây là phép đo, không phải kết luận về nguồn gốc dữ liệu.

## 3. Bảng số dòng trước và sau từng khâu (ViFoodRec ratings)

Nguồn: `reports/evidence/cleaning_log.csv` (bản mới), `backup_v2_truoc_S2/reports_evidence/cleaning_log.csv` (bản cũ).

| Khâu | Cũ (loại 0,0 và 0,5): còn lại | Cũ: loại | Mới (giữ 11 mức): còn lại | Mới: loại |
|---|---:|---:|---:|---:|
| Đọc thô | 182.678 | 0 | 182.678 | 0 |
| Bỏ NULL | 182.678 | 0 | 182.678 | 0 |
| Lọc thang điểm | 149.467 | 33.211 | 182.678 | 0 |
| Khử trùng cặp (người dùng, món) | 149.467 | 0 | 182.678 | 0 |
| Khóa ngoại tới danh mục món | 149.431 | 36 | 182.631 | 47 |
| K-core lặp, K = 3 (1 vòng) | 149.431 | 0 | 182.631 | 0 |

- Tỷ lệ giữ lại: 182.631 / 182.678 = 99,97% (bản cũ 81,80%). Mất 47 dòng, rất thấp so với ngưỡng dừng 10% ở CONTEXT mục 7.9.
- Ước tính trong prompt là "khoảng 182.642 nếu chỉ mất 36 dòng". Số đo là 182.631 vì có 47 dòng `food_id` = 4000 trong dữ liệu thô; 36 là số còn lại sau khi đã bỏ 0,0 và 0,5 (11 dòng `food_id` = 4000 mang điểm 0,0 hoặc 0,5, phân bố theo mức điểm ở log `S2_01`). Ước tính cũ chưa đo, số này thay thế.
- Sau làm sạch: 101 người dùng, 4.000 món, độ thưa 54,7943% (bản cũ 63,0121%), điểm trung bình 2,4996 (log `S2_05`).
- Food.com không chạy lại; `/data/clean/food_com/...` giữ nguyên dấu thời gian ghi 13/10/2026 (log `S2_04`).

## 4. Kết quả `verify_clean.py` (log `S2_04`, mã thoát 0)

```text
1. No NULL in primary keys & ratings             : ĐẠT [PASS]
   Chi tiết: fc_inter=0, fc_rec=0, vn_rat=0, vn_food=0
2. Rating scale (Food.com 1-5, ViFoodRec 11 levels) : ĐẠT [PASS]
   Chi tiết: fc_out=0, vn_out=0, vn_distinct_levels=11
3. No duplicate (user, item) pairs               : ĐẠT [PASS]
   Chi tiết: fc_inter(706514==706514), vn_rat(182631==182631)
4. K-core convergence (min interactions >= 3)    : ĐẠT [PASS]
   Chi tiết: Food.com: min_u=3, min_r=3 | ViFoodRec: min_u=1641, min_f=27
5. Foreign Key Integrity (0 orphan records)      : ĐẠT [PASS]
   Chi tiết: fc_orphan=0, vn_orphan=0
6. Row count consistency with cleaning_log.csv   : ĐẠT [PASS]
   Chi tiết: Raw matched=True, Final matched=True
ALL VERIFICATION CHECKS PASSED SUCCESSFULLY!
```

Hạ tầng: file Parquet mới ghi có replication 2 (`hdfs dfs -stat "%r"`), `hdfs fsck /data/clean` báo `HEALTHY`, `Under-replicated blocks: 0`.

## 5. Tiêu chí đạt

| Mục | Kết quả |
|---|---|
| `verify_clean.py` đạt toàn bộ | ĐẠT (6/6) |
| Số dòng ViFoodRec sạch lớn hơn 149.431 | ĐẠT (182.631) |
| Bảng "bài báo nói và file thật" không có kết luận bịa | ĐẠT (chỗ chưa giải thích được ghi rõ ở mục 2) |
| Sao lưu trước khi ghi đè | ĐẠT (`backup_v2_truoc_S2/`, 141 file) |
| Chuỗi "100 user" trong nhật ký sửa thành số sinh từ mã | ĐẠT (`còn 101 user và 4,000 món`) |

## 6. Còn tồn và ảnh hưởng đến stage sau

- Mọi kết quả phụ thuộc ViFoodRec đang cũ cho đến khi chạy S3: `/data/splits/food_vietnam`, `/models/food_vietnam`, `results/*vietnam*`, `results/model_comparison.csv`, `app/data`, `web/data`. Thư mục sao lưu giữ bản cũ.
- Tên bước lọc điểm đổi, nên hai nơi còn dùng tên cũ `filter_rating_range_1_to_5` cho ViFoodRec: [src/verify_web.py](../../src/verify_web.py) (dòng 89 và 90) và `app/pages/1_Tong_quan.py` (dòng 171, thuộc bản lưu Streamlit). `verify_web.py` sẽ lỗi nếu chạy trước khi S4 xuất lại dữ liệu web; tôi không sửa ở S2 vì ngoài phạm vi.
- Các biên bản P3, P5, P7, P11 còn câu "sinh điểm nhân tạo" hoặc "loại 0,0 và 0,5"; sẽ thêm khối đính chính ở S5.
- `docs/data_contract.md` mục 2 và mục 3 vẫn mô tả các file `app/data` ở trạng thái cũ (ví dụ "3 cụm hành vi" có tên diễn giải); sẽ cập nhật sau khi S3 và S4 tạo lại các file đó.
- `README.md` còn "149.431 đánh giá"; sửa ở S5.

## 7. Điểm cần hiểu để trả lời phản biện

1. **Vì sao giữ điểm 0,0 và 0,5?** Thang bài báo là 0,0 đến 5,0 bước 0,5, và hai mức này có số dòng ngang các mức khác (9,04% và 9,14% so với 8,99% đến 9,23%). Không có bằng chứng trong file rằng 0,0 là "chưa chấm". Quyết định này do nhóm chốt ở CONTEXT mục 7.1.
2. **Vì sao vẫn mất 47 dòng?** Chúng có `food_id` = 4000, không có trong `foods.csv` (chỉ đến 3999), nên không có thông tin món để gợi ý và vi phạm khóa ngoại.
3. **Vì sao K-core không loại thêm dòng nào?** Người dùng ít nhất có 1.641 đánh giá, món ít nhất có 27, đều vượt xa K = 3.
4. **Dữ liệu này có phải sinh nhân tạo không?** Chưa kiểm chứng. Chỉ đo được phân phối gần đều trên 11 mức (độ lệch chuẩn 1,5798 so với 1,5811 của phân phối đều lý thuyết); bài báo nói có điền giá trị thiếu bằng trung vị nhưng chưa nối được với phân phối đo được.
5. **Vì sao không chạy lại làm sạch Food.com?** Ghi lại Parquet Food.com có thể làm đổi thứ tự dòng và cách chia dữ liệu theo seed; dữ liệu này đã kiểm chứng và không đổi quy tắc.

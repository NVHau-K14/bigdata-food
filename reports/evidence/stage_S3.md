# Biên bản stage S3: ViFoodRec chia dữ liệu, mô hình cơ sở, ALS, K-means và EDA chạy lại

Ngày: 14/10/2026. Log nguyên văn nằm trong `reports/evidence/logs/S3_*.log`. Mọi số dưới đây trích từ các log và file kết quả đó.

## 1. Đã làm gì

Dữ liệu vào: `/data/clean/food_vietnam/ratings_clean.parquet` của S2 (182.631 dòng, 11 mức điểm 0,0 đến 5,0). Food.com không chạy lại, trừ EDA (xem mục 6).

File mã tạo hoặc sửa:

- [src/split_data.py](../../src/split_data.py): tách hàm dùng chung `split_with_cold_start_filter` (cùng cách chia cho kết quả chính và biến thể nhạy cảm), thêm `--only vietnam` (giữ nguyên dòng Food.com trong `split_log.csv`).
- [src/baseline.py](../../src/baseline.py), [src/train_als.py](../../src/train_als.py): thêm `--only vietnam`, ghép kết quả mới vào file cũ và giữ dòng Food.com. `train_als.py` còn ghi `results/als_best_params_food_vietnam.json` và sửa lỗi ghi bản sao local (mục 5).
- [src/kmeans_behavior.py](../../src/kmeans_behavior.py): thêm `--only vietnam`, đặt tên cụm bằng [src/cluster_naming.py](../../src/cluster_naming.py) (mới), bỏ tên tiếng Anh trong nhãn và tiêu đề biểu đồ.
- [src/relabel_food_com_clusters.py](../../src/relabel_food_com_clusters.py) (mới): đổi nhãn cụm Food.com, không đổi số liệu.
- [src/vifoodrec_sensitivity.py](../../src/vifoodrec_sensitivity.py) (mới): bảng nhạy cảm 3 biến thể.
- [src/eda_analysis.py](../../src/eda_analysis.py): bỏ số cứng của ViFoodRec cũ (149.431 dòng, độ thưa 63,01%, điểm trung bình 3,00, trung vị 1.469), bỏ chữ "nhân tạo" chưa kiểm chứng, bỏ icon, đặt trục theo thang 0 đến 5.
- Kiểm tra độc lập: `scratch/s3_leak_check.py` (rò rỉ), `scratch/s3_als_diag.py` (phân bố dự đoán của ALS).
- Sao lưu trước khi ghi đè: `backup_v3_truoc_S3/` (232 file, gồm kết quả cục bộ, `app/data`, `web/data`, hình, và HDFS `/data/splits/food_vietnam`, `/models/food_vietnam`, `/data/results`). Nằm trong `.gitignore`.
- Làm mới `app/data` bằng `export_for_app.py`; `verify_export.py` đạt 66/66 (log `S3_12`, `S3_13`). `web/data` chưa đổi, để S4.

Lệnh chạy (trong container, thư mục `/home/jovyan/work`):

```text
docker exec bigdata_spark_env /opt/conda/bin/python src/split_data.py --only vietnam        # S3_02
docker exec bigdata_spark_env /opt/conda/bin/python scratch/s3_leak_check.py                # S3_03
docker exec bigdata_spark_env /opt/conda/bin/python src/baseline.py --only vietnam          # S3_04
docker exec bigdata_spark_env /opt/conda/bin/python src/train_als.py --only vietnam         # S3_05
docker exec bigdata_spark_env /opt/conda/bin/python src/kmeans_behavior.py --only vietnam   # S3_06
docker exec bigdata_spark_env /opt/conda/bin/python src/vifoodrec_sensitivity.py            # S3_07
docker exec bigdata_spark_env /opt/conda/bin/python scratch/s3_als_diag.py                  # S3_08
docker exec bigdata_spark_env /opt/conda/bin/python src/relabel_food_com_clusters.py        # S3_09
docker exec bigdata_spark_env /opt/conda/bin/python src/eda_analysis.py                     # S3_10
docker exec bigdata_spark_env /opt/conda/bin/python src/export_for_app.py                   # S3_12
docker exec bigdata_spark_env /opt/conda/bin/python src/verify_export.py                    # S3_13
```

## 2. Chia dữ liệu và kiểm tra rò rỉ (log `S3_02`, `S3_03`)

| Tập | Số dòng | Ghi chú |
|---|---:|---|
| Đầu vào | 182.631 | |
| Train | 146.012 | 79,95% |
| Validation | 18.204 | loại cold-start: 0 dòng |
| Test | 18.415 | loại cold-start: 0 dòng |

Kiểm tra bằng truy vấn Spark SQL độc lập với `split_data.py` (log `S3_03`):

```text
Tổng train+validation+test: 182631
Giao cặp (user_id, food_id) train và validation: 0
Giao cặp (user_id, food_id) train và test: 0
Giao cặp (user_id, food_id) validation và test: 0
Số mức điểm phân biệt ở train: 11 | ở validation: 11 | ở test: 11
User và món ở test/validation không có trong train: 0 0
```

Rò rỉ bằng 0. `hdfs fsck /data` và `/models` báo HEALTHY, Under-replicated blocks = 0 (log `S3_14`).

## 3. Kết quả mô hình mới và so với kết quả cũ

Giao thức giữ nguyên: chia 80/10/10 seed 42, chọn tham số chỉ bằng validation, đo test một lần, món phù hợp là rating >= 4,0, lưới ALS giữ nguyên (rank 10, 20, 50; regParam 0,01, 0,05, 0,1, 0,5; maxIter 10, 15).

`results/model_comparison.csv` có 8 dòng: 4 dòng ViFoodRec mới và 4 dòng Food.com giữ nguyên từ kết quả đã kiểm chứng (Food.com không chạy lại, nên không có "8 dòng mới" theo nghĩa chạy lại cả hai bộ).

Bảng so sánh mô hình ViFoodRec (test, 18.415 dòng). Cột "Cũ" lấy từ `backup_v3_truoc_S3/results/model_comparison.csv` (dữ liệu cũ đã loại 0,0 và 0,5, test 15.080 dòng):

| Mô hình | RMSE mới | MAE mới | P@10 mới | R@10 mới | RMSE cũ | MAE cũ | P@10 cũ | R@10 cũ |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Trung bình toàn cục | 1,5706 | 1,3502 | 0 | 0 | 1,2866 | 1,1073 | 0 | 0 |
| Trung bình món làm trơn | 1,5873 | 1,3690 | 0,01584 | 0,00321 | 1,3033 | 1,1261 | 0,01584 | 0,00308 |
| Top món phổ biến | 1,5924 | 1,3723 | 0,02277 | 0,00461 | 1,3094 | 1,1299 | 0,01584 | 0,00331 |
| ALS | 1,6654 | 1,4185 | 0,01386 | 0,00285 | 1,3832 | 1,1752 | 0,01386 | 0,00286 |

Nhận xét có số:

- RMSE và MAE không so sánh trực tiếp với cột cũ vì thang điểm và tập test đã đổi (11 mức thay vì 9). Kỳ vọng ghi ở prompt S2 (Global Mean khoảng 1,5 đến 1,6) khớp: 1,5706.
- ALS có RMSE cao hơn Trung bình toàn cục (1,6654 so với 1,5706) và cao hơn Trung bình món làm trơn. Thứ tự RMSE giữa 4 mô hình giống bản cũ. Đây là điều CONTEXT mục 7.2 đã chấp nhận.
- Xếp hạng Top 10: Top món phổ biến có P@10 0,02277, cao hơn ALS (0,01386). P@10 của ALS giống hệt bản cũ (0,01386); đây là số đo được, chưa tìm hiểu vì sao trùng.
- Tham số ALS tốt nhất: rank 10, regParam 0,5, maxIter 10, Validation RMSE 1,6576 (bản cũ: rank 10, regParam 0,1, maxIter 10, 1,3779). regParam tốt nhất nằm ở biên lưới (0,5 là giá trị lớn nhất), và cả 6 cấu hình có regParam 0,5 cho cùng Validation RMSE 1,6576 (log `S3_05`). Theo prompt, lưới giữ nguyên; việc mở rộng lưới là việc của S3b.
- Kiểm chứng phân bố dự đoán của ALS (log `S3_08`): trên test, dự đoán có trung bình 2,0047, độ lệch chuẩn 0,2142, khoảng 1,1709 đến 2,8849; điểm thật có trung bình khoảng 2,50 và trải đều 0,0 đến 5,0. RMSE của ALS (1,6654) gần RMSE khi luôn dự đoán hằng số 2,0 (1,6531) và cao hơn khi luôn dự đoán 2,5 (1,5706). Nguyên nhân cụ thể (regParam lớn cùng ràng buộc không âm) là giả thuyết chưa kiểm chứng.
- Top món phổ biến: không món nào có điểm trung bình >= 4,0 trên train nên mã dùng nhánh dự phòng (xếp theo số đánh giá). Chưa đếm chính xác số món; đây là suy ra từ điều kiện `len(pop_candidates) < 20` trong mã và điểm trung bình toàn bộ 2,50, chưa kiểm chứng bằng truy vấn.

Chưa nghi ngờ kết quả "tốt bất thường": không mô hình nào tốt hơn Trung bình toàn cục về RMSE.

## 4. Bảng nhạy cảm 3 biến thể (`results/vifoodrec_sensitivity.csv`, log `S3_07`)

Chỉ để đối chiếu, không dùng làm kết quả chính. ALS dùng tham số của biến thể chính (rank 10, regParam 0,5, maxIter 10), không tinh chỉnh lại. Mỗi biến thể: K-core lặp K = 3 (hội tụ sau 1 vòng, không loại thêm dòng), chia 80/10/10 seed 42.

| Biến thể | Dòng sạch | Mức điểm | Test | Trung bình toàn cục RMSE / MAE | Trung bình món làm trơn RMSE / MAE | ALS RMSE / MAE |
|---|---:|---:|---:|---|---|---|
| Chính: giữ 11 mức | 182.631 | 11 | 18.415 | 1,5706 / 1,3502 | 1,5873 / 1,3690 | 1,6654 / 1,4185 |
| A: bỏ riêng 0,0 | 166.128 | 10 | 16.776 | 1,4325 / 1,2464 | 1,4507 / 1,2537 | 1,5337 / 1,3043 |
| B: quy tắc cũ, chỉ giữ 1,0 đến 5,0 | 149.431 | 9 | 15.080 | 1,2895 / 1,1103 | 1,3058 / 1,1280 | 1,3929 / 1,1822 |

- Biến thể chính khớp `model_comparison.csv`: chênh RMSE và MAE bằng 0 cho cả 3 mô hình (cuối log `S3_07`), nên cách chia và huấn luyện của biến thể giống kết quả chính.
- Biến thể B có 149.431 dòng, đúng bằng số dòng của bản cũ.
- Trong cả 3 biến thể, thứ tự RMSE giống nhau: Trung bình toàn cục thấp nhất, rồi Trung bình món làm trơn, rồi ALS. Bỏ càng nhiều điểm thấp thì RMSE tuyệt đối càng nhỏ (1,5706, 1,4325, 1,2895 cho Global Mean).
- Biến thể B không cho đúng số của bản cũ: Global Mean 1,2895 so với 1,2866 cũ, ALS 1,3929 so với 1,3832 cũ, dù cùng số dòng. Điểm khác là thứ tự dòng trong Parquet sạch (ghi lại ở S2) nên phép chia ngẫu nhiên theo seed ra tập test khác. Đây là giả thuyết chưa kiểm chứng.

## 5. K-means (log `S3_06`, `S3_09`)

K-means người dùng ViFoodRec (101 người dùng, huấn luyện trên train, k = 3 giữ nguyên quyết định cũ): Silhouette k = 2, 3, 4, 5 lần lượt 0,2474; 0,2219; 0,2369; 0,2130 (bản cũ k = 3: 0,2534).

Chênh lệch tương đối giữa 3 cụm (lớn nhất trừ nhỏ nhất, chia trung bình toàn hệ thống):

| Đặc trưng | Chênh lệch |
|---|---:|
| n_ratings | 2,69% |
| avg_rating | 2,76% |
| std_rating | 1,56% |
| pct_man_high | 6,49% |
| pct_chay_high | 17,52% |
| avg_calo_high | 1,15% |
| avg_time_high | 1,71% |

Quy tắc CONTEXT mục 7.4 yêu cầu mọi đặc trưng dưới 10%. Sáu đặc trưng thỏa, riêng `pct_chay_high` là 17,52% (chia cho giá trị nhỏ nhất: 19,01%; chia cho giá trị lớn nhất: 15,97%; cả ba cách chia đều trên 10%). Chênh lệch tuyệt đối là 0,0120 so với 0,0142 (tỷ lệ món chay được chấm cao trên toàn bộ đánh giá của người dùng, giá trị rất nhỏ). Vì điều kiện không thỏa trọn vẹn, tên "Cụm 1, 2, 3" đang là tạm thời, để tránh đặt tên diễn giải dựa trên chênh lệch rất nhỏ. Mã in cảnh báo "VƯỢT NGƯỠNG" trong log. Cần người dùng quyết định (mục 7).

Hồ sơ 3 cụm (train): Cụm 1 có 33 người (32,67%), Cụm 2 có 31 người (30,69%), Cụm 3 có 37 người (36,63%); điểm trung bình 2,5381; 2,4996; 2,4691. Nhãn nằm trong `cluster_profiles_food_vietnam.csv` và `user_clusters_food_vietnam.parquet`.

K-means món ViFoodRec: dùng đặc trưng dinh dưỡng của `foods_clean` (không phụ thuộc điểm đánh giá). Chạy lại cho số liệu y hệt bản cũ (1.486; 1.211; 195; 1.108 món). Chỉ đổi nhãn, bỏ phần tiếng Anh: "Món mặn nhiều calo và đường", "Món mặn ít đường", "Món chay", "Món mặn ít calo". Nhãn cũ có "chiên xào", "canh hầm", "bánh và ăn vặt" là mô tả chưa đo từ dữ liệu nên đã bỏ.

Nhãn cụm Food.com (không chạy lại K-means; log `S3_09`, số người mỗi cụm không đổi: 3.993; 10.679; 7.905; 8.195). Mỗi tên được mã kiểm tra với cực trị trong hồ sơ cụm, nếu sai thì báo lỗi:

| Cụm | Tên mới | Số liệu hồ sơ khớp tên |
|---|---|---|
| 0 | Người dùng khắt khe | điểm trung bình thấp nhất, 3,83 so với từ 4,68 trở lên ở các cụm khác |
| 1 | Người chuộng món nấu lâu, nhiều calo | thời gian nấu trung bình cao nhất 105,9 phút, calo cao nhất 604,5 |
| 2 | Người chuộng món nấu nhanh, ít calo | thời gian nấu thấp nhất 45,5 phút, calo thấp nhất 317,9 |
| 3 | Thành viên lâu năm, đánh giá nhiều | 56,0 đánh giá mỗi người và 1.949 ngày hoạt động, đều cao nhất |

Tên cũ của cụm 1 là "Người dùng phổ thông dễ tính (General Enthusiasts)" không khớp đặc điểm nổi bật của cụm (nấu lâu, nhiều calo). Cụm 1 và cụm 2 đã đổi nghĩa so với tên cũ; số liệu không đổi.

## 6. EDA (log `S3_10`, `S3_11`)

`eda_analysis.py` đọc cả hai bộ dữ liệu trong cùng một lần chạy (biểu đồ 1 và 12 so sánh hai bộ), nên chạy lại toàn bộ. Đây là lý do script bắt buộc chạy chung. Kiểm tra bằng `cmp` với bản sao lưu (log `S3_11`): 12 file CSV không đổi (gồm 11 file Food.com và `eda_11_vifoodrec_top_ingredients.csv`). Các hằng số Food.com cứng trong mã cũ (30.836 người dùng, 78.171 món, 706.514 tương tác, độ thưa 99,97%, điểm trung bình 4,71, trung vị 6 và 5) khớp số tính lại từ dữ liệu. `eda_03_food_com_top_popular.csv` có cùng 10 món nhưng khác thứ tự dòng. `eda_12_dataset_comparison.csv` có định dạng số giống bản cũ.

Số ViFoodRec mới (so sánh Food.com với ViFoodRec, `eda_12`): 101 người dùng, 4.000 món, 182.631 tương tác, độ thưa 54,79%, điểm trung bình 2,50, trung vị đánh giá mỗi người 1.795 và mỗi món 46. Phân phối 11 mức điểm: từ 8,99% (1,0) đến 9,23% (1,5); phân phối đều lý thuyết là 9,09%. Món mặn: 3.805 món, điểm trung bình 2,4993; món chay: 195 món, 2,4974.

`reports/evidence/eda_insights.md` còn nội dung của dữ liệu cũ ("phân phối đều nhân tạo", 149.431 dòng, 3,00, 1.469, độ thưa 63,01%). Tôi không viết lại ở S3; sẽ đính chính ở S5.

## 7. Đối chiếu bài báo (PACLIC 2024, Bảng 5)

Số trích từ `scratch/paclic_paper_text.txt` (dòng 582 đến 586), bài báo đo trên 200 điểm dữ liệu của tập test:

| Phương pháp bài báo | RMSE | MAE |
|---|---:|---:|
| User-user Cosine | 2,0635 | 1,7228 |
| User-user Pearson | 2,3324 | 1,9130 |
| Item-item Cosine | 2,1486 | 1,6902 |
| Item-item Pearson | 2,5543 | 2,1250 |

Giao thức vẫn khác: bài báo 200 điểm test; nhóm dùng 18.415 điểm test (chia 80/10/10, loại cold-start). Thang điểm nay trùng thang bài báo (0,0 đến 5,0, bước 0,5), nên khác biệt về thang không còn là một lý do khiến hai bên không so sánh được. Lưu ý: Trung bình toàn cục của nhóm (RMSE 1,5706) cũng thấp hơn mọi số trong bảng bài báo, nên khoảng cách này không chứng minh ALS tốt hơn.

## 8. Tiêu chí đạt (cổng kiểm tra S3)

| Mục | Kết quả |
|---|---|
| `model_comparison.csv` có 8 dòng (4 mới ViFoodRec, 4 Food.com giữ nguyên) | ĐẠT theo số dòng; xem ghi chú ở mục 3 |
| `vifoodrec_sensitivity.csv` có 3 biến thể | ĐẠT (9 dòng: 3 biến thể x 3 mô hình) |
| Rò rỉ bằng 0 | ĐẠT (log `S3_02`, `S3_03`) |
| Tên cụm ViFoodRec là "Cụm 1, 2, 3" nếu chênh lệch dưới 10% | CHƯA ĐẠT ĐIỀU KIỆN: `pct_chay_high` chênh 17,52%; tên "Cụm 1, 2, 3" đang tạm dùng, chờ quyết định |
| Mọi lệnh ghi log | ĐẠT (`S3_01` đến `S3_14`) |
| Sao lưu trước khi ghi đè | ĐẠT (`backup_v3_truoc_S3/`) |

## 9. Còn tồn và giả định

- Lỗi hạ tầng cũ phát hiện: khi `STORAGE_MODE=hdfs`, đường dẫn local không có scheme được hiểu theo HDFS mặc định. Vì vậy `train_als.py` bản cũ không bao giờ ghi bản sao `recommendations_*` và `item_neighbors_*` ra đĩa máy; các file local ở `data/results/` và `results/` còn là bản cũ ngày 13/10, và có bản sao thừa trong HDFS tại `/home/jovyan/work/data/results/`. Đã sửa trong `train_als.py` (hàm `save_local_copies`, ghi bằng pandas) và chạy lại ALS; log lần chạy đầu giữ ở `S3_05a_als_lan1_loi_ghi_local.log`. Kết quả hai lần chạy trùng nhau. Bản sửa cho nhánh Food.com chưa chạy thử (Food.com không chạy lại). Thư mục thừa trong HDFS chưa xóa (ngoài phạm vi, xóa là việc không khôi phục được).
- `web/data` chưa làm mới, `verify_web.py` còn chuỗi tên bước cũ `filter_rating_range_1_to_5` và hằng số 149.431 (ghi ở S2 mục 6). Làm ở S4.
- Hình `kmeans_user_clusters_foodcom_pca.png` (Food.com) chưa vẽ lại nên chú giải còn tên tiếng Anh cũ. Muốn vẽ lại cần chạy K-means Food.com (trái nguyên tắc không chạy lại), để người dùng quyết định.
- `eda_insights.md` và các biên bản P3, P5, P7, P8, P11 còn câu mô tả cũ (sinh nhân tạo, loại 0,0 và 0,5, nhãn cụm cũ). Đính chính ở S5.
- `docs/data_contract.md` mục 2 và 3 vẫn mô tả `app/data` ở trạng thái cũ (ví dụ "3 cụm hành vi" có tên diễn giải). Cập nhật ở S4 và S5.
- Dòng "Toàn bộ hệ thống" thay cho "Toàn bộ hệ thống (Overall)" ở hồ sơ cụm Food.com, và "Toàn bộ món" thay cho "Toàn bộ món (Overall)": đổi cả chuỗi mà web có thể đang so khớp; kiểm tra ở S4.

## 10. Điểm cần hiểu để trả lời phản biện

1. **Vì sao ALS thua Trung bình toàn cục?** Số đo: trên test, ALS dự đoán quanh 2,00 (độ lệch chuẩn 0,21) trong khi điểm thật trải 0,0 đến 5,0 với trung bình 2,50, nên RMSE 1,6654 gần RMSE của dự đoán hằng số 2,0 (1,6531). Nguyên nhân sâu hơn là giả thuyết chưa kiểm chứng; điều đã thấy là regParam tốt nhất nằm ở biên lưới và 6 cấu hình có cùng Validation RMSE.
2. **Điểm phân phối gần đều trên 11 mức thì mô hình học được gì?** Điểm trung bình món gần nhau (món mặn 2,4993, món chay 2,4974), và phân phối mỗi mức từ 8,99% đến 9,23%. Nhóm chưa kết luận về nguồn gốc dữ liệu (xem S2 mục 7, câu 4).
3. **Có rò rỉ train và test không?** Không: truy vấn Spark SQL độc lập cho giao cặp (người dùng, món) bằng 0 ở cả ba cặp tập, và tổng ba tập bằng 182.631.
4. **Vì sao còn dùng biến thể B?** Chỉ để đối chiếu với quy tắc cũ: cùng số dòng 149.431 với bản cũ. Ở cả 3 biến thể, thứ tự RMSE giữa 3 mô hình không đổi, nên kết luận "ALS không hơn baseline" không phụ thuộc vào việc giữ hay bỏ 0,0 và 0,5.
5. **Vì sao chia ViFoodRec không bị mất dòng cold-start?** Người dùng ít nhất có 1.641 đánh giá và món ít nhất có 27 (S2), nên mọi người dùng và món trong validation và test đều có trong train (0 dòng bị loại).
6. **Vì sao gọi cụm ViFoodRec là "Cụm 1, 2, 3"?** Sáu trong bảy đặc trưng chênh nhau dưới 7% giữa các cụm và Silhouette chỉ 0,2219 cho k = 3; đặc trưng thứ bảy (tỷ lệ món chay được chấm cao) chênh 17,52% nhưng ở giá trị tuyệt đối rất nhỏ (0,0120 so với 0,0142). Điều kiện 10% của CONTEXT chưa thỏa trọn vẹn, nên đang chờ quyết định.

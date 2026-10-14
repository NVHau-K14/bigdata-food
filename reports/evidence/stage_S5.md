# Biên bản stage S5: dọn tài liệu, sinh lại STATUS và Q_and_A

Ngày: 14/10/2026. Log nguyên văn: `reports/evidence/logs/S5_*.log`. Không chạy lại pipeline và không đổi số liệu kết quả; chỉ chạy các lệnh kiểm chứng (đọc) ở mục 3.

## 1. Đã làm gì

**Sửa trực tiếp**
- [README.md](../../README.md): viết lại. Số liệu lấy từ `cleaning_log.csv`, `eda_12_dataset_comparison.csv`, `model_comparison.csv`; Spark 4.2.0; mô tả cụm là giả lập trên một máy; web 122, 129 và 21 mục kiểm thử; bỏ các số không truy được (3.964 món, 116.184, 24.325, 226.570, 71,0%, 99,963%, 4,68). Chưa có hướng dẫn chạy từ đầu đến cuối (việc của S6).
- [docs/CONTEXT.md](../../docs/CONTEXT.md): mục 1, 2, 6 ghi dashboard là `web/` (mục 7 giữ nguyên).
- [docs/data_contract.md](../../docs/data_contract.md): bản 1.1; bảng danh mục tệp, số dòng, dung lượng và tên cụm đối chiếu lại với `app/data/` (log `S5_04`); thêm dòng `cluster_top_items.csv`; ghi chú `app/data/` là nguồn dữ liệu của web.
- [src/config.py](../../src/config.py): chú thích ngưỡng 1440 phút là giá trị chọn tay, kèm phân vị đo được ở P1 (99% = 750; 99,9% = 2.147.483.647). Không đổi giá trị.
- `docs/web_data_contract.md`, `src/export_for_web.py`, `web/`: đã đúng từ S4, không sửa (grep không còn "Spark 3." ngoài chuỗi kiểm tra trong `verify_web.py`).

**Thêm khối đính chính (không viết lại nội dung gốc)**
- Khối "ĐÍNH CHÍNH ngày 14/10/2026" ở đầu `stage_P2` đến `stage_P11`, `stage_WEB`, `eda_insights`, `web_design_plan` (14 file). `stage_P2` và `stage_P1_audit` không nằm trong danh sách của prompt; chỉ thêm khối vào `stage_P2` vì có điểm sai đã sửa ở S1 (replication, Python, bước down và up), `stage_P1_audit` không đổi.
- Banner "ĐÃ LỖI THỜI" ở đầu `docs/Bao_cao_Tien_xu_ly_va_Lam_sach_Du_lieu.md` và `docs/Bao_cao_cua_gemini.md`. Tôi chỉ đọc phần đầu của báo cáo thứ hai (khảo sát và kế hoạch), không kiểm chi tiết từng số; banner ghi đúng điều đó.

**Sinh lại**
- [reports/evidence/STATUS.md](STATUS.md) (cùng cấu trúc cũ: hạ tầng, bảng hạng mục, hạn chế, rà soát, quyết định cần người dùng, bảng số chính).
- [docs/Q_and_A.md](../../docs/Q_and_A.md) (15 câu). Số Food.com bị loại là 425.853 (60.847 + 365.006), thay cho "gần 400 nghìn".

## 2. Lệnh đã chạy và log

```text
docker exec -w /home/jovyan/work bigdata_spark_env /opt/conda/bin/python scratch/s5_verify_mu.py       # S5_01
python scratch/s5_verify_numbers.py                                                                    # S5_02
docker ps; hdfs dfsadmin -report; hdfs fsck /data /models; pyspark version; Spark Master /json/        # S5_03
python (đọc app/data, đếm dòng và dung lượng)                                                          # S5_04
docker exec -w /home/jovyan/work bigdata_spark_env /opt/conda/bin/python scratch/s5_verify_toppop.py   # S5_05
python src/verify_web.py                                                                               # S5_06 (122/122 đạt)
python scratch/s5_gate_check.py                                                                        # S5_07
```

## 3. Kiểm chứng các khẳng định chưa kiểm chứng (mục 4B của STATUS cũ)

| Khẳng định | Kết quả (log) | Xử lý |
|---|---|---|
| μ của Global Mean | Food.com 4,714605 (565.420 dòng train); ViFoodRec mới 2,501157 (146.012 dòng) (`S5_01`) | Đã kiểm chứng; 2,9981 lỗi thời |
| "−19,2%" ở mức 1,0 sao | −16,7% so với Trung bình món làm trơn, −18,9% so với Trung bình toàn cục, −15,2% so với Top món phổ biến (`S5_02`) | Sai; đính chính ở `stage_P7` |
| "Cụm nhỏ nhất 7,77%" | Nhỏ nhất 12,98% (`S5_02`) | Sai; đính chính ở `stage_P8` |
| Top món phổ biến ViFoodRec dùng nhánh dự phòng (S3) | 4.000 món, 0 món có điểm trung bình từ 4,0, lớn nhất 3,4848 (`S5_05`) | Đã kiểm chứng |
| Độ trễ "dưới 200 ms" và tương tự | Không có phép đo | Bỏ; ghi "chưa đo" ở `stage_P10`, `stage_P11` |
| Phần tuần tự theo Amdahl | Không có phép đo tách phần tuần tự | Giả thuyết chưa kiểm chứng |
| Lý do mức 10% chạy chậm | `scalability.csv` chỉ cho thấy lượt 1 chậm hơn lượt 2 ở mức 10%, không ở 25% và 100% (2 Worker); thứ tự chạy không ghi (`S5_02`) | Giả thuyết chưa kiểm chứng. Tôi không chạy lại thực nghiệm (tốn thời gian và ghi đè `scalability.csv`) |
| Pushdown loại hoàn toàn nút thắt I/O; "CSV đa dòng"; "nhân tạo"; k = 5 có cụm nhỏ | Không có thí nghiệm đối chứng hoặc không truy được | Giả thuyết chưa kiểm chứng |

## 4. Cổng kiểm tra S5

| Mục | Kết quả |
|---|---|
| Đối chiếu số ở bảng chính của STATUS với file nguồn | ĐẠT: 23 số, 0 sai (log `S5_07`). 5 số chọn ngẫu nhiên (seed 5): Silhouette Món ViFoodRec k = 4 (0,2334), số dòng ViFoodRec sạch (182.631), số người dùng Food.com (30.836), thời gian 1 Worker mức 10% (10,583 giây), tỷ lệ nén `interactions_clean` (4,19 lần). |
| Không còn mục "chưa kiểm chứng" mà không có giải thích | ĐẠT: mỗi mục ở 4B được ghi một trong: đã kiểm chứng (có log), giả thuyết chưa kiểm chứng (có lý do), bỏ (độ trễ). |
| `verify_web.py` vẫn đạt sau khi sửa tài liệu | ĐẠT: 122/122 (log `S5_06`) |
| Số liệu trong README lấy từ file kết quả mới | ĐẠT (cột "Nguồn" trong README) |

## 5. Còn tồn

- Các biên bản P3 đến P11 còn nguyên văn nội dung cũ sau khối đính chính; người đọc cần đọc khối này trước. Khối nêu điểm sai ở mức tôi đã kiểm chứng; tôi không rà từng câu của các biên bản dài, nên có thể còn câu cũ khác không được liệt kê (ví dụ các mô tả dữ liệu ViFoodRec cũ rải rác trong P3 và P5).
- `README.md` chưa có hướng dẫn chạy từ đầu đến cuối và chưa ghim phiên bản thư viện (S6).
- Những quyết định cần người dùng: xem `STATUS.md` mục 5 (thư mục thừa trên HDFS, chạy lại ALS ViFoodRec với lưới mở rộng, hình PCA Food.com, thông tin nhóm trong `web/config.js`, giấy phép dữ liệu, chế độ local).
- `web/config.js` vẫn để trống thông tin nhóm (nhóm tự điền).

## 6. Điểm cần hiểu để trả lời phản biện

1. **Vì sao không viết lại các biên bản P3 đến P11?** Để giữ dấu vết kết quả đã từng có; khối đính chính nêu điểm sai và trỏ tới `stage_S2.md` và `stage_S3.md` có số đúng.
2. **Vì sao μ của ViFoodRec đổi từ 2,9981 sang 2,5012?** Dữ liệu đổi (giữ 11 mức điểm thay vì 9 mức từ 1,0 đến 5,0); μ mới là trung bình điểm tập train mới (146.012 dòng), đo bằng truy vấn.
3. **"−19,2%" sai ở đâu?** So với Trung bình món làm trơn, giảm từ 3,6135 xuống 3,0118 là −16,7%; con số 19,2% không khớp phép tính nào với các baseline (−18,9% so với Trung bình toàn cục).
4. **Vì sao lời giải thích Amdahl chỉ là giả thuyết?** Không có phép đo nào tách phần chạy tuần tự khỏi phần song song; giá trị 35 đến 40% được suy ngược từ kết quả tăng tốc 1,25 lần.
5. **Q_and_A có còn câu nào nói ALS tốt hơn không?** Không. Câu 4 và 5 nêu số ALS thua mô hình cơ sở và nói rõ nguyên nhân nào đã đo, nguyên nhân nào còn là giả thuyết.

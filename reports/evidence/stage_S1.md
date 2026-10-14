# Biên bản stage S1: sửa hạ tầng

Ngày: 14/10/2026. Log nguyên văn nằm trong `reports/evidence/logs/S1_*.log`.

## 1. Đã làm gì

- Sửa [docker-compose.yml](../../docker-compose.yml): thêm healthcheck cho `spark-master` và hai `spark-worker`.
- Sửa [src/config.py](../../src/config.py): thêm `HDFS_REPLICATION` (mặc định 2) và đặt `spark.hadoop.dfs.replication` khi `STORAGE_MODE=hdfs`.
- Sao lưu `/models` và `/data/clean` ra `D:\Documents\BaiTap\BigData\backup_hdfs_S1` (72 file, 32.391.261 byte; log `S1_06*`).
- Chạy `hdfs dfs -setrep -R -w 2` cho `/data`, `/models` và `/home` (thư mục phụ do một lần chạy trước ghi vào HDFS, chứa kết quả gợi ý).
- Chạy `docker compose down` (không `-v`) rồi `up -d`, và chạy lại `smoke_test_cluster.py`.

## 2. H3: trạng thái unhealthy

Trước (log `S1_02`, `S1_03`): `spark-master`, `spark-worker-1`, `spark-worker-2` báo `unhealthy`. `docker inspect` cho thấy container dùng healthcheck có sẵn của image Jupyter (`/etc/jupyter/docker_healthcheck.py`), lệnh này tìm file `*server-*.json` của máy chủ Jupyter và lỗi `StopIteration`. Master và worker của Spark không chạy Jupyter, nên luôn báo lỗi dù Spark chạy tốt. `docker-compose.yml` cũ không khai báo healthcheck.

Sửa: healthcheck `curl -sf http://localhost:<cổng>/json/` (8080 cho master, 8081 cho worker). Không đổi cấu hình cụm.

Sau (log `S1_11`): cả 3 container `healthy`, Spark Master báo trạng thái `ALIVE` với 2 worker `ALIVE`. `bigdata_spark_env` vẫn `healthy` bằng healthcheck mặc định vì nó có chạy Jupyter. Container `namenode` và `datanode` không khai báo healthcheck nên không hiện trạng thái này.

## 3. H4: replication

Trước (log `S1_04`, `S1_05`): `Under replicated blocks: 144`, `Missing replicas: 144 (32,14%)`, file Spark ghi có replication 3 (ví dụ các phần của `/data/benchmark/...`) dù `dfs.replication=2` và chỉ có 2 DataNode.

Nguyên nhân (đã kiểm chứng): container client Spark không có `hdfs-site.xml` của cụm, nên client ghi theo mặc định của Hadoop là 3. Bằng chứng gián tiếp: file mới ghi bằng cấu hình mới có replication 2 (mục dưới), còn file cũ ghi bằng cấu hình cũ có replication 3.

Sửa: đặt `spark.hadoop.dfs.replication=2` ở `src/config.py`, rồi `setrep`.

Sau (log `S1_07` đến `S1_10`, `S1_13`):

| Chỉ số | Trước | Sau |
|---|---:|---:|
| Under replicated blocks | 144 | 0 |
| Missing blocks | 0 | 0 |
| Average block replication | không đo | 2,0 |
| Missing replicas | 144 | 0 |
| Replication file `smoke_test.parquet/_SUCCESS` ghi mới | 3 (bản cũ) | 2 |

Ghi chú: lần `setrep` đầu cho `/data` và `/models` còn 13 block (từ 144 xuống 13). Số còn lại nằm ở `/home/jovyan/work/data/results/...` (kết quả gợi ý do một lần chạy ghi nhầm vào đường dẫn này), xử lý bằng `setrep` thêm cho `/home`. Lúc đầu tôi gõ sai thứ tự cờ (`-w 2 -R`), lệnh báo lỗi `setrep: -R: No such file`, phải chạy lại với `-R -w 2` (log `S1_07`, `S1_08`). Thư mục `/home/jovyan/...` trên HDFS là nguồn gốc chưa tìm hiểu, chưa xóa.

## 4. Xác nhận dữ liệu sau `down` và `up` (P2 §3.7)

Log `S1_11`: trước và sau, `hdfs dfs -count` cho kết quả giống hệt (`/data`: 35 thư mục, 115 file, 1.165.516.762 byte; `/models`: 11 thư mục, 48 file, 5.002.869 byte). Safe mode tắt, 2 DataNode còn sống, 0 block thiếu.

## 5. Smoke test

Log `S1_12`: Spark 4.2.0, đọc 1.132.367 dòng khớp kỳ vọng, ghi và đọc lại Parquet 1.000 dòng khớp, kết quả "ĐẠT CHUẨN" (20,01 s).

## 6. Tiêu chí đạt

| Mục | Kết quả |
|---|---|
| Under replicated blocks = 0 | ĐẠT |
| Không còn unhealthy ở Spark master và worker | ĐẠT |
| Dữ liệu HDFS còn nguyên sau down và up | ĐẠT |
| Smoke test đạt | ĐẠT |

## 7. Còn tồn

- `docker compose down` đã tạo lại các container; không mất volume.
- Đã quét `src/`: chỉ `config.get_spark_session` tạo SparkSession (lệnh Grep `SparkSession.builder`), nên mọi script đi qua cấu hình replication mới. Thư mục `/home/jovyan/...` trên HDFS vẫn còn, chưa xóa.

## 8. Điểm cần hiểu để trả lời phản biện

1. **Vì sao replication 2?** Chỉ có 2 DataNode; yêu cầu 3 bản sao không thể đạt, nên HDFS báo under replicated.
2. **Vì sao Spark báo unhealthy mà vẫn chạy?** Healthcheck mặc định của image kiểm tra Jupyter, không phải Spark.
3. **Làm sao biết dữ liệu không mất sau `down` và `up`?** Do volume được giữ; số thư mục, file, byte trước và sau khớp.
4. **`Under replicated blocks` khác `Missing blocks` thế nào?** Under replicated là còn bản sao nhưng ít hơn mục tiêu; missing là mất hết bản sao.

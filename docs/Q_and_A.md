# Q&A PHẢN BIỆN: 15 CÂU GIẢNG VIÊN CÓ THỂ HỎI

Mỗi câu trả lời dựa trên số thật đã đối chiếu trong `reports/evidence/STATUS.md`. Câu nào có chỗ nhóm chưa kiểm chứng thì ghi thẳng ra, không nói tránh.

---

**1. Hạ tầng của nhóm là HDFS + Spark cụm thật, hay Spark local rồi lưu Parquet?**
Cụm thật theo nghĩa phần mềm: 1 NameNode, 2 DataNode (HDFS 3.3.6), 1 Spark Master, 2 Worker (Spark 4.2.0, mỗi worker 2 core, 3.5 GB), chạy bằng Docker Compose. Nhưng cả 7 container nằm trên **một máy Windows** nên đây là cụm giả lập, không có mạng thật giữa các máy. Bằng chứng: `stage_P2.md` (lệnh và kết quả nguyên văn) và lệnh đọc lại ngày 14/10. Chế độ `STORAGE_MODE=local` có trong `config.py` nhưng nhóm chưa chạy thử.

**2. Vì sao phải lọc K-core lặp? Kết quả cụ thể?**
Lọc một lượt để sót: bản đầu còn 735,006 dòng nhưng vẫn có 3,572 user và 10,637 món dưới 3 tương tác (`stage_P1_audit.md`). Khi bỏ user ít tương tác thì số tương tác của món giảm theo và ngược lại, nên phải lặp đến hội tụ. Bản lặp hội tụ ở **706,514** dòng sau 5 vòng, kiểm tra độc lập `verify_clean.py` cho min user = 3, min món = 3 (`stage_P3.md`).

**3. ViFoodRec mất 33,247 dòng. Vì sao, và loại rating 0.5 có đúng không?**
182,678 → 149,431: loại 16,509 dòng điểm 0.0, 16,702 dòng điểm 0.5 và 36 dòng `food_id = 4000` không có trong danh mục món (`cleaning_log.csv`). K-core không làm mất dòng nào. Thành thật: việc loại 0.0 và 0.5 là quyết định của nhóm. Đọc lại `ratings.csv`, 11 mức từ 0.0 đến 5.0 có số dòng gần bằng nhau (khoảng 16.4–16.9 nghìn mỗi mức), nên không có bằng chứng 0.0 là "chưa chấm". Nhóm đã nêu điều này trong `STATUS.md` và đề xuất người dùng quyết định có chạy lại hay không.

**4. ALS có tốt hơn baseline không?**
Không. Trên tập test (`results/model_comparison.csv`): Food.com ALS có RMSE 0.6747 so với 0.6177 của Smoothed Item Mean, MAE 0.5094 so với 0.4120, Precision@10 0.00017 so với 0.00534 của Top-N Popular. ViFoodRec ALS có RMSE 1.3832 so với 1.2866 của Global Mean, Precision@10 0.01386 so với 0.01584. Nhóm báo cáo đúng như vậy. Điểm duy nhất ALS tốt hơn là RMSE ở mức 1–4 sao trên Food.com (`als_rmse_breakdown.csv`), nhưng ALS tệ hơn ở lớp 5 sao (0.5903 so với 0.2854–0.3030) chiếm 78.4% dữ liệu, nên không đủ để nói ALS tốt hơn.

**5. Vì sao ALS thua? Nhóm có chắc nguyên nhân không?**
Có hai yếu tố đã quan sát được. Food.com lệch mạnh về 5 sao nên dự đoán hằng số 4.71 đã có RMSE 0.6266, khó vượt. ViFoodRec có phân phối điểm đều: RMSE của Global Mean (1.2866) gần bằng độ lệch chuẩn lý thuyết của phân phối đều √(15/9) = 1.291, nghĩa là chưa thấy tín hiệu để học. Còn việc dữ liệu ViFoodRec "do sinh nhân tạo" thì **nhóm chưa kiểm chứng**; bài báo gốc chỉ nói điền 40% giá trị thiếu bằng trung vị. Lưới regParam của Food.com cũng tốt nhất ở biên (0.2 là giá trị lớn nhất đã thử) nên chưa chắc đã tối ưu.

**6. Có dùng tập test để chọn tham số không? Có rò rỉ dữ liệu không?**
Không dùng test để chọn tham số: chọn trên validation (Food.com val RMSE 0.6754, ViFoodRec 1.3779) rồi mới đo test một lần. Kiểm tra rò rỉ bằng inner join cho ba cặp train/val/test đều **0** dòng chung (`split_log.csv`). Hai lưu ý: chia ngẫu nhiên theo dòng (`rand(seed=42)`), không chia theo thời gian; và K-core chạy trên toàn bộ dữ liệu trước khi chia. K-means chỉ dùng tập train.

**7. "Parquet nén 60 lần" có đúng không? Nén thực sự là bao nhiêu?**
Sai, và nhóm đã bỏ con số này. So sánh cũ đặt CSV thô (có cột review, 1.13 triệu dòng) với Parquet đã bỏ review và bỏ gần 400 nghìn dòng. So sánh công bằng (`storage_benchmark.csv`): dữ liệu thô đầy đủ nén **1.76x** (interactions) và **2.34x** (recipes); dữ liệu sạch nén **4.19x** và **7.03x**. Truy vấn trên Parquet nhanh hơn 1.71x–2.06x nhưng đo trên bảng chỉ 19 MB, 3 lần đo sau 1 lần khởi động.

**8. Thực nghiệm mở rộng quy mô chứng minh được điều gì?**
Ít hơn mong muốn. Thời gian tổng của pipeline với 2 worker là 11.99 s (10%), 8.39 s (25%), 7.17 s (50%), 7.93 s (100%): gần phẳng, không đơn điệu, nên bị chi phí cố định của Spark che hết (`scalability.csv`). Tăng tốc 1→2 worker là 0.88x, 0.87x, 1.15x, 1.25x. Nhóm chỉ kết luận được là "chưa thấy thời gian tăng theo dữ liệu trong khoảng đến 706,514 dòng" và 2 worker chỉ có lợi ở mức dữ liệu lớn. Nhóm không khẳng định mở rộng tuyến tính. Lời giải thích Amdahl "phần tuần tự ≈ 40%" là suy ngược từ kết quả, chưa đo.

**9. Vì sao chọn k=4 cho người dùng Food.com khi Silhouette lớn nhất ở k=2?**
Silhouette: k=2 đạt 0.5257, k=4 chỉ 0.2743 (`kmeans_tuning.csv`). k=2 chỉ tách "ít đánh giá" và "nhiều đánh giá", quá thô nên nhóm chọn k=4 vì các cụm diễn giải được (khắt khe 12.98%, dễ tính 34.70%, món nhanh gọn 25.69%, thâm niên 26.63%). Đây là chọn theo diễn giải, không theo Silhouette cao nhất. Silhouette 0.2743 cho thấy cấu trúc cụm yếu, không nên nói cụm "tách bạch".

**10. Các cụm người dùng ViFoodRec có ý nghĩa không?**
Không đáng kể. Ba cụm 44 / 28 / 29 user có điểm TB 3.00 / 2.96 / 3.03 và thời gian nấu món chấm cao 32.71 / 32.87 / 32.80 phút (`cluster_profiles_food_vietnam.csv`); độ lệch lớn nhất 2.42%. Vì vậy trang web gọi chúng là "Cụm 1, 2, 3". Các tên "Convenient/Selective/Active Gourmet Diners" trong P8 và `results/` không có số liệu hỗ trợ. Cụm món ViFoodRec (k=4) thì có ý nghĩa rõ hơn: cụm Chay 195 món có `is_savory` = 0 (`food_cluster_profiles_vietnam.csv`).

**11. Precision@10 chỉ 0.00017–0.0158, rất thấp. Có lỗi không?**
Không phải lỗi mà do thiết kế đánh giá. Món "phù hợp" là món trong test có điểm ≥ 4, danh sách gợi ý đã loại món có trong train, và chỉ tính user có ít nhất một món phù hợp (`src/evaluation.py`). Food.com có 78 nghìn món, mỗi user thường chỉ có vài tương tác trong test, nên trúng rất hiếm. Với ViFoodRec, ước tính thô của nhóm cho thấy chọn ngẫu nhiên đã đạt khoảng 1.8% (mỗi user ~50 món phù hợp trên ~2,800 món chưa xem), nên P@10 0.0139–0.0158 chỉ cùng bậc với ngẫu nhiên. Đây là ước tính, nhóm chưa đo baseline ngẫu nhiên.

**12. RMSE Food.com 0.62–0.67 có nghĩa là mô hình tốt không?**
Không. 78.40% đánh giá là 5 sao và điểm TB là 4.71, nên chỉ cần luôn đoán 4.71 đã có RMSE 0.6266. Cần nhìn RMSE theo từng mức điểm: Global Mean sai 3.71 sao khi người dùng chấm 1 sao (`baseline_rmse_breakdown.csv`), ALS sai 3.01. Con số tổng thể đẹp vì lớp 5 sao áp đảo.

**13. Dữ liệu ViFoodRec chỉ có 101 người dùng và điểm phân phối đều. Có đáng tin để đánh giá hệ gợi ý không?**
Chỉ nên dùng thận trọng. Ma trận dày (độ thưa 63.01%, mỗi user trung vị 1,469 đánh giá) và 9 mức điểm còn lại mỗi mức chiếm 10.99–11.28% (`eda_12`, `eda_01_vifoodrec_rating_dist.csv`). Với dữ liệu như vậy, mô hình đoán hằng số 3.0 gần như tối ưu, nên kết quả đo trên bộ này không phân biệt được các mô hình. Bộ này phù hợp để demo ứng dụng món Việt hơn là để chứng minh chất lượng mô hình. Food.com là bộ để đánh giá quy mô và hành vi.

**14. Gợi ý cho người dùng mới (cold-start) trên dashboard hoạt động thế nào, và đã đánh giá chưa?**
Người dùng chọn vài món yêu thích, hệ thống cộng điểm cosine với các món lân cận (`item_neighbors`, tính từ item factor của ALS), loại món đã chọn và sắp xếp. Mới được kiểm thử bằng 4 ca (3 bộ món ViFoodRec và 1 bộ Food.com) trong `test_app_log.txt`, **chưa có đánh giá định lượng** (không có P@K cho chế độ này). Vì mô hình ALS gốc không thắng baseline nên chất lượng item factor chưa được chứng minh.

**15. Kết quả của nhóm so với bài báo ViFoodRec ra sao?**
Bài báo (PACLIC 2024, Bảng 5, đối chiếu từ `scratch/paclic_paper_text.txt`) báo RMSE 2.0635–2.5543 cho CF dựa trên lân cận; ALS của nhóm đạt 1.3832, nhỏ hơn khoảng 33%. Nhưng **không so sánh trực tiếp được**: bài báo đo trên 200 điểm test (tỉ lệ 1:900), nhóm đo trên 15,080 điểm sau khi bỏ các điểm 0.0 và 0.5. Đáng lưu ý hơn: baseline Global Mean của nhóm còn tốt hơn ALS (1.2866 so với 1.3832), nên "vượt bài báo" phần lớn do giao thức đo và dữ liệu khác nhau, không do ALS giỏi.
